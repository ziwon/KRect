#!/usr/bin/python3
"""KRect desktop entry point; run with the distribution Python and Qt binding."""
import argparse
from pathlib import Path
import sys
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description="Rectangle-style window placement for KDE")
    parser.add_argument("--background", action="store_true", help="Start in the system tray")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help="Check native UI construction without changing KDE")
    parser.add_argument("--language", choices=["ko", "en"], help="Override the desktop language")
    args = parser.parse_args()
    from krect import VERSION
    if args.version:
        print("KRect " + VERSION)
        return 0
    try:
        from krect.qt import QtCore as C, QtGui as G, QtWidgets as W, QtDBus as D, run
        from krect import model
        if args.language:
            model.KOREAN = args.language == "ko"
            model.LABELS.update({key: model.tr(en, ko) for key, en, ko in model.ACTIONS})
        from krect.backend import Backend, DesktopBridge, SERVICE
        from krect.window import Window
        from krect.snap import SnapBar
        from krect.assist import SnapAssist
    except ImportError as error:
        print(f"KRect: {error}. Install python3-dbus and python3-pyqt5 (Plasma 5) or python3-pyqt6 (Plasma 6).", file=sys.stderr)
        return 1
    app = W.QApplication(["krect"])
    app.setApplicationName("krect")
    app.setApplicationDisplayName("KRect")
    app.setOrganizationName("krect")
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName(SERVICE)
    app.setQuitOnLastWindowClosed(False)
    icon = G.QIcon.fromTheme(SERVICE, G.QIcon(str(Path(__file__).parent / "assets/org.krect.KRect.svg")))
    app.setWindowIcon(icon)
    if args.smoke_test:
        from krect.smoke import smoke
        return smoke(app, icon)
    bus = D.QDBusConnection.sessionBus()
    if not bus.isConnected():
        print("KRect: no desktop session D-Bus is available.", file=sys.stderr)
        return 1
    if not bus.registerService(SERVICE):
        if not args.background:
            reply = D.QDBusInterface(SERVICE, "/KRect", SERVICE, bus).call("Activate")
            if reply.type() == D.QDBusMessage.MessageType.ErrorMessage:
                print("KRect: " + reply.errorMessage(), file=sys.stderr)
                return 1
        return 0
    bridge = DesktopBridge()
    if not bus.registerObject("/KRect", SERVICE, bridge, D.QDBusConnection.RegisterOption.ExportAllSlots):
        print("KRect: could not register the desktop bridge.", file=sys.stderr)
        return 1
    try:
        backend = Backend(bridge)
        window = Window(backend, icon)
        snap_bar = SnapBar()
        snap_assist = SnapAssist()
        bridge.snap_updated.connect(snap_bar.receive)
        bridge.assist_updated.connect(snap_assist.receive)
        snap_assist.command.connect(backend.assist_command)
        backend.changed.connect(lambda status: snap_bar.dismiss() if not backend.enabled else None)
        backend.changed.connect(lambda status: snap_assist.dismiss() if not backend.enabled else None)
        app.aboutToQuit.connect(snap_bar.dismiss)
        app.aboutToQuit.connect(snap_assist.dismiss)
        bridge.activated.connect(window.activate)
        window.perform(backend.connect_engine)
    except Exception as error:
        W.QMessageBox.critical(None, "KRect", str(error))
        return 1
    if not args.background or not W.QSystemTrayIcon.isSystemTrayAvailable():
        window.show()
    return run(app)


if __name__ == "__main__":
    sys.exit(main())
