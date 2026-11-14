"""A native widget construction check, independent of the compositor/session."""
from pathlib import Path

from .backend import DEFAULTS
from .qt import QtCore as C, QtWidgets as W, Signal
from .window import Window


class OfflineBackend(C.QObject):
    changed = Signal(dict)
    message = Signal(str, bool)
    major = 6 if C.QT_VERSION_STR.startswith("6") else 5
    enabled = False
    status = {}
    pending = None
    values = DEFAULTS.copy()

    def autostart_path(self):
        return Path("/nonexistent/krect-smoke/autostart.desktop")

    def close_to_tray(self):
        return False


def smoke(app, icon):
    backend = OfflineBackend()
    window = Window(backend, icon)
    window.show()
    app.processEvents()
    assert len(window.buttons) == 18
    assert len(window.key_editors) == 18
    assert all(not b.isEnabled() for b in window.buttons.values())
    assert not icon.pixmap(32, 32).isNull(), "Application icon could not be rendered"
    for index in range(3):
        window.tabs.setCurrentIndex(index)
        app.processEvents()
        assert not window.grab().isNull()
    window.quit()
    print("KRect native UI construction passed (no compositor commands sent).")
    return 0
