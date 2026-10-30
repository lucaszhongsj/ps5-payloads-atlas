#!/usr/bin/env python3
"""Aggregate PS5 payload catalogue into payloads.json.

Three-layer composition, all read-only against upstream:
  1. Discovery: `itsPLK/ps5-payloads-mirror` catalog and
     `phantomptr/ps5upload` CATALOGUE both supply upstream repo URLs.
     The mirror's `payloads_v2.json` (object wrapper plus `icons_url`)
     is the only shape consumed here.
  2. Curation: `sources.json` overrides display name / description / asset
     selection per repo, and can `"exclude": true` to suppress one.
  3. Enrichment: `phantomptr/ps5upload` CATALOGUE provides longer
     descriptions / display names where available; the mirror supplies
     category and `icon_key` for the repos it already curates.

Design rules:
- A repo is identified by its full HTML URL string (e.g.
  `https://github.com/owner/repo`). All maps are keyed by the lowercased URL.
- The API response is the source of truth. Nothing is reassembled from
  parsed fragments — `version`, `published_at`, asset `name` /
  `browser_download_url` / `digest`, and the canonical repo URL (via
  `release.html_url`) all come straight from the JSON the API returns.
- No binaries are downloaded. GitHub checksums come from the asset `digest`
  field. Forgejo / missing-digest assets get an empty checksum.
- `/releases/latest` 404 → fall back to `/releases[0]` for pre-release-only
  repos.
- `id` starts as the manager's own slug of `name` (so existing installs keep
their slots) and is then pinned across runs, so a later display-name edit no
longer orphans anything. Collisions get a numeric suffix.
- `last_update` is ISO 8601 with offset, the format the manager's version
  tie-breaker can parse.
- Icons are content-addressed data URIs: inherited from the mirror when it has
  the repo, generated from the owner avatar otherwise, and reused across runs.
"""

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "payloads.json"
ICONS_FILE = "icons.json"
README_FILE = "README.md"
ITSPLK_CATALOG_URL = (
    "https://raw.githubusercontent.com/itsPLK/ps5-payloads-mirror/main/payloads_v2.json"
)
# Icon data URIs the manager accepts: base64 PNG/JPEG/SVG, bounded per entry.
ICON_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/svg+xml;base64,",
)
ICON_MAX_LEN = 12288
PS5UPLOAD_CATALOGUE_URL = (
    "https://raw.githubusercontent.com/phantomptr/ps5upload/main/"
    "client/src-tauri/src/commands/payloads.rs"
)
CATALOGUE_NAME = "lucaszhongsj/ps5-payloads-atlas"
GH_API_ATTEMPTS = 3  # GitHub 偶发 TLS EOF，单次失败会让该条目整轮缺席
CST = timezone(timedelta(hours=8))  # UTC+8 / 东八区


# ─── URL helpers ─────────────────────────────────────────────────────
def normalize_repo_url(url: str) -> str:
    """Lowercase a repo HTML URL for use as a map key. Trims trailing slash and .git."""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower()


def parse_repo_url(url: str):
    """Extract (host, owner, repo) from a repo HTML URL for API calls."""
    m = re.search(r"https?://([^/]+)/([^/]+)/([^/?#]+)", url or "")
    if not m:
        return None
    host, owner, repo = m.groups()
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return host, owner, repo


def format_last_update(iso_str: str) -> str:
    """Upstream UTC timestamp → ISO 8601 in UTC+8 ('2026-10-22T04:55:47+08:00').

    The manager parses `last_update` as a date for version tie-breaking; a
    non-ISO string silently degrades that to lexicographic comparison.
    """
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return iso_str


# ─── HTTP / API ──────────────────────────────────────────────────────
def http_get(url: str, timeout: int = 30) -> str:
    return http_get_bytes(url, timeout).decode("utf-8")


