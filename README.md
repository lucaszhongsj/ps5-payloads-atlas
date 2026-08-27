# ps5-payloads-atlas

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors).

The aggregator composes three layers:

- **Discovery** — the upstream repo list is the union of [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror) `payloads.json` and [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) `CATALOGUE` and some of the plugin information was compiled by `tekqart` forum user `@a83848400`. Both are first-class sources; new payloads in either appear here automatically.
- **Curation** — `sources.json` overrides display name / description / asset selection per repo, and can `"exclude": true` to suppress a repo entirely.
- **Enrichment** — `phantomptr/ps5upload` `CATALOGUE` provides longer descriptions / display names where available.

**A GitHub Action refreshes `payloads.json` hourly.**

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
- Checksums come from the GitHub Release API `digest` field. Non-GitHub repos (e.g. Forgejo on `git.etawen.dev`) and assets without a published digest have an empty `checksum`.
- `LightningMods/Itemzflow` is auto-skipped — its releases ship no `.elf`/`.bin` asset, so the aggregator finds no canonical asset to list.
- Pre-release-only repos fall back to the most recent pre-release.
- Repos are deduped by canonical `(owner, repo)` after redirect resolution (e.g. `LightningMods/etaHEN` folds into `etaHEN/etaHEN`).

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **BackPork** | `0.1` | Installer | Lets you sideload system libraries into PS5 games. | `2026-05-01 00:34:19 UTC+8` | [bestpig/backpork](https://github.com/bestpig/backpork) |
| **bdj_unpatch** | `2.0` | Kernel | BD-JB Blu-ray patch payload for supported optical-drive PS5 firmware. Apply the patch and reboot to use Blu-ray based jailbreaking without reflashing. | `2026-08-05 07:40:33 UTC+8` | [gezine/bd-jb5](https://github.com/gezine/bd-jb5) |
| **BFpilot** | `v0.4.4` | Files | Web-based PS5 file manager serving a browser interface on port 5905 for browsing and managing console files. | `2026-08-12 02:08:09 UTC+8` | [itsblurf/bfpilot](https://github.com/itsblurf/bfpilot) |
| **CheatRunner** | `v0.17` | Tools | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-07-31 05:27:18 UTC+8` | [notmaj0r/cheatrunner](https://github.com/notmaj0r/cheatrunner) |
| **elf-arsenal** | `v1.6.22` | Kernel | etaHEN-oriented payload bundle combining ELF loading, resource management, FTP, trophy tools, ShadowMountPlus, kstuff-lite, Linux loading, controller tools, fake sign-in, and a web UI. | `2026-07-04 06:28:45 UTC+8` | [soniciso/elf-arsenal](https://git.etawen.dev/soniciso/elf-arsenal) |
| **elfldr** | `v0.25` | Kernel | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-08-22 19:59:54 UTC+8` | [ps5-payload-dev/elfldr](https://github.com/ps5-payload-dev/elfldr) |
| **ezremote-DPI** | `1.04` | Installer | Long-lived loopback PKG install daemon (127.0.0.1:9040). Owns Sony's PlayGo/AppInstUtil install state machine so installs don't evaporate when the calling process exits. | `2025-07-02 03:42:24 UTC+8` | [cy33hc/ps5-ezremote-dpi](https://github.com/cy33hc/ps5-ezremote-dpi) |
| **ftpsrv** | `v0.21.1` | Files | Lightweight FTP server on :2121 with SELF/ELF auto-decryption and remount-RW SITE commands. Browse the PS5 filesystem from any FTP client. | `2026-08-21 01:02:45 UTC+8` | [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) |
| **ftpsrv (drakmor)** | `1.15-ng-stable` | Files | drakmor's fork of ftpsrv. | `2026-04-08 10:17:12 UTC+8` | [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) |
| **Garlic SaveMgr** | `v1.13` | Backup | On-console save decrypt/encrypt daemon. Back up saves in plaintext, edit on PC, re-encrypt for the same console. No network. | `2026-08-22 22:03:51 UTC+8` | [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) |
| **Garlic Worker** | `v1.1.6` | Backup | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. Opt-in: connects to garlicsaves.com. | `2026-07-04 21:24:04 UTC+8` | [earthonion/garlic-worker](https://git.etawen.dev/earthonion/garlic-worker) |
| **gdbsrv-ps5** | `v0.9` | Network | GDB remote debugging service payload for inspecting PS5 game processes. | `2026-08-03 00:50:41 UTC+8` | [ps5-payload-dev/gdbsrv](https://github.com/ps5-payload-dev/gdbsrv) |
| **Ghostcontrol** | `1.0.5` | Tools | USB HID controller patcher that injects third-party controller input into a virtual DualSense device. | `2026-07-06 10:19:27 UTC+8` | [stonedmodder/ghostcontrol-ps5-usb-controller-patcher](https://github.com/stonedmodder/ghostcontrol-ps5-usb-controller-patcher) |
| **Ghostpad** | `v1.0.0` | Tools | Creates a virtual PS5 controller on the console and redirects input to it — useful for input automation, remote control, and accessibility setups. | `2026-05-31 23:27:41 UTC+8` | [stonedmodder/ghostpad](https://github.com/stonedmodder/ghostpad) |
| **klogsrv** | `v0.9` | Network | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). | `2026-08-03 00:37:37 UTC+8` | [ps5-payload-dev/klogsrv](https://github.com/ps5-payload-dev/klogsrv) |
| **kstuff** | `v1.6.7` | Kernel | Full build of kstuff: dynamically patches the PS5 kernel to bypass security. | `2026-01-04 23:55:09 UTC+8` | [echostretch/kstuff](https://github.com/echostretch/kstuff) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | Kernel | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Adds an option to disable automatic mounting (noautomount) for a controlled startup. | `2026-05-31 21:18:16 UTC+8` | [drakmor/kstuff-lite](https://github.com/drakmor/kstuff-lite) |
| **kstuff-lite (EchoStretch)** | `v1.10` | Kernel | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00–12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-08-12 11:31:03 UTC+8` | [echostretch/kstuff-lite](https://github.com/echostretch/kstuff-lite) |
| **Kylin Core** | `v1.3.1-community-lite` | Tools | Game cheat trainer for jailbroken PS5. Apply in-game cheats and modifications to running titles; community-lite build distributed as a single payload. | `2026-06-20 02:21:33 UTC+8` | [aydencharles/kylin-core-release](https://github.com/aydencharles/kylin-core-release) |
| **Lapy JB Daemon** | `v1.2` | Kernel | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. Multi-firmware (3.00 to 12.00). No etaHEN required. Upstream voidwhisper/lapy-jb-daemon on git.etawen.dev is offline; this GitHub mirror is the live source. | `2026-06-02 02:26:02 UTC+8` | [itsplk/ps5-lapy-jb-daemon](https://github.com/itsplk/ps5-lapy-jb-daemon) |
| **nanoDNS** | `0.4` | Network | Minimal DNS server running on the PS5 (UDP :53). Blocks PlayStation Network + update domains by default and can redirect any domain to a LAN IP. | `2026-08-05 02:27:26 UTC+8` | [drakmor/nanodns](https://github.com/drakmor/nanodns) |
| **NP Fake Sign-in** | `v1.3` | Tools | Headless payload that registers PS5 user slots directly via the system registry. Offline account activation without PSN. One-shot ELF: send, runs, exits. | `2026-05-15 19:41:36 UTC+8` | [earthonion/np-fake-signin](https://git.etawen.dev/earthonion/np-fake-signin) |
| **pegasus-dl** | `v1.7.0` | Installer | PS5 payload that serves a local web interface for downloading and installing game or application package data. | `2026-06-25 00:10:11 UTC+8` | [pegasus-ps5/pegasus-dl](https://github.com/pegasus-ps5/pegasus-dl) |
| **pldmgr** | `v0.5.1` | Tools | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-08-02 21:20:44 UTC+8` | [itsplk/ps5-payload-manager](https://github.com/itsplk/ps5-payload-manager) |
| **PS5 Console** | `6.3.1` | Files | Web-based PS5 control center combining game mounting, save management, USB controller support, FTP, fan control, and ELF management. | `2026-08-12 11:46:32 UTC+8` | [junleb/ps5console](https://github.com/junleb/ps5console) |
| **PS5 File Explorer** | `file-explorer-v0.2.1` | Files | BFpilot-derived web file manager for browsing and managing files on a jailbroken PS5. | `2026-06-19 20:34:09 UTC+8` | [juma-sayeh/ps5-file-explorer](https://github.com/juma-sayeh/ps5-file-explorer) |
| **PS5 Unified Autoloader** | `v0.1.4-955249d` | Kernel | Standalone ELF autoloader that reads autoload.txt from USB or /data and sends listed payloads to elfldr. | `2026-08-16 21:35:51 UTC+8` | [itsplk/ps5-unified-autoloader](https://github.com/itsplk/ps5-unified-autoloader) |
| **PS5 Web File Manager** | `v1.6` | Files | Web-based file manager for jailbroken PS5. Serves a browser UI over HTTP so you can browse, transfer, and manage files on the console's internal storage from any device on the LAN. | `2026-08-23 23:56:17 UTC+8` | [owendswang/ps5-web-file-manager](https://github.com/owendswang/ps5-web-file-manager) |
| **ps5-app-dumper** | `v1.11` | Backup | Dumps installed PS5 apps to USB or internal storage in fakepkg/folder format. Reads config from /data/ps5-app-dumper/config.ini. | `2026-07-28 10:10:49 UTC+8` | [echostretch/ps5-app-dumper](https://github.com/echostretch/ps5-app-dumper) |
| **ps5-fan-control** | `v0.3` | Tools | Standalone PS5 fan controller with a configurable target temperature. | `2026-08-09 00:39:00 UTC+8` | [owendswang/ps5-fan-control](https://github.com/owendswang/ps5-fan-control) |
| **ps5-linux-loader** | `v2.4` | Kernel | Linux payload implementing HV exploits to run a custom bootloader. | `2026-07-06 16:03:05 UTC+8` | [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) |
| **ps5-syslang** | `v0.2` | Tools | ShellUI language-switching payload for changing the PS5 system language, including on region-locked consoles. | `2026-06-28 10:57:08 UTC+8` | [owendswang/ps5-syslang](https://github.com/owendswang/ps5-syslang) |
| **ps5debug-NG** | `1.3.0` | Network | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-06-21 15:37:35 UTC+8` | [opensourcerer-dev/ps5debug-ng](https://github.com/opensourcerer-dev/ps5debug-ng) |
| **PS5upload** | `v5.11.0` | Backup | Integrated PS5 file, mount, save-management, monitoring, and remote package-install payload with a companion desktop client. | `2026-08-27 19:19:59 UTC+8` | [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) |
| **ShadowMount+** | `1.6beta16` | Installer | Fully automated background 'Auto-Mounter' payload for jailbroken PS5. Watches scan folders for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, auto-mounts them, stages sce_sys + appmeta + trophy data, and registers them on the home screen. | `2026-06-28 21:59:58 UTC+8` | [drakmor/shadowmountplus](https://github.com/drakmor/shadowmountplus) |
| **shsrv** | `v0.20` | Network | Telnet server on :2323 with 42 POSIX-ish commands plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). | `2026-08-03 00:41:01 UTC+8` | [ps5-payload-dev/shsrv](https://github.com/ps5-payload-dev/shsrv) |
| **singleDPI** | `0.1.0` | Installer | Standalone DPI payload accepting TCP 9090 JSON package-install requests and an experimental 12800 URL endpoint. | `2026-06-22 00:50:40 UTC+8` | [maxmilu/ps5-direct-package-installer](https://github.com/maxmilu/ps5-direct-package-installer) |
| **Sonic Loader** | `v1.6.0-elf-arsenal-rebrand` | Kernel | Integrated web-based payload loader and management dashboard combining autoloading, cheat management, monitoring, file transfer, and file management. | `2026-05-22 21:05:50 UTC+8` | [soniciso/sonicloader](https://git.earthonion.com/soniciso/sonicloader) |
| **unrar_ps5** | `v1.4.0` | Installer | On-console archive extraction payload for 7z and RAR files, with configurable installation layouts. | `2026-06-18 22:24:15 UTC+8` | [bizkut/unrar-ps5](https://github.com/bizkut/unrar-ps5) |
| **WebKit Autoloader (installer)** | `v0.4.0` | Kernel | Installs an autoloader reachable from the PS5's own web browser, so payloads can be launched from the console without sending them from a PC every time. One-shot installer ELF: send it, it installs, it exits. Run it after your kernel exploit, like any other payload. | `2026-08-24 08:54:26 UTC+8` | [itsplk/ps5-webkit-autoloader](https://github.com/itsplk/ps5-webkit-autoloader) |
| **websrv** | `v0.34` | Network | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-08-03 03:51:42 UTC+8` | [ps5-payload-dev/websrv](https://github.com/ps5-payload-dev/websrv) |
| **zftpd** | `v1.5.0` | Files | Zero-copy FTP/HTTP server. | `2026-06-15 01:25:58 UTC+8` | [seregonwar/zftpd](https://github.com/seregonwar/zftpd) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
