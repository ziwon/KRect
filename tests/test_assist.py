"""Chooser input, stale messages and the compositor-to-Qt boundary."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
try:
    from krect.assist import SnapAssist, application_icon
    from krect.backend import DesktopBridge
    from krect.qt import QtCore as C, QtGui as G, QtWidgets as W, QT_MAJOR
    if QT_MAJOR == 6:
        from PyQt6.QtTest import QTest
    else:
        from PyQt5.QtTest import QTest
except ImportError:
    SnapAssist = None


@unittest.skipUnless(SnapAssist, "Needs distribution PyQt and python3-dbus")
class AssistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = W.QApplication.instance() or W.QApplication(["krect"])

    def setUp(self):
        self.bridge = DesktopBridge()
        self.chooser = SnapAssist()
        self.bridge.assist_updated.connect(self.chooser.receive)
        self.commands = []
        self.chooser.command.connect(lambda session, target: self.commands.append((session, target)))
        self.model = dict(visible=True, session="test:1", action="right",
                          geometry=dict(x=-800, y=200, width=480, height=400),
                          candidates=[dict(id="editor", caption="notes.md — Editor", application="editor"),
                                      dict(id="browser", caption="Documentation — Browser", application="browser")])

    def tearDown(self):
        self.chooser.dismiss()

    def show(self, model=None):
        self.bridge.AssistUpdate(json.dumps(model or self.model))
        self.app.processEvents()

    def test_click_places_exactly_once_and_old_heartbeats_do_not_reopen(self):
        self.show()
        item = self.chooser.windows.item(1)
        QTest.mouseClick(self.chooser.windows.viewport(), C.Qt.MouseButton.LeftButton,
                         pos=self.chooser.windows.visualItemRect(item).center())
        self.assertEqual(self.commands, [("test:1", "browser")])
        self.assertFalse(self.chooser.isVisible())
        self.show()
        self.assertFalse(self.chooser.isVisible())
        self.show(dict(self.model, session="test:2"))
        self.assertTrue(self.chooser.isVisible())

    def test_keyboard_navigation_and_enter_choose_the_focused_window(self):
        self.show()
        QTest.keyClick(self.chooser.windows, C.Qt.Key.Key_Down)
        QTest.keyClick(self.chooser.windows, C.Qt.Key.Key_Return)
        self.assertEqual(self.commands, [("test:1", "browser")])

    def test_escape_skip_focus_loss_and_watchdog_cancel_without_a_target(self):
        for index, dismiss in enumerate([
            lambda: QTest.keyClick(self.chooser.windows, C.Qt.Key.Key_Escape),
            self.chooser.skip_button.click,
            lambda: self.app.sendEvent(self.chooser, C.QEvent(C.QEvent.Type.WindowDeactivate)),
            self.chooser.watchdog.timeout.emit,
        ]):
            session = f"cancel:{index}"
            self.show(dict(self.model, session=session))
            dismiss()
            self.assertEqual(self.commands[-1], (session, ""))
            self.assertFalse(self.chooser.isVisible())
            self.assertFalse(self.chooser.watchdog.isActive())

    def test_candidate_updates_preserve_selection_and_engine_hide_sends_no_command(self):
        self.show()
        self.chooser.windows.setCurrentRow(1)
        self.show(dict(self.model, candidates=list(reversed(self.model["candidates"]))))
        self.assertEqual(self.chooser.windows.currentItem().data(C.Qt.ItemDataRole.UserRole), "browser")
        self.assertFalse(self.chooser.grab().isNull())
        self.bridge.AssistUpdate('{"visible":false}')
        self.assertFalse(self.chooser.isVisible())
        self.assertEqual(self.commands, [])

    def test_invalid_payloads_never_open_a_chooser(self):
        invalid = ["invalid", "null", "[]", '{"visible":true}',
                   json.dumps(dict(self.model, session=3)), json.dumps(dict(self.model, action="maximize")),
                   json.dumps(dict(self.model, candidates=[])), json.dumps(dict(self.model, candidates=[None])),
                   json.dumps(dict(self.model, candidates=self.model["candidates"] * 2)),
                   json.dumps(dict(self.model, candidates=[dict(id="x", caption=[], application="app")])),
                   json.dumps(dict(self.model, geometry=dict(x=float("nan"), y=0, width=480, height=400))),
                   json.dumps(dict(self.model, geometry=dict(x=0, y=0, width=100000, height=400)))]
        for raw in invalid:
            self.bridge.AssistUpdate(raw)
            self.assertFalse(self.chooser.isVisible(), raw)

    def test_desktop_entry_icon_can_differ_from_application_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pixmap = G.QPixmap(16, 16)
            color = G.QColor("#2176aa")
            pixmap.fill(color)
            self.assertTrue(pixmap.save(str(root / "actual-icon.png")))
            desktop = root / "org.example.App.desktop"
            desktop.write_text(f"[Desktop Entry]\nType=Application\nName=Example\nIcon={root / 'actual-icon.png'}\n")
            with patch.object(C.QStandardPaths, "locate", return_value=str(desktop)):
                icon = application_icon("org.example.App")
            self.assertFalse(icon.isNull())
            self.assertEqual(icon.pixmap(16, 16).toImage().pixelColor(8, 8), color)


if __name__ == "__main__":
    unittest.main()
