# Local Plasma 6 upgrade assessment

Checked: 2026-11-14. This is an assessment; no system upgrade or repository change
was performed.

## Conclusion

The local machine can follow the official **Ubuntu 24.04 LTS → 26.04.1 LTS**
release upgrade path. The read-only `do-release-upgrade -c` command returned:

```text
Checking for a new Ubuntu release
New release '26.04.1 LTS' available.
Run 'do-release-upgrade' to upgrade to it.
```

Kubuntu 26.04 ships Plasma 6.6. Its default supported session is Wayland;
`plasma-session-x11` is available separately but is not supported by the Kubuntu
team. This makes the move from the current Plasma 5 X11 desktop both a desktop
generation change and, by default, a session protocol change.

Sources: [Ubuntu LTS upgrade announcement](https://lists.ubuntu.com/archives/ubuntu-announce/2026-September/000328.html),
[Kubuntu 26.04 release notes](https://www.kubuntu.org/news/kubuntu-26-04-release-notes/).

## Local observations

| Item | Observed state |
| --- | --- |
| OS | Ubuntu 24.04.5 LTS, `noble` |
| Desktop packages | `ubuntu-desktop` installed; `kubuntu-desktop` not installed; Plasma installed alongside Ubuntu |
| Current desktop | Plasma 5.27.12, KWin 5.27.11, X11 |
| Package candidates in existing APT cache | Plasma 5.27; no `kpackagetool6` candidate |
| Upgrade policy | `/etc/update-manager/release-upgrades`: `Prompt=lts` |
| GPU | NVIDIA GeForce RTX 5080, driver 580.178.04; `nvidia-driver-580-open` installed |
| Root filesystem | 234 GiB total, approximately 22 GiB available, 91% used; `/home` and `/boot` share this filesystem |
| Package health | `dpkg --audit` empty; `apt-mark showhold` empty |
| Simulated ordinary upgrade | `apt-get -s upgrade`: 21 upgraded, 0 newly installed, 0 removed, 3 not upgraded |

The normal-upgrade simulation used the existing package cache. It is not a
simulation of the distribution upgrade and does not establish the download
size, disk requirement, or package removals for 26.04.1.

Existing third-party repositories include graphics-drivers, PipeWire/WirePlumber,
Docker, NVIDIA container tooling, Cloudflare WARP, Tailscale, ProtonVPN, browsers,
and development tools. Several target `noble` specifically. Their Resolute
support and any disabled repositories need review during the release upgrade;
do not mechanically change all suite names.

## Recommended execution path

1. Back up user data and KDE configuration, and prepare a bootable recovery USB.
   Preserve at least `kwinrc`, `kglobalshortcutsrc`, `kdeglobals`, Plasma panel
   configuration, display configuration, and the installed-package inventory.
2. Resolve pending package updates and the three packages not upgraded in the
   simulation. Reboot if the update requires it. Check the upgrader's calculated
   space requirement; the observed 22 GiB alone is not proof that space is sufficient.
3. Confirm NVIDIA, VPN/network tooling, container tooling, and required third-party
   packages support the target release. Review the upgrader's proposed package
   removals before accepting them. On this mixed Ubuntu/KDE installation, also
   confirm the resulting Plasma session packages.
4. Run the supported `do-release-upgrade` workflow for 26.04.1 LTS after those
   preparations. The local check does not require the development-release `-d`
   flag. This step changes the operating system and has not been run here.
5. Log into Plasma 6, check `plasmashell --version`, KWin `supportInformation`,
   and `kscreen-doctor -o`. Recheck 125% UI scaling, portrait rotation, primary
   output, NVIDIA rendering, Electron/browser windows, clipboard, screen sharing,
   and any automation that currently depends on X11.
6. Reinstall KRect using `bash install.sh`, which then selects `kpackagetool6`.
   Enable it and repeat [VALIDATION.md](VALIDATION.md). The Plasma 5 live results
   do not certify Plasma 6/Wayland.

An ordinary `apt upgrade` using the currently configured Noble package candidates
does not provide Plasma 6. Adding newer Ubuntu suites or replacing only KWin
would bypass the supported release upgrade and mix desktop dependencies.

For Plasma 6 development before changing the working desktop, a separate
Kubuntu 26.04 virtual machine or installation can validate installation and API
behaviour. GPU passthrough, real output hotplug, mixed scaling, and the local
NVIDIA/Wayland combination still require suitable hardware testing.
