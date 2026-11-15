"""Desktop snapshots, durable storage and unambiguous window identity."""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from krect.workspaces import PresetStore, plan_restore


def snapshot():
    area = dict(x=-1600, y=32, width=1600, height=968)
    return dict(schema=1, session="session-1", activity="work", currentDesktop="d1",
                desktops=[dict(id=f"d{i}", number=i, name=n) for i, n in enumerate(["Development", "Study", "Trading", "Work"], 1)],
                windows=[dict(id=str(i), application=app, resourceClass=app, role="", caption=title,
                              desktop=f"d{i}", output="DP-1", area=area.copy(), mode=0, minimized=False,
                              geometry=dict(x=-1500+i*100, y=100, width=800, height=600))
                         for i, (app, title) in enumerate([("code", "KRect — Code"), ("browser", "Course"),
                                                           ("browser", "Market"), ("terminal", "Company")], 1)],
                runningApplications=["code", "browser", "terminal"])


class PresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "workspaces.json"
        self.store = PresetStore(self.path)
        self.snapshot = snapshot()
        self.store.save(self.snapshot)

    def test_four_desktops_round_trip_and_names_options_survive_recapture(self):
        self.assertEqual(len(self.store.profiles), 4)
        first = self.store.profiles[0]
        self.store.update(first["id"], "개인 개발", True, True)
        self.store.save(self.snapshot)
        loaded = PresetStore(self.path)
        self.assertFalse(loaded.error)
        self.assertEqual(loaded.profiles[0]["name"], "개인 개발")
        self.assertTrue(loaded.profiles[0]["launchMissing"])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_failed_atomic_replace_preserves_previous_file_and_memory(self):
        before, profiles = self.path.read_bytes(), deepcopy(self.store.profiles)
        with patch("krect.workspaces.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.store.remove(profiles[0]["id"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.profiles, profiles)
        self.assertEqual(list(self.path.parent.glob(".workspaces-*")), [])

    def test_corrupt_or_future_schema_is_preserved_instead_of_overwritten(self):
        for raw in ("not json", '{"schema":2,"profiles":[]}'):
            self.path.write_text(raw)
            store = PresetStore(self.path)
            self.assertTrue(store.error)
            with self.assertRaises(ValueError):
                store.save(self.snapshot)
            self.assertEqual(self.path.read_text(), raw)

    def test_same_session_ids_match_after_caption_changes_without_reusing_windows(self):
        live = deepcopy(self.snapshot)
        for w in live["windows"]:
            w["caption"] = "Changed"
            w["desktop"] = "d1"
        placements, waiting, skipped = plan_restore(self.store.profiles, live)
        self.assertEqual(len(placements), 4)
        self.assertEqual(len({p["id"] for p in placements}), 4)
        self.assertEqual([p["saved"]["desktop"] for p in placements], ["d1", "d2", "d3", "d4"])
        self.assertFalse(waiting or skipped)

    def test_restart_matches_titles_and_only_uniquely_identified_app_fallback(self):
        live = deepcopy(self.snapshot)
        live["session"] = "new-session"
        for w in live["windows"]:
            w["id"] += "-new"
            w["desktop"] = "d1"
        live["windows"][0]["caption"] = "Other code project"
        placements, waiting, _ = plan_restore(self.store.profiles, live)
        self.assertEqual(len(placements), 4)
        self.assertFalse(waiting)
        live["windows"][1]["caption"] = live["windows"][2]["caption"] = "New tab"
        placements, waiting, _ = plan_restore(self.store.profiles, live)
        self.assertEqual(len(placements), 2)
        self.assertEqual(len(waiting), 2)
        self.assertTrue(all(w["reason"] == "ambiguous" for w in waiting))

    def test_single_desktop_restore_does_not_steal_another_saved_browser(self):
        live = deepcopy(self.snapshot)
        live["session"] = "new"
        live["windows"] = [dict(live["windows"][2], id="other", caption="New tab")]
        placements, waiting, _ = plan_restore([self.store.profiles[1]], live, known_profiles=self.store.profiles)
        self.assertFalse(placements)
        self.assertEqual(waiting[0]["reason"], "ambiguous")

    def test_missing_desktop_or_different_activity_is_skipped(self):
        live = deepcopy(self.snapshot)
        live["desktops"] = live["desktops"][:3]
        live["windows"] = live["windows"][:3]
        placements, _, skipped = plan_restore(self.store.profiles, live)
        self.assertEqual(len(placements), 3)
        self.assertEqual(len(skipped), 1)
        live["activity"] = "other"
        placements, _, skipped = plan_restore(self.store.profiles, live)
        self.assertFalse(placements)
        self.assertEqual(len(skipped), 4)

    def test_completed_rows_and_windows_are_never_applied_twice(self):
        first, _, _ = plan_restore(self.store.profiles, self.snapshot)
        again, waiting, _ = plan_restore(self.store.profiles, self.snapshot,
                                       done={p["key"] for p in first}, used={p["id"] for p in first})
        self.assertEqual(again, [])
        self.assertEqual(waiting, [])

    def test_invalid_geometry_does_not_damage_existing_snapshot(self):
        before = self.path.read_bytes()
        self.snapshot["windows"][0]["geometry"]["width"] = float("nan")
        with self.assertRaises(ValueError):
            self.store.save(self.snapshot)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
