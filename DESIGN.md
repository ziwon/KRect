# KRect desktop interface

## Overview

The desktop app uses native Qt widgets, the system font, palette, icons and focus indicators. The user pinned Rectangle as the interaction reference and KDE as the operating environment. This is an Operate surface: selecting a layout and identifying its target lead the screen.

The window has Layouts, Shortcuts, and Preferences tabs. Layouts shows the selected external window, the real display topology, and compact layout buttons with geometric icons. The tray provides the same actions in a native menu. Preferences use standard form controls with explicit application and inline results. Shortcuts use native key sequence editors and reject conflicts before changing KDE bindings.

Spacing uses 8, 12, 16 and 24 logical pixels. Accent is reserved for the previewed placement and current target display. There is no custom stylesheet, decorative animation, or fixed light/dark palette. Hover and keyboard focus preview a placement; clicking applies it. A caption and accessible action name accompany each geometric icon.

Disabled, disconnected, no target, pending command and failed command states are explicit. Closing a window hides it only when a tray is available and that preference is enabled; Quit exits the app while KWin shortcuts continue.

KRect 0.3.0 adds a passive snap bar while dragging a work window to a display's top center. Six miniature layouts show halves, thirds, asymmetric thirds and quarters. The selected region uses the system highlight, a stronger outline and a text label. The actual destination uses KWin's outline. Leaving the strip resumes normal dragging; Esc cancels the move. The bar never takes focus or pointer input: KWin owns hit testing and placement, and sends the same cell geometry that the app paints. This avoids independent coordinate calculations under scaling. The app must remain running in the tray; Preferences exposes a native checkbox to disable the feature.

## Components

### Second-window chooser

The development app extends the drag workflow with a native Qt chooser after a window is placed in a left, right, top or bottom half through the snap bar. The chooser offers the opposite half; shortcuts, thirds and quarters do not open it. The first placement remains in place when the chooser is dismissed. The Preferences checkbox for suggesting another window is enabled only while the snap bar is enabled.

The chooser is a frameless, above-window native panel centered inside the opposite region. KWin supplies its geometry, positions the mapped window and activates it; the Qt app does not calculate desktop coordinates. The panel is capped at 480 × 400 compositor coordinates and leaves at least 16 on each side within the destination. Destinations smaller than 360 × 320 suppress it, giving the smallest offered panel 328 × 288. There is no chooser when no eligible candidate remains or an eligible window already occupies the matching half.

A bold, wrapping heading names the destination half, followed by a short Enter hint and a native single-selection list. Each row pairs a 32-pixel application icon with the window title and application ID. Icons resolve through the application's desktop-file Icon entry, then the system icon theme and generic application fallback. Long titles elide in the row and remain available in a tooltip; the list scrolls vertically. Selection and focus use the desktop palette and native Qt indicators. Internal margins are 16 logical pixels with 12 at the bottom; vertical spacing is 12. Korean and English labels share this structure.

The first candidate is selected on opening. Arrow keys navigate; Enter or clicking a row requests placement. Escape, the visible Skip button, closing the panel or moving focus outside dismisses it. Skip and Escape return focus to the first window when the chooser still owns focus. A lost update heartbeat also dismisses the panel, and a dismissed session cannot reappear from a late update.

KWin owns the candidate list and validates the active session again on selection. Candidates must be eligible work windows on the same display, desktop and activity, and their minimum/maximum client sizes, including decoration extents, must fit the destination. Success waits for the second window's actual frame to match the requested geometry. A refused or invalidated placement restores that window's previous placement when its context still permits rollback; it does not undo the first placement. Each window retains its own restore state.

### About

The footer's About button and the tray's About KRect action open the same reusable native dialog, including while the main window is hidden. It uses the application icon, a bold name, a selectable version from the application's shared version value, a short KDE description, website/source/license links and a standard Close button. Its system font and palette follow the main window; the name is 1.5 times the inherited point size, the icon is 64 pixels, and the layout uses 24-pixel margins with 20 at the bottom and 16-pixel spacing. Labels are available in Korean and English.

The capture prototype is shelved in `experiments/capture/`. Capture is absent from the desktop application's tabs, tray and package payload; the current app remains a window-placement utility.

### Evidence and review scope

The chooser's local Plasma 5.27/X11 evidence is `.impeccable/review/assist-native-x11.png`; `.impeccable/review/assist-ko.png` and `.impeccable/review/assist-en.png` are Qt 5 offscreen widget views. The finish review returned **ship** for the scoped fix pass: candidate size constraints/placement rollback and desktop-file icon resolution were both scored resolved. This disposition covers those two findings. Qt 6 and live Wayland behavior remain unverified. The web design detector does not apply to this native Qt surface.
