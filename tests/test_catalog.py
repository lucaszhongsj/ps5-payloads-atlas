"""The catalogue pipeline, verified end to end and section by section.

One test file mirrors one production module: the classes below are ordered like
the sections of scripts/catalog.py — identity, harvest, the sources contract,
merging, collect, releases, build, failure paths, render, site packaging, the
CLI, and the end-to-end pipeline.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import atlas
import catalog
from catalog import (Settings, assign_filenames, assign_ids, build, canonical,
                     choose_proxy, cn_catalogue, cn_proxy_url,
                     collect, checksum_of, derive_category,
                     digest_from_checksum_assets, format_last_update, harvest,
                     source_layers, normalize_repo_url, parse_repo_url, read_mirror,
                     read_manual, render_readme, slots, slugify, payload_table,
                     version_of, write_cn_catalogue, write_readme)

ROOT = Path(__file__).resolve().parents[1]


# ─── fixtures ────────────────────────────────────────────────────────

def write(tmp: Path, additional: list[str] | None = None, manual: str = "",
          mirror: str = "", snapshots: dict[str, list[str]] | None = None) -> Settings:
    """Lay out a sources/ tree: the manual contract plus optional mirror data."""
    root = tmp / "sources"
    (root / "manual").mkdir(parents=True, exist_ok=True)
    (root / "mirror").mkdir(parents=True, exist_ok=True)
    if additional is not None:
        (root / "manual" / "additional.json").write_text(
            json.dumps(additional, indent=2), encoding="utf-8")
    if manual:
        (root / "manual" / "manual.toml").write_text(manual, encoding="utf-8")
    if mirror:
        (root / "mirror" / "mirror.toml").write_text(mirror, encoding="utf-8")
    for name, urls in (snapshots or {}).items():
        (root / "mirror" / name).write_text(json.dumps(urls, indent=2), encoding="utf-8")
    return Settings(root=tmp)


def fact(repo: str, name: str = "Tool", asset: str = "tool.elf",
         reason: str = "") -> dict:
    """One observation; `reason` non-empty means the release could not be read."""
    if reason:
        return {"repo": repo, "canon": "", "name": "", "description": "",
                "tag": "", "published_at": "", "asset_name": "", "asset_url": "",
                "digest": "", "reason": reason,
                "stale_pattern": "", "ambiguous": None, "redundant_pattern": ""}
    return {"repo": repo, "canon": repo.lower(), "name": name, "description": "d",
            "tag": "v1.0", "published_at": "2026-10-21T20:55:47Z",
            "asset_name": asset, "asset_url": f"{repo}/releases/download/v1.0/{asset}",
            "digest": "sha256:" + "A" * 64, "reason": "",
            "stale_pattern": "", "ambiguous": None, "redundant_pattern": ""}


def payload(description="d", version="v1", category="Utilities & Tools") -> dict:
    """A published record, as render sees it."""
    return {"source": "https://github.com/a/tool", "version": version,
            "category": category, "description": description,
            "last_update": "2026-10-22T04:55:47+08:00"}


def quiet(callable_):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = callable_()
    return result, out.getvalue()


# ─── URL identity ────────────────────────────────────────────────────

class RepoIdentity(unittest.TestCase):
    def test_normalize_handles_case_slash_and_git_suffix(self):
        self.assertEqual(normalize_repo_url("https://github.com/etaHEN/etaHEN/"),
                         "https://github.com/etahen/etahen")
        self.assertEqual(normalize_repo_url("https://github.com/x/y.git"),
                         "https://github.com/x/y")

    def test_parse_extracts_host_owner_repo(self):
        self.assertEqual(parse_repo_url("https://codeberg.org/elmonomalva0/Any-Pad-ps5"),
                         ("codeberg.org", "elmonomalva0", "Any-Pad-ps5"))
        self.assertIsNone(parse_repo_url("not a url"))

    def test_canonical_rejects_document_examples(self):
        for owner in ("me", "owner", "username", "example", "your-org"):
            self.assertIsNone(canonical("github.com", owner, "my-payload"))

    def test_canonical_rejects_hosts_and_documents_that_are_not_repos(self):
        self.assertIsNone(canonical("api.github.com", "x", "y"))
        self.assertIsNone(canonical("github.com", "x", "payloads.json"))
        self.assertIsNone(canonical("github.com", "x", "links.txt"))

    def test_canonical_builds_lowercased_url(self):
        self.assertEqual(canonical("github.com", "ItsPLK", "ps5-Payloads-Mirror"),
                         "https://github.com/itsplk/ps5-payloads-mirror")


# ─── harvest ─────────────────────────────────────────────────────────

class Harvest(unittest.TestCase):
    def test_json_document_reads_source_urls(self):
        text = ('{"payloads": [{"source": "https://github.com/Alpha/Tool"},'
                '{"homepage": "https://codeberg.org/Beta/Thing"}]}')
        self.assertEqual(harvest(text),
                         ["https://github.com/alpha/tool",
                          "https://codeberg.org/beta/thing"])

    def test_text_scan_finds_full_and_shorthand_urls(self):
        text = "# see https://github.com/Alpha/Tool and github:Beta/Thing\n"
        self.assertEqual(harvest(text),
                         ["https://github.com/alpha/tool",
                          "https://github.com/beta/thing"])

    def test_duplicates_collapse_in_document_order(self):
        text = "https://github.com/Alpha/Tool\nhttps://github.com/Alpha/Tool\n"
        self.assertEqual(harvest(text), ["https://github.com/alpha/tool"])

    def test_example_repos_in_comments_are_not_harvested(self):
        self.assertEqual(harvest("example: https://github.com/me/my-payload"), [])


# ─── sources: contracts ──────────────────────────────────────────────

class Contract(unittest.TestCase):
    def test_layers_are_additional_then_manual_then_mirrors(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      additional=["https://github.com/a/t"],
                      snapshots={"feed.json": ["https://github.com/b/s"]})
            layers, _ = quiet(lambda: source_layers(s))
            self.assertEqual([(l["name"], l["role"]) for l in layers],
                             [("additional", "intake"), ("manual", "correction"),
                              ("feed", "mirror")])

    def test_missing_additional_list_is_an_error(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp))
            with self.assertRaises(SystemExit):
                quiet(lambda: source_layers(s))

    def test_stray_file_in_manual_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = write(root, additional=["https://github.com/a/t"])
            (root / "sources" / "manual" / "notes.txt").write_text("hello")
            _, printed = quiet(lambda: source_layers(s))
            self.assertIn("not part of the manual contract", printed)


class Corrections(unittest.TestCase):
    def test_empty_table_corrects_nothing(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_unknown_field_is_rejected(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\ncategory = "X"\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_unparseable_key_is_rejected(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["not a url"]\nskip = true\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_duplicate_table_is_a_toml_error(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\nskip = true\n'
                                '["https://github.com/a/t"]\nskip = true\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_skip_must_be_true(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\nskip = "because"\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_skip_false_corrects_nothing(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\nskip = false\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_asset_pattern_must_compile(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\nasset_pattern = "(\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_skip_prerelease_must_be_true(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/a/t"]\nskip_prerelease = false\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_skip_prerelease_is_carried_into_the_slot(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=["https://github.com/a/t"],
                      manual='["https://github.com/a/t"]\nskip_prerelease = true\n')
            self.assertTrue(slots(s)["https://github.com/a/t"]["skip_prerelease"])


class Manifest(unittest.TestCase):
    def test_mirror_needs_a_url(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), mirror='["https://github.com/a/feed"]\n')
            with self.assertRaises(SystemExit):
                read_mirror(s)

    def test_mirror_table_takes_nothing_but_a_url(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      mirror='["https://github.com/a/feed"]\nurl = "https://x"\nbranch = "main"\n')
            with self.assertRaises(SystemExit):
                read_mirror(s)

    def test_key_must_be_a_repository_url(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), mirror='["not a url"]\nurl = "https://x"\n')
            with self.assertRaises(SystemExit):
                read_mirror(s)

    def test_two_mirrors_cannot_share_a_snapshot(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      mirror='["https://github.com/Feed/tool"]\nurl = "https://x"\n'
                              '["https://github.com/feed/tool"]\nurl = "https://y"\n')
            with self.assertRaises(SystemExit):
                read_mirror(s)

    def test_snapshot_name_is_derived_from_the_repo(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      mirror='["https://github.com/SomeOne/My-List"]\nurl = "https://x"\n')
            self.assertEqual(read_mirror(s), {"my-list": "https://x"})

    def test_uncollected_mirror_is_reported_by_lists(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      mirror='["https://github.com/ghost/list"]\nurl = "https://x"\n')
            _, printed = quiet(lambda: source_layers(s))
            self.assertIn("no snapshot yet", printed)


# ─── sources: dictionary order ───────────────────────────────────────

class Ordering(unittest.TestCase):
    def test_unsorted_json_is_rejected(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      additional=["https://github.com/b/t", "https://github.com/a/t"])
            with self.assertRaises(SystemExit):
                quiet(lambda: source_layers(s))

    def test_order_is_case_insensitive(self):
        with TemporaryDirectory() as tmp:
            # plain code-point order would put B/t2 first; dictionary order does not
            s = write(Path(tmp),
                      additional=["https://github.com/a/t", "https://github.com/B/t2"])
            layers, _ = quiet(lambda: source_layers(s))
            self.assertEqual(layers[0]["entries"],
                             [{"url": "https://github.com/a/t"},
                              {"url": "https://github.com/B/t2"}])

    def test_unsorted_manual_tables_are_rejected(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp), additional=[],
                      manual='["https://github.com/b/t"]\nskip = true\n'
                                '["https://github.com/a/t"]\nskip = true\n')
            with self.assertRaises(SystemExit):
                read_manual(s)

    def test_unsorted_mirror_tables_are_rejected(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      mirror='["https://github.com/b/feed"]\nurl = "https://x"\n'
                              '["https://github.com/a/feed"]\nurl = "https://y"\n')
            with self.assertRaises(SystemExit):
                read_mirror(s)

    def test_collect_writes_snapshots_in_dictionary_order(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = write(root, mirror='["https://github.com/a/feed"]\nurl = "https://x"\n')
            upstream = ["https://github.com/B/two", "https://github.com/a/one"]
            with mock.patch.object(catalog, "http_get", return_value=""), \
                 mock.patch.object(catalog, "harvest", return_value=upstream):
                collect(s)
            kept = json.loads((root / "sources" / "mirror" / "feed.json").read_text())
            self.assertEqual(kept, ["https://github.com/a/one", "https://github.com/B/two"])


# ─── merging ─────────────────────────────────────────────────────────

class Merge(unittest.TestCase):
    def test_curated_wins_over_mirror_and_skip_is_sticky(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      additional=["https://github.com/a/tool", "https://github.com/b/skip"],
                      manual='["https://github.com/a/tool"]\nasset_pattern = "^x"\n'
                                '["https://github.com/b/skip"]\nskip = true\n',
                      snapshots={"feed.json": ["https://github.com/a/tool"]})
            slot_map, _ = quiet(lambda: slots(s))
            self.assertEqual(slot_map["https://github.com/a/tool"]["asset_pattern"], "^x")
            self.assertEqual(slot_map["https://github.com/a/tool"]["sources"],
                             ["additional", "manual", "feed"])
            self.assertTrue(slot_map["https://github.com/b/skip"]["exclude"])


class OrphanCorrections(unittest.TestCase):
    def test_trailing_slash_does_not_false_positive(self):
        with TemporaryDirectory() as tmp:
            s = write(Path(tmp),
                      additional=["https://github.com/a/tool"],
                      manual='["https://github.com/a/tool/"]\nasset_pattern = "^x"\n',
                      snapshots={"feed.json": ["https://github.com/a/tool"]})
            _, printed = quiet(lambda: slots(s))
            self.assertNotIn("nothing else source_layers", printed)


# ─── collect ─────────────────────────────────────────────────────────

class ShrinkGuard(unittest.TestCase):
    def test_shrink_over_threshold_is_refused_without_force(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = write(root, snapshots={"feed.json": [f"https://github.com/a/r{i}"
                                                     for i in range(20)]},
                      mirror='["https://github.com/a/feed"]\nurl = "https://x"\n')
            smaller = [f"https://github.com/a/r{i}" for i in range(5)]
            with mock.patch.object(catalog, "http_get", return_value=""), \
                 mock.patch.object(catalog, "harvest", return_value=smaller):
                collect(s)
            kept = json.loads((root / "sources" / "mirror" / "feed.json").read_text())
            self.assertEqual(len(kept), 20)

    def test_shrink_is_allowed_with_force(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = write(root, snapshots={"feed.json": [f"https://github.com/a/r{i}"
                                                     for i in range(20)]},
                      mirror='["https://github.com/a/feed"]\nurl = "https://x"\n')
            smaller = [f"https://github.com/a/r{i}" for i in range(5)]
            with mock.patch.object(catalog, "http_get", return_value=""), \
                 mock.patch.object(catalog, "harvest", return_value=smaller):
                collect(s, force=True)
            kept = json.loads((root / "sources" / "mirror" / "feed.json").read_text())
            self.assertEqual(len(kept), 5)

    def test_snapshot_without_manifest_entry_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = write(root, snapshots={"leftover.json": ["https://github.com/a/t"]})
            _, printed = quiet(lambda: collect(s))
            self.assertIn("no entry in mirror.toml", printed)
            self.assertTrue((root / "sources" / "mirror" / "leftover.json").exists())


# ─── releases digest ─────────────────────────────────────────────────

class DigestFromChecksumAssets(unittest.TestCase):
    def test_coreutils_sums_matched_by_basename(self):
        assets = [{"name": "app.elf", "browser_download_url": "https://example/d"},
                  {"name": "SHA256SUMS", "browser_download_url": "https://example/s"}]
        body = f"{'a' * 64}  app.elf\n{'b' * 64}  notes.txt\n"
        with mock.patch.object(catalog, "http_get", return_value=body):
            self.assertEqual(digest_from_checksum_assets(assets, "app.elf"),
                             f"sha256:{'a' * 64}")

    def test_binary_mode_marker_and_path_are_stripped(self):
        assets = [{"name": "tool.elf", "browser_download_url": "https://example/d"},
                  {"name": "SHA256SUMS", "browser_download_url": "https://example/s"}]
        body = f"{'a' * 64} *dir/tool.elf\n"
        with mock.patch.object(catalog, "http_get", return_value=body):
            self.assertEqual(digest_from_checksum_assets(assets, "tool.elf"),
                             f"sha256:{'a' * 64}")

    def test_single_asset_sha256_attachment_with_bare_digest(self):
        assets = [{"name": "AnyPad-PS5-0.9.5-beta.elf",
                   "browser_download_url": "https://example/d"},
                  {"name": "AnyPad-PS5-0.9.5-beta.elf.sha256",
                   "browser_download_url": "https://example/s"}]
        with mock.patch.object(catalog, "http_get", return_value=f"{'b' * 64}\n"):
            self.assertEqual(digest_from_checksum_assets(
                assets, "AnyPad-PS5-0.9.5-beta.elf"), f"sha256:{'b' * 64}")

    def test_unmatched_names_degrade_to_no_checksum(self):
        assets = [{"name": "app.elf", "browser_download_url": "https://example/d"},
                  {"name": "SHA256SUMS", "browser_download_url": "https://example/s"}]
        body = f"{'a' * 64}  something-else.elf\n"
        with mock.patch.object(catalog, "http_get", return_value=body):
            self.assertEqual(digest_from_checksum_assets(assets, "app.elf"), "")

    def test_fetch_failure_degrades_to_no_checksum(self):
        assets = [{"name": "app.elf", "browser_download_url": "https://example/d"},
                  {"name": "SHA256SUMS", "browser_download_url": "https://example/s"}]
        with mock.patch.object(catalog, "http_get", side_effect=OSError("down")):
            self.assertEqual(digest_from_checksum_assets(assets, "app.elf"), "")

    def test_no_checksum_attachment_is_a_no_op(self):
        assets = [{"name": "app.elf", "browser_download_url": "https://example/d"},
                  {"name": "README.md", "browser_download_url": "https://example/r"}]
        self.assertEqual(digest_from_checksum_assets(assets, "app.elf"), "")

    def test_malformed_lines_are_skipped_not_fatal(self):
        assets = [{"name": "app.elf", "browser_download_url": "https://example/d"},
                  {"name": "SHA256SUMS", "browser_download_url": "https://example/s"}]
        body = f"not-a-hash  app.elf\n\n{'a' * 64}  app.elf\n"
        with mock.patch.object(catalog, "http_get", return_value=body):
            self.assertEqual(digest_from_checksum_assets(assets, "app.elf"),
                             f"sha256:{'a' * 64}")


# ─── releases: which release counts ──────────────────────────────────

class LatestRelease(unittest.TestCase):
    STABLE = {"tag_name": "v1.0", "draft": False, "prerelease": False}
    PRERELEASE = {"tag_name": "v1.1-rc1", "draft": False, "prerelease": True}
    DRAFT = {"tag_name": "v1.2", "draft": True, "prerelease": False}

    def test_newer_prerelease_wins_over_older_stable(self):
        with mock.patch.object(catalog, "gh_api",
                               return_value=[self.PRERELEASE, self.STABLE]):
            release = catalog.latest_release("https://github.com/a/tool")
        self.assertEqual(release["tag_name"], "v1.1-rc1")

    def test_draft_on_top_does_not_hide_the_newest_published(self):
        with mock.patch.object(catalog, "gh_api",
                               return_value=[self.DRAFT, self.PRERELEASE, self.STABLE]):
            release = catalog.latest_release("https://github.com/a/tool")
        self.assertEqual(release["tag_name"], "v1.1-rc1")

    def test_stable_only_repo_is_unchanged(self):
        with mock.patch.object(catalog, "gh_api", return_value=[self.STABLE]):
            release = catalog.latest_release("https://github.com/a/tool")
        self.assertEqual(release["tag_name"], "v1.0")

    def test_forgejo_lists_use_the_limit_page(self):
        with mock.patch.object(catalog, "forgejo_api",
                               return_value=[self.PRERELEASE]) as api:
            release = catalog.latest_release("https://codeberg.org/a/tool")
        api.assert_called_once_with("codeberg.org", "repos/a/tool/releases?limit=10")
        self.assertEqual(release["tag_name"], "v1.1-rc1")

    def test_no_releases_is_none(self):
        with mock.patch.object(catalog, "gh_api", return_value=[]):
            self.assertIsNone(catalog.latest_release("https://github.com/a/tool"))

    def test_skip_prerelease_takes_the_newest_stable(self):
        with mock.patch.object(catalog, "gh_api",
                               return_value=[self.PRERELEASE, self.STABLE]):
            release = catalog.latest_release("https://github.com/a/tool",
                                             skip_prerelease=True)
        self.assertEqual(release["tag_name"], "v1.0")

    def test_skip_prerelease_can_exhaust_the_list(self):
        with mock.patch.object(catalog, "gh_api", return_value=[self.PRERELEASE]):
            self.assertIsNone(catalog.latest_release("https://github.com/a/tool",
                                                     skip_prerelease=True))

    def test_resolve_passes_the_skip_prerelease_flag(self):
        with mock.patch.object(catalog, "latest_release", return_value=None) as latest:
            catalog.resolve({"repo_url": "https://github.com/a/tool",
                             "skip_prerelease": True})
        latest.assert_called_once_with("https://github.com/a/tool", True)


# ─── build: field shaping ────────────────────────────────────────────

class FieldShaping(unittest.TestCase):
    def test_version_strips_project_prefix_only_when_followed_by_v_number(self):
        self.assertEqual(version_of("file-explorer-v0.2.1"), "v0.2.1")
        self.assertEqual(version_of("nightly-20250901"), "nightly-20250901")
        self.assertEqual(version_of("v1.0"), "v1.0")

    def test_checksum_accepts_only_64_hex_digits(self):
        digest = "sha256:" + "A" * 64
        self.assertEqual(checksum_of(digest), "a" * 64)
        self.assertEqual(checksum_of("sha256:short"), "")
        self.assertEqual(checksum_of(""), "")

    def test_last_update_is_iso_with_utc_plus_8(self):
        self.assertEqual(format_last_update("2026-10-21T20:55:47Z"),
                         "2026-10-22T04:55:47+08:00")
        self.assertEqual(format_last_update(""), "")

    def test_category_rules(self):
        self.assertEqual(derive_category("elfldr", ""), "Loaders")
        self.assertEqual(derive_category("kstuff-lite", ""), "System & Jailbreak")
        self.assertEqual(derive_category("ftpsrv", ""), "Networking & Servers")
        self.assertEqual(derive_category("random-tool", ""), "Utilities & Tools")


class IdsAndFilenames(unittest.TestCase):
    def test_ids_are_pinned_across_runs(self):
        items = [{"id": "", "name": "Renamed Tool", "source": "https://github.com/a/tool"}]
        assign_ids(items, {"https://github.com/a/tool": "tool-old-slug"})
        self.assertEqual(items[0]["id"], "tool-old-slug")

    def test_id_collisions_get_numeric_suffix(self):
        items = [{"id": "", "name": "Tool", "source": "https://github.com/a/tool"},
                 {"id": "", "name": "Tool", "source": "https://github.com/b/tool"}]
        assign_ids(items, {})
        self.assertEqual([p["id"] for p in items], ["tool", "tool-2"])

    def test_slug_matches_the_client_on_consecutive_dots(self):
        # the client inserts a hyphen on consecutive dots (the first '.' sets
        # lastDash=false, the second '.' falls into the else branch) — the quirk
        # must be replicated exactly.
        self.assertEqual(slugify("Foo..Bar"), "foo.-bar")
        self.assertEqual(slugify("_tool."), "tool")

    def test_filenames_are_lowercased(self):
        items = [{"id": "cheat", "filename": "", "_asset_name": "CheatRunner.elf",
                  "source": "https://github.com/a/cheat"}]
        assign_filenames(items)
        self.assertEqual(items[0]["filename"], "cheatrunner.elf")

    def test_collision_falls_back_to_id_not_overwrite(self):
        items = [{"id": "a-kstuff", "filename": "", "_asset_name": "kstuff.elf",
                  "source": "https://github.com/a/kstuff"},
                 {"id": "b-kstuff", "filename": "", "_asset_name": "kstuff.elf",
                  "source": "https://github.com/b/kstuff"}]
        assign_filenames(items)
        self.assertEqual([p["filename"] for p in items],
                         ["kstuff.elf", "b-kstuff.elf"])

    def test_placeholder_does_not_claim_an_install_name(self):
        items = [{"id": "ghost", "filename": "", "_asset_name": "",
                  "source": "https://github.com/a/ghost"}]
        assign_filenames(items)
        self.assertEqual(items[0]["filename"], "")


# ─── build failure path ──────────────────────────────────────────────

class FailurePath(unittest.TestCase):
    def test_transient_failure_carries_the_last_good_record(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = write(root, additional=["https://github.com/Alpha/Tool"])
            settings.catalogue_file.write_text(json.dumps({"name": "x", "payloads": [
                {"id": "tool", "source": "https://github.com/alpha/tool", "name": "Tool",
                 "filename": "tool.elf", "url": "https://example/tool.elf",
                 "version": "v1.0", "checksum": "a" * 64}]}))

            slot_map = slots(settings)
            facts = {"https://github.com/alpha/tool":
                     fact("https://github.com/Alpha/Tool",
                          reason="no release found (or repo unreachable)")}
            document, counters = build(settings, slot_map, facts)

            self.assertEqual(counters["carried"], 1)
            self.assertEqual(len(document["payloads"]), 1)
            kept = document["payloads"][0]
            self.assertEqual(kept["filename"], "tool.elf")
            self.assertEqual(kept["url"], "https://example/tool.elf")

    def test_never_resolved_record_stays_out_of_the_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = write(root, additional=["https://github.com/Alpha/Tool"])

            slot_map = slots(settings)
            facts = {"https://github.com/alpha/tool":
                     fact("https://github.com/Alpha/Tool",
                          reason="no release found (or repo unreachable)")}
            document, counters = build(settings, slot_map, facts)

            self.assertEqual(document["payloads"], [])
            self.assertEqual(counters["placeholder"], 1)
            self.assertEqual(counters["carried"], 0)


# ─── render ──────────────────────────────────────────────────────────

class Table(unittest.TestCase):
    def test_pipes_are_escaped_so_columns_survive(self):
        row = payload_table([payload(description="manager | browser based")]).splitlines()[-1]
        self.assertEqual(row.count(" | "), 4)  # 5 columns → 4 inner separators
        self.assertIn(r"manager \| browser based", row)

    def test_long_descriptions_are_truncated_with_ellipsis(self):
        row = payload_table([payload(description="x" * 200)]).splitlines()[-1]
        self.assertIn("…", row.split(" | ")[3])  # ellipsis lands in the description column
        self.assertLessEqual(len(row), 400)

    def test_empty_version_renders_dash(self):
        self.assertIn("—", payload_table([payload(version="")]))


class Write(unittest.TestCase):
    def test_second_write_changes_nothing(self):
        with TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            readme.write_text("<!-- STATS_START -->\n<!-- STATS_END -->\n"
                              "<!-- PAYLOADS_START -->\n<!-- PAYLOADS_END -->\n",
                              encoding="utf-8")
            settings = Settings(root=Path(tmp))
            self.assertTrue(write_readme(settings, [payload()]))
            self.assertFalse(write_readme(settings, [payload()]))

    def test_missing_markers_is_an_error_not_a_silent_skip(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("no markers here", encoding="utf-8")
            with self.assertRaises(SystemExit):
                write_readme(Settings(root=Path(tmp)), [payload()])


# ─── site packaging (pure functions) ─────────────────────────────────

class SitePackaging(unittest.TestCase):
    def test_title_is_extracted_from_the_first_heading(self):
        page = catalog.page_html("<h1>My Atlas</h1><p>x</p>")
        self.assertIn("<title>My Atlas</title>", page)
        self.assertIn("<h1>My Atlas</h1>", page)

    def test_markdown_without_heading_falls_back_to_default_title(self):
        page = catalog.page_html("<p>no heading</p>")
        self.assertIn("<title>ps5-payloads-atlas</title>", page)

    def test_site_packs_the_cn_catalogue_when_present(self):
        with TemporaryDirectory() as tmp:
            settings = Settings(root=Path(tmp))
            settings.readme_file.write_text("# Atlas\n", encoding="utf-8")
            settings.catalogue_file.write_text('{"name": "x", "payloads": []}', encoding="utf-8")
            settings.cn_catalogue_file.write_text(
                '{"name": "x (CN proxy)", "payloads": []}', encoding="utf-8")
            with mock.patch.object(catalog, "render_markdown", return_value="<h1>Atlas</h1>"), \
                    mock.patch.dict(os.environ, {"GH_TOKEN": "test"}):
                quiet(lambda: atlas.cmd_site(settings, []))
            self.assertTrue((settings.site_dir / "payloads.json").exists())
            self.assertTrue((settings.site_dir / "payloads-cn.json").exists())


# ─── CN proxy view ──────────────────────────────────────────────────

GH = "https://github.com/a/tool/releases/download/v1/tool.elf"


def asset(name: str) -> dict:
    """A routable catalogue record: GitHub release, checksummed, `.elf`."""
    return {"url": f"https://github.com/a/{name}/releases/download/v1/{name}.elf",
            "checksum": "a" * 64}


class FakeResponse:
    """The slice of an http.client response that `probe_proxy` uses."""

    def __init__(self, body=b"", status=200, url="https://p/",
                 content_type="application/octet-stream"):
        self._body, self._offset = body, 0
        self.status = status
        self._url = url
        self.headers = {"Content-Type": content_type}

    def read(self, count=-1):
        chunk = self._body[self._offset:self._offset + count]
        self._offset += len(chunk)
        return chunk

    def read1(self, count=-1):
        return self.read(count)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class CnProxyView(unittest.TestCase):
    def test_only_checksummed_github_release_downloads_are_routed(self):
        checksum = "a" * 64
        self.assertEqual(cn_proxy_url(GH, checksum, "https://p/"), "https://p/" + GH)
        self.assertEqual(cn_proxy_url(GH, "", "https://p/"), GH)
        self.assertEqual(cn_proxy_url(None, None, "https://p/"), "")
        archive = "https://github.com/a/tool/archive/v1.zip"
        self.assertEqual(cn_proxy_url(archive, checksum, "https://p/"), archive)
        codeberg = "https://codeberg.org/a/tool/releases/download/v1/tool.elf"
        self.assertEqual(cn_proxy_url(codeberg, checksum, "https://p/"), codeberg)

    def test_the_cn_view_does_not_mutate_the_catalogue(self):
        document = {"name": "atlas", "icons_url": "icons.json", "payloads": [asset("tool")]}
        view = cn_catalogue(document, "https://p/")
        self.assertEqual(view["name"], "atlas (CN proxy)")
        self.assertEqual(view["icons_url"], "icons.json")
        self.assertEqual(view["payloads"][0]["url"], "https://p/" + asset("tool")["url"])
        self.assertEqual(document["payloads"][0]["url"], asset("tool")["url"])

    def test_probe_targets_spread_across_the_catalogue(self):
        payloads = [{"url": "https://example.com/x.elf", "checksum": "a" * 64}] + \
                   [asset(f"p{index}") for index in range(5)]
        targets, _ = quiet(lambda: catalog._probe_targets(payloads))
        self.assertEqual(len(targets), 3)
        self.assertEqual(targets[0], payloads[1]["url"])
        self.assertEqual(targets[-1], payloads[-1]["url"])

    def test_probe_targets_are_empty_without_routable_entries(self):
        self.assertEqual(catalog._probe_targets([{"url": "https://example.com/x"}]), [])

    def test_a_served_asset_passes_the_probe(self):
        body = catalog.ELF_MAGIC + b"\0" * 2048
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResponse(body, status=206, url="https://p/" + GH)):
            self.assertIsNotNone(catalog.probe_proxy("https://p/", GH))

    def test_a_redirect_off_the_proxy_is_a_failure(self):
        body = catalog.ELF_MAGIC + b"\0" * 2048
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResponse(body, url="https://objects.example/x")):
            self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_a_downgrade_to_http_is_a_failure(self):
        body = catalog.ELF_MAGIC + b"\0" * 2048
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResponse(body, url="http://p/" + GH)):
            self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_error_pages_and_wrong_magic_are_failures(self):
        cases = [
            FakeResponse(b"<html>blocked</html>", content_type="text/html"),
            FakeResponse(b'{"error":"rate limited"}', content_type="application/json"),
            FakeResponse(b'{"error":"rate limited"}'),
            FakeResponse(b"PK\x03\x04" + b"\0" * 128),
        ]
        for response in cases:
            with self.subTest(content_type=response.headers["Content-Type"]):
                with mock.patch("urllib.request.urlopen", return_value=response):
                    self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_a_bom_prefixed_html_page_is_a_failure(self):
        response = FakeResponse(b"\xef\xbb\xbf<html>blocked</html>")
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_a_non_success_status_is_a_failure(self):
        for status in (403, 404, 500):
            with self.subTest(status=status):
                response = FakeResponse(catalog.ELF_MAGIC + b"\0" * 64, status=status)
                with mock.patch("urllib.request.urlopen", return_value=response):
                    self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_a_base_without_a_trailing_slash_still_probes(self):
        body = catalog.ELF_MAGIC + b"\0" * 64
        response = FakeResponse(body, url="https://p/" + GH)
        with mock.patch("urllib.request.urlopen", return_value=response) as opener:
            self.assertIsNotNone(catalog.probe_proxy("https://p", GH))
        self.assertEqual(opener.call_args.args[0].full_url, "https://p/" + GH)

    def test_the_probe_stops_at_its_total_deadline(self):
        response = FakeResponse(catalog.ELF_MAGIC + b"\0" * 64)
        ticks = iter([0.0, 0.0, 100.0])
        with mock.patch("urllib.request.urlopen", return_value=response), \
                mock.patch.object(catalog.time, "monotonic",
                                  side_effect=lambda: next(ticks, 100.0)):
            self.assertIsNone(catalog.probe_proxy("https://p/", GH, timeout=5))

    def test_transport_failure_is_a_failure(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("boom")):
            self.assertIsNone(catalog.probe_proxy("https://p/", GH))

    def test_the_first_candidate_serving_every_target_wins(self):
        payloads = [asset(f"p{index}") for index in range(3)]
        timings = {"https://dead/": None, "https://live/": 0.4}
        base, _ = quiet(lambda: choose_proxy(
            payloads, ("https://dead/", "https://live/"),
            probe=lambda candidate, url: timings[candidate]))
        self.assertEqual(base, "https://live/")

    def test_one_transient_miss_demotes_to_a_full_pass(self):
        payloads = [asset(f"p{index}") for index in range(3)]

        def probe(candidate, url):
            return None if candidate == "https://partial/" and url.endswith("p1.elf") else 0.1

        base, _ = quiet(lambda: choose_proxy(
            payloads, ("https://partial/", "https://full/"), probe=probe))
        self.assertEqual(base, "https://full/")

    def test_a_majority_falls_back_when_no_candidate_serves_everything(self):
        payloads = [asset(f"p{index}") for index in range(3)]

        def probe(candidate, url):
            return None if url.endswith("p0.elf") else 0.1

        base, output = quiet(lambda: choose_proxy(
            payloads, ("https://partial/",), probe=probe))
        self.assertEqual(base, "https://partial/")
        self.assertIn("falling back", output)

    def test_no_candidate_means_no_view(self):
        payloads = [asset("tool")]
        base, _ = quiet(lambda: choose_proxy(
            payloads, ("https://dead/",), probe=lambda candidate, url: None))
        self.assertIsNone(base)

    def test_write_skips_an_identical_snapshot(self):
        with TemporaryDirectory() as tmp:
            settings = Settings(root=Path(tmp))
            settings.catalogue_file.write_text(json.dumps(
                {"name": "atlas", "payloads": [asset("tool")]}), encoding="utf-8")
            writes = []
            original = catalog.atomic_write_json

            def counting(path, document):
                writes.append(path)
                original(path, document)

            with mock.patch.object(catalog, "atomic_write_json", side_effect=counting):
                write_cn_catalogue(settings, "https://p/")
                write_cn_catalogue(settings, "https://p/")
            self.assertEqual(len(writes), 1)
            self.assertIn("https://p/" + asset("tool")["url"],
                          settings.cn_catalogue_file.read_text(encoding="utf-8"))

    def test_a_corrupt_snapshot_is_rewritten(self):
        with TemporaryDirectory() as tmp:
            settings = Settings(root=Path(tmp))
            settings.catalogue_file.write_text(json.dumps(
                {"name": "atlas", "payloads": [asset("tool")]}), encoding="utf-8")
            settings.cn_catalogue_file.write_text("<<<not json>>>", encoding="utf-8")
            write_cn_catalogue(settings, "https://p/")
            self.assertIn("(CN proxy)",
                          settings.cn_catalogue_file.read_text(encoding="utf-8"))


# ─── CLI ─────────────────────────────────────────────────────────────

class CliEndToEnd(unittest.TestCase):
    def test_render_via_the_documented_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "render"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


# ─── end to end ──────────────────────────────────────────────────────

class Pipeline(unittest.TestCase):
    def test_slots_plus_facts_become_the_client_document(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = write(root, additional=["https://github.com/Alpha/Tool"],
                             snapshots={"feed.json": ["https://github.com/Beta/Server"]})

            slot_map = slots(settings)
            facts = {"https://github.com/alpha/tool":
                     fact("https://github.com/Alpha/Tool", "Tool", "tool.elf"),
                     "https://github.com/beta/server":
                     fact("https://github.com/Beta/Server", "Server", "server.elf")}

            document, counters = build(settings, slot_map, facts)
            payloads = document["payloads"]
            self.assertEqual(len(payloads), 2)
            self.assertEqual({p["id"] for p in payloads}, {"server", "tool"})
            self.assertEqual({p["filename"] for p in payloads}, {"server.elf", "tool.elf"})
            self.assertTrue(all(p["checksum"] == "a" * 64 for p in payloads))
            self.assertEqual(counters["placeholder"], 0)

    def test_previous_id_is_kept_when_name_changes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = write(root, additional=["https://github.com/Alpha/Tool"])
            settings.catalogue_file.write_text(json.dumps({"name": "x", "payloads": [
                {"id": "tool-old", "source": "https://github.com/alpha/tool",
                 "name": "Old Name", "filename": "tool.elf"}]}))

            slot_map = slots(settings)
            facts = {"https://github.com/alpha/tool":
                     fact("https://github.com/Alpha/Tool", "New Name", "tool.elf")}
            document, _ = build(settings, slot_map, facts)
            self.assertEqual(document["payloads"][0]["id"], "tool-old")


if __name__ == "__main__":
    unittest.main()
