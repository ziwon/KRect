"""Exercise the passive overlay and its D-Bus boundary without a compositor."""
import json
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
try:
    from krect.backend import DesktopBridge
    from krect.qt import QtCore as C, QtWidgets as W
    from krect.snap import SnapBar
except ImportError:
    SnapBar = None


@unittest.skipUnless(SnapBar, "Needs distribution PyQt and python3-dbus")
class SnapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = W.QApplication.instance() or W.QApplication(["krect-snap-test"])

    def setUp(self):
        self.bridge = DesktopBridge()
        self.bar = SnapBar()
        self.bridge.snap_updated.connect(self.bar.receive)
        self.model = dict(visible=True, geometry=dict(x=-1900, y=40, width=648, height=120),
                          cells=[dict(action="left", rect=dict(x=12, y=38, width=40, height=62))], selected=0)

    def tearDown(self):
        self.bar.dismiss()

    def test_visible_selection_renders_without_taking_focus_and_dismisses(self):
        self.bridge.SnapUpdate(json.dumps(self.model))
        self.app.processEvents()
        self.assertTrue(self.bar.isVisible())
        self.assertTrue(self.bar.windowFlags() & C.Qt.WindowType.WindowTransparentForInput)
        self.assertTrue(self.bar.windowFlags() & C.Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertFalse(self.bar.grab().isNull())
        self.bridge.SnapUpdate('{"visible":false}')
        self.assertFalse(self.bar.isVisible())
        self.assertFalse(self.bar.watchdog.isActive())

    def test_dead_engine_watchdog_hides_the_overlay(self):
        self.bridge.SnapUpdate(json.dumps(self.model))
        self.bar.watchdog.timeout.emit()
        self.assertFalse(self.bar.isVisible())
        self.assertEqual(self.bar.model, {})

    def test_bad_bridge_payloads_cannot_show_an_overlay(self):
        for raw in ["invalid", "null", "[]", '{"visible":true}',
                    json.dumps(dict(self.model, selected="0")),
                    json.dumps(dict(self.model, cells=[dict(action="left", rect=dict(x=0, y=0, width=float("nan"), height=10))])),
                    json.dumps(dict(self.model, cells=[dict(action="unknown", rect={})]))]:
            self.bridge.SnapUpdate(raw)
            self.assertFalse(self.bar.isVisible(), raw)


if __name__ == "__main__":
    unittest.main()
