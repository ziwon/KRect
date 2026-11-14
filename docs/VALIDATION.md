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

## Not executed here

No running KWin, Plasma, Wayland server, X server, Qt UI, KGlobalAccel, or
kpackagetool6 is available. Native runtime behaviour, installation, and the
settings dialog therefore remain unverified. A Node mock cannot validate
Qt metatype conversions, actual Wayland clients, compositor-specific timing,
shortcut conflicts, or KConfig module loading.

## First desktop smoke test

1. Check `plasmashell --version`; use a Plasma 6 session. Install and enable KRect.
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
