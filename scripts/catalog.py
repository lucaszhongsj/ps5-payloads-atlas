"""The catalogue pipeline — one module, sections in pipeline order.

    identity → transport → harvest → sources → collect → releases → build → render → site

    sources/ contracts + mirror snapshots
        |  collect             refresh the mirror snapshots  (network)
        v
    slots                   merge into one opinion per repo (pure)
        |  observe            watch each repo's latest release (network)
        v
    build                   shape into the client catalogue  (pure)
        |  write_readme      the README page                 (pure)
        v
    payloads.json / README.md / _site

Every path is derived from one `Settings`, and nothing reads a module-level
constant. That is the whole point: a test can point `root` at a temp directory
and run the pipeline end to end without touching the checkout, and without a
network.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

CATALOGUE_NAME = "lucaszhongsj/ps5-payloads-atlas"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


# ─── Settings ────────────────────────────────────────────────────────
# Every path the pipeline touches, derived from a single `root` — the seam
# that lets a test point the whole pipeline at a temp directory.

@dataclass(frozen=True)
class Settings:
    """Every path the pipeline touches, derived from a single `root`."""

    root: Path = DEFAULT_ROOT

    @property
    def mirror_file(self) -> Path:
        """Where each mirror copies from — the manifest beside the snapshots it drives."""
        return self.sources_dir / "mirror" / "mirror.toml"

    @property
    def sources_dir(self) -> Path:
        return self.root / "sources"

    @property
    def facts_file(self) -> Path:
        """The observation artifact: what upstream said, before any shaping."""
        return self.root / "build" / "releases.json"

    @property
    def catalogue_file(self) -> Path:
        return self.root / "payloads.json"

    @property
    def readme_file(self) -> Path:
        return self.root / "README.md"

    @property
    def site_dir(self) -> Path:
        return self.root / "_site"


# ─── URL identity ────────────────────────────────────────────────────
# What counts as the same repository is defined here and nowhere else.
# Discovery, merging, dedupe and the API path all call these functions; a
# second copy is how a catalogue ends up listing one repo twice.

# https://host/owner/repo — the only shape we treat as an address, and the shape
# the collector scans documents for.
REPO_URL = re.compile(r"https?://([\w.-]+)/([\w.-]+)/([\w.-]+)")
# `github:owner/repo` shorthand, used by link source_layers.
REPO_SHORT = re.compile(r"\b(github|codeberg|git):([\w.-]+)/([\w.-]+)")
SHORT_HOSTS = {"github": "github.com", "codeberg": "codeberg.org", "git": "github.com"}
# Documentation examples look like real repos; they are not.
PLACEHOLDER_OWNERS = {"me", "owner", "user", "username", "example", "your-org", "org", "you"}
# Hosts that serve files about a repo rather than being the repo.
NON_REPO_HOSTS = {"api.github.com", "raw.githubusercontent.com", "codeload.github.com"}
# A "repo" that ends in one of these is a document someone linked.
NON_REPO_SUFFIXES = (".json", ".txt", ".md", ".rs")


def canonical(host: str, owner: str, repo: str) -> str | None:
    """`host/owner/repo` → `https://host/owner/repo`, or None if it is not one."""
    if host in NON_REPO_HOSTS or "." not in host or owner.lower() in PLACEHOLDER_OWNERS:
        return None
    repo = repo.split("#")[0].split("?")[0]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not repo or repo.endswith(NON_REPO_SUFFIXES):
        return None
    return f"https://{host}/{owner}/{repo}".lower()


def normalize_repo_url(url: str) -> str:
    """Lowercase a repo HTML URL for use as a map key. Trims trailing slash and .git."""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower()


def parse_repo_url(url: str):
    """Extract (host, owner, repo) from a repo HTML URL, for API calls."""
    match = re.search(r"https?://([^/]+)/([^/]+)/([^/?#]+)", url or "")
    if not match:
        return None
    host, owner, repo = match.groups()
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return host, owner, repo


# ─── transport ───────────────────────────────────────────────────────
# The only section that talks network: retries classify failures instead of
# retrying everything, and writes land atomically.

GH_API_ATTEMPTS = 3  # GitHub hits TLS EOF now and then; one failure would drop the entry for a whole run
FETCH_WORKERS = 8    # fetching is pure network wait; serially a refresh would stretch into tens of minutes
# a publishable checksum is exactly 64 hex digits; build and the release section share this one test.
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def http_get(url: str, timeout: int = 30, attempts: int = 3) -> str:
    """GET with retries. Transport errors and 5xx are blips; 4xx are answers."""
    request = urllib.request.Request(url, headers={"User-Agent": "ps5-payloads-atlas/1.0"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == attempts:
                raise
        except Exception:
            if attempt == attempts:
                raise
    raise AssertionError("unreachable")


def gh_api(endpoint: str):
    """Call `gh api`, classifying the failure instead of retrying everything.

    `gh` reports the HTTP status in stderr, not in the exception, so the
    classification has to read stderr — otherwise every 404 gets retried as if
    it were a network glitch. A rate limit is not one entry's problem: it aborts
    the run rather than quietly publishing a catalogue with holes.
    """
    for attempt in range(1, GH_API_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ["gh", "api", endpoint], capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            # a subprocess without a timeout hangs the whole task on a black-hole connection.
            if attempt == GH_API_ATTEMPTS:
                print(f"  gh api {endpoint} timed out; treating as unreachable")
                return None
            print(f"  gh api {endpoint} timed out, retrying")
            time.sleep(2)
            continue
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else None
        error = (result.stderr or result.stdout or "").strip().splitlines()
        error = error[0] if error else f"exit status {result.returncode}"
        if "HTTP 404" in error or "HTTP 410" in error:
            print(f"  gh api {endpoint}: not found")
            return None
        if "rate limit" in error.lower() or "HTTP 429" in error:
            sys.exit(f"error: GitHub rate limit hit at {endpoint} ({error}); "
                     "refusing to publish a catalogue with silently missing entries")
        if attempt == GH_API_ATTEMPTS:
            print(f"  gh api {endpoint} failed after {attempt} attempts: {error}")
            return None
        print(f"  gh api {endpoint} transport error, retrying: {error}")
        time.sleep(2)
    return None


def forgejo_api(host: str, endpoint: str):
    """Forgejo/Gitea speaks a compatible API; failures degrade to None."""
    try:
        return json.loads(http_get(f"https://{host}/api/v1/{endpoint}"))
    except Exception as e:
        print(f"  forgejo {host}/{endpoint} failed: {e}")
        return None


def render_markdown(text: str, token: str) -> str:
    """GitHub renders GFM for us, so the page matches the repository exactly."""
    request = urllib.request.Request(
        "https://api.github.com/markdown",
        data=json.dumps({"text": text, "mode": "gfm"}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    return urllib.request.urlopen(request, timeout=30).read().decode("utf-8")


def atomic_write_json(path, document) -> None:
    """Write via a sibling temp file so a crash never truncates a valid artifact."""
    path = str(path)
    fd, temporary = tempfile.mkstemp(prefix=os.path.basename(path) + ".",
                                     dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.chmod(temporary, 0o644)  # mkstemp defaults to 0600; published files must be readable
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


# ─── harvest: upstream documents → repo urls ─────────────────────────
# Three shapes, one rule: a document is either JSON with objects that name a
# repo (`source` / `url` / `homepage`), free text that mentions repos, or a
# link list that uses the `github:owner/repo` shorthand. The shape is
# discovered, never declared — which is why tracking another maintainer is one
# TOML table and no code.
#
# Only URLs come out of here. Names, descriptions and categories are
# deliberately not copied: they are observable from the repo itself, so
# transcribing them would create a second copy that goes stale.

def harvest_json(document) -> list[str]:
    """Every repository URL named by an object inside a JSON document."""
    items = document.get("payloads") if isinstance(document, dict) else document
    if not isinstance(items, list):
        items = [document]
    urls = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = item.get("source") or item.get("url") or item.get("homepage") or ""
        match = REPO_URL.search(str(raw))
        url = canonical(*match.groups()) if match else None
        if url:
            urls.append(url)
    return urls


def harvest_text(text: str) -> list[str]:
    """Every repository URL or `<host>:owner/repo` token in free text."""
    urls = []
    for host, owner, repo in REPO_URL.findall(text):
        url = canonical(host, owner, repo)
        if url:
            urls.append(url)
    for short, owner, repo in REPO_SHORT.findall(text):
        url = canonical(SHORT_HOSTS[short], owner, repo)
        if url:
            urls.append(url)
    return urls


def harvest(text: str) -> list[str]:
    """Deduplicated repository urls, in document order."""
    try:
        urls = harvest_json(json.loads(text))
    except json.JSONDecodeError:
        urls = harvest_text(text)
    if not urls:
        urls = harvest_text(text)
    return list(dict.fromkeys(urls))


# ─── sources: contracts ──────────────────────────────────────────────
# The repositories this catalogue is built from — data in JSON, opinions in
# TOML.
#
#     sources/manual/additional.json    repos nobody else source_layers       bare url array
#     sources/manual/manual.toml     corrections to a listed repo  url-keyed tables
#     sources/mirror/mirror.toml        the repo each mirror copies   url-keyed tables
#     sources/mirror/*.json             copies of upstream source_layers      bare url arrays
#
# `manual/` is everything a human writes; `mirror/` is everything collect
# writes — the directory is the write permission, so a mistyped name costs a
# snapshot at worst and can never reach a hand-maintained file. Within that,
# the format is the intent: a `.json` can only hold url strings, so additions
# and snapshots carry no opinions; every opinion lives in TOML, keyed by the
# identity it talks about.
#
# Layers merge in a fixed order — additional, then manual, then mirrors
# alphabetically. That is the only precedence the merge needs: curated answers
# before mirrored copies. A later source wins nothing an earlier one already
# answered, and `skip` is sticky — a repo a maintainer rejected cannot come
# back through someone else's list.

MANUAL = "manual"
MIRROR = "mirror"
ADDITIONAL = "additional"
# Role labels: the additional list is intake, the manual tables correct, snapshots are mirrors.
INTAKE = "intake"
CORRECTION = "correction"
# Keys allowed in manual.toml. Any other key (category, once) is a dead branch: zero uses in the data.
MANUAL_KEYS = ("asset_pattern", "skip")
# a mirror shedding many repos at once is almost always upstream truncation or a revamp, not a real purge.
SHRINK_RATIO = 0.7
SHRINK_FLOOR = 10


def _read_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as stream:
            return tomllib.load(stream)
    except OSError as e:
        sys.exit(f"error: cannot read {path}: {e}")
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"error: {path} is not valid TOML: {e}")


def _sort_key(url: str) -> tuple[str, str]:
    """Dictionary order for urls: case-insensitive, original text breaks ties."""
    return (url.lower(), url)


def _misordered(items: list[str]) -> tuple[str, str] | None:
    """First adjacent pair that violates dictionary order, if any."""
    for a, b in zip(items, items[1:]):
        if _sort_key(b) < _sort_key(a):
            return a, b
    return None


def read_urls(path: Path, check_order: bool = True) -> list[str]:
    """A bare array of repository urls — the only thing a sources/*.json can say.

    The array must be in dictionary order; the build refuses an unsorted file
    so the sources tree stays greppable and diffs stay honest. `collect` reads
    previous snapshots with the check off: it only needs a set, and it rewrites
    the file in order anyway.
    """
    if not path.exists():
        sys.exit(f"error: {path} is missing")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        sys.exit(f"error: cannot read {path}: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"error: {path} is not valid JSON: {e}")
    if not isinstance(document, list) or not all(isinstance(u, str) for u in document):
        sys.exit(f"error: {path} must be a bare array of url strings")
    if check_order:
        misordered = _misordered(document)
        if misordered:
            a, b = misordered
            sys.exit(f"error: {path}: urls are not in dictionary order; "
                     f"{b!r} belongs before {a!r}")
    return document


def read_manual(settings: Settings) -> list[dict]:
    """Corrections from manual.toml: `[{url, ...fields}]`, validated.

    The table key is the repository url — the identity the correction talks
    about — so a mistyped key fails loudly here instead of silently matching
    nothing. Duplicate tables are already a TOML error: the format checks
    identity uniqueness for free. `asset_pattern` must compile, `skip` must be
    exactly `true` — an exclusion carries no message; the reason is a comment.
    """
    path = settings.sources_dir / MANUAL / f"{MANUAL}.toml"
    if not path.exists():
        return []
    document = _read_toml(path)
    misordered = _misordered(list(document))
    if misordered:
        a, b = misordered
        sys.exit(f"error: {path}: tables are not in dictionary order; "
                 f"[{b}] belongs before [{a}]")
    entries = []
    for url, body in document.items():
        if not isinstance(body, dict):
            sys.exit(f"error: {path}: [{url}] must be a table of correction fields")
        unknown = sorted(set(body) - set(MANUAL_KEYS))
        if unknown:
            sys.exit(f"error: {path}: [{url}] has unknown field(s) {unknown}; "
                     f"allowed corrections are {', '.join(MANUAL_KEYS)}")
        if not body:
            sys.exit(f"error: {path}: [{url}] corrects nothing — "
                     f"an addition belongs in {ADDITIONAL}.json")
        if not parse_repo_url(url):
            sys.exit(f"error: {path}: [{url}] is not a repository url")
        pattern = body.get("asset_pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                sys.exit(f"error: {path}: [{url}] asset_pattern must be a regex string")
            try:
                re.compile(pattern)
            except re.error as e:
                sys.exit(f"error: {path}: [{url}] asset_pattern {pattern!r} "
                         f"is not a valid regex: {e}")
        if "skip" in body and body["skip"] is not True:
            sys.exit(f"error: {path}: [{url}] skip must be `true`; "
                     "the reason belongs in a comment above the table")
        entries.append({"url": url, **body})
    return entries


def read_mirror(settings: Settings) -> dict[str, str]:
    """`{snapshot name: upstream url}` — every mirror collect may refresh.

    The table key is the repository being mirrored — identity, the same schema
    as manual.toml — and `url` is where its list lives. The snapshot filename
    is derived, never declared: the repo in the key, lowercased, the same rule
    every other filename here follows.
    """
    path = settings.mirror_file
    if not path.exists():
        return {}
    document = _read_toml(path)
    misordered = _misordered(list(document))
    if misordered:
        a, b = misordered
        sys.exit(f"error: {path}: tables are not in dictionary order; "
                 f"[{b}] belongs before [{a}]")
    mirrors, files = {}, set()
    for repo_url, body in document.items():
        if not isinstance(body, dict):
            sys.exit(f"error: {path}: [{repo_url}] must be a table with a `url`")
        if not body.get("url"):
            sys.exit(f"error: {path}: {repo_url} needs a `url` to copy from")
        unknown = sorted(set(body) - {"url"})
        if unknown:
            sys.exit(f"error: {path}: [{repo_url}] has unknown field(s) {unknown}; "
                     "only `url` applies")
        parsed = parse_repo_url(repo_url)
        if not parsed or not canonical(*parsed):
            sys.exit(f"error: {path}: [{repo_url}] is not a repository url")
        name = parsed[2].lower()
        if name in files:
            sys.exit(f"error: {path}: two mirrors would both write {name}.json; keep one")
        files.add(name)
        mirrors[name] = body["url"]
    return mirrors


def source_layers(settings: Settings) -> list[dict]:
    """Every source in merge order: `[{name, role, entries}]`, already validated.

    Entries are normalized to `{"url": ...}` at this boundary so the merge never
    sees two shapes. A mirror declared in `mirror.toml` but never collected is
    reported — silence would look exactly like upstream listing nothing — and a
    file outside the manual contract is reported too, before it can be mistaken
    for data.
    """
    manual_dir = settings.sources_dir / MANUAL
    mirror_dir = settings.sources_dir / MIRROR
    layers = [
        {"name": ADDITIONAL, "role": INTAKE,
         "entries": [{"url": u} for u in read_urls(manual_dir / f"{ADDITIONAL}.json")]},
        {"name": MANUAL, "role": CORRECTION, "entries": read_manual(settings)},
    ]
    for path in sorted(mirror_dir.glob("*.json"), key=lambda p: p.name.lower()):
        layers.append({"name": path.stem, "role": MIRROR,
                       "entries": [{"url": u} for u in read_urls(path)]})
    for name in read_mirror(settings):
        if not (mirror_dir / f"{name.lower()}.json").exists():
            print(f"warning: mirror {name!r} has no snapshot yet; run collect first")
    for path in sorted(manual_dir.iterdir()):
        if path.name not in (f"{ADDITIONAL}.json", f"{MANUAL}.toml"):
            print(f"warning: {path.name} is not part of the manual contract "
                  f"({ADDITIONAL}.json, {MANUAL}.toml); ignored")
    return layers


# ─── collect: refresh the mirror snapshots ───────────────────────────

def collect(settings: Settings, force: bool = False) -> None:
    """Refresh every mirror in `sources/mirror/mirror.toml`. Nothing else is written.

    The directory is the permission: collect reads one manifest and writes one
    directory. The files under `manual/` are outside that world, and a snapshot
    is a bare url array — there is nothing in one to hand-edit.

    Two properties this deliberately does not have:

    - **No delete power.** A mirror dropped from the manifest leaves its file
      behind as an inert orphan, reported at the end. Discovery only reads what
      the role directories hold, so an orphan cannot leak into the catalogue.
    - **No opinion about upstream churn.** A fetch failure keeps the previous
      snapshot; a suspicious shrink refuses to overwrite unless `--force`.
    """
    mirrors = read_mirror(settings)
    mirror_dir = settings.sources_dir / MIRROR
    for name, url in sorted(mirrors.items(), key=lambda kv: kv[0].lower()):
        path = mirror_dir / f"{name.lower()}.json"
        previous = set(read_urls(path, check_order=False)) if path.exists() else set()
        print(f"Collecting {name}…")
        try:
            entries = harvest(http_get(url))
        except Exception as e:
            print(f"  fetch failed ({e}); keeping {len(previous)} previous repos")
            continue
        if not entries:
            print(f"  found no repositories in {url}; keeping previous repos")
            continue
        entries = sorted(entries, key=_sort_key)
        current = set(entries)
        if previous == current:
            print(f"  unchanged ({len(entries)} repos)")
            continue
        if len(previous) >= SHRINK_FLOOR and len(current) < len(previous) * SHRINK_RATIO and not force:
            print(f"  error: {name} shrank from {len(previous)} to {len(current)} repos "
                  f"(> {(1 - SHRINK_RATIO):.0%} drop); refusing to overwrite. "
                  "If upstream really deleted them, re-run with --force")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, entries)
        print(f"  wrote {len(entries)} repos")
        _report_drift(previous, current)

    known = {f"{name.lower()}.json" for name in mirrors}
    for path in sorted(mirror_dir.glob("*.json")):
        if path.name not in known:
            print(f"warning: {path.name} has no entry in mirror.toml; "
                  "ignored — delete it if obsolete")


def _report_drift(previous: set[str], current: set[str]) -> None:
    """Say what the mirror just gained or lost. Silence would hide upstream churn."""
    for label, urls in (("added", current - previous), ("removed", previous - current)):
        for url in sorted(urls):
            print(f"  {label}: {url}")


# ─── merging: one opinion per repository ─────────────────────────────

def slots(settings: Settings) -> dict[str, dict]:
    """Union every source into {repo_key: slot}, curated before mirrored."""
    layers = source_layers(settings)
    _warn_orphan_corrections(layers)
    merged: dict[str, dict] = {}
    for order, layer in enumerate(layers):
        print(f"Source {layer['name']}: {len(layer['entries'])} entries")
        for entry in layer["entries"]:
            repo_url = (entry.get("url") or "").strip()
            if not repo_url:
                print(f"warning: {layer['name']} entry without url, skipped: {entry}")
                continue
            if not parse_repo_url(repo_url):
                print(f"warning: {layer['name']} entry has no parseable url {repo_url!r}, skipped")
                continue
            slot = merged.setdefault(normalize_repo_url(repo_url),
                                     {"repo_url": repo_url, "order": order, "sources": []})
            slot["sources"].append(layer["name"])
            for field in MANUAL_KEYS:
                if entry.get(field) and not slot.get(field):
                    slot[field] = entry[field]
            if entry.get("skip"):
                # skip is a pure switch: the reason lives in manual.toml comments, the data carries none.
                slot["exclude"] = True
    print(f"Merged {len(merged)} distinct repos")
    return merged


def _warn_orphan_corrections(layers: list[dict]) -> None:
    """A correction whose repo nothing source_layers has become an intake by accident.

    Nobody decides that on purpose; it happens when an upstream drops a repo. The
    entry still works, but it now *creates* a payload instead of correcting one.
    """
    listed = {normalize_repo_url(entry["url"])
              for layer in layers if layer["role"] != CORRECTION
              for entry in layer["entries"]}
    for layer in layers:
        if layer["role"] != CORRECTION:
            continue
        for entry in layer["entries"]:
            url = normalize_repo_url(entry.get("url") or "")
            if url and url not in listed:
                print(f"warning: {layer['name']} corrects {url}, which nothing else source_layers; "
                      f"it is now an intake entry — move it to {ADDITIONAL}.json")


# ─── releases: watch what upstream published ─────────────────────────
# The only stage that observes anything. `resolve()` answers questions, it does
# not decide anything: it returns a flat dictionary of facts — tag, asset,
# digest, published date, the repo's own name and description — plus a `reason`
# when it could not. Shaping those facts into the client schema is `build`'s
# job, which is why a change to the output format never needs the network
# again.
#
# This is also where the catalogue's *format policy* lives: only `.elf` release
# assets are collected, so a repo that ships `.bin` alone simply has no facts
# to give.

ASSET_SUFFIX = ".elf"
# upstream occasionally ships PS4 and PS5 builds side by side; this PS5 catalogue wants only the latter.
WRONG_PLATFORM_MARKER = "ps4"


def latest_release(repo_url: str) -> dict | None:
    """The newest release, stable or pre-release alike; drafts never ship.

    Both APIs list releases newest-first and include pre-releases — only the
    `latest` endpoint hides them. Reading the list directly means a fresh
    `-rc` or `-beta` updates the catalogue without waiting for a stable tag,
    and one request replaces the old stable-then-fallback pair. Ten entries
    are scanned so a stale draft on top cannot hide the newest published one.
    """
    info = parse_repo_url(repo_url)
    if not info:
        return None
    host, owner, repo = info
    api = gh_api if host == "github.com" else (lambda endpoint: forgejo_api(host, endpoint))
    page = "per_page=10" if host == "github.com" else "limit=10"
    releases = api(f"repos/{owner}/{repo}/releases?{page}") or []
    for release in releases:
        if isinstance(release, dict) and not release.get("draft"):
            return release
    return None


def release_repo_url(release: dict) -> str:
    """`…/releases/tag/v1` → the repo root, so a renamed repo folds onto its new name.

    Anchored on `/releases/tag/` so an owner or repo whose name contains
    'releases' is not truncated.
    """
    match = re.match(r"^(.*?)/releases/tag/", release.get("html_url") or "")
    return match.group(1).lower() if match else ""


def repo_metadata(repo_url: str) -> dict:
    """The repo's own name and one-liner — the only source of `name`/`description`."""
    info = parse_repo_url(repo_url)
    if not info:
        return {"name": "", "description": ""}
    host, owner, repo = info
    data = gh_api(f"repos/{owner}/{repo}") if host == "github.com" \
        else forgejo_api(host, f"repos/{owner}/{repo}")
    if not isinstance(data, dict):
        data = {}
    return {"name": data.get("name") or "",
            "description": (data.get("description") or "").strip()}


def pick_asset(assets: list, asset_pattern: str, repo_url: str):
    """Choose the canonical asset, and report what curation may need to change.

    Returns `(asset, stale, ambiguous, redundant)`:

    - `stale` — a curated pattern no longer matches any asset. Selection falls
      back so the entry keeps working, but curation has drifted from upstream.
    - `ambiguous` — no pattern, and the heuristics still leave several plausible
      builds. This is the only case that genuinely needs a person to choose.
    - `redundant` — a pattern that still matches, but picks exactly the asset the
      heuristics would have picked anyway. The correction no longer does anything,
      and nothing else would ever say so.

    All three are curation debt made visible; none of them block a release.
    """
    candidates = [a for a in assets if a["name"].endswith(ASSET_SUFFIX)]
    if not candidates:
        return None, None, None, None

    def preferred(pool: list) -> dict:
        return min(pool, key=lambda a: (WRONG_PLATFORM_MARKER in a["name"].lower(),
                                        len(a["name"])))

    heuristic = preferred(candidates)
    stale = ambiguous = redundant = None
    chosen = heuristic

    if asset_pattern:
        matched = [a for a in candidates if re.search(asset_pattern, a["name"], re.IGNORECASE)]
        if matched:
            chosen = preferred(matched)
            if chosen["name"] == heuristic["name"]:
                redundant = {"url": repo_url, "pattern": asset_pattern}
        else:
            print(f"  warning: asset_pattern {asset_pattern!r} matched nothing for {repo_url}")
            stale = {"url": repo_url, "pattern": asset_pattern}
    else:
        pool = [a for a in candidates if WRONG_PLATFORM_MARKER not in a["name"].lower()] or candidates
        if len(pool) > 1:
            ambiguous = {"url": repo_url, "candidates": sorted(a["name"] for a in pool)}

    return chosen, stale, ambiguous, redundant


def digest_from_checksum_assets(assets: list, asset_name: str) -> str:
    """Read the asset's digest from an upstream checksum file when the API has none.

    Forgejo releases carry no `digest` field, but many publishers attach a
    `SHA256SUMS` or `<asset>.sha256` file. Parsing it keeps the rule that a
    checksum is copied, never computed. Lines are coreutils-shaped
    (`<hex>  <name>` or `<hex> *<name>`), matched by basename; a single bare hex
    line is the digest of the file the attachment is named after. The result is
    shaped like the API's own digest (`sha256:<hex>`) so downstream sees one
    format. Anything unparseable degrades to no checksum rather than a wrong one.
    """
    for attachment in assets:
        name = (attachment.get("name") or "").lower()
        if name != "sha256sums" and not name.endswith(".sha256"):
            continue
        try:
            text = http_get(attachment.get("browser_download_url") or "")
        except Exception:
            continue
        pairs = []
        for line in text.splitlines():
            digest, _, target = line.strip().partition(" ")
            if not SHA256_HEX.fullmatch(digest):
                continue
            target = target.lstrip("*").strip()
            pairs.append((digest.lower(), target.rsplit("/", 1)[-1].lower()))
        for digest, target in pairs:
            if target and target == asset_name.lower():
                return f"sha256:{digest}"
        if len(pairs) == 1 and not pairs[0][1]:
            return f"sha256:{pairs[0][0]}"
    return ""


def resolve(slot: dict) -> dict:
    """Observe one repo. Always returns facts; `reason` says what went wrong."""
    repo_url = slot["repo_url"]
    facts = empty_facts(repo_url)

    if not parse_repo_url(repo_url):
        facts["reason"] = "unparseable repo url"
        return facts

    print(f"Checking {repo_url}...")
    release = latest_release(repo_url)
    if not release:
        facts["reason"] = "no release found (or repo unreachable)"
        return facts
    assets = release.get("assets") or []
    if not assets:
        facts["reason"] = f"release {release.get('tag_name')} has no assets"
        return facts

    # repo_metadata is fetched only once a release is confirmed: a repo that fails to observe never reaches the artifact, so the call would be wasted.
    facts.update(repo_metadata(repo_url))

    asset, stale, ambiguous, redundant = pick_asset(assets, slot.get("asset_pattern") or "",
                                                    repo_url)
    if not asset:
        facts["reason"] = f"no {ASSET_SUFFIX} asset in the latest release"
        return facts

    digest = asset.get("digest") or ""
    if not digest:
        digest = digest_from_checksum_assets(assets, asset["name"])

    facts.update({
        "canon": release_repo_url(release),
        "tag": release.get("tag_name") or "",
        "published_at": release.get("published_at") or "",
        "asset_name": asset["name"],
        "asset_url": asset["browser_download_url"],
        "digest": digest,
        "stale_pattern": stale["pattern"] if stale else "",
        "ambiguous": ambiguous,
        "redundant_pattern": redundant["pattern"] if redundant else "",
    })
    print(f"  → {asset['name']} @ {facts['tag']}")
    return facts


def empty_facts(repo_url: str, reason: str = "") -> dict:
    """The fact shape before anything is known. One constructor, so adding a key
    to the fact schema only ever happens here."""
    return {"repo": repo_url, "canon": "", "name": "", "description": "",
            "tag": "", "published_at": "", "asset_name": "", "asset_url": "",
            "digest": "", "reason": reason, "stale_pattern": "", "ambiguous": None,
            "redundant_pattern": ""}


def observe(slots: list[dict]) -> dict[str, dict]:
    """Observe every slot concurrently, keyed by normalised repo URL.

    Results are collected per future and merged here, so no thread mutates shared
    state; keys are unique because slots are already keyed by normalised URL.
    """
    facts: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(resolve, slot): slot for slot in slots}
        try:
            for future in as_completed(futures):
                slot = futures[future]
                try:
                    facts[normalize_repo_url(slot["repo_url"])] = future.result()
                except Exception as e:
                    print(f"  error observing {slot['repo_url']}: {e}")
                    key = normalize_repo_url(slot["repo_url"])
                    facts[key] = empty_facts(slot["repo_url"],
                                             f"observation crashed: {e}")
        except BaseException:
            # on a rate limit gh_api sys.exits; do not wait out the dozens of in-flight requests too.
            pool.shutdown(wait=False, cancel_futures=True)
            raise
    return facts


def save_observations(settings: Settings, facts: dict[str, dict]) -> None:
    """Write the observation so `build --offline` can re-shape without the network."""
    settings.facts_file.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(settings.facts_file, {"observations": facts})


def load_observations(settings: Settings) -> dict[str, dict]:
    """Read the last observation. Missing or unreadable reads as empty."""
    try:
        return json.loads(settings.facts_file.read_text(encoding="utf-8")).get("observations", {})
    except (OSError, json.JSONDecodeError):
        return {}


# ─── build: shape into the client catalogue ──────────────────────────
# Pure: no network, no globals. The only section that knows what `payloads.json`
# looks like. Everything it needs arrives as arguments — slots, facts, and a
# `Settings` for where to read the previous publication — so the whole schema
# can be re-derived from a fixture in a test, or from the last observation via
# `build --offline`.
#
# Three invariants are enforced here rather than hoped for, because each one,
# when violated, breaks something on a real console:
#
# - `source` (identity) is unique — one record per repo.
# - `id` is unique — it is the slot key the client persists favourites against.
# - `filename` is unique — it is the file the console writes, so a collision
#   means one payload silently overwrites another.

# the client parses last_update as ISO 8601; dates are expressed in UTC+8.
UTC_PLUS_8 = timezone(timedelta(hours=8))


def format_last_update(iso_str: str) -> str:
    """Upstream UTC timestamp → ISO 8601 in UTC+8 ('2026-10-22T04:55:47+08:00').

    The client parses this as a date for version tie-breaking; a non-ISO string
    silently degrades that to lexicographic comparison.
    """
    if not iso_str:
        return ""
    try:
        moment = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return moment.astimezone(UTC_PLUS_8).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return iso_str


def checksum_of(digest: str) -> str:
    """`sha256:…` → 64 hex digits, else empty.

    The client rejects an entry whose non-empty checksum is malformed, so a
    missing or foreign digest degrades to "no checksum" rather than a bad one.
    """
    value = digest.split(":", 1)[1] if digest.startswith("sha256:") else ""
    return value.lower() if SHA256_HEX.fullmatch(value) else ""


def version_of(tag: str) -> str:
    """Strip a project-name prefix when it is followed by 'v<digit>.'.

    'file-explorer-v0.2.1' → 'v0.2.1'. Bare-digit tags ('1.2.3', 'nightly-20250901')
    and already-clean 'v…' tags pass through untouched.
    """
    match = re.match(r"^[a-z][a-z0-9-]*-(?=v\d+\.)", tag or "", re.IGNORECASE)
    return tag[match.end():] if match else (tag or "")


# the vocabulary matches the four categories of upstream itsPLK/ps5-payloads-mirror, so two taxonomies never coexist.
# two tiers of tests: device categories (loaders / jailbreak kernels) match the name
# only — "jailbroken" or "ELF loader" in a description would misfile ordinary tools;
# service categories match name + description. No Misc fallback: anything unmatched
# lands in Utilities & Tools.
CATEGORY_LOADERS = "Loaders"
CATEGORY_SYSTEM = "System & Jailbreak"
CATEGORY_NETWORK = "Networking & Servers"
CATEGORY_DEFAULT = "Utilities & Tools"
CATEGORY_NAME_RULES = [
    (r"elfldr|loader|autoload", CATEGORY_LOADERS),
    (r"kernel|kstuff|jailbreak|\bjb\b|\b(?:onion|eta)?hen\b|exploit|fself|npdrm|lapy", CATEGORY_SYSTEM),
]
CATEGORY_TEXT_RULES = [
    (r"\bftps?\b|ftpsrv|zftpd|\bhttps?\b|telnet|\bdns\b|klog|\bshell\b|websrv|upload|tailscale|\bgdb\b",
     CATEGORY_NETWORK),
]


def derive_category(name: str, description: str) -> str:
    lowered = name.lower()
    for pattern, category in CATEGORY_NAME_RULES:
        if re.search(pattern, lowered):
            return category
    text = f"{name} {description}".lower()
    for pattern, category in CATEGORY_TEXT_RULES:
        if re.search(pattern, text):
            return category
    return CATEGORY_DEFAULT


def item_from_facts(facts: dict, slot: dict) -> dict:
    """One installable record. Field order is the order the client sees."""
    repo_url = slot["repo_url"]
    # name fallback: the repo's own name wins; otherwise the last segment of the url.
    name = facts.get("name") or repo_url.rstrip("/").split("/")[-1]
    description = facts.get("description") or ""
    info = parse_repo_url(repo_url)
    return {
        # assign_ids fills the id after the whole set is sorted, keeping output order stable.
        "id": "",
        "name": name,
        "filename": "",
        "url": facts["asset_url"],
        "source": facts["canon"] or normalize_repo_url(repo_url),
        "author": info[1] if info else "",
        "description": description,
        "version": version_of(facts["tag"]),
        "category": derive_category(name, description),
        "checksum": checksum_of(facts["digest"]),
        "last_update": format_last_update(facts["published_at"]),
        # internal field (stripped before output): the raw asset name decides the install filename.
        "_asset_name": facts["asset_name"],
    }


def slugify(text: str) -> str:
    """Slug identical to the client's slot_slug, so ids match its default.

    Replicates the frontend rule exactly: alphanumerics lowercase, `.` and `_`
    kept (but a `.` never follows a `.` or starts the slug), every other run of
    characters becomes one dash, trailing `-._` stripped.
    """
    out = []
    last_dash = True
    for char in text or "":
        if char.isalnum():
            out.append(char.lower())
            last_dash = False
        elif char in ("_", ".") and out and out[-1] != ".":
            out.append(char)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).rstrip("-._") or "payload"


def assign_ids(items: list[dict], pinned: dict) -> None:
    """Fill ids: the previous run's id wins, fresh entries slug their name."""
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


def assign_filenames(items: list[dict]) -> None:
    """Lowercase the install key and make it globally unique.

    Identity is the URL, never the filename — two forks are two payloads. The
    console saves by filename, so a shared name means one file overwrites the
    other; that is the client's constraint, not a second identity. We only
    guarantee uniqueness, and we do not rank which project "deserves" the plain
    name: the order is the source URL, which is identity, stable, and carries no
    opinion about who is upstream. The loser falls back to its stable `id`.
    """
    for item in sorted(items, key=lambda p: p["source"]):
        raw = item.pop("_asset_name", None) or ""
        if not raw:
            # no asset name means no install name: this record is not installable and must not claim anyone's filename.
            item["filename"] = ""
            continue
        extension = "." + raw.rsplit(".", 1)[1].lower() if "." in raw else ""
        base = raw.lower()  # the client installs by name; a case flip would read as a second payload
        owner = _owner_of(items, base)
        if owner is None:
            item["filename"] = base
            continue
        print(f'  filename clash: {base!r} kept by {owner}; {item["id"]} saves as its id')
        candidate, suffix = f"{item['id']}{extension}", 2
        while _owner_of(items, candidate) is not None:
            candidate = f"{item['id']}-{suffix}{extension}"
            suffix += 1
        item["filename"] = candidate


def _owner_of(items: list[dict], filename: str) -> str | None:
    """Which item already claimed this install name, if any."""
    for other in items:
        if other.get("filename") and other["filename"].lower() == filename.lower():
            return other["id"]
    return None


def load_previous_catalogue(settings: Settings) -> tuple[dict, dict]:
    """{source: id} and {source: record} from the last published catalogue.

    Both exist to protect users: the id keeps a payload's slot, and the record is
    what a failed fetch is carried over from instead of being dropped.
    """
    try:
        document = json.loads(settings.catalogue_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, {}
    ids, records = {}, {}
    for record in document.get("payloads", []):
        key = normalize_repo_url(record.get("source", ""))
        if not key:
            continue
        records[key] = {k: v for k, v in record.items() if not k.startswith("_")}
        if record.get("id"):
            ids[key] = record["id"]
    return ids, records


def build(settings: Settings, slots: dict, facts: dict) -> tuple[dict, dict]:
    """Assemble the catalogue and report what happened to each source entry."""
    previous_ids, previous_records = load_previous_catalogue(settings)
    counters = {"excluded": 0, "deduped": 0, "carried": 0, "placeholder": 0}

    active = []
    for key in sorted(slots, key=lambda k: (slots[k]["order"], k)):
        slot = slots[key]
        if slot.get("exclude"):
            print(f"Skipped by {slot['sources'][0]}: {slot['repo_url']}")
            counters["excluded"] += 1
            continue
        active.append(slot)

    items, listed = [], set()
    for slot in active:
        key = normalize_repo_url(slot["repo_url"])
        observed = facts.get(key)
        # note: a successful observation carries an empty reason; a bare `or` fallback would read success as missing.
        reason = observed.get("reason", "") if observed else "no observation"

        if reason:
            fallback = _fallback(slot, key, reason, previous_records, counters)
            if fallback is None:
                continue
            item, canon = fallback
        else:
            item, canon = item_from_facts(observed, slot), \
                observed["canon"] or normalize_repo_url(slot["repo_url"])

        if canon in listed:
            print(f"  dedup: {slot['repo_url']} folds into {canon}, already listed")
            counters["deduped"] += 1
            continue
        listed.add(canon)
        items.append(item)

    # sort before assigning ids and filenames: a fixed (name, source) order makes conflict disambiguation reproducible.
    items.sort(key=lambda p: (p.get("name", "").lower(), p.get("source", "")))
    assign_ids(items, previous_ids)
    assign_filenames(items)
    _enforce_invariants(items)

    document = {"name": CATALOGUE_NAME, "payloads": items}
    return document, counters


def _fallback(slot: dict, key: str, reason: str, previous: dict, counters: dict):
    """What to publish when observation failed: the last good record, if there was one.

    A repo that resolved before is republished unchanged — a transient fetch
    failure must not yank an installable payload out of users' catalogues. A
    repo that has never resolved has nothing installable to offer: the client's
    own spec requires a filename, so publishing an empty-shaped entry would put
    a broken row into its catalogue. The record lives in the facts instead and
    returns by itself once the repo resolves.
    """
    reused = previous.get(key)
    if reused and not reused.get("unavailable"):
        print(f"  carry-over: {slot['repo_url']} kept from the last published run")
        counters["carried"] += 1
        item = dict(reused)
        # clear the filename: assign_filenames re-claims the same name from _asset_name;
        # carrying the old value into _owner_of counts the record as its own occupant
        # and collides the original name into the id-based one.
        item["filename"] = ""
        item["_asset_name"] = reused["filename"]
        return item, reused["source"]

    print(f"  placeholder: {slot['repo_url']} — {reason} (kept out of the artifact; "
          "facts recorded)")
    counters["placeholder"] += 1
    return None


def _enforce_invariants(items: list[dict]) -> None:
    """Refuse to publish a catalogue that would misbehave on a console."""
    filenames = [p["filename"].lower() for p in items if p["filename"]]
    duplicates = {
        "source": len({p["source"] for p in items}) != len(items),
        "id": len({p["id"] for p in items}) != len(items),
        "filename": len(set(filenames)) != len(filenames),
    }
    if any(duplicates.values()):
        raise SystemExit("error: duplicate survived dedup "
                         f"({', '.join(k for k, v in duplicates.items() if v)}); "
                         "two entries would overwrite each other on the console")


# ─── render: the README page ─────────────────────────────────────────
# A view over `payloads.json`, and nothing more. Deliberately outside the build
# stage: the catalogue is the product; this page is one way of looking at it,
# so it must be replaceable without re-observing anything — which is why
# `write_readme` takes the finished catalogue as input and never touches the
# network.
#
# Everything between the markers is generated; everything outside them is prose
# a human wrote and is never touched.

PAYLOADS_START, PAYLOADS_END = "<!-- PAYLOADS_START -->", "<!-- PAYLOADS_END -->"
STATS_START, STATS_END = "<!-- STATS_START -->", "<!-- STATS_END -->"
DESCRIPTION_LIMIT = 110


def stats_line(payloads: list[dict]) -> str:
    """One line of inventory. Generated, because a hand-kept count goes stale."""
    counts: dict[str, int] = {}
    for payload in payloads:
        counts[payload["category"]] = counts.get(payload["category"], 0) + 1
    categories = ", ".join(
        f"{name} {count}"
        for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    return f"**{len(payloads)} records** — Categories: {categories}."


def _cell(text: str) -> str:
    """Markdown table cells cannot contain a bare pipe or a newline."""
    return " ".join((text or "").split()).replace("|", "\\|")


def payload_table(payloads: list[dict]) -> str:
    """Source / Version / Category / Description / Updated.

    `Source` is the upstream repo, because the payload's `name` *is* the repo's
    own name now that the catalogue stores no separate title — a Name column would
    print the same string twice.
    """
    rows = ["| Source | Version | Category | Description | Updated |",
            "| --- | --- | --- | --- | --- |"]
    for payload in payloads:
        source = payload.get("source", "")
        info = parse_repo_url(source)
        label = f"{info[1]}/{info[2]}" if info else (source or "-")
        description = _cell(payload.get("description"))
        if len(description) > DESCRIPTION_LIMIT:
            description = description[:DESCRIPTION_LIMIT - 1].rstrip() + "…"
        version = _cell(payload.get("version"))
        updated = (payload.get("last_update") or "-").split("T")[0]
        rows.append(f"| [{label}]({source}) | {f'`{version}`' if version else '—'} | "
                    f"{payload.get('category', '')} | {description or '—'} | `{updated}` |")
    return "\n".join(rows)


def _replace_block(content: str, start: str, end: str, body: str) -> str:
    return re.sub(f"{re.escape(start)}.*?{re.escape(end)}",
                  lambda _: f"{start}\n{body}\n{end}", content, flags=re.DOTALL)


def write_readme(settings: Settings, payloads: list[dict]) -> bool:
    """Rewrite the generated blocks in place. Returns whether anything changed."""
    path = settings.readme_file
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if PAYLOADS_START not in content or STATS_START not in content:
        raise SystemExit(f"error: {path} is missing the generated-block markers")
    updated = _replace_block(content, STATS_START, STATS_END, stats_line(payloads))
    updated = _replace_block(updated, PAYLOADS_START, PAYLOADS_END, payload_table(payloads))
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def render_readme(settings: Settings) -> None:
    """Read the finished catalogue, refresh the page."""
    document = json.loads(settings.catalogue_file.read_text(encoding="utf-8"))
    payloads = document.get("payloads", [])
    changed = write_readme(settings, payloads)
    print(f"{settings.readme_file.name}: {'updated' if changed else 'unchanged'} "
          f"({len(payloads)} rows)")


# ─── site: package into a standalone page ────────────────────────────
# The pure half of packaging: wrap GitHub-rendered markdown in a standalone
# page. The token/env/network half lives in the CLI (cmd_site).

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown-light.css">
<style>
body {{ box-sizing: border-box; max-width: 980px; margin: 0 auto; padding: 32px 16px; }}
@media (max-width: 767px) {{ body {{ padding: 16px; }} }}
</style>
</head>
<body class="markdown-body">
{body}
</body>
</html>
"""


def page_html(markdown_html: str) -> str:
    """Wrap GitHub-rendered markdown in the standalone page shell.

    The page title comes from the first `<h1>`; a document without one falls
    back to the bare repo name.
    """
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", markdown_html, re.S)
    title = re.sub(r"<[^>]+>", "", heading.group(1)).strip() if heading else "ps5-payloads-atlas"
    return PAGE_TEMPLATE.format(title=title, body=markdown_html)
