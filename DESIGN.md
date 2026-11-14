# KRect desktop interface

The desktop app uses native Qt widgets, the system font, palette, icons and focus indicators. The user pinned Rectangle as the interaction reference and KDE as the operating environment. This is an Operate surface: selecting a layout and identifying its target lead the screen.

The window has Layouts, Shortcuts, and Preferences tabs. Layouts shows the selected external window, the real display topology, and compact layout buttons with geometric icons. The tray provides the same actions in a native menu. Preferences use standard form controls with explicit application and inline results. Shortcuts use native key sequence editors and reject conflicts before changing KDE bindings.

Spacing uses 8, 12, 16 and 24 logical pixels. Accent is reserved for the previewed placement and current target display. There is no custom stylesheet, decorative animation, or fixed light/dark palette. Hover and keyboard focus preview a placement; clicking applies it. A caption and accessible action name accompany each geometric icon.

Disabled, disconnected, no target, pending command and failed command states are explicit. Closing a window hides it only when a tray is available and that preference is enabled; Quit exits the app while KWin shortcuts continue.
