# Validation notes

Date: 2026-11-15. Development: workspace presets and window swap (unreleased).
Published prerelease: 0.4.0-rc.1 second-window suggestions and About.
Older release sections below retain their historical results and limitations.

## Workspace presets — unreleased

The Workspaces tab captures one or all virtual desktops in the current KDE
activity. Presets retain app identity, title/role, desktop/output, geometry/work
area and available maximize/minimize state. Atomic local storage uses mode 0600;
a corrupt or unsupported file is preserved rather than silently replaced.
Startup restoration is per preset, waits up to 30 seconds for late windows, and
applies each matched window once. Optional app launching uses installed desktop
entries through GIO, never a captured caption or process command line.

Matching prefers a live-session window ID, then exact app/title and desktop
affinity. App-only fallback requires one saved and one available window. Ambiguous
windows, missing desktops and other activities are skipped with visible results.
KWin validates a fresh expected frame before each placement and waits for actual
geometry. Refused placement attempts to roll back that window. Completed windows
remain in place when the user stops restoration; the current desktop is not set.

Observed on 2026-11-15:

- **136 automated tests passed:** 91 Node and 45 Python, including eight new
  engine scenarios, nine persistence/matching cases and seven controller/Qt UI
  cases. Both mocked Plasma APIs restore D1–D4; tests cover atomic-write failure,
  ambiguous windows, late app windows, launch-once behavior, startup selection,
  stopping, missing outputs, stale requests and refused geometry.
- Qt 5.15.13 constructed the new tab in the Korean app smoke test. The native
  offscreen page test saved a desktop name/options and captured its snapshot.
- Ubuntu 26.04 / **Qt 6.10.2** passed Korean/English app smoke checks and the seven
  workspace controller/page tests, plus the existing chooser/snap-bar tests.
  This container check does not establish native compositor restoration.
- `/usr/bin/python3 -B tools/inspect_workspaces.py` read **four real Plasma 5
  desktops and six eligible windows** without moving windows, registering
  shortcuts or changing the installed app. Schema validation passed. The probe
  unloads its temporary script and writes only desktop names/counts to
  `dist/workspace-probe-results.json`.
- **Real restoration and app launching remain pending**, as do relogin timing,
  mixed scaling/hotplug and Plasma 6/Wayland. The user currently has terminal-only
  access. No production presets have been saved or applied; installed RC1 remains
  in use. Unknown initial Plasma 5 maximize mode falls back to frame restoration.

API reference: [KDE KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/).

## Window swap — unreleased

The app/tray and assignable shortcuts offer a chooser for exchanging the position
and size of two compatible normal windows on the same monitor, desktop and
activity. Swap and Undo swap have no default key binding. Undo restores both
frames and their previous per-window restore histories; changing either window's
placement or closing it invalidates the pair. Both actual frames must match before
success is reported. Refusal, timeout, closure or task switching cancels the
transaction and attempts to roll back surviving eligible windows.

Observed checks:

- **112 automated tests** passed: 83 Node and 29 Python. New cases cover both
  Plasma API generations, both-direction size constraints, delayed frames,
  refusal rollback, cancelled/stale choices, task switching, a closed candidate,
  a missing desktop chooser and preserving earlier restore history through undo.
- Korean/English UI smoke passed on **Qt 5.15.13** and container **Qt 6.10.2**.
  Qt 6 also passed seven chooser and three snap-bar tests, including swap wording
  and Enter selection.
- The user's installed package is `0.4.0~rc.1-1ubuntu24.04`. A lingering snapfix3
  tray process was replaced with `/usr/share/krect/main.py`; the live D-Bus engine
  reported `0.4.0-rc.1`, `snapBar: 1`, `snapAssist: 1`. The installed package and
  engine are kept at RC1; the unreleased swap code has not been installed.
- **Native swap validation is pending.** The first disposable-window attempt
  could not deliver Enter while KDE's screen lock was active (`GetActive=true`).
  The harness cleaned up its windows/script; production KRect remained running.
  It now checks the screen lock before sending input. After unlocking, run
  `/usr/bin/python3 -B tools/validate_snap_x11.py --swap` for native Enter/undo,
  Esc and click/per-window-restore scenarios. No live swap pass is claimed.
  The user currently has terminal-only remote access, so live input checks are
  deferred until desktop access is available. Keep RC1 installed in the meantime.

Live Plasma 6/Wayland remains unverified. Maximized/fullscreen/minimized windows,
dialogs, fixed sizes, custom tiles and cross-monitor swaps are outside this first
implementation.

## Release candidate packaging and Qt 6

Ubuntu 26.04's Qt 6.10.2 passed the Korean and English native offscreen smoke
checks, including the About version and second-window chooser. Its six chooser
tests and three snap-bar tests also passed without skips. The disposable container
mounted the checkout read-only and did not modify the host desktop. The package
smoke check now exercises both languages, and each Ubuntu CI job runs these nine
UI tests against its own Qt generation.

