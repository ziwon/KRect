"""KWin and KDE integration. No X11-only window manipulation is used."""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

import dbus

from . import VERSION
from .model import LABELS, tr
from .qt import QtCore, Signal, Slot

SERVICE = "org.krect.KRect"
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULTS = {"Gap": 8, "CycleHalves": True, "CycleTimeout": 1200,
            "PortraitThirds": True, "SnapBar": True, "SnapAssist": True, "IgnoredApplications": ""}


class DesktopBridge(QtCore.QObject):
    updated = Signal(dict)
    activated = Signal()
    snap_updated = Signal(dict)
    assist_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.command = {}

    @Slot(str)
    def Update(self, raw):
        try:
            status = json.loads(raw)
            if isinstance(status, dict) and status.get("protocol") == 1:
                self.updated.emit(status)
        except (ValueError, TypeError):
            pass

    @Slot(result=str)
    def TakeCommand(self):
        command, self.command = self.command, {}
        return json.dumps(command)

    @Slot(str)
    def SnapUpdate(self, raw):
        try:
            model = json.loads(raw)
            if not isinstance(model, dict):
                return
            if model.get("visible"):
                geometry = model.get("geometry", {})
                cells = model.get("cells", [])
                if not all(type(geometry.get(k)) in (int, float) and math.isfinite(geometry[k]) for k in ("x", "y", "width", "height")):
                    return
                if not (0 < geometry.get("width", 0) <= 1000 and 0 < geometry.get("height", 0) <= 200):
                    return
                if not isinstance(cells, list) or not cells or len(cells) > 20:
                    return
                for cell in cells:
                    r = cell.get("rect", {})
                    if cell.get("action") not in LABELS or not all(type(r.get(k)) in (int, float) and math.isfinite(r[k]) for k in ("x", "y", "width", "height")):
                        return
                    if not (r["x"] >= 0 and r["y"] >= 0 and r["width"] > 0 and r["height"] > 0 and
                            r["x"] + r["width"] <= geometry["width"] and r["y"] + r["height"] <= geometry["height"]):
                        return
                if type(model.get("selected", -1)) is not int or not -1 <= model.get("selected", -1) < len(cells):
                    return
            self.snap_updated.emit(model)
        except (ValueError, TypeError, AttributeError):
            pass

    @Slot()
    def Activate(self):
        self.activated.emit()

    @Slot(str)
    def AssistUpdate(self, raw):
        try:
            model = json.loads(raw)
            if not isinstance(model, dict) or type(model.get("visible")) is not bool:
                return
            if model["visible"]:
                geometry = model.get("geometry", {})
                if not all(type(geometry.get(k)) in (int, float) and math.isfinite(geometry[k]) for k in ("x", "y", "width", "height")):
                    return
                if not (0 < geometry["width"] <= 1000 and 0 < geometry["height"] <= 800):
                    return
                if not isinstance(model.get("session"), str) or not 0 < len(model["session"]) <= 100:
                    return
                if model.get("action") not in ("left", "right", "top", "bottom"):
                    return
                candidates = model.get("candidates")
                if not isinstance(candidates, list) or not 0 < len(candidates) <= 50:
                    return
                ids = set()
                for candidate in candidates:
                    for key, limit in (("id", 200), ("caption", 300), ("application", 200)):
                        if not isinstance(candidate.get(key), str) or len(candidate[key]) > limit:
                            return
                    if not candidate["id"] or candidate["id"] in ids:
                        return
                    ids.add(candidate["id"])
            self.assist_updated.emit(model)
        except (ValueError, TypeError, AttributeError):
            pass


