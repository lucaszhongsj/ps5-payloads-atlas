# ps5-payloads-atlas

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors).

The aggregator composes three layers:

- **Discovery** — the upstream repo list is the union of [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror) catalog and [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) `CATALOGUE`. Both are first-class sources; new payloads in either appear here automatically. The mirror's `payloads_v2.json` (object wrapper + `icons_url`) is the format read here. Additional plugin information compiled by `tekqart` forum user `@a83848400` has been merged into `sources.json` by hand.
- **Curation** — `sources.json` overrides display name / description / asset selection per repo, and can `"exclude": true` to suppress a repo entirely.
- **Enrichment** — `phantomptr/ps5upload` `CATALOGUE` provides longer descriptions / display names where available; the mirror supplies the category and `icon_key` for the repos it already curates.

**A GitHub Action refreshes `payloads.json` every 3 hours.**

## Files

- `payloads.json` — the catalogue consumed by ps5-payload-manager (`Settings → Manage Sources → Add Source`, paste the raw URL).
- `icons.json` — content-addressed icon catalog referenced by the top-level `icons_url`; keys are SHA-256 hashes of the data URI, so identical images share one entry.
- `sources.json` — curation overlay (override / exclude). Acts as fallback seed if discovery fails.
- `update_payloads.py` — the aggregator.

## Catalogue schema

`payloads.json` follows the [custom repository format](https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md): object wrapper with `name`, optional `icons_url`, and the `payloads` array.

- `id` — stable slug. It starts as exactly what the manager derives from `name` by default (collisions get `-2`, `-3`), so existing installs keep their slots, and it is then carried over from the previous `payloads.json` so a later display-name change no longer orphans favorites or autoload entries.
- `category` — the mirror's four-category vocabulary (`System & Jailbreak`, `Networking & Servers`, `Loaders`, `Utilities & Tools`). Entries the mirror already curates reuse its category verbatim; the rest are classified by the rules in `update_payloads.py`.
- `last_update` — ISO 8601 with the UTC+8 offset (`2026-10-22T04:55:47+08:00`); the manager parses it as the version tie-breaker. The README table shows the date part only.
- `checksum` — SHA-256 hex or empty. The manager rejects an entry whose non-empty checksum is malformed, so values are validated before writing.

## `sources.json` schema

Each entry is one upstream repo. Only `url` is required; every other field is an optional override with the fallback shown.

| Field | Required | Purpose | Fallback if omitted |
| --- | --- | --- | --- |
| `url` | yes | Repo HTML URL — the entry's identity and API lookup key | — |
| `display_name` | no | Overrides the output `name` | ps5upload `display_name` → repo name from URL |
| `description` | no | Overrides the output `description` | ps5upload / itsPLK description → empty |
| `asset_pattern` | no | Regex narrowing which release asset to pick (multiple `.elf` files) | ps5upload `asset_name_hint` → itsPLK `asset_pattern` → no filter |
| `exclude` | no | `true` skips this repo entirely | `false` (include) |

Same repo under multiple aliases (e.g. `LightningMods/etaHEN` and `etaHEN/etaHEN`) needs one entry per alias if you want to override or exclude both.

## Notes

