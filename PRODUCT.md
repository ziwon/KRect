# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

Native Linux desktop application for Ubuntu KDE, using Qt 5 on Plasma 5.27 and Qt 6 on Plasma 6.

## Users

Ubuntu KDE users who want the discoverability and direct controls of Mac Rectangle alongside fast keyboard window placement.

## Product Purpose

Find KRect in the application launcher, arrange a selected working window, and manage shortcuts and placement preferences from a dedicated app and system tray.

## Positioning

Rectangle's window placement workflow integrated with KWin, KDE global shortcuts, panel work areas, portrait displays, and multiple monitors. Window management runs inside the compositor on X11 and Wayland.

## Capabilities and Constraints

Support Plasma 5.27 and 6, preserve the existing 18 placement actions, and retain a script-only installation option. A desktop app must never arrange its own settings window. Original placements are kept only during a KWin script session. Plasma 6 and Wayland require live validation beyond the current Plasma 5/X11 machine.

## Brand Commitments

Name: KRect. The user requested a Mac Rectangle clone optimized for Ubuntu KDE. Familiar KDE controls and the user's desktop theme take precedence over an independent visual identity.

## Evidence on Hand

README.md, docs/VALIDATION.md, source and automated tests. Local desktop has one landscape and one portrait display. Existing release is 0.1.0, a script prototype.
