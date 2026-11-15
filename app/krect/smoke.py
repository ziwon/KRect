"""A native widget construction check, independent of the compositor/session."""
from pathlib import Path

from . import VERSION
from .assist import SnapAssist
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
    for index in range(window.tabs.count()):
        window.tabs.setCurrentIndex(index)
        app.processEvents()
        assert not window.grab().isNull()
    window.about_button.click()
    app.processEvents()
    about = window.about_dialog
    assert about.isVisible()
    assert about.version.text().endswith(VERSION)
    assert app.applicationVersion() == VERSION
    assert not about.grab().isNull()
    about.findChild(W.QDialogButtonBox).button(W.QDialogButtonBox.StandardButton.Close).click()
    assert not about.isVisible()
    window.hide()
    window.tray_about.trigger()
    app.processEvents()
    assert about.isVisible() and not window.isVisible(), "Tray About must work with the main window hidden"
    window.tray_about.trigger()
    assert window.about_dialog is about, "Repeated About commands must reuse the dialog"
    about.close()
    chooser = SnapAssist()
    selected = []
    chooser.command.connect(lambda session, target: selected.append((session, target)))
    chooser.receive(dict(visible=True, session="smoke", action="right",
                         geometry=dict(x=0, y=0, width=480, height=400),
                         candidates=[dict(id="sample", caption="Sample window", application="org.krect.KRect")]))
    app.processEvents()
    assert chooser.isVisible() and chooser.windows.count() == 1
    assert not chooser.grab().isNull()
    chooser.windows.itemActivated.emit(chooser.windows.item(0))
    assert selected == [("smoke", "sample")] and not chooser.isVisible()
    window.quit()
    print(f"KRect UI, About version and window chooser passed on Qt {C.QT_VERSION_STR} (no compositor commands sent).")
    return 0
