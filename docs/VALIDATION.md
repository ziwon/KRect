# Validation notes

Date: 2026-11-14. Release: 0.2.0 desktop app.
The 0.1.0 sections below retain the historical prototype results.

## Snap bar — unreleased development, 2026-11-15

The KWin engine observes real interactive moves and the compositor cursor position.
The desktop app paints an input-transparent, nonactivating native Qt overlay;
KWin positions it, hit-tests its cells and shows the destination outline. The app
and engine share one cell model. No X11 API is used by the product at runtime.
The optional live validation tool below uses XTest only to drive its disposable client.

Node tests cover both Plasma signal names, show/preview/drop/restore, Esc after the
geometry blocker, restored native maximize/tile state with delayed acknowledgements,
leaving the strip and cell gaps, no app, top panels, portrait transfer, exclusions,
disabled preferences, stale contexts and small/fractional/negative work areas.
Qt tests cover bridge validation, painting, nonactivating/input-transparent flags
and watchdog dismissal when the engine stops. Generated package code is rebuilt
from `src/main.js`.

Current automated result: **80 passing tests** (59 Node, 21 Python, no skips).
The 3 overlay tests also passed with Qt 6 in a disposable Ubuntu 26.04 container,
as did the full native UI construction check. The initial minimal Qt 6 container
could not render the app's SVG icon, even with `libqt6svg6`. Installing
`qt6-svg-plugins` supplied `libqsvgicon.so`/`libqsvg.so` and resolved the failure.
That dependency is now explicit in the Ubuntu 26.04 package and source-install
instructions. Offscreen tray/raise warnings are expected; these checks do not
run a compositor or establish Wayland drag behavior.

Observed on the unchanged Plasma 5.27.12 / KWin 5.27.11 / X11 dual-monitor desktop:

- Real title-bar drag → visible bar → left-half drop matched the panel-excluded
  work area and gap exactly. The temporary work client retained focus, and restore
  returned to its initial frame.
- Esc cancelled both a normal and a maximized window drag without snapping.
- Moving away from the strip hid it and releasing preserved the manually dragged frame.
- Moving to the portrait display selected a vertical center third, placed it exactly,
  and restored to the original landscape display.
- The overlay's actual KWin frame matched the shared hit-test geometry with the
  desktop's 125% UI font scaling. Captured dark-theme cells received stronger outlines.

The first harness run hit Python D-Bus overload introspection; an explicit `ss`
signature fixed script loading. An initial synthetic title-bar gesture did not
start a move; the harness now waits for and checks focus and the setup frame before
sending input. Subsequent live checks passed. The harness uses an isolated script
and service, registers no shortcuts, writes no settings, removes its test client
and script, and restores the pointer and previous focus. Evidence is in ignored
`dist/snap-validation/results.json` and the adjacent bar captures.

Repeat the live check on a KDE/X11 desktop with a landscape and portrait display:

```bash
/usr/bin/python3 tools/validate_snap_x11.py
```

Still pending: an actual Plasma 6/Wayland compositor, mixed Wayland display scales,
display hotplug during a drag, and applications with restrictive size hints.
KWin's Finished signal does not expose its cancellation flag. The engine waits for
the finish geometry blocker and rejects a restored initial frame or native
maximize/tile state. Wayland cancellation of already tiled/maximized clients
requires live verification; mocks are not compositor evidence.

## Desktop app 0.2.0

The app uses native Qt widgets and KWin/KGlobalAccel D-Bus APIs. It does not
use X11 window IDs, wmctrl or simulated keystrokes at runtime. KWin remembers
the last eligible external window; the app sends its expected window identity
with every command. A changed/closed/excluded target, another desktop/activity,
and KRect's own windows cannot receive a stale layout command. The two monitors
and scaling of the preflight below are unchanged.

Automated coverage adds the app bridge's targeting rules and the shortcut
editor's conflict, swap, and failed-write rollback behavior. Native construction
smoke checks create every tab and render the app icon without starting KWin.
Installer tests verify the application launcher, a path containing spaces,
script-only installation, and removal of the user app.
The current automated result is **63 passing tests** (45 Node, 18 Python,
no skips on this desktop).

Observed on Plasma 5.27.12 / KWin 5.27.11 / Qt 5.15.13 / X11:

- **14 live checks passed** using a dedicated temporary Qt client. App buttons
  and tray actions placed/restored that client while the KRect window remained
  unchanged. Landscape-to-portrait transfer and vertical center-third placement
  used the actual panel-excluded work areas.
- Native maximization, left placement, and restore preserved both X11 maximize
  flags. The Plasma 5 adapter now observes the workspace's boolean
  `clientMaximizeSet` signal; the former enum signal was insufficient on this
  desktop. Windows maximized before engine startup remain subject to the
  older-API limitation described below.
- The KDE shortcut service accepted a temporary unused binding and restored the
  original bindings. An Alt+F4 conflict was rejected before any change.
- Gap 12 was written to KConfig and verified against actual window geometry,
  then the original preferences were restored. The first attempt exposed KWin's
  cached configuration: restarting the script alone still used gap 8. The app
  now requests KWin reconfiguration before reloading its engine.
- A second application launch activated the existing instance and exited
  successfully. KDE reported a system tray available. All three tabs were
  captured with the system's dark theme and 125% UI scaling. An initial fixed
  layout overlapped buttons; scrollable content now keeps controls separated.
- An initial self-resize assertion sampled a not-yet-mapped app window before
  KWin added its decorations. Waiting for exposure and comparing the app's client
  size removed that test-harness false positive.

Local evidence is in ignored `dist/desktop-validation/results.json` and the
adjacent screenshots. Live checks changed only the temporary client, restored
shortcut bindings and placement preferences, and did not alter monitor settings.

Repeatable automated checks:

```bash
node --test tests/*.test.cjs
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen /usr/bin/python3 app/main.py --smoke-test
desktop-file-validate app/org.krect.KRect.desktop
```

Ubuntu package smoke checks install the real dependency set in disposable Docker
containers, discover the global KPackage, launch `krect --version`, construct
the Qt 5/6 UI offscreen, validate the desktop entry, and remove the package.
These checks do not establish Plasma 6/Wayland window-management behavior.
Both Ubuntu 24.04/Qt 5 and Ubuntu 26.04/Qt 6 container checks passed. Lintian
reported no errors for the Ubuntu 24.04 package. KDE's `kstart5 --application
org.krect.KRect` successfully launched the installed user desktop entry; its
app D-Bus service was present and KWin reported KRect loaded.

Still pending: physical shortcut key presses, a login cycle for autostart,
interactive tray clicks by a person, KDE's separate generic config module save,
Plasma 6 compositor sessions, mixed/fractional Wayland scaling, and actual
display unplug/reconnect. No OS upgrade was performed.

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
