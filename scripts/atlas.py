#!/usr/bin/env python3
"""The atlas pipeline behind one entry point — four stages, one command each.

    python scripts/atlas.py collect [--force]   # refresh mirror snapshots (network)
    python scripts/atlas.py build [--offline]   # observe + shape the catalogue (network)
    python scripts/atlas.py render              # refresh the README page (idempotent)
    python scripts/atlas.py site                # package _site/ for Pages (needs GH_TOKEN)

All pipeline logic lives in scripts/catalog.py; this file is only the CLI
surface: argv, env vars, exit codes.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog
from catalog import Settings


def cmd_collect(settings: Settings, argv: list[str]) -> None:
    """Stage 1 — refresh the mirrors listed in sources/mirror/mirror.toml."""
    catalog.collect(settings, force="--force" in argv)


def cmd_build(settings: Settings, argv: list[str]) -> None:
    """Stage 2 — observe every repo, then shape the client catalogue.

    Two sub-stages, one command, because they belong to different worlds:
    observe talks to GitHub/Gitea/Codeberg once per repo (network, slow), build
    shapes those observations into the client schema (pure, instant). The
    observation is written to build/releases.json, so --offline re-shapes the
    catalogue without touching the network again.
    """
    offline = "--offline" in argv
    slots = catalog.slots(settings)
    active = [slot for slot in slots.values() if not slot.get("exclude")]

    if offline:
        facts = catalog.load_observations(settings)
        if not facts:
            sys.exit(f"error: --offline needs {settings.facts_file}; "
                     "run once without it first")
        print(f"Reusing {len(facts)} observations from {settings.facts_file.name}")
    else:
        facts = catalog.observe(active)
        catalog.save_observations(settings, facts)

    document, counters = catalog.build(settings, slots, facts)
    catalog.atomic_write_json(settings.catalogue_file, document)

    stale = sum(1 for fact in facts.values() if fact.get("stale_pattern"))
    ambiguous = sum(1 for fact in facts.values() if fact.get("ambiguous"))
    redundant = sum(1 for fact in facts.values() if fact.get("redundant_pattern"))
    print(f"\nWrote {settings.catalogue_file.name}: {len(document['payloads'])} records, "
          f"{counters['excluded']} skipped by source, {counters['deduped']} deduped, "
          f"{counters['carried']} carried over, {counters['placeholder']} placeholders, "
          f"{stale} stale patterns, {ambiguous} ambiguous assets, {redundant} redundant patterns")


def cmd_render(settings: Settings, argv: list[str]) -> None:
    """Stage 3 — refresh the generated blocks in README.md. Always idempotent."""
    catalog.render_readme(settings)


def cmd_site(settings: Settings, argv: list[str]) -> None:
    """Stage 4 — package `_site/` for Pages: the rendered README plus the catalogue."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("error: site needs GH_TOKEN (the markdown API is authenticated)")
    body = catalog.render_markdown(settings.readme_file.read_text(encoding="utf-8"), token)
    settings.site_dir.mkdir(exist_ok=True)
    (settings.site_dir / "index.html").write_text(catalog.page_html(body), encoding="utf-8")
    (settings.site_dir / "payloads.json").write_bytes(settings.catalogue_file.read_bytes())
    print(f"Packed {settings.site_dir.name}/: index.html + {settings.catalogue_file.name}")


COMMANDS = {"collect": cmd_collect, "build": cmd_build,
            "render": cmd_render, "site": cmd_site}


def main(argv: list[str]) -> None:
    if not argv or argv[0] not in COMMANDS:
        sys.exit(f"usage: atlas.py {'|'.join(COMMANDS)} [--force | --offline]")
    settings = Settings()
    COMMANDS[argv[0]](settings, argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