- This repository aggregates **metadata only** (name, description, version, checksum, download URL) about third-party PS5 payload projects. The upstream payloads themselves remain the property of their respective authors under their own licenses. The MIT license above covers only the aggregation script, the curated `sources.json`, and the generated `payloads.json`.
- No binaries are hosted here. `url` points at the upstream release asset; download happens on the PS5 side.
- Checksums come from the GitHub Release API `digest` field. Non-GitHub repos (Forgejo instances such as `git.etawen.dev` and `git.earthonion.com`) and assets without a published digest have an empty `checksum`.
- `LightningMods/Itemzflow` is auto-skipped — its releases ship no `.elf`/`.bin` asset, so the aggregator finds no canonical asset to list. Repos that are curated in `sources.json` but produce no payload (no matching asset, or the repo is unreachable) are listed under a top-level `skipped` array in `payloads.json` so the gap is visible in the data itself. `skipped` entries intentionally carry only `url` + `reason` — adding `name`/`filename`/`url` would make the ps5-payload-manager parser ingest them as installable payloads.
- Pre-release-only repos fall back to the most recent pre-release.
- Repos are deduped by canonical `(owner, repo)` after redirect resolution (e.g. `LightningMods/etaHEN` folds into `etaHEN/etaHEN`).
- **Filename collisions**: `filename` is the client's install key and on-disk name. Two entries sharing a filename (e.g. two forks both shipping `kstuff.elf`) overwrite each other on install — the later one wins. This is inherent to the client, not something this catalogue can fix without renaming upstream assets. For the same reason, when this catalogue corrects which asset it points at (via `asset_pattern`), the `filename` may change — users who installed the old asset will see the corrected one as a new install rather than an in-place upgrade.
- Running `update_payloads.py` locally requires the [`gh` CLI](https://cli.github.com/) to be installed and authenticated (`gh auth login`) — the GitHub API is queried through it. Python 3.10+ is required (the script uses `dict | None` annotations). PIL/Pillow is optional — without it, icon generation for repos the mirror does not cover is skipped and the existing `icons.json` entries are kept.

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **007 First Light PS5 Online** | `v0.3.1` | Utilities & Tools | 007 First Light (PPSA11386) online on a jailbroken PS5, with no IOI servers involved and no PC needed. One payload does everything on the console, so the online features and TacSim work. | `2026-10-22` | [theghostonline/007-first-light-ps5](https://theghostonline.dev/theghostonline/007-first-light-ps5) |
| **AnyPad PS5** | `v0.9.5-beta` | Utilities & Tools | A Bluetooth controller bridge for jailbroken PS5 consoles. Un puente de mandos Bluetooth para PS5 con jailbreak. | `2026-10-15` | [elmonomalva0/any-pad-ps5](https://codeberg.org/elmonomalva0/any-pad-ps5) |
| **APR Emu Updater** | `v2.0.6` | Utilities & Tools | PS5 payload that keeps APR Emu up to date on installed titles, from a web interface on the console. | `2026-08-29` | [tsuramatsu1/apr-emu-updater](https://github.com/tsuramatsu1/apr-emu-updater) |
| **BackPork (backport helper)** | `0.1` | Utilities & Tools | Runs in the background and watches for game launches. When a title starts, it looks for a `fakelib` folder inside that game's install directory and union-mounts it over the sandbox's `common/lib`, so the game loads newer system libraries without altering the originals. This is the runtime half of backporting a game to older firmware — use it together with the SDK Version Changer, which lowers the SDK version recorded in `eboot.bin` and every `prx`/`sprx`. A title needs both: downgraded ELFs so the system agrees to launch it, and compatible libraries so it does not crash on missing imports. The libraries themselves usually need patching to drop imports your firmware lacks; upstream ships BPS patch sets for 6.xx and 7.xx. | `2026-05-01` | [bestpig/backpork](https://github.com/bestpig/backpork) |
| **BFpilot** | `v0.4.4` | Utilities & Tools | Web-based PS5 file manager serving a browser interface on port 5905 for browsing and managing console files. | `2026-08-12` | [itsblurf/bfpilot](https://github.com/itsblurf/bfpilot) |
| **BFplayer** | `v0.1.0-alpha.44` | Utilities & Tools | A PS5 media and video player that also functions as a complete media library, with support for subtitles, multiple audio tracks, aspect-ratio adjustment, cropping, and many other playback settings. | `2026-07-31` | [itsblurf/bfplayer](https://github.com/itsblurf/bfplayer) |
| **CheatRunner** | `v0.18` | Utilities & Tools | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-10-11` | [notmaj0r/cheatrunner](https://github.com/notmaj0r/cheatrunner) |
| **elfldr** | `v0.27` | Loaders | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-10-22` | [ps5-payload-dev/elfldr](https://github.com/ps5-payload-dev/elfldr) |
| **etaHEN** | `2.5B` | System & Jailbreak | AIO HEN payload | `2025-12-25` | [etahen/etahen](https://github.com/etahen/etahen) |
| **etaHEN** | `v2.5B-unified.1` | System & Jailbreak | Unofficial etaHEN 2.5B unified PS5 11.00-13.60 port: Toolbox, plugins and PS4/PS5 FPS. Original etaHEN by LightningMods and contributors. | `2026-10-06` | [gronedwaffel/etahen-11.00-13.60](https://github.com/gronedwaffel/etahen-11.00-13.60) |
| **ftpsrv** | `v0.21.1` | Networking & Servers | Lightweight FTP server on :2121 with SELF↔ELF auto-decryption and remount-RW SITE commands. Lets you browse the PS5's filesystem from any FTP client. | `2026-08-21` | [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) |
| **ftpsrv (drakmor)** | `1.16-ng-stable` | Networking & Servers | A simple FTP server for jailbroken PS4s and PS5s | `2026-09-21` | [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) |
| **Ftpsrv Streamextract** | `1.0.1` | Networking & Servers | This is a simple FTP server that can be executed on a Playstation 4 or Playstation 5 that has been jailbroken and is running an ELF loader. The FTP server accepts connection on port 2121. | `2026-10-21` | [ruinelson/ftpsrv-streamextract](https://github.com/ruinelson/ftpsrv-streamextract) |
| **Garlic SaveMgr for PS5** | `v1.14` | Utilities & Tools | PS5 save decrypt/encrypt/browse with embedded web UI. | `2026-10-21` | [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) |
| **Garlic Worker** | `v1.1.7` | Utilities & Tools | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. Opt-in: connects to garlicsaves.com. | `2026-09-04` | [earthonion/garlic-worker](https://git.etawen.dev/earthonion/garlic-worker) |
| **gdbsrv-ps5** | `v0.9` | Networking & Servers | GDB remote debugging service payload for inspecting PS5 game processes. | `2026-08-03` | [ps5-payload-dev/gdbsrv](https://github.com/ps5-payload-dev/gdbsrv) |
| **HearBridge PS5** | `v1.3.6` | Utilities & Tools | Bluetooth A2DP audio bridge for PS5 homebrew | `2026-10-18` | [x-f1reball-x/hearbridge-ps5](https://github.com/x-f1reball-x/hearbridge-ps5) |
| **KeepAwake** | `v1.5.0` | Utilities & Tools | A PS5 and PS4 payload that stops the console from going into rest mode while it runs. | `2026-10-10` | [mortyzip/keepawake](https://github.com/mortyzip/keepawake) |
| **klogsrv** | `v0.9` | Networking & Servers | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). | `2026-08-03` | [ps5-payload-dev/klogsrv](https://github.com/ps5-payload-dev/klogsrv) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | System & Jailbreak | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Recent builds extended firmware coverage through FW 12.xx (the '12.xx Support' update) on top of the original 3.00→10.01 range — check the release notes for your exact firmware. Adds an option to disable automatic mounting (noautomount) for a controlled startup. Recommended when your primary workflow is ShadowMount+ with .ffpkg/.exfat/PFS images. Same load-first ordering as any other kstuff: must boot before ShadowMount+ or ps5upload. | `2026-05-31` | [drakmor/kstuff-lite](https://github.com/drakmor/kstuff-lite) |
| **kstuff-lite (EchoStretch)** | `v1.11` | System & Jailbreak | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00–12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-09-21` | [echostretch/kstuff-lite](https://github.com/echostretch/kstuff-lite) |
| **Kylin Core** | `v2.0.0-community-lite` | Utilities & Tools | A homebrew cheat loader and real-time game modifier for PlayStation 5 | `2026-10-01` | [aydencharles/kylin-core-release](https://github.com/aydencharles/kylin-core-release) |
| **Lapy-JB-Daemon** | `v1.2` | System & Jailbreak | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. | `2026-06-02` | [itsplk/ps5-lapy-jb-daemon](https://github.com/itsplk/ps5-lapy-jb-daemon) |
| **LiveShell** | `v1.6.0` | Utilities & Tools | Animated backgrounds for PS5 home screen. | `2026-10-27` | [zizc3/liveshell](https://github.com/zizc3/liveshell) |
| **LZ4 Compression for PS5** | `v1.6.4` | Utilities & Tools | Shrink your PS5 games on the console itself. Pick a game, choose Compress with LZ4, and it packs the game data into LZ4 asset packs that APR-EMU reads while the game runs. Every file gets checked before anything's deleted, and if the game doesn't ship APR-EMU, the right runtime is added for you. | `2026-10-26` | [theghostonline/ps5-lz4-compression](https://theghostonline.dev/theghostonline/ps5-lz4-compression) |
| **nanoDNS** | `0.4` | Networking & Servers | Minimal DNS server running on the PS5 (UDP :53). Blocks PlayStation Network + update domains by default and can redirect any domain to a LAN IP. | `2026-08-05` | [drakmor/nanodns](https://github.com/drakmor/nanodns) |
| **NeoEnabler** | `v0.6.0` | Utilities & Tools | Allows PS4 games with no PS4 Support to receive patches via illusionyy's ps-patch-system that can unlock higher resolutions | `2026-10-30` | [gasb07/neoenabler](https://github.com/gasb07/neoenabler) |
| **NP Fake Signin** | `v1.4` | Utilities & Tools | ELF payload for PS4/PS5 that fakes PSN sign-in for the foreground user by writing NP files and patching registry/ShellCore state. | `2026-10-02` | [earthonion/np-fake-signin](https://git.etawen.dev/earthonion/np-fake-signin) |
| **Nuvio PS5** | `v1.9.1` | Utilities & Tools | Nuvio as a PS5 app, with a native 4K HDR player built for the console's own video hardware. | `2026-10-20` | [theghostonline/nuvio-ps5](https://theghostonline.dev/theghostonline/nuvio-ps5) |
| **onionHEN** | `v0.9.0` | System & Jailbreak | OnionHEN is a homebrew enabler and Toolbox for jailbroken PS5 consoles, built on etaHEN. It prepares the system, injects a Toolbox into the home screen, and adds cheats, in-game overlays, payload management, and background services. | `2026-10-15` | [aydencharles/onionhen](https://github.com/aydencharles/onionhen) |
| **PerfBar** | `v0.1.3` | Utilities & Tools | A standalone on-screen performance overlay for the PS5. It draws FPS, frametimes, 1% lows, CPU/SoC temperatures, and RAM/VRAM usage directly over your games. | `2026-10-21` | [x1nons/prefbar](https://github.com/x1nons/prefbar) |
| **PKG-Manager** | `v1.5.1` | Utilities & Tools | Browse and install PKGs from USB, disc, or SMB shares directly on your PS5 | `2026-10-10` | [itsplk/ps5-pkg-manager](https://github.com/itsplk/ps5-pkg-manager) |
| **pLinux5-NG** | `v0.1.0` | Utilities & Tools | boot linux on PS5 consoles running high firmware (8.xx through 13.60) | `2026-10-14` | [plabs5/plinux5-ng](https://github.com/plabs5/plinux5-ng) |
| **PoorDS4** | `v0.2.0` | Utilities & Tools | Use a wireless DualShock 4 in native PS5 games on jailbroken consoles. | `2026-10-21` | [itsblurf/poords4](https://github.com/itsblurf/poords4) |
| **ps-patch-system** | `38108724867` | Utilities & Tools | App patching system | `2026-10-11` | [illusionyy/ps-patch-system](https://github.com/illusionyy/ps-patch-system) |
| **PS4Mount** | `v0.7.2` | Utilities & Tools | Allows for PKG games on USB external devices to mount on jailbroken PS5s without installing on internal storage or PS5 formatted USB storage | `2026-10-30` | [gasb07/ps4mount](https://github.com/gasb07/ps4mount) |
| **PS5 aria2** | `v1.37.0-3` | Utilities & Tools | This fork builds aria2 as a PS5 ELF payload. | `2026-10-05` | [owendswang/ps5-aria2](https://github.com/owendswang/ps5-aria2) |
| **PS5 Console** | `6.5.1` | Networking & Servers | Web-based PS5 control center combining game mounting, save management, USB controller support, FTP, fan control, and ELF management. | `2026-08-31` | [junleb/ps5console](https://github.com/junleb/ps5console) |
| **PS5 File Explorer** | `v0.2.1` | Utilities & Tools | BFpilot-derived web file manager for browsing and managing files on a jailbroken PS5. | `2026-06-19` | [juma-sayeh/ps5-file-explorer](https://github.com/juma-sayeh/ps5-file-explorer) |
| **PS5 Game Compressor** | `v1.1.1` | Utilities & Tools | Standalone PS5 payload for compressing, unpacking, validating, and repairing ShadowMountPlus-mounted games | `2026-10-02` | [gcoding97/ps5-game-compressor](https://github.com/gcoding97/ps5-game-compressor) |
| **PS5 Game Updater** | `v1.1.2` | Utilities & Tools | Update your installed PS5 games in a few taps, on the console. Finds the newest official update for each game and installs it, and applies a backport when an update needs a newer firmware than yours. No PC needed. | `2026-10-28` | [theghostonline/ps5-game-updater](https://theghostonline.dev/theghostonline/ps5-game-updater) |
| **PS5 TabShifter** | `v1.3.0` | Utilities & Tools | Standalone PS5 on-console payload to move apps between Games/Media tabs and hide offline PSN bloatware (FW 13.60 supported). | `2026-10-25` | [xvvulcanvx/ps5-tabshifter](https://github.com/xvvulcanvx/ps5-tabshifter) |
| **PS5 Tailscale** | `v0.7.1` | Networking & Servers | Tailscale for jailbroken PS5: reach the console over your tailnet and stream to it with Moonlight/Sunshine (unofficial) | `2026-10-07` | [holdmysocks/ps5-tailscale](https://github.com/holdmysocks/ps5-tailscale) |
| **PS5 Web File Manager** | `v1.13-rc1` | Utilities & Tools | Web-based file manager for jailbroken PS5. Serves a browser UI over HTTP so you can browse, transfer, and manage files on the console's internal storage from any device on the LAN. | `2026-10-30` | [owendswang/ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) |
| **PS5 WebKit Autoloader** | `v0.6.2` | Loaders | Automatically loads the WebKit exploit and your elf payloads. | `2026-10-28` | [itsplk/ps5-webkit-autoloader](https://github.com/itsplk/ps5-webkit-autoloader) |
| **ps5-60FPS** | `v1.0.0` | Utilities & Tools | Unlock 60 FPS in PS4 and PS5 games on a jailbroken PS5, with one switch per game. | `2026-10-16` | [eladharels/ps5-60fps](https://github.com/eladharels/ps5-60fps) |
| **ps5-app-dumper** | `v2.10` | Utilities & Tools | Dumps the running game, decrypted, to a USB drive or the console, one at a time or as a queue. ps5upload drives it from Games → Dumps (enter the code the TV shows once); it also has a web page of its own on port 8081. | `2026-10-03` | [echostretch/ps5-app-dumper](https://github.com/echostretch/ps5-app-dumper) |
| **ps5-date-time-sync** | `v1.0.0` | Utilities & Tools | Automatically restores the system date and time using public NTP servers | `2026-08-24` | [kerrdec97/ps5-date-time-sync](https://github.com/kerrdec97/ps5-date-time-sync) |
| **ps5-dump-forge** | `v0.5.0` | Utilities & Tools | A toolkit for working with PS5 game dumps | `2026-10-30` | [quer3q/ps5-dump-forge](https://github.com/quer3q/ps5-dump-forge) |
| **ps5-exporter** | `v0.3.1` | Utilities & Tools | Prometheus exporter for a jailbroken PS5 | `2026-10-20` | [marice/ps5-exporter](https://github.com/marice/ps5-exporter) |
| **ps5-fan-control** | `v0.3` | Utilities & Tools | Standalone PS5 fan controller with a configurable target temperature. | `2026-08-09` | [owendswang/ps5-fan-control](https://github.com/owendswang/ps5-fan-control) |
| **ps5-linux-loader** | `v2.5` | Loaders | Linux payload implementing HV exploits to run a custom bootloader. | `2026-09-05` | [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) |
| **ps5-payload-manager** | `v0.6.3` | Utilities & Tools | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-10-19` | [itsplk/ps5-payload-manager](https://github.com/itsplk/ps5-payload-manager) |
| **ps5-syslang** | `v0.3` | Utilities & Tools | ShellUI language-switching payload for changing the PS5 system language, including on region-locked consoles. | `2026-10-19` | [owendswang/ps5-syslang](https://github.com/owendswang/ps5-syslang) |
| **ps5debug-NG** | `1.3.2` | Utilities & Tools | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-09-23` | [pharaoh2k/ps5debug-ng](https://github.com/pharaoh2k/ps5debug-ng) |
| **PS5Save** | `v2` | Utilities & Tools | USB save backup utility for jailbroken PS5’s | `2026-10-22` | [heni0xyz/ps5save](https://github.com/heni0xyz/ps5save) |
| **PS5upload** | `v9.4.0` | Networking & Servers | Integrated PS5 file, mount, save-management, monitoring, and remote package-install payload with a companion desktop client. | `2026-10-30` | [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) |
| **RDR2 60fps — PS5 runtime patcher** | `v2.0` | Utilities & Tools | Unlocks 60 FPS in Red Dead Redemption 2 (PS4, v1.32) on a jailbroken PS5, and on a 1080p TV renders the game's own PS4 Pro 4K checkerboard, shown at 1080p (supersampled). | `2026-10-11` | [armanate/rdr2-60fps-runtime-patcher](https://github.com/armanate/rdr2-60fps-runtime-patcher) |
| **RecompStore** | `v2.7.3` | Utilities & Tools | A homebrew app store for jailbroken PS5. It installs and updates native PS5 ports of recompiled games, emulators, apps and tools, and sets each game up from your own disc image. | `2026-10-26` | [elripalda/recompstore](https://github.com/elripalda/recompstore) |
| **ShadowMount+** | `1.7beta11` | Utilities & Tools | Fully automated background 'Auto-Mounter' payload for jailbroken PS5. Watches scan folders for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, auto-mounts them, stages sce_sys + appmeta + trophy data, and registers them on the home screen. | `2026-10-30` | [drakmor/shadowmountplus](https://github.com/drakmor/shadowmountplus) |
| **shsrv** | `v0.20` | Networking & Servers | Telnet server on :2323 with 42 POSIX-ish commands plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). | `2026-08-03` | [ps5-payload-dev/shsrv](https://github.com/ps5-payload-dev/shsrv) |
| **unrar_ps5** | `v1.4.0` | Utilities & Tools | On-console archive extraction payload for 7z and RAR files, with configurable installation layouts. | `2026-06-18` | [bizkut/unrar-ps5](https://github.com/bizkut/unrar-ps5) |
| **websrv** | `v0.34` | Networking & Servers | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-08-03` | [ps5-payload-dev/websrv](https://github.com/ps5-payload-dev/websrv) |
| **WelcomeHubActivator** | `v1.2.0` | Utilities & Tools | A PS5 ELF payload that enables the Welcome Hub. | `2026-10-24` | [ghost1372/welcomehubactivator](https://github.com/ghost1372/welcomehubactivator) |
| **WFM 7-Zip Helper** | `v26.04-0` | Utilities & Tools | A separate extraction helper for PS5 Web File Manager. It uses 7-Zip's native archive handlers and runs as an independent PS5 payload. | `2026-10-22` | [owendswang/wfm-7zip-helper](https://github.com/owendswang/wfm-7zip-helper) |
| **zftpd** | `v1.7.0` | Networking & Servers | Zero-copy FTP/HTTP server. | `2026-10-28` | [seregonwar/zftpd](https://github.com/seregonwar/zftpd) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