RC package versions use `~rc.N` so Debian upgrades from 0.3.1 through the RC to
the final release in the intended order. The workflow marks RCs as prereleases,
keeps them out of Latest, and permits the landing page to retain stable 0.3.1.
Live Plasma 6/Wayland remains pending; an offscreen Qt 6 pass is not compositor
validation. The tag workflow separately verifies package installation/removal.

The [RC tag workflow](https://github.com/ziwon/KRect/actions/runs/43662134726)
passed validation and both Ubuntu package jobs. Its publication job failed because
the container used `sh` for Bash array syntax. The workflow now explicitly selects
Bash. The already validated artifacts were published through `gh`, without changing
their contents or moving the tag. GitHub also rewrote `~` in uploaded asset names;
publication now converts it to `-` before generating checksums. The internal Debian
version retains `~rc.1`.

The published RC was downloaded again: all four payload checksums, both Debian
versions/dependencies/app and engine contents, prerelease status, bilingual notes
and all five download links passed verification. Stable Latest remains 0.3.1.
The publication step passed local checks for stable creation, RC creation and RC
republication using its declared shell, including the renamed-file checksums.
These publication fixes are later commits on `main`; the original tag workflow
still records its publication failure.

## Second-window suggestions — 0.4.0-rc.1

The development build offers a native chooser after dragging a window into a
left/right/top/bottom half. The engine supplies eligible candidates from the same
monitor, desktop and activity, waits for the first window's accepted frame, and
validates the session, source, work area and candidate again when selected. Candidate
minimum/maximum client sizes include current decoration extents; incompatible
windows are excluded. The second placement waits for the accepted frame before
reporting success, and rolls back on refusal without changing the first placement.
The size properties follow the [KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/).
Click
or Enter places the second window; Esc, Skip or an outside focus change dismisses
the chooser. Each window retains its own restore state. Shortcuts, thirds and
quarters do not trigger it. The preference is `SnapAssist`; small destination
regions (less than 360 × 320 compositor coordinates), no candidates and an already
occupied matching half suppress the chooser.

Observed checks on 2026-11-15:

- **101 automated tests** passed without skips: 73 Node and 28 Python. These cover
  both mocked Plasma APIs, all four half directions, stale/closed candidates,
  context and geometry changes, delayed frame acknowledgements, restoring both
  windows, Qt mouse/keyboard input, dismissal, heartbeat replay and malformed
  D-Bus payloads, declared client sizes with borders, refused placement rollback
  task switching during delayed placement and desktop-file icon resolution. The Debian tests build/extract Ubuntu 24.04 and 26.04 packages,
  verify dependency selection and payloads, and confirm Capture is absent.
- Korean and English Qt 5 application/About construction checks passed. The
  offscreen backend emitted its usual size-hint/tray/raise warnings and exited 0.
- **Four Plasma 5.27/X11 live scenarios** passed using
  `/usr/bin/python3 -B tools/validate_snap_x11.py --assist`: native click with
  target focus and both original-frame restores, Enter selection, Esc preserving
  the first placement and focus, and outside-click dismissal. The harness used
  disposable windows and restricted its candidate list to them. It checked actual
  chooser mapping, frame coordinates and focus; a native `QScreen.grabWindow`
  image is in ignored `dist/snap-validation/assist-native.png`, with results in
  `assist-results.json`.
- The existing snapfix3 app was paused for isolation and its engine restored
  afterward. A final D-Bus check confirmed the original engine is loaded and the
  validation engine is unloaded. No new package was installed.

The first new mock tests accidentally shared move signals across synthetic
windows; independent signals fixed those failures. The initial live harness
attempt stopped before exercising the feature because of an argument-variable
collision and malformed generated JavaScript. Its restore helper also selected
the wrong D-Bus overload; the original engine/app were recovered immediately.
The helper now uses an explicit `ss` signature, and generated JavaScript is
syntax-checked before loading. The subsequent four-scenario live run passed and
its automatic restore completed successfully. A compact widget inspection found
that 248 × 188 was below Qt's minimum usable height; the engine's small-region
gate was raised, and 328 × 288 and 480 × 400 renders fit.

Still pending: real Plasma 6/Wayland,
mixed scale/hotplug and unusually large UI fonts or restrictive candidate size
hints. Node mocks and Qt 5 widget checks do not establish those environments.
This feature is included in the 0.4.0-rc.1 prerelease, not in stable 0.3.1.

## About — 0.4.0-rc.1

The development app has an About dialog accessible from the footer and the tray.
Its selectable version comes from `krect.VERSION`, the same source as the CLI,
application metadata and footer. It includes website, source and license links,
with Korean and English labels. This change ships in the 0.4.0-rc.1 prerelease and
is not part of the published 0.3.1 package.

The Qt 5 offscreen construction check passed in both languages:
`QT_QPA_PLATFORM=offscreen /usr/bin/python3 -B app/main.py --smoke-test --language ko`
and the equivalent `--language en`. It renders the application tabs, opens About from the
footer, verifies its version against application metadata, closes it with its
button, and reopens it from the tray while the main window stays hidden. Repeated
tray commands reuse the dialog. Five existing capture tests also pass without skips.
Widget previews are saved in ignored `dist/about-validation/`; the Korean dialog
and English Capture tab with the new footer button were visually checked.

The offscreen backend emits its known tray-signal, size-hint and raise warnings;
the checks exit successfully. These are widget checks, not proof of compositor
stacking or live capture. Qt 6 was subsequently checked in the Ubuntu 26.04
container described above; a live Wayland session has not been checked.
The installed app and running KWin engine were not replaced.

## Native capture — unreleased prototype

**Shelved:** the prototype and its five tests now live in `experiments/capture/`.
The application, tray and Debian packages no longer include Capture. The notes
below record the earlier experiment, not a supported feature.

The prototype included a Capture tab and tray commands for interactive
window/display selection, a native region overlay, preview, clipboard copy and PNG
save. It uses KWin's `org.kde.KWin.ScreenShot2.CaptureInteractive` interface, present
on this Plasma 5.27 session and in the inspected Plasma 5.27/6.0 upstream sources.
No Spectacle process or dependency is used. Interactive selection uses the user's
click; the shared Python interpreter is not granted a restricted screenshot interface.

Five targeted Qt 5 tests pass: raw pixel decoding and truncated transfers; invalid
or oversized frames; scaled/reversed region crops; cancellation/error preserving
the previous image; original-resolution clipboard and atomic PNG output. The Qt 5
application construction check passes with all four tabs.

**Live capture is not validated.** In this desktop session, KWin returned its
`Cancelled` error before an automated selection could occur. Moving from a full-screen
test window to a normal window, increasing the input delay, enabling the test X11
connection during server grabs, and sending Escape did not resolve it. Independent
X11 probes reported `AlreadyGrabbed` for both pointer and keyboard with no mouse
button held. This persisted after the installed KRect app was stopped. The input
grab owner is not identified; do not treat these runs as successful captures or as
proof that the implementation is otherwise correct. Native computer-tool keyboard
input was also unavailable because `ydotool` is absent; the isolated X11 test path
was used instead. The installed 0.3.0 package has not been replaced by this prototype.

Further work: identify/release the session input grab, verify real window/display
pixels and region selection/cancellation, and test Qt 6 / Plasma 6 Wayland,
mixed scaling and monitor removal. Capture is currently per display rather than a
combined multi-monitor image. Tests and preview assets do not establish live capture
compatibility.

## Snap bar 0.3.1

Three integration problems caused the 0.3.0 bar to disappear or sit behind the
window being dragged. Qt appended the application display name to the native
caption, so the engine did not recognize or position the overlay. KWin hid the
`Qt.Tool` overlay while another application's window was active. Finally, another
always-on-top window could stack above the bar. The engine now recognizes both
native title forms, the app uses a nonactivating normal window, and visible
updates raise the overlay on X11. Plasma 6 uses `workspace.raiseWindow` without
activating it. Input remains transparent and the target's keep-above setting is
unchanged.

The original isolated live harness had neither the production application display
name nor a main application window. Qt visibility and correct frame geometry
therefore missed both native title handling and KWin utility-window hiding. The
harness now includes both, checks `_NET_WM_STATE_HIDDEN` and native stacking order,
and exercises an always-on-top work window. A widget-only image is not evidence
of compositor visibility.

Release checks on this source passed **82 automated tests** (61 Node, 21 Python,
no skips), generated-package consistency, shell syntax, the desktop entry, the
three-language static site build, and Qt 5 native UI construction. The offscreen
platform emitted its expected system-tray signal warning; construction completed.

The updated live harness passed **six scenarios** on Plasma 5.27/X11: landscape
placement with exact gaps/focus/restore, Esc from normal and maximized windows,
leaving the strip, portrait transfer with vertical thirds, and placement/restore
of an always-on-top window. Every visible-bar check also verified native hidden
state and stacking above the target. The previously running KRect app/engine were
restored after the isolated run. Evidence is in ignored `dist/snap-validation/`
and `dist/release-validation/live-snap.log` in the release checkout.

The tag workflow separately builds and installs/removes Ubuntu 24.04 and 26.04
packages with their real Qt 5/6 dependencies. Check its completed jobs for package
results; these container checks are not a live Plasma 6/Wayland session.

Earlier targeted checks on Plasma 5.27.12 / KWin 5.27.11 / X11 reproduced the failures
with the installed app and confirmed both monitor orientations, focus preservation,
exact left-half placement and visibility after the fixes. A cropped screen image
confirmed the bar above an always-on-top disposable client. A real Dolphin window
also placed correctly, and the user confirmed manual drag placement after snapfix2.
One held-drag attempt interrupted around a portal screenshot failed its final
geometry assertion; that attempt is not counted as a passing check.

Still pending: a real Plasma 6/Wayland compositor, mixed display scales, display
hotplug during a drag, and applications with restrictive size hints. Container
package and Qt 6 construction checks do not establish Wayland stacking behavior.
Screenshot capture is not included in 0.3.1.

## Snap bar 0.3.0 — 2026-11-15

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

0.3.0 automated result: **80 passing tests** (59 Node, 21 Python, no skips).
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
The 0.2.0 automated result was **63 passing tests** (45 Node, 18 Python,
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
