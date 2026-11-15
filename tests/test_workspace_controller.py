"""Startup restoration and native preset controls without a running compositor."""
from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from test_workspaces import snapshot
try:
    from krect.qt import QtCore as C, QtWidgets as W, Signal
    from krect.workspace_controller import WorkspaceController, launch_application
    from krect.workspace_page import WorkspacePage
except ImportError:
    WorkspaceController = None


if WorkspaceController:
    class Backend(C.QObject):
        changed = Signal(dict)
        workspace_result = Signal(dict)
        message = Signal(str, bool)

        def __init__(self):
            super().__init__()
            s = snapshot()
            self.enabled = True
            self.pending = None
            self.status = dict(workspacePresets=1, activity="work", desktops=s["desktops"], currentDesktop="d1")
            self.commands = []

        def submit(self, command):
            self.commands.append(command)
            self.pending = "request"

        def reply(self, **result):
            self.pending = None
            self.workspace_result.emit(result)

        def cancel_command(self):
            self.pending = None


@unittest.skipUnless(WorkspaceController, "Needs distribution Qt")
class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = W.QApplication.instance() or W.QApplication(["krect-test"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backend = Backend()
        self.clock = 10
        self.launched = []
        self.manager = WorkspaceController(self.backend, Path(self.temp.name) / "presets.json",
                                           launcher=self.launched.append, clock=lambda: self.clock)
        self.backend.workspaces = self.manager
        self.manager.store.save(snapshot())
        self.addCleanup(self.manager.timer.stop)

    def test_startup_restores_only_enabled_profiles_and_does_not_steal_focus(self):
        profile = self.manager.store.profiles[0]
        self.manager.store.update(profile["id"], profile["name"], False, False)
        self.manager.startup()
        self.assertEqual(self.backend.commands[-1]["kind"], "workspace-snapshot")
        self.backend.reply(success=True, snapshot=snapshot())
        command = self.backend.commands[-1]
        self.assertEqual(command["kind"], "workspace-restore")
        self.assertEqual(len(command["placements"]), 3)
        self.assertFalse(any(p["saved"]["desktop"] == "d1" for p in command["placements"]))
        self.backend.reply(success=True, rows=[dict(key=p["key"], id=p["id"], status="restored") for p in command["placements"]])
        self.assertFalse(self.manager.busy)
        self.assertEqual(self.launched, [])

    def test_startup_is_scheduled_once_and_skips_user_initiated_pending_commands(self):
        with patch.object(C.QTimer, "singleShot") as schedule:
            self.manager.observe(self.backend.status)
            self.manager.observe(self.backend.status)
        schedule.assert_called_once()
        self.backend.pending = "user-placement"
        self.manager.startup()
        self.assertEqual(self.backend.commands, [])

    def test_missing_program_launches_once_then_its_new_window_is_restored(self):
        profile = self.manager.store.profiles[0]
        self.manager.store.update(profile["id"], profile["name"], True, True)
        self.manager.restore([profile["id"]])
        empty = snapshot(); empty["windows"] = []; empty["runningApplications"] = []
        self.backend.reply(success=True, snapshot=empty)
        self.assertEqual(self.launched, ["code"])
        self.manager.poll(); self.backend.reply(success=True, snapshot=empty)
        self.assertEqual(self.launched, ["code"])
        self.manager.poll()
        live = snapshot(); live["session"] = "new"; live["windows"][0]["id"] = "new-window"
        self.backend.reply(success=True, snapshot=live)
        command = self.backend.commands[-1]
        self.assertEqual(command["placements"][0]["id"], "new-window")
        self.backend.reply(success=True, rows=[dict(key=command["placements"][0]["key"], id="new-window", status="restored")])
        self.assertFalse(self.manager.busy)

    def test_missing_windows_wait_bounded_time_without_launch_permission(self):
        self.manager.startup()
        empty = snapshot(); empty["windows"] = []; empty["runningApplications"] = []
        self.backend.reply(success=True, snapshot=empty)
        self.assertTrue(self.manager.busy)
        self.assertFalse(self.launched)
        self.clock = 41
        self.manager.poll()
        self.assertFalse(self.manager.busy)
        self.assertIn("4", self.manager.message)

    def test_cancel_stops_retries_and_asks_engine_to_cancel_pending_moves(self):
        self.manager.startup()
        self.manager.cancel()
        self.assertFalse(self.manager.busy)
        self.assertFalse(self.manager.timer.isActive())
        self.assertEqual(self.backend.commands[-1]["kind"], "workspace-cancel")
        self.backend.reply(success=True, snapshot=snapshot())
        self.assertFalse(self.manager.busy)

    def test_native_page_saves_names_options_and_snapshot_for_selected_desktop(self):
        page = WorkspacePage(self.backend)
        page.show(); self.app.processEvents()
        page.desktops.setCurrentIndex(1)
        page.name.setText("학습")
        page.auto.setChecked(True); page.launch.setChecked(True)
        page.buttons["save"].click()
        self.assertEqual(self.manager.store.profiles[1]["name"], "학습")
        self.assertTrue(self.manager.store.profiles[1]["launchMissing"])
        page.buttons["capture"].click()
        self.backend.reply(success=True, snapshot=snapshot())
        self.assertEqual(self.manager.store.profiles[1]["windows"][0]["caption"], "Course")
        self.assertFalse(page.grab().isNull())
        page.close()

    def test_app_launcher_uses_desktop_entry_without_a_shell(self):
        entry = Path(self.temp.name) / "code.desktop"
        entry.write_text('[Desktop Entry]\nType=Application\nName=Code\nExec=code\n')
        with patch.object(C.QStandardPaths, "locate", return_value=str(entry)), \
                patch("krect.workspace_controller.shutil.which", return_value="/usr/bin/gio"), \
                patch("krect.workspace_controller.subprocess.Popen") as spawn:
            launch_application("code")
            self.assertEqual(spawn.call_args.args[0], ["/usr/bin/gio", "launch", str(entry)])
            self.assertNotIn("shell", spawn.call_args.kwargs)
            with self.assertRaises(ValueError):
                launch_application("$(touch /tmp/unwanted)")
            self.assertEqual(spawn.call_count, 1)


if __name__ == "__main__":
    unittest.main()