class Backend(QtCore.QObject):
    changed = Signal(dict)
    message = Signal(str, bool)

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.bus = dbus.SessionBus()
        self.status = {}
        self.enabled = False
        self.pending = None
        self.major = self.plasma_major()
        self.preferences = QtCore.QSettings("krect", "desktop")
        self.values = self.read_settings()
        bridge.updated.connect(self.receive)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.timeout = QtCore.QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(4000)
        self.timeout.timeout.connect(self.command_timeout)

    @staticmethod
    def plasma_major():
        result = subprocess.run(["plasmashell", "--version"], capture_output=True, text=True, timeout=5)
        match = re.search(r"plasmashell (\d+)\.(\d+)", result.stdout)
        if not match or int(match[1]) not in (5, 6) or (int(match[1]) == 5 and int(match[2]) < 27):
            raise RuntimeError(tr("KRect needs KDE Plasma 5.27 or 6.", "KDE Plasma 5.27 또는 6이 필요해요."))
        return int(match[1])

    def call(self, service, path, interface, method, signature="", args=()):
        return self.bus.call_blocking(service, path, interface, method, signature, args, timeout=3)

    def scripting(self, method, signature="", args=()):
        return self.call("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", method, signature, args)

    def accel(self, method, signature, args):
        return self.call("org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel", method, signature, args)

    def invoke(self, action):
        self.call("org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component",
                  "invokeShortcut", "s", ("KRect-" + action,))

    @staticmethod
    def script_path():
        # A source checkout is runnable without installing. Installed apps use
        # KPackage precedence, including an existing user override.
        checkout = Path(__file__).resolve().parents[2]
        if (checkout / "src/main.js").is_file():
            return checkout / "src/main.js"
        roots = [DATA, *[Path(p) for p in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")]]
        for root in roots:
            candidate = root / "kwin/scripts/krect/contents/code/main.js"
            if candidate.is_file():
                return candidate
        raise RuntimeError(tr("KRect's KWin script is missing. Reinstall KRect.", "KWin 스크립트가 없어요. KRect를 다시 설치하세요."))

    def write_config(self, group, key, value):
        tool = shutil.which(f"kwriteconfig{self.major}")
        if not tool:
            raise RuntimeError(f"kwriteconfig{self.major} is missing")
        text = str(value).lower() if isinstance(value, bool) else str(value)
        subprocess.run([tool, "--file", "kwinrc", "--group", group, "--key", key, text],
                       check=True, capture_output=True, text=True, timeout=5)

    def read_settings(self):
        tool = shutil.which(f"kreadconfig{self.major}")
        if not tool:
            raise RuntimeError(f"kreadconfig{self.major} is missing")
        values = {}
        for key, default in DEFAULTS.items():
            value = subprocess.check_output([tool, "--file", "kwinrc", "--group", "Script-krect", "--key", key,
                                             "--default", str(default).lower()], text=True, timeout=5).strip()
            try:
                values[key] = value.lower() == "true" if isinstance(default, bool) else int(value) if isinstance(default, int) else value
            except ValueError:
                values[key] = default
        return values

    def desired_enabled(self):
        return subprocess.check_output([f"kreadconfig{self.major}", "--file", "kwinrc", "--group", "Plugins",
                                        "--key", "krectEnabled", "--default", "false"], text=True, timeout=5).strip() == "true"

    def start(self, persist=True):
        path = self.script_path()
        self.cancel_command()
        if self.scripting("isScriptLoaded", "s", ("krect",)):
            self.scripting("unloadScript", "s", ("krect",))
        script_id = int(self.scripting("loadScript", "ss", (str(path), "krect")))
        if script_id < 0:
            raise RuntimeError(tr("KWin could not load KRect. Try signing out and back in.", "KWin이 KRect를 불러오지 못했어요. 다시 로그인한 뒤 실행하세요."))
        object_path = f"/{script_id}" if self.major == 5 else f"/Scripting/Script{script_id}"
        self.call("org.kde.KWin", object_path, "org.kde.kwin.Script", "run")
        if persist:
            self.write_config("Plugins", "krectEnabled", True)
        self.enabled = True
        self.status = {}
        self.changed.emit(self.status)
        QtCore.QTimer.singleShot(200, self.refresh)

    def connect_engine(self):
        if self.desired_enabled():
            if self.scripting("isScriptLoaded", "s", ("krect",)):
                self.enabled = True
                self.refresh()
                QtCore.QTimer.singleShot(1000, self.upgrade_connection)
            else:
                self.start()

    def upgrade_connection(self):
        if self.enabled and (self.status.get("version") != VERSION or self.status.get("snapBar") != 1 or self.status.get("snapAssist") != 1):
            try:
                self.start()
            except Exception as error:
                self.enabled = False
                self.message.emit(str(error), True)
                self.changed.emit({})

    def stop(self):
        self.cancel_command()
        self.write_config("Plugins", "krectEnabled", False)
        self.scripting("unloadScript", "s", ("krect",))
        self.enabled = False
        self.status = {}
        self.changed.emit(self.status)

    def cancel_command(self):
        self.bridge.command = {}
        self.pending = None
        self.timeout.stop()

    def refresh(self):
        if not self.enabled or self.pending:
            return
        try:
            if not self.scripting("isScriptLoaded", "s", ("krect",)):
                self.enabled = False
                self.status = {}
                self.changed.emit(self.status)
                return
            self.invoke("app-command")
        except dbus.DBusException as error:
            self.message.emit(str(error), True)

    def receive(self, status):
        self.status = status
        result = status.get("result") or {}
        if self.pending and result.get("token") == self.pending:
            self.pending = None
            self.timeout.stop()
            if not result.get("quiet"):
                self.message.emit(tr("Placement applied.", "배치를 적용했어요.") if result.get("success") else
                                  tr("Cannot apply to this window. Select a movable window and try again.", "이 창에 적용할 수 없어요. 이동 가능한 창을 선택하고 다시 시도하세요."), not result.get("success", False))
        self.changed.emit(status)

    def apply(self, action):
        target = self.status.get("target")
        if not self.enabled or not target or self.pending:
            return
        self.submit({"target": target["id"], "action": action})

    def assist_command(self, session, target):
        if self.enabled and not self.pending:
            self.submit({"kind": "assist", "session": session, "target": target})

    def submit(self, command):
        self.pending = uuid.uuid4().hex
        self.bridge.command = dict(command, token=self.pending)
        try:
            self.invoke("app-command")
            self.timeout.start()
            self.changed.emit(self.status)
        except dbus.DBusException as error:
            self.command_timeout()
            self.message.emit(str(error), True)

    def command_timeout(self):
        self.bridge.command = {}
        self.pending = None
        self.message.emit(tr("KWin did not respond. Switch KRect off and on, then try again.", "KWin 응답이 없어요. KRect를 껐다 켠 뒤 다시 시도하세요."), True)
        self.changed.emit(self.status)

    def save_settings(self, values, autostart, close_to_tray):
        for key in DEFAULTS:
            self.write_config("Script-krect", key, values[key])
        self.values = values
        self.preferences.setValue("closeToTray", close_to_tray)
        self.preferences.sync()
        self.set_autostart(autostart)
        if self.enabled:
            self.call("org.kde.KWin", "/KWin", "org.kde.KWin", "reconfigure")
            self.start()
        self.message.emit(tr("Preferences saved.", "환경설정을 저장했어요."), False)

    @staticmethod
    def autostart_path():
        return CONFIG / "autostart/org.krect.KRect.desktop"

    def set_autostart(self, enabled):
        path = self.autostart_path()
        if enabled:
            user_launcher = Path.home() / ".local/bin/krect"
            launcher = str(user_launcher) if user_launcher.is_file() else shutil.which("krect")
            if not launcher:
                raise RuntimeError(tr("Install KRect before enabling login startup.", "로그인 시 실행하려면 KRect를 먼저 설치하세요."))
            path.parent.mkdir(parents=True, exist_ok=True)
            # Desktop Entry quoting, not shell quoting; no command interpreter.
            quoted = launcher.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
            path.write_text(f'[Desktop Entry]\nType=Application\nName=KRect\nExec="{quoted}" --background\nIcon=org.krect.KRect\nOnlyShowIn=KDE;\n')
        else:
            path.unlink(missing_ok=True)

    def close_to_tray(self):
        return self.preferences.value("closeToTray", True, type=bool)

    @staticmethod
    def action_id(action):
        return dbus.Array(["kwin", "KRect-" + action, "KWin", "KRect: " + LABELS[action]], signature="s")

    def shortcuts(self):
        return {action: [int(k) for k in self.accel("shortcut", "as", (self.action_id(action),)) if int(k)] for action in LABELS}

    def save_shortcuts(self, mapping):
        before = self.shortcuts()
        occupied = {}
        for action, keys in mapping.items():
            for key in keys:
                if key in occupied:
                    raise RuntimeError(tr("Two KRect actions use the same shortcut: ", "KRect 단축키가 중복돼요: ") + LABELS[action])
                occupied[key] = action
                owner = list(self.accel("action", "i", (key,)))
                if owner and not (len(owner) > 1 and owner[0] == "kwin" and str(owner[1]) in {"KRect-" + a for a in mapping}):
                    raise RuntimeError(tr("Shortcut already used by: ", "이미 사용 중인 단축키: ") + str(owner[-1]))
        changed = [a for a in mapping if mapping[a] != before[a]]
        try:
            for action in changed:
                self.accel("setForeignShortcut", "asai", (self.action_id(action), dbus.Array([], signature="i")))
            for action in changed:
                self.accel("setForeignShortcut", "asai", (self.action_id(action), dbus.Array(mapping[action], signature="i")))
            if any(self.shortcuts()[a] != mapping[a] for a in changed):
                raise RuntimeError(tr("KDE did not accept the shortcuts.", "KDE가 단축키 변경을 적용하지 못했어요."))
        except Exception:
            for action in changed:
                self.accel("setForeignShortcut", "asai", (self.action_id(action), dbus.Array(before[action], signature="i")))
            raise
        self.message.emit(tr("Shortcuts saved in KDE.", "KDE에 단축키를 저장했어요."), False)

    def open_kde_shortcuts(self):
        subprocess.Popen([f"kcmshell{self.major}", "kcm_keys"], start_new_session=True)
