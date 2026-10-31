# ps5-payloads-atlas

An aggregated catalogue of `.elf` payloads for
[ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager)'s
[custom repository format](https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md).
No binaries are hosted here: every entry links to an upstream release and belongs to
its author. Everything here is MIT licensed. Install third-party content at your own risk.

[![ps5-payloads-atlas](https://github.com/lucaszhongsj/ps5-payloads-atlas/actions/workflows/ps5-payloads-atlas.yml/badge.svg?branch=main)](https://github.com/lucaszhongsj/ps5-payloads-atlas/actions/workflows/ps5-payloads-atlas.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Quick start

Open the console's Payload Manager dashboard from a phone or PC browser. Sources are
managed there, not on the console itself.

1. Go to **Settings → Manage Sources → Add Source**.
2. Paste `https://lucaszhongsj.github.io/ps5-payloads-atlas/payloads.json`.
3. If the list stays empty, enable third-party payload repositories in Settings.

A CI job rebuilds the catalogue from upstream releases every 6 hours.

## Payloads

The full catalogue as of the last scheduled build:

<!-- STATS_START -->
**74 records** — Categories: Utilities & Tools 52, Networking & Servers 13, System & Jailbreak 6, Loaders 3.
<!-- STATS_END -->
<!-- PAYLOADS_START -->
| Source | Version | Category | Description | Updated |
| --- | --- | --- | --- | --- |
| [theghostonline/007-first-light-ps5](https://theghostonline.dev/theghostonline/007-first-light-ps5) | `v0.3.1` | Utilities & Tools | 007 First Light online on a jailbroken PS5, with the whole backend inside the payload. No PC needed. | `2026-10-22` |
| [elmonomalva0/any-pad-ps5](https://codeberg.org/elmonomalva0/any-pad-ps5) | `v0.9.5-beta` | Utilities & Tools | Free your PS5 from the DualSense | `2026-10-15` |
| [tsuramatsu1/apr-emu-updater](https://github.com/tsuramatsu1/apr-emu-updater) | `v2.0.6` | Utilities & Tools | PS5 payload that keeps APR Emu up to date on installed titles, from a web interface on the console. | `2026-08-29` |
| [bestpig/backpork](https://github.com/bestpig/backpork) | `0.1` | Utilities & Tools | Lets you sideload system libraries into PS5 games | `2026-05-01` |
| [itsblurf/bfpilot](https://github.com/itsblurf/bfpilot) | `v0.4.9` | Utilities & Tools | Lightweight PS5 file manager \| browser based | `2026-10-24` |
| [itsblurf/bfplayer](https://github.com/itsblurf/bfplayer) | `v0.1.0-alpha.44` | Utilities & Tools | A PS5 media and video player that also functions as a complete media library, with support for subtitles, mul… | `2026-07-31` |
| [notmaj0r/cheatrunner](https://github.com/notmaj0r/cheatrunner) | `v0.18` | Utilities & Tools | Web-Based Cheat Trainer for PS5! | `2026-10-11` |
| [ps5-payload-dev/elfldr](https://github.com/ps5-payload-dev/elfldr) | `v0.27` | Loaders | An ELF loader for jailbroken PS5s that accepts payloads on port 9021 | `2026-10-22` |
| [gronedwaffel/etahen-11.00-13.60](https://github.com/gronedwaffel/etahen-11.00-13.60) | `v2.5B-unified.1` | System & Jailbreak | Unofficial etaHEN 2.5B unified PS5 11.00-13.60 port: Toolbox, plugins and PS4/PS5 FPS. Original etaHEN by Lig… | `2026-10-06` |
| [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) | `1.16-ng-stable` | Networking & Servers | A simple FTP server for jailbroken PS4s and PS5s | `2026-09-21` |
| [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) | `v0.21.1` | Networking & Servers | An FTP server for jailbroken PS4s and PS5s | `2026-08-21` |
| [ruinelson/ftpsrv-streamextract](https://github.com/ruinelson/ftpsrv-streamextract) | `1.0.1` | Networking & Servers | A simple FTP server for jailbroken PS4s and PS5s | `2026-10-21` |
| [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) | `v1.15-beta1` | Utilities & Tools | — | `2026-10-23` |
| [earthonion/garlic-worker](https://git.etawen.dev/earthonion/garlic-worker) | `v1.1.7` | Utilities & Tools | — | `2026-09-04` |
| [ps5-payload-dev/gdbsrv](https://github.com/ps5-payload-dev/gdbsrv) | `v0.9` | Networking & Servers | A simple GDB server for jailbroken PS4s and PS5s | `2026-08-03` |
| [x-f1reball-x/hearbridge-ps5](https://github.com/x-f1reball-x/hearbridge-ps5) | `v1.4.0` | Utilities & Tools | Play PS5 game audio on any Bluetooth headphones or earbuds. Payload for jailbroken PS5 | `2026-10-30` |
| [stupiditytries/kabuki-ps5](https://github.com/stupiditytries/kabuki-ps5) | `v0.2.0-rc.1` | Utilities & Tools | Kabuki: a native ShellUI control-centre overlay for the PS5 that homebrew can add tiles to | `2026-10-17` |
| [mortyzip/keepawake](https://github.com/mortyzip/keepawake) | `v1.5.0` | Utilities & Tools | — | `2026-10-10` |
| [ps5-payload-dev/klogsrv](https://github.com/ps5-payload-dev/klogsrv) | `v0.9` | Networking & Servers | A socket server for jailbroken PS4s and PS5s that redirects /dev/klog to sockets connected on port 3232 | `2026-08-03` |
| [drakmor/kstuff-lite](https://github.com/drakmor/kstuff-lite) | `1.2-dr-test2` | System & Jailbreak | — | `2026-06-12` |
| [echostretch/kstuff-lite](https://github.com/echostretch/kstuff-lite) | `v1.11` | System & Jailbreak | — | `2026-09-21` |
| [aydencharles/kylin-core-release](https://github.com/aydencharles/kylin-core-release) | `v2.0.0-community-lite` | Utilities & Tools | kylin-core-release | `2026-10-01` |
| [zizc3/liveshell](https://github.com/zizc3/liveshell) | `v1.6.0` | Utilities & Tools | Animated backgrounds for PS5 home screen. | `2026-10-27` |
| [seregonwar/memdbg](https://github.com/seregonwar/memdbg) | `nightly-20260930-g6e493c9` | Utilities & Tools | MemDBG is a high-performance memory debugging and inspection suite designed for PlayStation 4 and PlayStation… | `2026-09-30` |
| [drakmor/nanodns](https://github.com/drakmor/nanodns) | `0.4` | Networking & Servers | Playstation 4/5 DNS proxy server | `2026-08-05` |
| [gasb07/neoenabler](https://github.com/gasb07/neoenabler) | `v0.6.0` | Utilities & Tools | Allows PS4 games with no PS4 Support to receive patches via illusionyy's ps-patch-system that can unlock high… | `2026-10-30` |
| [earthonion/np-fake-signin](https://git.etawen.dev/earthonion/np-fake-signin) | `v1.4` | Utilities & Tools | — | `2026-10-02` |
| [theghostonline/nuvio-ps5](https://theghostonline.dev/theghostonline/nuvio-ps5) | `v1.9.1` | Utilities & Tools | Nuvio as a PS5 app, with a native 4K HDR player built for the console's own video hardware. | `2026-10-20` |
| [diegobarbosaa/omnipad-ps5](https://github.com/diegobarbosaa/omnipad-ps5) | `v1.0.4-hotfix1` | Utilities & Tools | Universal controller engine & Web Dashboard for PlayStation 5 (FW 7.00 - 13.60) | `2026-10-06` |
| [aydencharles/onionhen](https://github.com/aydencharles/onionhen) | `v0.9.0` | System & Jailbreak | Yet another HEN enabler for jailbroken PS5 | `2026-10-15` |
| [michele-m-media/pizza-hen](https://github.com/michele-m-media/pizza-hen) | `v2.00` | System & Jailbreak | — | `2026-08-25` |
| [plabs5/plinux5-ng](https://github.com/plabs5/plinux5-ng) | `v0.1.0` | Utilities & Tools | PS5 Linux for high FW's (8.xx, 9.xx, 10.xx, 11.xx, 12.xx, 13.xx) | `2026-10-14` |
| [itsblurf/poords4](https://github.com/itsblurf/poords4) | `v0.2.0` | Utilities & Tools | Use a wireless DualShock 4 in native PS5 games on jailbroken consoles. | `2026-10-21` |
| [x1nons/prefbar](https://github.com/x1nons/prefbar) | `v0.1.3` | Utilities & Tools | PerfBar - On-Screen Performance Overlay for Jailbroken PS5 | `2026-10-21` |
| [notmaj0r/prosperomgr](https://github.com/notmaj0r/prosperomgr) | `v1.1` | Utilities & Tools | All-In-One manager for your PS5! | `2026-09-29` |
| [illusionyy/ps-patch-system](https://github.com/illusionyy/ps-patch-system) | `38108724867` | Utilities & Tools | App patching system for PS4/PS5 | `2026-10-11` |
| [mounirhero/ps-play](https://github.com/mounirhero/ps-play) | `2.1` | Utilities & Tools | — | `2026-08-15` |
| [gasb07/ps4mount](https://github.com/gasb07/ps4mount) | `v0.7.2` | Utilities & Tools | Allows for PKG games on USB external devices to mount on jailbroken PS5s without installing on internal stora… | `2026-10-30` |
| [eladharels/ps5-60fps](https://github.com/eladharels/ps5-60fps) | `v1.0.0` | Utilities & Tools | — | `2026-10-16` |
| [echostretch/ps5-app-dumper](https://github.com/echostretch/ps5-app-dumper) | `v2.10` | Utilities & Tools | — | `2026-10-03` |
| [owendswang/ps5-aria2](https://github.com/owendswang/ps5-aria2) | `v1.37.0-3` | Utilities & Tools | aria2 for PS5 | `2026-10-05` |
| [kerrdec97/ps5-date-time-sync](https://github.com/kerrdec97/ps5-date-time-sync) | `v1.0.0` | Utilities & Tools | Standalone PS5 payload that automatically restores the system date and time using public NTP servers. | `2026-08-24` |
| [quer3q/ps5-dump-forge](https://github.com/quer3q/ps5-dump-forge) | `v0.5.0` | Utilities & Tools | A toolkit for working with PS5 game dumps. Cross-platform - including the PS5 itself. | `2026-10-30` |
| [marice/ps5-exporter](https://github.com/marice/ps5-exporter) | `v0.3.1` | Utilities & Tools | Prometheus exporter payload for a jailbroken PS5: temperatures, uptime, storage and ShadowMountPlus game stat… | `2026-10-20` |
| [owendswang/ps5-fan-control](https://github.com/owendswang/ps5-fan-control) | `v0.3` | Utilities & Tools | Small PS5 daemon keeps applying fan temperature threshold. | `2026-08-09` |
| [juma-sayeh/ps5-file-explorer](https://github.com/juma-sayeh/ps5-file-explorer) | `v0.2.1` | Utilities & Tools | Browser-based PS5 file explorer payload | `2026-06-19` |
| [gcoding97/ps5-game-compressor](https://github.com/gcoding97/ps5-game-compressor) | `v1.1.1` | Utilities & Tools | Standalone PS5 payload for compressing, unpacking, validating, and repairing ShadowMountPlus-mounted games | `2026-10-02` |
| [theghostonline/ps5-game-updater](https://theghostonline.dev/theghostonline/ps5-game-updater) | `v1.1.2` | Utilities & Tools | Update your installed PS5 games in a few taps, on the console. Finds the newest official update for each game… | `2026-10-28` |
| [itsplk/ps5-lapy-jb-daemon](https://github.com/itsplk/ps5-lapy-jb-daemon) | `v1.2` | System & Jailbreak | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. Multi-firmware (3.00 t… | `2026-06-02` |
| [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) | `v2.5` | Loaders | Linux payload implementing HV exploits to run a custom bootloader | `2026-09-05` |
| [theghostonline/ps5-lz4-compression](https://theghostonline.dev/theghostonline/ps5-lz4-compression) | `v1.6.4` | Utilities & Tools | Shrink PS5 games on the console itself with LZ4 asset packs and .ffpfsc compression. | `2026-10-26` |
| [knutwurst/ps5-patchdl](https://github.com/knutwurst/ps5-patchdl) | `v0.3.11` | Utilities & Tools | Official updates for your PS5 and PS4 games, from any browser. PatchDL runs on the PS5, finds the newest upda… | `2026-10-29` |
| [itsplk/ps5-payload-manager](https://github.com/itsplk/ps5-payload-manager) | `v0.6.3` | Utilities & Tools | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-10-19` |
| [itsplk/ps5-pkg-manager](https://github.com/itsplk/ps5-pkg-manager) | `v1.5.1` | Utilities & Tools | A clean and intuitive package manager for PS5 | `2026-10-10` |
| [owendswang/ps5-syslang](https://github.com/owendswang/ps5-syslang) | `v0.3` | Utilities & Tools | Small PS5 payload for switching the ShellUI system language. | `2026-10-19` |
| [xvvulcanvx/ps5-tabshifter](https://github.com/xvvulcanvx/ps5-tabshifter) | `v1.3.0` | Utilities & Tools | Standalone PS5 on-console payload to move apps between Games/Media tabs and hide offline PSN bloatware (Unive… | `2026-10-25` |
| [holdmysocks/ps5-tailscale](https://github.com/holdmysocks/ps5-tailscale) | `v0.7.1` | Networking & Servers | Tailscale for jailbroken PS5: reach the console over your tailnet for Remote Play and stream to it with Moonl… | `2026-10-07` |
| [neokuze/ps5-tailscale](https://github.com/neokuze/ps5-tailscale) | `1.0.0` | Networking & Servers | Tailscale for jailbroken PS5: reach the console over your tailnet for Remote Play | `2026-10-10` |
| [owendswang/ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) | `v1.13-rc1` | Utilities & Tools | A file manager for PS5 with a web UI. | `2026-10-30` |
| [itsplk/ps5-webkit-autoloader](https://github.com/itsplk/ps5-webkit-autoloader) | `v0.6.2` | Loaders | An automated payload loader for exploited PS5 consoles | `2026-10-28` |
| [junleb/ps5console](https://github.com/junleb/ps5console) | `6.5.1` | Networking & Servers | PS5 Console 一体化 PS5 本地控制中心，将游戏挂载、存档管理、USB 手柄兼容、FTP、风扇温控和 ELF 管理整合到一个 Payload 与 Web UI 中。 当前项目用于已具备 Payload 运行… | `2026-08-31` |
| [pharaoh2k/ps5debug-ng](https://github.com/pharaoh2k/ps5debug-ng) | `1.3.2` | Utilities & Tools | PS5 debugger payload - userland TCP wire-protocol server hosted inside SceShellCore. GPL-3. | `2026-09-23` |
| [heni0xyz/ps5save](https://github.com/heni0xyz/ps5save) | `v2` | Utilities & Tools | USB save backup utility for jailbroken PS5’s | `2026-10-22` |
| [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) | `v10.0.2` | Networking & Servers | Send games, apps and homebrew to a jailbroken PS5, and manage the console from your computer, phone or browse… | `2026-10-31` |
| [armanate/rdr2-60fps-runtime-patcher](https://github.com/armanate/rdr2-60fps-runtime-patcher) | `v2.0` | Utilities & Tools | Unlocks 60 FPS in Red Dead Redemption 2 (PS4, v1.32) on a jailbroken PS5. | `2026-10-11` |
| [elripalda/recompstore](https://github.com/elripalda/recompstore) | `v2.7.4` | Utilities & Tools | RecompStore: the free homebrew app store for jailbroken PS5. Installs and updates recompiled game ports, emul… | `2026-10-30` |
| [drakmor/shadowmountplus](https://github.com/drakmor/shadowmountplus) | `1.7beta11` | Utilities & Tools | Automated background auto-mounter payload for jailbroken PS5 consoles. Detects, mounts, and installs game bac… | `2026-10-30` |
| [ps5-payload-dev/shsrv](https://github.com/ps5-payload-dev/shsrv) | `v0.20` | Networking & Servers | A simple telnet-like shell server for jailbroken PS5s that accepts connections on port 2323 | `2026-08-03` |
| [bizkut/unrar-ps5](https://github.com/bizkut/unrar-ps5) | `v1.4.0` | Utilities & Tools | PS5 UnRAR payload for extracting homebrew archives | `2026-06-18` |
| [ps5-payload-dev/websrv](https://github.com/ps5-payload-dev/websrv) | `v0.35` | Networking & Servers | A web server for jailbroken PS5s that accepts connections on port 8080 | `2026-10-11` |
| [ghost1372/welcomehubactivator](https://github.com/ghost1372/welcomehubactivator) | `v1.2.0` | Utilities & Tools | A PS5 ELF payload that enables the Welcome Hub. | `2026-10-24` |
| [owendswang/wfm-7zip-helper](https://github.com/owendswang/wfm-7zip-helper) | `v26.04-0` | Utilities & Tools | A separate extraction helper based on 7zip for PS5 Web File Manager. | `2026-10-22` |
| [megacadedev/yetanothercontrollerenabler](https://github.com/megacadedev/yetanothercontrollerenabler) | `v0.0.1` | Utilities & Tools | YetAnotherControllerEnabler is a homebrew payload for a PS5. It lets a controller from another console play o… | `2026-10-04` |
| [seregonwar/zftpd](https://github.com/seregonwar/zftpd) | `v1.7.0` | Networking & Servers | Zero-copy FTP/HTTP Daemon compatible with all POSIX systems | `2026-10-28` |
<!-- PAYLOADS_END -->
`Source` links to the upstream repository; `Updated` is that release's publish date.

## Notes

- **Missing a payload?** Only `.elf` release assets are listed. A repo whose latest
  release ships none does not appear; request it in an issue.
- **Two similar entries?** `source`, the repository, is the identity. Forks are
  separate payloads.
- **Install names.** `filename` is the client's install key: lowercase and globally
  unique. When two entries ship the same name, the loser installs under its `id`.
- **Disappearing entries?** A failed fetch keeps the last good record. A repo that
  never resolved waits outside the catalogue and returns by itself once it resolves.
- **Checksums.** Copied from the upstream release: the API digest when present, or
  the release's own `SHA256SUMS` / `.sha256` file. Never computed here.
- **Prereleases count.** The newest release wins, `-rc` / `-beta` included: a fresh
  pre-release updates the catalogue without waiting for a stable tag. Drafts never ship.

## Maintaining

`sources/` is the only writable surface. `manual/` holds everything a human edits;
`mirror/` belongs to the collector.

| File | Meaning | Written by |
| --- | --- | --- |
| `sources/manual/additional.json` | repos nobody else lists | you |
| `sources/manual/manual.toml` | corrections to a listed repo | you |
| `sources/mirror/mirror.toml` | which repository each mirror copies | you |
| `sources/mirror/*.json` | snapshots of upstream lists | `collect` |

Layers merge in a fixed order: additional, then manual, then mirrors alphabetically.
Curated answers land before mirrored copies. Every file under `sources/` is kept in
dictionary order (case-insensitive); the build refuses an unsorted file.

- **Add a repo.** One url line in `additional.json`. A JSON there holds url strings
  only; any judgement belongs in the TOML beside it.
- **Correct a repo.** Add a table keyed by the repo url to `manual.toml`.
  `asset_pattern = '^that-one\.elf$'` picks the asset (`re.search`, case-insensitive).
  `skip = true` removes it from every source, with the reason in a comment above the
  table. An empty table is rejected, and a correction nothing else lists is reported
  as an intake entry.
- **Mirror another list.** Add a table keyed by their repository to `mirror.toml`,
  with `url` pointing at its list, then run `collect`. The snapshot lands as
  `<repo>.json`, named after the key's repo segment in lowercase. `collect` never
  deletes and refuses to shrink a mirror by more than 30% in one run; `--force`
  accepts that on purpose.

### Pipeline

| Command | Does |
| --- | --- |
| `python scripts/atlas.py collect` | refresh mirror snapshots (network) |
| `python scripts/atlas.py build` | observe releases, shape `payloads.json` (network) |
| `python scripts/atlas.py build --offline` | re-shape from `build/releases.json`, no network |
| `python scripts/atlas.py render` | regenerate the blocks in this page (idempotent) |
| `python scripts/atlas.py site` | package `_site/` for Pages (needs `GH_TOKEN`) |

Requires Python 3.11+ (`tomllib`) and an authenticated `gh` CLI for `build`. Tests:
`python3 -m unittest discover -s tests` (no network). Do not hand-edit the content
between the `STATS` / `PAYLOADS` markers; `render` owns it.

