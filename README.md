# ps5-payloads-atlas

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors).

The aggregator composes three layers:

- **Discovery** — the upstream repo list is the union of [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror) `payloads.json` and [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) `CATALOGUE`. Both are first-class sources; new payloads in either appear here automatically. Additional plugin information compiled by `tekqart` forum user `@a83848400` has been merged into `sources.json` by hand.
- **Curation** — `sources.json` overrides display name / description / asset selection per repo, and can `"exclude": true` to suppress a repo entirely.
- **Enrichment** — `phantomptr/ps5upload` `CATALOGUE` provides longer descriptions / display names where available.

**A GitHub Action refreshes `payloads.json` every 3 hours.**

## Files

- `payloads.json` — the catalogue consumed by ps5-payload-manager (`Settings → Manage Sources → Add Source`, paste the raw URL).
- `sources.json` — curation overlay (override / exclude). Acts as fallback seed if discovery fails.
- `update_payloads.py` — the aggregator.

## `sources.json` schema

Each entry is one upstream repo. Only `url` is required; every other field is an optional override with the fallback shown.

| Field | Required | Purpose | Fallback if omitted |
| --- | --- | --- | --- |
| `url` | yes | Repo HTML URL — the entry's identity and API lookup key | — |
| `display_name` | no | Overrides the output `name` | ps5upload `display_name` → repo name from URL |
| `description` | no | Overrides the output `description` | ps5upload / itsPLK description → empty |
| `asset_pattern` | no | Regex narrowing which release asset to pick (multiple `.elf` files) | ps5upload `asset_name_hint` → no filter |
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
- Running `update_payloads.py` locally requires the [`gh` CLI](https://cli.github.com/) to be installed and authenticated (`gh auth login`) — the GitHub API is queried through it. Python 3.10+ is required (the script uses `dict | None` annotations).

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **007 First Light PS5 Online** | `v0.3.1` | Tools | 007 First Light (PPSA11386) online on a jailbroken PS5, with no IOI servers involved and no PC needed. One payload does everything on the console, so the online features and TacSim work. | `2026-10-22 04:55:47 UTC+8` | [theghostonline/007-first-light-ps5](https://theghostonline.dev/theghostonline/007-first-light-ps5) |
| **AnyPad PS5** | `v0.9.5-beta` | Kernel | A Bluetooth controller bridge for jailbroken PS5 consoles. Un puente de mandos Bluetooth para PS5 con jailbreak. | `2026-10-15 03:05:40 UTC+8` | [elmonomalva0/any-pad-ps5](https://codeberg.org/elmonomalva0/any-pad-ps5) |
| **APR Emu Updater** | `v2.0.6` | Installer | PS5 payload that keeps APR Emu up to date on installed titles, from a web interface on the console. | `2026-08-29 17:54:19 UTC+8` | [tsuramatsu1/apr-emu-updater](https://github.com/tsuramatsu1/apr-emu-updater) |
| **BackPork (backport helper)** | `0.1` | Installer | Runs in the background and watches for game launches. When a title starts, it looks for a `fakelib` folder inside that game's install directory and union-mounts it over the sandbox's `common/lib`, so the game loads newer system libraries without altering the originals. This is the runtime half of backporting a game to older firmware — use it together with the SDK Version Changer, which lowers the SDK version recorded in `eboot.bin` and every `prx`/`sprx`. A title needs both: downgraded ELFs so the system agrees to launch it, and compatible libraries so it does not crash on missing imports. The libraries themselves usually need patching to drop imports your firmware lacks; upstream ships BPS patch sets for 6.xx and 7.xx. | `2026-05-01 00:34:19 UTC+8` | [bestpig/backpork](https://github.com/bestpig/backpork) |
| **BFpilot** | `v0.4.4` | Files | Web-based PS5 file manager serving a browser interface on port 5905 for browsing and managing console files. | `2026-08-12 02:08:09 UTC+8` | [itsblurf/bfpilot](https://github.com/itsblurf/bfpilot) |
| **BFplayer** | `v0.1.0-alpha.44` | Tools | A PS5 media and video player that also functions as a complete media library, with support for subtitles, multiple audio tracks, aspect-ratio adjustment, cropping, and many other playback settings. | `2026-07-31 08:54:17 UTC+8` | [itsblurf/bfplayer](https://github.com/itsblurf/bfplayer) |
| **CheatRunner** | `v0.18` | Tools | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-10-11 02:01:49 UTC+8` | [notmaj0r/cheatrunner](https://github.com/notmaj0r/cheatrunner) |
| **elfldr** | `v0.27` | Kernel | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-10-22 01:42:19 UTC+8` | [ps5-payload-dev/elfldr](https://github.com/ps5-payload-dev/elfldr) |
| **etaHEN** | `v2.5B-unified.1` | Tools | Unofficial etaHEN 2.5B unified PS5 11.00-13.60 port: Toolbox, plugins and PS4/PS5 FPS. Original etaHEN by LightningMods and contributors. | `2026-10-06 00:00:19 UTC+8` | [gronedwaffel/etahen-11.00-13.60](https://github.com/gronedwaffel/etahen-11.00-13.60) |
| **etaHEN** | `2.5B` | Tools | AIO HEN payload | `2025-12-25 13:31:40 UTC+8` | [etahen/etahen](https://github.com/etahen/etahen) |
| **ftpsrv** | `v0.21.1` | Files | Lightweight FTP server on :2121 with SELF↔ELF auto-decryption and remount-RW SITE commands. Lets you browse the PS5's filesystem from any FTP client. | `2026-08-21 01:02:45 UTC+8` | [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) |
| **ftpsrv (drakmor)** | `1.16-ng-stable` | Files | A simple FTP server for jailbroken PS4s and PS5s | `2026-09-21 04:48:47 UTC+8` | [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) |
| **Ftpsrv Streamextract** | `1.0.1` | Kernel | This is a simple FTP server that can be executed on a Playstation 4 or Playstation 5 that has been jailbroken and is running an ELF loader. The FTP server accepts connection on port 2121. | `2026-10-21 20:27:11 UTC+8` | [ruinelson/ftpsrv-streamextract](https://github.com/ruinelson/ftpsrv-streamextract) |
| **Garlic SaveMgr for PS5** | `v1.14` | Backup | PS5 save decrypt/encrypt/browse with embedded web UI. | `2026-10-21 21:16:26 UTC+8` | [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) |
| **Garlic Worker** | `v1.1.7` | Backup | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. Opt-in: connects to garlicsaves.com. | `2026-09-04 20:49:28 UTC+8` | [earthonion/garlic-worker](https://git.etawen.dev/earthonion/garlic-worker) |
| **gdbsrv-ps5** | `v0.9` | Network | GDB remote debugging service payload for inspecting PS5 game processes. | `2026-08-03 00:50:41 UTC+8` | [ps5-payload-dev/gdbsrv](https://github.com/ps5-payload-dev/gdbsrv) |
| **HearBridge PS5** | `v1.3.6` | Tools | Bluetooth A2DP audio bridge for PS5 homebrew | `2026-10-18 13:44:23 UTC+8` | [x-f1reball-x/hearbridge-ps5](https://github.com/x-f1reball-x/hearbridge-ps5) |
| **KeepAwake** | `v1.5.0` | Tools | A PS5 and PS4 payload that stops the console from going into rest mode while it runs. | `2026-10-10 05:28:26 UTC+8` | [mortyzip/keepawake](https://github.com/mortyzip/keepawake) |
| **klogsrv** | `v0.9` | Network | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). | `2026-08-03 00:37:37 UTC+8` | [ps5-payload-dev/klogsrv](https://github.com/ps5-payload-dev/klogsrv) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | Kernel | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Recent builds extended firmware coverage through FW 12.xx (the '12.xx Support' update) on top of the original 3.00→10.01 range — check the release notes for your exact firmware. Adds an option to disable automatic mounting (noautomount) for a controlled startup. Recommended when your primary workflow is ShadowMount+ with .ffpkg/.exfat/PFS images. Same load-first ordering as any other kstuff: must boot before ShadowMount+ or ps5upload. | `2026-05-31 21:18:16 UTC+8` | [drakmor/kstuff-lite](https://github.com/drakmor/kstuff-lite) |
| **kstuff-lite (EchoStretch)** | `v1.11` | Kernel | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00–12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-09-21 03:08:36 UTC+8` | [echostretch/kstuff-lite](https://github.com/echostretch/kstuff-lite) |
| **Kylin Core** | `v2.0.0-community-lite` | Kernel | A homebrew cheat loader and real-time game modifier for PlayStation 5 | `2026-10-01 21:29:25 UTC+8` | [aydencharles/kylin-core-release](https://github.com/aydencharles/kylin-core-release) |
| **Lapy-JB-Daemon** | `v1.2` | Kernel | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. | `2026-06-02 02:26:02 UTC+8` | [itsplk/ps5-lapy-jb-daemon](https://github.com/itsplk/ps5-lapy-jb-daemon) |
| **LZ4 Compression for PS5** | `v1.6.3` | Tools | Shrink your PS5 games on the console itself. Pick a game, choose Compress with LZ4, and it packs the game data into LZ4 asset packs that APR-EMU reads while the game runs. Every file gets checked before anything's deleted, and if the game doesn't ship APR-EMU, the right runtime is added for you. | `2026-10-22 04:53:50 UTC+8` | [theghostonline/ps5-lz4-compression](https://theghostonline.dev/theghostonline/ps5-lz4-compression) |
| **nanoDNS** | `0.4` | Network | Minimal DNS server running on the PS5 (UDP :53). Blocks PlayStation Network + update domains by default and can redirect any domain to a LAN IP. | `2026-08-05 02:27:26 UTC+8` | [drakmor/nanodns](https://github.com/drakmor/nanodns) |
| **NeoEnabler** | `v0.5.0` | Tools | Allows PS4 games with no PS4 Support to receive patches via illusionyy's ps-patch-system that can unlock higher resolutions | `2026-10-23 19:03:10 UTC+8` | [gasb07/neoenabler](https://github.com/gasb07/neoenabler) |
| **NP Fake Signin** | `v1.4` | Tools | ELF payload for PS4/PS5 that fakes PSN sign-in for the foreground user by writing NP files and patching registry/ShellCore state. | `2026-10-02 08:58:43 UTC+8` | [earthonion/np-fake-signin](https://git.etawen.dev/earthonion/np-fake-signin) |
| **onionHEN** | `v0.9.0` | Tools | OnionHEN is a homebrew enabler and Toolbox for jailbroken PS5 consoles, built on etaHEN. It prepares the system, injects a Toolbox into the home screen, and adds cheats, in-game overlays, payload management, and background services. | `2026-10-15 15:42:25 UTC+8` | [aydencharles/onionhen](https://github.com/aydencharles/onionhen) |
| **pegasus-dl** | `v1.11.0` | Installer | PS5 payload that serves a local web interface for downloading and installing game or application package data. | `2026-10-10 06:57:31 UTC+8` | [pegasus-ps5/pegasus-dl](https://github.com/pegasus-ps5/pegasus-dl) |
| **PerfBar** | `v0.1.3` | Tools | A standalone on-screen performance overlay for the PS5. It draws FPS, frametimes, 1% lows, CPU/SoC temperatures, and RAM/VRAM usage directly over your games. | `2026-10-21 23:57:50 UTC+8` | [x1nons/prefbar](https://github.com/x1nons/prefbar) |
| **PKG-Manager** | `v1.5.1` | Installer | Browse and install PKGs from USB, disc, or SMB shares directly on your PS5 | `2026-10-10 23:38:10 UTC+8` | [itsplk/ps5-pkg-manager](https://github.com/itsplk/ps5-pkg-manager) |
| **pLinux5-NG** | `v0.1.0` | Tools | boot linux on PS5 consoles running high firmware (8.xx through 13.60) | `2026-10-14 12:57:17 UTC+8` | [plabs5/plinux5-ng](https://github.com/plabs5/plinux5-ng) |
| **PoorDS4** | `v0.2.0` | Tools | Use a wireless DualShock 4 in native PS5 games on jailbroken consoles. | `2026-10-21 10:59:15 UTC+8` | [itsblurf/poords4](https://github.com/itsblurf/poords4) |
| **ps-patch-system** | `38108724867` | Tools | App patching system | `2026-10-11 11:33:58 UTC+8` | [illusionyy/ps-patch-system](https://github.com/illusionyy/ps-patch-system) |
| **PS4Mount** | `v0.6.1` | Installer | Allows for PKG games on USB external devices to mount on jailbroken PS5s without installing on internal storage or PS5 formatted USB storage | `2026-10-21 11:06:30 UTC+8` | [gasb07/ps4mount](https://github.com/gasb07/ps4mount) |
| **PS5 aria2** | `v1.37.0-3` | Tools | This fork builds aria2 as a PS5 ELF payload. | `2026-10-05 22:00:24 UTC+8` | [owendswang/ps5-aria2](https://github.com/owendswang/ps5-aria2) |
| **PS5 Console** | `6.5.1` | Files | Web-based PS5 control center combining game mounting, save management, USB controller support, FTP, fan control, and ELF management. | `2026-08-31 19:42:15 UTC+8` | [junleb/ps5console](https://github.com/junleb/ps5console) |
| **PS5 File Explorer** | `v0.2.1` | Files | BFpilot-derived web file manager for browsing and managing files on a jailbroken PS5. | `2026-06-19 20:34:09 UTC+8` | [juma-sayeh/ps5-file-explorer](https://github.com/juma-sayeh/ps5-file-explorer) |
| **PS5 Game Compressor** | `v1.1.1` | Installer | Standalone PS5 payload for compressing, unpacking, validating, and repairing ShadowMountPlus-mounted games | `2026-10-02 14:39:43 UTC+8` | [gcoding97/ps5-game-compressor](https://github.com/gcoding97/ps5-game-compressor) |
| **PS5 TabShifter** | `v.1.2.1` | Tools | Standalone PS5 on-console payload to move apps between Games/Media tabs and hide offline PSN bloatware (FW 13.60 supported). | `2026-10-17 04:56:27 UTC+8` | [xvvulcanvx/ps5-tabshifter](https://github.com/xvvulcanvx/ps5-tabshifter) |
| **PS5 Tailscale** | `v0.7.1` | Tools | Tailscale for jailbroken PS5: reach the console over your tailnet and stream to it with Moonlight/Sunshine (unofficial) | `2026-10-07 07:46:38 UTC+8` | [holdmysocks/ps5-tailscale](https://github.com/holdmysocks/ps5-tailscale) |
| **PS5 Web File Manager** | `v1.12` | Files | Web-based file manager for jailbroken PS5. Serves a browser UI over HTTP so you can browse, transfer, and manage files on the console's internal storage from any device on the LAN. | `2026-10-22 23:28:23 UTC+8` | [owendswang/ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) |
| **PS5 WebKit Autoloader** | `v0.6.1` | Kernel | Automatically loads the WebKit exploit and your elf payloads. | `2026-10-09 00:06:48 UTC+8` | [itsplk/ps5-webkit-autoloader](https://github.com/itsplk/ps5-webkit-autoloader) |
| **ps5-60FPS** | `v1.0.0` | Tools | Unlock 60 FPS in PS4 and PS5 games on a jailbroken PS5, with one switch per game. | `2026-10-16 13:37:57 UTC+8` | [eladharels/ps5-60fps](https://github.com/eladharels/ps5-60fps) |
| **ps5-app-dumper** | `v2.10` | Backup | Dumps installed PS5 apps to USB or internal storage in fakepkg/folder format. Reads config from /data/ps5-app-dumper/config.ini. | `2026-10-03 09:11:22 UTC+8` | [echostretch/ps5-app-dumper](https://github.com/echostretch/ps5-app-dumper) |
| **ps5-date-time-sync** | `v1.0.0` | Tools | Automatically restores the system date and time using public NTP servers | `2026-08-24 22:44:14 UTC+8` | [kerrdec97/ps5-date-time-sync](https://github.com/kerrdec97/ps5-date-time-sync) |
| **ps5-exporter** | `v0.3.1` | Tools | Prometheus exporter for a jailbroken PS5 | `2026-10-20 01:10:18 UTC+8` | [marice/ps5-exporter](https://github.com/marice/ps5-exporter) |
| **ps5-fan-control** | `v0.3` | Tools | Standalone PS5 fan controller with a configurable target temperature. | `2026-08-09 00:39:00 UTC+8` | [owendswang/ps5-fan-control](https://github.com/owendswang/ps5-fan-control) |
| **ps5-linux-loader** | `v2.5` | Kernel | Linux payload implementing HV exploits to run a custom bootloader. | `2026-09-05 16:40:09 UTC+8` | [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) |
| **ps5-payload-manager** | `v0.6.3` | Tools | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-10-19 21:42:55 UTC+8` | [itsplk/ps5-payload-manager](https://github.com/itsplk/ps5-payload-manager) |
| **ps5-syslang** | `v0.3` | Tools | ShellUI language-switching payload for changing the PS5 system language, including on region-locked consoles. | `2026-10-19 00:22:59 UTC+8` | [owendswang/ps5-syslang](https://github.com/owendswang/ps5-syslang) |
| **ps5debug-NG** | `1.3.2` | Network | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-09-23 11:21:00 UTC+8` | [pharaoh2k/ps5debug-ng](https://github.com/pharaoh2k/ps5debug-ng) |
| **PS5upload** | `v7.1.19` | Backup | Integrated PS5 file, mount, save-management, monitoring, and remote package-install payload with a companion desktop client. | `2026-10-23 17:58:44 UTC+8` | [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) |
| **ShadowMount+** | `1.7beta7` | Installer | Fully automated background 'Auto-Mounter' payload for jailbroken PS5. Watches scan folders for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, auto-mounts them, stages sce_sys + appmeta + trophy data, and registers them on the home screen. | `2026-10-21 19:56:24 UTC+8` | [drakmor/shadowmountplus](https://github.com/drakmor/shadowmountplus) |
| **shsrv** | `v0.20` | Network | Telnet server on :2323 with 42 POSIX-ish commands plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). | `2026-08-03 00:41:01 UTC+8` | [ps5-payload-dev/shsrv](https://github.com/ps5-payload-dev/shsrv) |
| **unrar_ps5** | `v1.4.0` | Installer | On-console archive extraction payload for 7z and RAR files, with configurable installation layouts. | `2026-06-18 22:24:15 UTC+8` | [bizkut/unrar-ps5](https://github.com/bizkut/unrar-ps5) |
| **websrv** | `v0.34` | Network | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-08-03 03:51:42 UTC+8` | [ps5-payload-dev/websrv](https://github.com/ps5-payload-dev/websrv) |
| **WFM 7-Zip Helper** | `v26.04-0` | Files | A separate extraction helper for PS5 Web File Manager. It uses 7-Zip's native archive handlers and runs as an independent PS5 payload. | `2026-10-22 23:27:06 UTC+8` | [owendswang/wfm-7zip-helper](https://github.com/owendswang/wfm-7zip-helper) |
| **zftpd** | `v1.6.0` | Files | Zero-copy FTP/HTTP server. | `2026-10-01 03:14:18 UTC+8` | [seregonwar/zftpd](https://github.com/seregonwar/zftpd) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