def http_get_bytes(url: str, timeout: int = 30, attempts: int = 3) -> bytes:
    """GET with retries. HTTP status errors are answers, not transport blips."""
    req = urllib.request.Request(url, headers={"User-Agent": "ps5-payloads-atlas/1.0"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError:
            raise
        except Exception:
            if attempt == attempts:
                raise
    raise RuntimeError(f"unreachable: {url}")


def atomic_write_json(path: str, document: dict) -> None:
    """Write via a sibling temp file so a crash never truncates a valid catalog."""
    fd, temporary = tempfile.mkstemp(prefix=path + ".", dir=".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def gh_api(endpoint: str):
    """Call gh api with retries: a transport blip must not drop a payload.

    HTTP 404 is a real answer (repo renamed or gone) and is not retried.
    """
    for attempt in range(1, GH_API_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ["gh", "api", endpoint], capture_output=True, text=True, check=True
            )
            return json.loads(result.stdout) if result.stdout.strip() else None
        except Exception as e:
            if "HTTP 404" in str(e) or attempt == GH_API_ATTEMPTS:
                print(f"  gh api {endpoint} failed: {e}")
                return None
            print(f"  gh api {endpoint} transport error, retrying: {e}")
            time.sleep(2)
    return None


def forgejo_api(host: str, endpoint: str):
    try:
        return json.loads(http_get(f"https://{host}/api/v1/{endpoint}"))
    except Exception as e:
        print(f"  forgejo {host}/{endpoint} failed: {e}")
        return None


def get_latest_release(repo_url: str) -> dict | None:
    """Fetch latest release (with pre-release fallback) for a repo URL."""
    info = parse_repo_url(repo_url)
    if not info:
        return None
    host, owner, repo = info
    if host == "github.com":
        release = gh_api(f"repos/{owner}/{repo}/releases/latest")
        if release:
            return release
        releases = gh_api(f"repos/{owner}/{repo}/releases?per_page=1") or []
        return releases[0] if releases else None
    release = forgejo_api(host, f"repos/{owner}/{repo}/releases/latest")
    if release and isinstance(release, dict):
        return release
    releases = forgejo_api(host, f"repos/{owner}/{repo}/releases?limit=1") or []
    return releases[0] if releases else None


def repo_url_from_release(release: dict) -> str:
    """`https://github.com/o/r/releases/tag/v1` → `https://github.com/o/r` (lowercased).

    Matches the full `/releases/tag/` anchor so owners/repos whose names contain
    'releases' (e.g. `releases-app/foo`) are not mis-truncated.
    """
    html_url = release.get("html_url") or ""
    m = re.search(r"^(.*?)/releases/tag/", html_url)
    return m.group(1).lower() if m else ""


# ─── Asset selection ─────────────────────────────────────────────────
def pick_asset(assets: list, asset_pattern: str, repo_url: str) -> dict | None:
    """Select the canonical payload asset by explicit priority (no magic numbers).

    Keep only .elf/.bin → if asset_pattern given, narrow to matches (with a
    warning + fallback to unfiltered if the pattern matches nothing) → prefer
    .elf over .bin, non-ps4 over ps4, shorter filename over longer.
    """
    candidates = [a for a in assets if a["name"].endswith((".elf", ".bin"))]
    if not candidates:
        return None
    if asset_pattern:
        matched = [a for a in candidates if re.search(asset_pattern, a["name"], re.IGNORECASE)]
        if not matched:
            print(f"  warning: asset_pattern {asset_pattern!r} matched no asset for {repo_url}; falling back")
        else:
            candidates = matched
    return min(
        candidates,
        key=lambda a: (
            "ps4" in a["name"].lower(),                # avoid ps4 builds first (PS5 catalogue)
            0 if a["name"].endswith(".elf") else 1,   # then prefer .elf over .bin
            len(a["name"]),                            # then shorter canonical name
        ),
    )


def get_checksum(asset: dict) -> str:
    """SHA-256 hex from the asset's `digest` field ('sha256:...' on GitHub; absent on Forgejo).

    The manager rejects an entry whose non-empty checksum is not 64 hex digits,
    so a malformed digest degrades to an empty (optional) checksum instead.
    """
    digest = asset.get("digest") or ""
    value = digest.split(":", 1)[1] if digest.startswith("sha256:") else ""
    return value.lower() if re.fullmatch(r"[0-9a-fA-F]{64}", value) else ""


def normalize_version(tag: str, repo_url: str) -> str:
    """Strip a leading project-name prefix from the tag (e.g. 'file-explorer-v0.2.1' → 'v0.2.1').

    Only strips when the prefix is followed by 'v<digit>.', i.e. '<words>-v1.2.3'.
    Bare-digit tags ('1.2.3', 'beta-1.2', 'nightly-20250901') and already-clean
    'v…' tags pass through untouched. The client treats `version` as display-only.
    """
    m = re.match(r"^[a-z][a-z0-9-]*-(?=v\d+\.)", tag, re.IGNORECASE)
    return tag[m.end():] if m else tag


# ─── 分类 ───────────────────────────────────────────────────────────
# 词表与上游 itsPLK/ps5-payloads-mirror 的 4 类保持一致，避免两套分类并存：
# Loaders（ELF 装载器）/ System & Jailbreak（越狱与内核）/
# Networking & Servers（FTP、HTTP、Shell 等网络服务）/ Utilities & Tools（其余）。
# 上游已收录的条目直接沿用其 category；本地独有的条目按下面的规则派生。
# 判据分两档：设备类别（装载器 / 越狱内核）只看名称——描述里的“jailbroken”、
# “ELF loader”会把普通工具误判进去；服务类别才看名称 + 描述。
# 无 Misc 兜底，未命中即 Utilities & Tools。
NAME_CATEGORY_RULES = [
    (r"elfldr|loader|autoload", "Loaders"),
    (r"kernel|kstuff|jailbreak|\bjb\b|\b(?:onion|eta)?hen\b|exploit|fself|npdrm|lapy",
     "System & Jailbreak"),
]
TEXT_CATEGORY_RULES = [
    (r"\bftps?\b|ftpsrv|zftpd|\bhttps?\b|telnet|\bdns\b|klog|\bshell\b|websrv|upload|tailscale|\bgdb\b",
     "Networking & Servers"),
]
DEFAULT_CATEGORY = "Utilities & Tools"


def derive_category(name: str, description: str) -> str:
    lowered_name = name.lower()
    for pattern, category in NAME_CATEGORY_RULES:
        if re.search(pattern, lowered_name):
            return category
    text = f"{name} {description}".lower()
    for pattern, category in TEXT_CATEGORY_RULES:
        if re.search(pattern, text):
            return category
    return DEFAULT_CATEGORY


# ─── Discovery: itsPLK catalog ───────────────────────────────────────
def fetch_itsplk_discovery() -> tuple[dict, dict]:
    """Return ({repo_url_lower: entry}, {icon_key: data_uri}).

    Reads the mirror's `payloads_v2.json` only: the object wrapper is the
    documented format and the sole shape that can carry `icons_url`.
    """
    try:
        document = json.loads(http_get(ITSPLK_CATALOG_URL, timeout=30))
    except Exception as e:
        print(f"itsPLK discovery fetch failed (continuing from sources.json only): {e}")
        return {}, {}
    entries = document.get("payloads") if isinstance(document, dict) else None
    if not isinstance(entries, list) or not entries:
        print("itsPLK catalogue has no payloads array (continuing from sources.json only)")
        return {}, {}

    icons_url = document.get("icons_url") or ""
    icons = fetch_icon_catalog(urljoin(ITSPLK_CATALOG_URL, icons_url) if icons_url else "")

    discovered = {}
    for p in entries:
        repo_url = p.get("source", "")
        info = parse_repo_url(repo_url)
        if not info:
            continue
        # `source` in itsPLK points at .../releases; trim to the repo root URL.
        # Anchored regex avoids mis-truncation when owner/repo names contain
        # 'releases' (e.g. releases-app/foo/releases).
        m = re.search(r"^(.*?)/releases(?:/|$)", repo_url)
        repo_url = (m.group(1) if m else repo_url).rstrip("/")
        discovered[normalize_repo_url(repo_url)] = {
            "repo_url": repo_url,
            "display_name": p.get("name"),
            "description": p.get("description") or "",
            "asset_pattern": p.get("asset_pattern") or "",
            "category": p.get("category") or "",
            "icon_key": p.get("icon_key") or "",
        }
    print(f"itsPLK discovery loaded: {len(discovered)} repos, {len(icons)} icons")
    return discovered, icons


# ─── Icons ───────────────────────────────────────────────────────────
def is_icon_uri(data) -> bool:
    return (
        isinstance(data, str)
        and data.startswith(ICON_PREFIXES)
        and len(data) <= ICON_MAX_LEN
    )


def icon_key(data_uri: str) -> str:
    """Content-addressed key, same scheme as the mirror's catalog.py."""
    return hashlib.sha256(data_uri.encode("ascii")).hexdigest()


def fetch_icon_catalog(url: str) -> dict:
    """Load the separately published icon map. Best effort, never fatal."""
    if not url:
        return {}
    try:
        data = json.loads(http_get(url, timeout=30))
    except Exception as e:
        print(f"icon catalogue fetch failed ({url}): {e}")
        return {}
    icons = data.get("icons") if isinstance(data, dict) else None
    return {k: v for k, v in (icons or {}).items() if is_icon_uri(v)}


def resolve_avatar_url(host: str, owner: str) -> str:
    """Owner avatar for a repo host: GitHub by profile PNG, Forgejo via its API."""
    if host == "github.com":
        return f"https://github.com/{owner}.png"
    profile = forgejo_api(host, f"users/{owner}")
    return (profile or {}).get("avatar_url") or ""


def encode_icon_uri(raw: bytes) -> str:
    """Downscale an avatar into a bounded PNG data URI the PS5 WebKit renders.

    PNG only: the manager rejects WebP, and 128 px avatars stay far below the
    12 KiB budget after quantization.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("  pillow is not installed; skipping generated icons")
        return ""
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    except Exception as e:
        print(f"  avatar decode failed: {e}")
        return ""
    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA" if has_alpha else "RGB")
    for dim in (128, 96, 64, 48):
        thumb = image.copy()
        thumb.thumbnail((dim, dim), Image.LANCZOS)
        variants = [thumb]
        if has_alpha:
            variants += [
                thumb.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
                for colors in (128, 64)
            ]
        for variant in variants:
            buffer = io.BytesIO()
            variant.save(buffer, format="PNG", optimize=True)
            uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
            if len(uri) <= ICON_MAX_LEN:
                return uri
    return ""


def load_previous_state() -> tuple[dict, dict]:
    """Return ({source: id}, {id: data_uri}) from the last run.

    Ids are reused so a display-name edit does not orphan installed slots;
    icons are reused so steady state needs no image downloads.
    """
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}, {}
    try:
        with open(ICONS_FILE, encoding="utf-8") as f:
            cached = json.load(f).get("icons") or {}
    except (OSError, json.JSONDecodeError):
        cached = {}
    entries = previous.get("payloads", [])
    ids = {p["source"]: p["id"] for p in entries if p.get("source") and p.get("id")}
    icons = {
        p["id"]: cached[p["icon_key"]]
        for p in entries
        if p.get("id") and p.get("icon_key") in cached
    }
    return ids, icons


def build_icon(item: dict, entry: dict, upstream_icons: dict, cached: dict) -> str:
    """Prefer the mirror's icon, then the previous run's, then the owner avatar."""
    if entry.get("icon_key") in upstream_icons:
        return upstream_icons[entry["icon_key"]]
    if item["id"] in cached:
        return cached[item["id"]]
    info = parse_repo_url(item["source"])
    if not info:
        return ""
    host, owner, _ = info
    avatar = resolve_avatar_url(host, owner)
    if not avatar:
        return ""
    print(f"  generating icon for {item['id']} from {owner}@{host}")
    try:
        return encode_icon_uri(http_get_bytes(avatar))
    except Exception as e:
        print(f"  avatar fetch failed for {owner}@{host}: {e}")
        return ""


# ─── Enrichment + discovery: ps5upload CATALOGUE ────────────────────
def strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def extract_catalogue_block(text: str) -> str:
    marker = "const CATALOGUE: &[CatalogueEntry] = &["
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    struct_depth = 0
    array_depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                struct_depth += 1
            elif ch == "}":
                struct_depth -= 1
            elif ch == "[":
                if struct_depth == 0:
                    array_depth += 1
            elif ch == "]":
                if struct_depth == 0:
                    if array_depth == 0:
                        return text[start:i]
                    array_depth -= 1
    return ""


def split_catalogue_entries(block: str) -> list[str]:
    entries = []
    for m in re.finditer(r"CatalogueEntry\s*\{", block):
        s = m.start()
        depth = 0
        in_str = False
        escape = False
        for i, ch in enumerate(block[s:], s):
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        entries.append(block[s : i + 1])
                        break
    return entries


def parse_catalogue_str(entry: str, key: str) -> str | None:
    """Read a Rust string literal value for `key`. Handles `\\\"` escapes so
    descriptions containing escaped quotes are not truncated."""
    m = re.search(rf'\b{re.escape(key)}\s*:\s*"((?:\\.|[^"\\])*)"', entry)
    if not m:
        return None
    raw = m.group(1)
    # Unescape the Rust escapes we are likely to see in catalogue strings.
    return raw.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def fetch_ps5upload_catalogue() -> dict:
    """Return {repo_url_lower: {repo_url, display_name, description, asset_name_hint}}.

    ps5upload CATALOGUE is used both for discovery and for enrichment.
    """
    try:
        raw = strip_block_comments(http_get(PS5UPLOAD_CATALOGUE_URL, timeout=30))
    except Exception as e:
        print(f"ps5upload catalogue fetch failed (continuing without it): {e}")
        return {}
    block = extract_catalogue_block(raw)
    if not block:
        print("ps5upload CATALOGUE block not found; skipping")
        return {}
    catalogue = {}
    for entry_text in split_catalogue_entries(block):
        host = parse_catalogue_str(entry_text, "repo_host")
        owner = parse_catalogue_str(entry_text, "repo_owner")
        repo = parse_catalogue_str(entry_text, "repo_name")
        if not (host and owner and repo):
            continue
        repo_url = f"https://{host}/{owner}/{repo}"
        catalogue[normalize_repo_url(repo_url)] = {
            "repo_url": repo_url,
            "display_name": parse_catalogue_str(entry_text, "display_name"),
            "description": parse_catalogue_str(entry_text, "description"),
            "asset_name_hint": parse_catalogue_str(entry_text, "asset_name_hint") or "",
        }
    print(f"ps5upload catalogue loaded: {len(catalogue)} entries")
    return catalogue


# ─── Stable ids ──────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """Slug identical to the manager's slot_slug, so ids match its default.

    Emitting the same value explicitly means future display-name edits keep
    every installed slot mapped instead of orphaning favourites.
    """
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in ("_", "."):
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    slug = "".join(out).strip("-._")
    return slug or "payload"


def assign_ids(items: list[dict], pinned: dict) -> None:
    """Fill each entry's id placeholder with a unique [a-z0-9._-] slug.

    The previous run's id wins for the same repo, so renaming a payload keeps
    its slot; fresh entries slugify their name and take name-2, name-3 on clash.
    """
    used = set()
    for item in items:
        candidate = pinned.get(item["source"])
        if candidate and candidate not in used:
            item["id"] = candidate
            used.add(candidate)
    for item in items:
        if item["id"]:
            continue
        base = slugify(item["name"])[:120]
        candidate, suffix = base, 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        item["id"] = candidate
        used.add(candidate)


# ─── Item builder ────────────────────────────────────────────────────
def build_item(repo_url: str, override: dict, asset_hint: str) -> tuple[dict, str] | None:
    """Fetch release, pick asset, emit schema item. Returns (item, canon_url) or None."""
    if not parse_repo_url(repo_url):
        return None
    asset_pattern = override.get("asset_pattern") or asset_hint or ""

    print(f"Checking {repo_url}...")
    release = get_latest_release(repo_url)
    if not release:
        print("  no release found, skipping")
        return None

    assets = release.get("assets", [])
    if not assets:
        print(f"  no assets in release {release.get('tag_name')}, skipping")
        return None

    selected = pick_asset(assets, asset_pattern, repo_url)
    if not selected:
        print("  no suitable asset, skipping")
        return None

    display_name = override.get("display_name") or repo_url.rstrip("/").split("/")[-1]
    description = override.get("description") or ""
    # 上游已收录的条目沿用其人工分类，本地独有条目才按规则派生。
    category = override.get("category") or derive_category(display_name, description)

    canon = repo_url_from_release(release) or normalize_repo_url(repo_url)
    item = {
        # 占位：id 在全集排序后由 assign_ids 填入，靠前的位置保证输出顺序稳定。
        "id": "",
        "name": display_name,
        "filename": selected["name"],
        "url": selected["browser_download_url"],
        # Source = repo root URL, straight from release.html_url (no concat).
        "source": canon,
        "description": description,
        "version": normalize_version(release.get("tag_name", ""), repo_url),
        "category": category,
        "checksum": get_checksum(selected),
        "last_update": format_last_update(release.get("published_at") or ""),
    }
    print(f"  → {selected['name']} @ {release.get('tag_name')} ({category})")
    return item, canon


# ─── README ──────────────────────────────────────────────────────────
def update_readme(payloads: list[dict]) -> None:
    rows = [
        "| Name | Version | Category | Description | Last Updated | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in payloads:
        description = (p.get("description") or "No description provided.").replace("|", "\\|")
        source_url = p.get("source", "")
        m = re.search(r"https?://[^/]+/([^/]+)/([^/]+)", source_url)
        source_label = f"{m.group(1)}/{m.group(2)}" if m else "Source"
        # ISO 8601 全量时间保留在 JSON 里，README 只展示日期。
        last_update = (p.get("last_update") or "-").split("T")[0]
        rows.append(
            f"| **{p.get('name','')}** | `{p.get('version','')}` | {p.get('category','')} | "
            f"{description} | `{last_update}` | [{source_label}]({source_url}) |"
        )
    table = "\n".join(rows)
    start, end = "<!-- PAYLOADS_START -->", "<!-- PAYLOADS_END -->"
    if not Path(README_FILE).exists():
        return
    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if start in content and end in content:
        pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
        new_content = pattern.sub(f"{start}\n{table}\n{end}", content)
        if new_content == content:
            return  # no change, skip write
        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {README_FILE}")


# ─── Main ────────────────────────────────────────────────────────────
def main() -> None:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} curated entries from {SOURCES_FILE}")

    discovery, upstream_icons = fetch_itsplk_discovery()
    ps5upload = fetch_ps5upload_catalogue()
    previous_ids, cached_icons = load_previous_state()

    # Curation: overrides keyed by lowercased repo URL; `exclude` read from the entry directly.
    overrides = {}
    for src in sources:
        repo_url = src.get("url") or src.get("source", "")
        if not repo_url:
            print(f"warning: sources.json entry without url/source, skipped: {src}")
            continue
        if not parse_repo_url(repo_url):
            print(f"warning: sources.json entry has unparseable url {repo_url!r}, skipped")
            continue
        key = normalize_repo_url(repo_url)
        if key in overrides:
            print(f"warning: duplicate sources.json entry for {repo_url}; last one wins")
        overrides[key] = {**src, "repo_url": repo_url}

    # Union: curated overrides + itsPLK discovery + ps5upload catalogue
    seen = set(overrides.keys())
    all_keys = list(overrides.keys())
    for k in list(discovery.keys()) + list(ps5upload.keys()):
        if k not in seen:
            all_keys.append(k)
            seen.add(k)

    final_items = []
    canon_seen = set()
    n_excluded = 0
    n_deduped = 0
    skipped = []

    for key in all_keys:
        if overrides.get(key, {}).get("exclude"):
            print(f"Excluded by sources.json: {overrides[key].get('repo_url', key)}")
            n_excluded += 1
            continue

        src_override = overrides.get(key, {})
        disc = discovery.get(key, {})
        psu = ps5upload.get(key, {})

        repo_url = (
            src_override.get("repo_url")
            or disc.get("repo_url")
            or psu.get("repo_url")
        )
        if not repo_url:
            continue

        # Merged override with priority: sources.json > ps5upload > itsPLK.
        # `display_name`/`description`/`asset_pattern`/`category` come from this
        # merge; `asset_hint` (ps5upload's asset_name_hint) is threaded separately
        # because itsPLK/sources.json use `asset_pattern`, not `asset_name_hint`.
        override = {}
        for field in ("display_name", "description", "asset_pattern", "category"):
            for src_data in (src_override, psu, disc):
                val = src_data.get(field)
                if val:
                    override[field] = val
                    break

        result = build_item(repo_url, override, psu.get("asset_name_hint") or "")
        if not result:
            skipped.append(repo_url)
            continue

        item, canon = result
        if canon in canon_seen:
            print(f"  dedup: {repo_url} folds into {canon}, already listed")
            n_deduped += 1
            continue
        canon_seen.add(canon)
        final_items.append(item)

    # 排序后再分配 id：(name, source) 排序确定，冲突消歧才能稳定复现。
    final_items.sort(key=lambda p: (p.get("name", "").lower(), p.get("source", "")))
    assign_ids(final_items, previous_ids)

    # 图标：上游提供的整套继承，本地独有条目用 owner 头像生成，跨轮次缓存。
    icons = {}
    for item in final_items:
        entry = discovery.get(normalize_repo_url(item["source"]), {})
        data_uri = build_icon(item, entry, upstream_icons, cached_icons)
        if data_uri:
            item["icon_key"] = icon_key(data_uri)
            icons[item["icon_key"]] = data_uri

    # 护栏：条目数较上一次骤降 >20% 视为上游大面积失效，拒绝写盘并退出非零，
    # 防止残缺目录被 Action 自动 commit 部署。
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            prev_count = len(json.load(f).get("payloads", []))
    except (OSError, json.JSONDecodeError):
        prev_count = 0
    if prev_count and len(final_items) < prev_count * 0.8:
        print(
            f"error: payload count dropped from {prev_count} to {len(final_items)} "
            f"(>20% drop); aborting to avoid publishing a broken catalogue",
            file=sys.stderr,
        )
        sys.exit(1)

    document = {"name": CATALOGUE_NAME, "payloads": final_items}
    if icons:
        # 对象包装才能声明 icons_url；裸数组源不允许图标。
        document["icons_url"] = ICONS_FILE
    # skipped 区块：让"投了 sources.json 但没产出"的源在输出里可见。
    # 注意：skipped 条目只含 url/reason，绝不能含 name+filename+url 三件套——
    # ps5-payload-manager 的解析器会把任何带三件套的 {…} 对象误收进可安装列表。
    if skipped:
        document["skipped"] = [
            {"url": u, "reason": "no release with .elf/.bin asset, or repo unreachable"}
            for u in sorted(skipped)
        ]
    atomic_write_json(OUTPUT_FILE, document)
    if icons:
        atomic_write_json(ICONS_FILE, {"icons": dict(sorted(icons.items()))})
    print(
        f"\nWrote {OUTPUT_FILE}: {len(final_items)} listed, "
        f"{n_excluded} excluded, {n_deduped} deduped, {len(skipped)} skipped, "
        f"{len(icons)} icons"
    )
    if skipped:
        print(f"Skipped: {', '.join(skipped)}")

    update_readme(final_items)


if __name__ == "__main__":
    main()
