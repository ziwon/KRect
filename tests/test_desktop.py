"""The shortcut editor must never steal a different application's binding."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
try:
    from krect.backend import Backend
    from krect.qt import QtCore
    from krect.model import LABELS
except ImportError:
    Backend = None


class MemoryBackend(Backend or object):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.keys = {action: [] for action in LABELS}
        self.keys.update(left=[101], right=[102])
        self.foreign = {999: ["other-app", "close", "Other app", "Close"]}
        self.writes = []
        self.fail_once = False

    def accel(self, method, signature, args):
        if method == "shortcut":
            return self.keys[str(args[0][1]).removeprefix("KRect-")]
        if method == "action":
            if args[0] in self.foreign:
                return self.foreign[args[0]]
            for action, keys in self.keys.items():
                if args[0] in keys:
                    return ["kwin", "KRect-"+action, "KWin", action]
            return []
        if method == "setForeignShortcut":
            action = str(args[0][1]).removeprefix("KRect-")
            keys = [int(k) for k in args[1]]
            self.writes.append((action, keys))
            if self.fail_once and keys:
                self.fail_once = False
                raise RuntimeError("simulated KDE rejection")
            self.keys[action] = keys
            return
        raise AssertionError(method)


@unittest.skipUnless(Backend, "Desktop tests need distribution PyQt and python3-dbus")
class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.backend = MemoryBackend()
        self.original = self.backend.shortcuts()

    def test_foreign_conflict_changes_no_bindings(self):
        mapping = dict(self.original, left=[999])
        with self.assertRaisesRegex(RuntimeError, "Close"):
            self.backend.save_shortcuts(mapping)
        self.assertEqual(self.backend.shortcuts(), self.original)
        self.assertEqual(self.backend.writes, [])

    def test_duplicate_krect_bindings_are_rejected_before_writing(self):
        with self.assertRaises(RuntimeError):
            self.backend.save_shortcuts(dict(self.original, left=[102]))
        self.assertEqual(self.backend.writes, [])

    def test_swapping_krect_bindings_preserves_unedited_actions(self):
        self.backend.save_shortcuts(dict(self.original, left=[102], right=[101]))
        self.assertEqual(self.backend.shortcuts(), dict(self.original, left=[102], right=[101]))
        self.assertEqual({action for action, _ in self.backend.writes}, {"left", "right"})

    def test_failed_kde_write_restores_all_changed_bindings(self):
        self.backend.fail_once = True
        with self.assertRaisesRegex(RuntimeError, "rejection"):
            self.backend.save_shortcuts(dict(self.original, left=[103], right=[104]))
        self.assertEqual(self.backend.shortcuts(), self.original)


if __name__ == "__main__":
    unittest.main()
