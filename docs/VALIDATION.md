# Validation notes

Date: 2026-11-14. Release: 0.1.0 prototype.

## Automated scope

The tests use Node and a simulated KWin workspace. They cover geometry rounding,
panel exclusion, window-specific restore state, maximize state, a delayed geometry
acknowledgement, output mapping, portrait thirds, exclusions, the JavaScript entry
point, and targeting a selected window through the window menu.

Installer tests replace KPackage/config/D-Bus commands with temporary local stubs.
They verify arguments, paths with spaces, failure propagation, update selection,
and that removal targets this plugin alone. They do not install a KDE package.

XML well-formedness, config widget binding names, generated entry-point equality,
ZIP member layout, shell syntax, and deterministic packaging are checked during
release validation. They do not prove Qt widget loading or KPackage acceptance.

## Desktop preflight: 2026-11-14

**Initial result, before Plasma 5.27 support was added: installation blocked.**
The initial build environment had no KDE runtime. This follow-up inspected a
real KDE desktop running Plasma 5. The original installer required Plasma 6.
The follow-up implementation and live results below supersede that blocker.

| Check | Observed result |
| --- | --- |
| `plasmashell --version` | `plasmashell 5.27.12` |
| Running KWin, via D-Bus `supportInformation` | KWin 5.27.11; Qt 5.15.13; `Operation Mode: X11 only` |
| Session environment | `XDG_SESSION_TYPE=x11`, `XDG_CURRENT_DESKTOP=KDE`, `DISPLAY=:0`; no `WAYLAND_DISPLAY` |
| Installation tools | `kpackagetool5` available; `kpackagetool6` absent from PATH and not found by `dpkg-query` |
| Plasma Wayland session | No Plasma entry in `/usr/share/wayland-sessions`; `kwin_wayland` absent from PATH |
| Desktop bounds | 6000 × 3840, two active outputs |

Display geometry was cross-checked with `kscreen-doctor -o`, KWin's
`supportInformation`, and `xrandr --listmonitors` / `xrandr --verbose`:

| Output | Mode | Desktop geometry | Orientation | KScreen/KWin scale |
| --- | --- | --- | --- | --- |
| HDMI-0 (primary) | 3840 × 2160, 60 Hz | `(0, 1680)`, 3840 × 2160 | Landscape | 1 |
| DP-0 | 3840 × 2160, approximately 60 Hz | `(3840, 0)`, 2160 × 3840 | Portrait, right rotation | 1 |

The portrait monitor is to the right, with both monitors aligned at the bottom.
Both XRandR transforms are identity matrices. Separately, `kdeglobals` contains
`[KScreen] ScaleFactor=1.25` and `ScreenScaleFactors` entries of 1.25 for both
active outputs. `kcmfonts` contains `forceFontDPI=120`, and `xrdb -query` reports
`Xft.dpi: 120`. Thus the stored KDE UI scaling is **125%**, while KWin reports
output coordinate scales of **1**. These observations do not validate each
application's rendering scale or Plasma 6 fractional/mixed scaling.

Running `bash install.sh` as the desktop user returned **exit code 1**:

```text
kpackagetool6 was not found. KRect requires KDE Plasma 6.
On Kubuntu with Plasma 6, install the kpackagetool6 package first.
```

This is the installer's existing prerequisite failure, not successful KPackage
validation. No package was installed: `~/.local/share/kwin/scripts/krect` remained
absent, `kwinrc` had no `krectEnabled` entry, and the running KWin's D-Bus
`isScriptLoaded krect` returned `false`. No desktop upgrade, display change,
script activation, or window manipulation was performed.

Automated checks rerun on this desktop passed: **35 Node tests and 9 Python tests
(44 total, no skips)**. The installer tests still use stubs; their passing result
does not remove the real installation blocker.

## Plasma 5.27 compatibility follow-up

The runtime now selects `activeClient`, `clientAdded` / `clientRemoved`,
`clientList()`, numeric screen indices, `clientFinishUserMovedResized`, and
`clientMaximizedStateAboutToChange` on Plasma 5.27. Plasma 6 retains its existing
window/output APIs. The placement calculations are shared. On Plasma 5, screen
geometry identifies restore destinations across index reordering. A changed
position/resolution/rotation falls back to the current output's work area.

The installer/remover select version-matched KPackage/KConfig tools using
`plasmashell --version`. Plasma 5.26 and earlier are rejected before mutation.

Observed on the desktop described above:

- `bash install.sh` succeeded with the real `kpackagetool5` and installed the
  user package. KWin loaded the installed entry point, and KGlobalAccel listed
  all 18 `KRect-*` actions.
