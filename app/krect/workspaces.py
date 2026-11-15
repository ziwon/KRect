"""Local workspace presets and conservative window matching, independent of Qt."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import uuid


def text(value, limit=512):
    return isinstance(value, str) and len(value) <= limit


def geometry(value):
    return (isinstance(value, dict) and all(type(value.get(k)) in (int, float) and
            math.isfinite(value[k]) and abs(value[k]) <= 1000000 for k in ("x", "y", "width", "height")) and
            value["width"] > 0 and value["height"] > 0)


def desktop(value):
    return (isinstance(value, dict) and text(value.get("id")) and bool(value["id"]) and
            type(value.get("number")) is int and 1 <= value["number"] <= 64 and text(value.get("name")))


def window(value):
    return (isinstance(value, dict) and all(text(value.get(k)) for k in
            ("id", "application", "resourceClass", "role", "caption", "desktop", "output")) and
            bool(value["id"]) and bool(value["application"] or value["resourceClass"]) and
            geometry(value.get("geometry")) and geometry(value.get("area")) and
            type(value.get("mode")) is int and value["mode"] in range(4) and
            type(value.get("minimized")) is bool)


def validate_snapshot(value):
    if not (isinstance(value, dict) and value.get("schema") == 1 and text(value.get("session")) and
            text(value.get("activity")) and text(value.get("currentDesktop")) and
            isinstance(value.get("desktops"), list) and 1 <= len(value["desktops"]) <= 64 and
            all(desktop(d) for d in value["desktops"]) and
            isinstance(value.get("windows"), list) and len(value["windows"]) <= 256 and
            all(window(w) for w in value["windows"])):
        raise ValueError("Invalid workspace snapshot")
    ids = {d["id"] for d in value["desktops"]}
    if (len(ids) != len(value["desktops"]) or len({w["id"] for w in value["windows"]}) != len(value["windows"]) or
            any(w["desktop"] not in ids for w in value["windows"])):
        raise ValueError("Invalid workspace window/desktop identity")
    return value


def identity(w):
    return (w["application"] or w["resourceClass"]).removesuffix(".desktop")


class PresetStore:
    def __init__(self, path):
        self.path = Path(path)
        self.profiles = []
        self.error = None
        try:
            if self.path.exists():
                if self.path.stat().st_size > 4 * 1024 * 1024:
                    raise ValueError("Preset file is too large")
                data = json.loads(self.path.read_text())
                if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("profiles"), list):
                    raise ValueError("Unsupported preset file")
                for p in data["profiles"]:
                    if not (isinstance(p, dict) and text(p.get("id")) and bool(p["id"]) and
                            text(p.get("name"), 100) and bool(p["name"].strip()) and desktop(p.get("desktop")) and
                            text(p.get("activity")) and text(p.get("session")) and text(p.get("updated")) and
                            type(p.get("restoreOnStart")) is bool and type(p.get("launchMissing")) is bool and
                            isinstance(p.get("windows"), list) and len(p["windows"]) <= 256 and
                            all(window(w) and w["desktop"] == p["desktop"]["id"] for w in p["windows"])):
                        raise ValueError("Invalid workspace preset")
                if len(data["profiles"]) > 64 or len({p["id"] for p in data["profiles"]}) != len(data["profiles"]):
                    raise ValueError("Duplicate or excessive presets")
                self.profiles = data["profiles"]
        except (OSError, ValueError, TypeError) as error:
            self.error = str(error)

    def write(self, profiles):
        if self.error:
            raise ValueError(self.error + "; the existing file has been preserved")
        if len(profiles) > 64:
            raise ValueError("At most 64 workspace presets can be saved")
        payload = json.dumps(dict(schema=1, profiles=profiles), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if len(payload.encode()) > 4 * 1024 * 1024:
            raise ValueError("Preset file would exceed 4 MiB")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, prefix=".workspaces-", delete=False) as f:
                temporary = Path(f.name)
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
            self.profiles = deepcopy(profiles)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def save(self, snapshot, desktop_id=None, name=None, preferences=None):
        validate_snapshot(snapshot)
        if name is not None and (not text(name, 100) or not name.strip()):
            raise ValueError("Give the workspace a name (1–100 characters)")
        profiles = deepcopy(self.profiles)
        selected = [d for d in snapshot["desktops"] if desktop_id is None or d["id"] == desktop_id]
        if not selected:
            raise ValueError("The selected desktop no longer exists")
        for d in selected:
            prior = next((p for p in profiles if p["desktop"]["id"] == d["id"] and p["activity"] == snapshot["activity"]), None)
            p = dict(id=prior["id"] if prior else uuid.uuid4().hex,
                     name=(name.strip() if name else prior["name"] if prior else d["name"] or f"D{d['number']}"),
                     desktop=deepcopy(d), activity=snapshot["activity"], session=snapshot["session"],
                     updated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     restoreOnStart=prior["restoreOnStart"] if prior else True,
                     launchMissing=prior["launchMissing"] if prior else False,
                     windows=deepcopy([w for w in snapshot["windows"] if w["desktop"] == d["id"]]))
            if preferences is not None:
                p.update(restoreOnStart=bool(preferences[0]), launchMissing=bool(preferences[1]))
            if prior:
                profiles[profiles.index(prior)] = p
            else:
                profiles.append(p)
        self.write(profiles)

    def update(self, profile_id, name, restore_on_start, launch_missing):
        if not text(name, 100) or not name.strip():
            raise ValueError("Give the workspace a name (1–100 characters)")
        profiles = deepcopy(self.profiles)
        p = next(p for p in profiles if p["id"] == profile_id)
        p.update(name=name.strip(), restoreOnStart=bool(restore_on_start), launchMissing=bool(launch_missing))
        self.write(profiles)

    def remove(self, profile_id):
        self.write([p for p in self.profiles if p["id"] != profile_id])


def plan_restore(profiles, snapshot, done=(), used=(), known_profiles=None):
    """Never guess between indistinguishable windows, or reuse one window twice."""
    validate_snapshot(snapshot)
    counts = Counter(identity(w) for p in (known_profiles or profiles) for w in p["windows"])
    windows = snapshot["windows"]
    taken = set(used)
    placements, waiting, skipped = [], [], []
    desktops = {d["id"] for d in snapshot["desktops"]}
    for profile in profiles:
        for index, saved in enumerate(profile["windows"]):
            key = f"{profile['id']}:{index}"
            if key in done:
                continue
            if profile["activity"] != snapshot["activity"] or profile["desktop"]["id"] not in desktops:
                skipped.append(dict(key=key, reason="desktop-or-activity-missing"))
                continue
            pool = [w for w in windows if w["id"] not in taken and identity(w) == identity(saved) and
                    (not saved["role"] or w["role"] == saved["role"])]
            matches = [w for w in pool if profile["session"] == snapshot["session"] and w["id"] == saved["id"]]
            if not matches:
                matches = [w for w in pool if saved["caption"] and w["caption"] == saved["caption"]]
                if len(matches) > 1:
                    matches = [w for w in matches if w["desktop"] == profile["desktop"]["id"]]
            if not matches and counts[identity(saved)] == 1 and len(pool) == 1:
                matches = pool
            if len(matches) != 1:
                waiting.append(dict(key=key, application=saved["application"], identity=identity(saved),
                                    aliases=[saved["application"].removesuffix(".desktop"), saved["resourceClass"]],
                                    launch=profile["launchMissing"], reason="ambiguous" if pool else "missing"))
                continue
            current = matches[0]
            taken.add(current["id"])
            placements.append(dict(key=key, id=current["id"], expected=deepcopy(current), saved=deepcopy(saved)))
    return placements, waiting, skipped
