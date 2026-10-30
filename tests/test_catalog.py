"""The catalogue pipeline, verified end to end and section by section.

One test file mirrors one production module: the classes below are ordered like
the sections of scripts/catalog.py — identity, harvest, the sources contract,
merging, collect, releases, build, failure paths, render, site packaging, the
CLI, and the end-to-end pipeline.
"""

import contextlib
import io
import json
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import catalog
from catalog import (Settings, assign_filenames, assign_ids, build, canonical,
                     collect, checksum_of, derive_category,
                     digest_from_checksum_assets, format_last_update, harvest,
                     source_layers, normalize_repo_url, parse_repo_url, read_mirror,
                     read_manual, render_readme, slots, slugify, payload_table,
                     version_of, write_readme)

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

    def test_old_placeholder_record_is_not_carried_forward(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = write(root, additional=["https://github.com/Alpha/Tool"])
            settings.catalogue_file.write_text(json.dumps({"name": "x", "payloads": [
                {"id": "tool", "source": "https://github.com/alpha/tool", "name": "Tool",
                 "filename": "", "url": "", "unavailable": "no release found"}]}))

            slot_map = slots(settings)
            facts = {"https://github.com/alpha/tool":
                     fact("https://github.com/Alpha/Tool",
                          reason="no release found (or repo unreachable)")}
            document, counters = build(settings, slot_map, facts)

            self.assertEqual(document["payloads"], [])
            self.assertEqual(counters["carried"], 0)
            self.assertEqual(counters["placeholder"], 1)


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


# ─── CLI ─────────────────────────────────────────────────────────────

class CliEndToEnd(unittest.TestCase):
    def test_build_offline_and_render_via_the_documented_cli(self):
        build_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "build", "--offline"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        document = json.loads((ROOT / "payloads.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(document), ["name", "payloads"])
        self.assertTrue(all(p["filename"] and p["url"] and p["id"]
                            for p in document["payloads"]),
                        "every record must be installable-shaped")

        render_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "render"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(render_result.returncode, 0, render_result.stderr)


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