- A temporary PyQt5/X11 window was manipulated through the installed actions
  using KGlobalAccel D-Bus `invokeShortcut`. A separate KWin script read actual
  `frameGeometry` after each action and sent measurements to a temporary D-Bus
  receiver. This exercised real KWin and Qt metatype conversions, rather than
  the Node workspace mock.
- **24 geometry checks passed**: all half/quarter/third layouts, half cycling,
  center, maximize, restore, right-half transfer to the portrait output,
  portrait center-third, restore to the original output, and fullscreen exclusion.
- A further **5 geometry checks passed** for an already maximized window's
  placement/restore and a native quick-tiled window's placement/restore, bringing
  the live total to **29**. The local quick tile measured 1015 pixels wide, so
  restore was checked against that observed baseline rather than an assumed
  half-screen width. An initial probe assumed 1920 pixels and failed on this
  setup; correcting the probe's baseline resolved the mismatch without a runtime
  change. Tile-group membership restoration was not tested or added.
- The measured primary work area was `(0, 1738, 3840, 2102)`, excluding the panel.
  With gap 8, its left-half target was `(8, 1746, 1908, 2086)`; the portrait
  center-third target was `(3848, 1284, 2144, 1272)`. Actual frames matched the
  requested frames in these checks.
- PyQt5 instantiated `config.ui` and all five `kcfg_*` widgets successfully.
  This checks native Qt 5 widget loading, not KConfig saving through System Settings.
- Automated tests passed: **39 Node tests and 11 Python tests (50 total)**,
  including Plasma 5 screen zero, portrait transfer, index reordering, missing
  outputs, move/maximize/lifecycle signals, and version-matched installer tools.
- Real `bash uninstall.sh` removed the user package and KWin
  `isScriptLoaded krect` returned `false`. The final package was reinstalled,
  its entry point matched `src/main.js`, KWin reported it loaded, and
  `[Plugins] krectEnabled=true` was saved in `kwinrc` for subsequent logins.

The live probe uses a separate test window and closes it afterwards. The
installation did not require an OS upgrade or a display configuration change.

API references: [KWin 5.27 workspace wrapper](https://github.com/KDE/kwin/blob/Plasma/5.27/src/scripting/workspace_wrapper.h),
[KWin 5.27 window properties/signals](https://github.com/KDE/kwin/blob/Plasma/5.27/src/window.h),
[KWin 5.27 JavaScript/geometry conversion](https://github.com/KDE/kwin/blob/Plasma/5.27/src/scripting/scripting.cpp).

## Runtime validation still pending

Neither a Plasma 6 X11 run nor a Plasma 6 Wayland run has been completed. Use a
running Plasma 6 / KWin 6 session with `kpackagetool6` for those checks; see
[UPGRADE.md](UPGRADE.md) for the local upgrade assessment.

Physical keyboard shortcut conflict resolution, System Settings configuration
save/reload, title-bar menu interaction, browser/Electron/terminal-specific size
constraints, manual drag/resize, gap 0/12, exclusions configured through KConfig,
output unplug/reconnect, and mixed/fractional Wayland scaling remain pending.
The successful KGlobalAccel dispatch does not certify every default physical
key combination. The Qt form check does not certify the KConfig module.

A Node mock cannot validate Qt metatype conversions, actual Wayland clients,
compositor-specific timing, shortcut conflicts, or KConfig module loading.

## First desktop smoke test

1. Check `plasmashell --version`; use Plasma 5.27 or Plasma 6. Install and enable KRect.
2. Open a terminal and browser. Test halves, quarters, thirds, repeat cycling,
   center, maximize, and restore on each. Test an already maximized window too.
3. Set the gap to 0, then 12. Reload KRect and confirm outer/internal gaps.
4. Move a window manually, apply a layout, and restore: the manually chosen
   geometry should be the new baseline.
5. Use the title-bar KRect menu on a window that was not previously focused.
6. Test two displays, including a portrait display and different scaling. Move
   a right-half window between screens and restore it to its starting screen.
7. Disconnect the starting screen after moving a window, then restore. It should
   stay within an available work area.
8. Confirm fullscreen and excluded apps are untouched. Check shortcut conflicts
   in System Settings. Disable KRect to confirm shortcuts stop affecting windows.
9. Test with a currently quick-tiled/custom-tiled window. The target geometry
   should detach it from the tile. Restoring tile-group membership is not supported.
10. Uninstall and confirm KRect no longer loads on the next login.

If an action fails, capture the Plasma version, session type, display geometry/
scaling, application name, action sequence, and relevant KRect/KWin scripting
messages from `journalctl --user -b`. Do not assume a size mismatch is a script
bug until minimum-size rules and the app's aspect-ratio constraints are checked.
