#!/usr/bin/python3
"""Opt-in native workspace checks using only four disposable KDE/X11 windows.

Uses the real controller, local store and unmodified engine on a private D-Bus
service. Production KRect/config/shortcuts are untouched; no input is injected.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import dbus
from krect.backend import Backend, DesktopBridge
from krect.qt import QtCore as C, QtWidgets as W, QtDBus as D, Slot
from krect.workspace_controller import WorkspaceController
from krect.workspaces import PresetStore

SERVICE = "org.krect.WorkspaceValidation"
SCRIPT = "krect-workspace-validation"
EVIDENCE = ROOT / "dist/workspace-validation"

WRAPPER = r'''
var allowed = __IDS__;
function ours(w) { return allowed.indexOf(Number(w.windowId)) !== -1; }
function clients() { return workspace.clientList().filter(ours); }
function frame(w) { return module.exports.rect(w.frameGeometry); }
function otherFrames() {
    return workspace.clientList().filter(function (w) { return !ours(w) && w.normalWindow; }).map(function (w) {
        return { id: String(w.internalId), geometry: frame(w), desktop: w.desktop, screen: w.screen, minimized: w.minimized };
    }).sort(function (a, b) { return a.id.localeCompare(b.id); });
}
var originalOthers = JSON.stringify(otherFrames());
var isolated = { clientList: clients };
["activeClient", "currentDesktop", "currentActivity", "numScreens", "desktops", "cursorPos"].forEach(function (key) {
    Object.defineProperty(isolated, key, { get: function () { return workspace[key]; } });
});
["clientAdded", "clientRemoved", "clientActivated", "clientMaximizeSet", "numberScreensChanged", "currentDesktopChanged", "currentActivityChanged"].forEach(function (key) { isolated[key] = workspace[key]; });
isolated.desktopName = function (n) { return workspace.desktopName(n); };
isolated.clientArea = function (kind, output, desktop) { return workspace.clientArea(kind, output, desktop); };
isolated.sendClientToScreen = function (w, screen) { if (!ours(w)) { throw new Error("Non-test client"); } workspace.sendClientToScreen(w, screen); };
function send(method, value) { callDBus("org.krect.WorkspaceValidation", "/KRect", "org.krect.WorkspaceValidation", method, value); }
var appCommand;
module.exports.start({ workspace: isolated, KWin: KWin,
    readConfig: function (key, fallback) { return key === "SnapBar" || key === "SnapAssist" ? false : fallback; },
    createTimer: function () { return new QTimer(); },
    registerShortcut: function (name, text, key, fn) { if (name === "KRect-app-command") { appCommand = fn; } },
    callDBus: function (service, path, iface, method, raw) { send(method, raw); },
    log: function (message) { send("TestLog", message); }
});
var poll = new QTimer(); poll.interval = 40;
poll.timeout.connect(function () {
    callDBus("org.krect.WorkspaceValidation", "/KRect", "org.krect.WorkspaceValidation", "TestTake", function (raw) {
        var c = JSON.parse(raw); if (!c.action) { return; }
        if (c.action === "engine") { appCommand(); return; }
        var result = { token: c.token };
        try {
            if (c.action === "setup") {
                c.windows.forEach(function (item) {
                    var w = clients().filter(function (candidate) { return Number(candidate.windowId) === item.xid; })[0];
                    if (!w) { throw new Error("Test window missing"); }
                    w.minimized = false; w.setMaximize(false, false); w.desktop = item.desktop;
                    workspace.sendClientToScreen(w, item.screen); w.frameGeometry = item.geometry;
                    w.setMaximize(Boolean(item.mode & 1), Boolean(item.mode & 2)); w.minimized = item.minimized;
                });
            }
            result.desktop = workspace.currentDesktop;
            result.active = String(workspace.activeClient && workspace.activeClient.internalId);
            result.othersUnchanged = originalOthers === JSON.stringify(otherFrames());
            result.windows = clients().map(function (w) { return { xid: Number(w.windowId), id: String(w.internalId),
                geometry: frame(w), desktop: w.desktop, screen: w.screen, minimized: Boolean(w.minimized) }; });
            result.screens = [];
            for (var i = 0; i < workspace.numScreens; i++) {
                result.screens.push(module.exports.rect(workspace.clientArea(KWin.MaximizeArea, i, workspace.currentDesktop)));
            }
        } catch (error) { result.error = String(error); }
        send("TestUpdate", JSON.stringify(result));
    });
}); poll.start();
'''


class Bridge(DesktopBridge):
    def __init__(self):
        super().__init__()
        self.queue, self.replies, self.logs = [], {}, []
        self.wake = False

    @Slot(result=str)
    def TestTake(self):
        if self.queue:
            return json.dumps(self.queue.pop(0))
        if self.wake:
            self.wake = False
            return '{"action":"engine"}'
        return "{}"

    @Slot(str)
    def TestUpdate(self, raw):
        result = json.loads(raw)
        self.replies[result["token"]] = result

    @Slot(str)
    def TestLog(self, message):
        self.logs.append(message)


class TestBackend(Backend):
    """Use production command/reply handling, replacing only engine transport."""
    def __init__(self, bridge):
        C.QObject.__init__(self)
        self.bridge, self.status, self.enabled = bridge, {}, True
        self.pending = self.pending_kind = None
        self.timeout = C.QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(5000)
        self.timeout.timeout.connect(self.command_timeout)
        bridge.updated.connect(self.receive)

    def invoke(self, action):
        assert action == "app-command"
        self.bridge.wake = True


def main():
    if os.environ.get("XDG_SESSION_TYPE") != "x11" or Backend.plasma_major() != 5:
        raise SystemExit("This opt-in live harness requires Plasma 5/X11.")
    bus = dbus.SessionBus()
    if bus.call_blocking("org.freedesktop.ScreenSaver", "/ScreenSaver", "org.freedesktop.ScreenSaver", "GetActive", "", []):
        raise SystemExit("Unlock KDE before running native workspace checks.")
    app = W.QApplication(["krect-workspace-validation"])
    app.setQuitOnLastWindowClosed(False)
    windows = []
    for n in range(4):
        w = W.QLabel(f"Temporary workspace validation window {n+1}")
        w.setWindowTitle(f"KRect Workspace Validation {n+1}")
        w.setAttribute(C.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        w.resize(640, 400)
        windows.append(w)
    ids = [int(w.winId()) for w in windows]
    bridge = Bridge()
    backend = TestBackend(bridge)
    qtbus = D.QDBusConnection.sessionBus()
    assert qtbus.registerService(SERVICE), "Another workspace validation is running"
    assert qtbus.registerObject("/KRect", SERVICE, bridge, D.QDBusConnection.RegisterOption.ExportAllSlots)
    scripting = dbus.Interface(bus.get_object("org.kde.KWin", "/Scripting"), "org.kde.kwin.Scripting")
    assert not scripting.isScriptLoaded(SCRIPT), "Inspect the existing validation script before retrying"
    installed_loaded = bool(scripting.isScriptLoaded("krect"))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "engine.js"
    path.write_text("var module = { exports: {} };\n" + (ROOT / "src/main.js").read_text() + WRAPPER.replace("__IDS__", json.dumps(ids)))
    subprocess.run(["node", "--check", str(path)], check=True)

    def wait_for(condition, description, seconds=8):
        deadline = time.monotonic() + seconds
        while not condition():
            if time.monotonic() >= deadline:
                raise AssertionError(f"Timeout: {description}; engine logs: {bridge.logs}")
            app.processEvents()
            time.sleep(.01)

    def settle(seconds=.4):
        end = time.monotonic() + seconds
        wait_for(lambda: time.monotonic() >= end, "settling")

    def control(action="read", **args):
        token = uuid.uuid4().hex
        bridge.queue.append(dict(action=action, token=token, **args))
        wait_for(lambda: token in bridge.replies, action)
        result = bridge.replies.pop(token)
        assert "error" not in result, result
        return result

    def actual():
        state = control()
        assert state["othersUnchanged"], "A non-test window changed during validation"
        return state

    def comparable(state):
        return sorted(state["windows"], key=lambda row: row["xid"])

    report = dict(passed=False, scenarios=[], logs=bridge.logs)
    loaded = False
    manager = None
    try:
        script_id = int(bus.call_blocking("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", "loadScript", "ss", [str(path), SCRIPT]))
        assert script_id >= 0
        loaded = True
        dbus.Interface(bus.get_object("org.kde.KWin", f"/{script_id}"), "org.kde.kwin.Script").run()
        for w in windows:
            w.show()
        settle(.6)
        backend.invoke("app-command")
        wait_for(lambda: backend.status.get("workspacePresets") == 1, "engine handshake")
        assert len(backend.status["desktops"]) >= 4, "Needs four existing desktops"
        initial = actual()
        assert len(initial["screens"]) >= 2, "Needs two connected monitors"
        setup = []
        for n, xid in enumerate(ids):
            screen = n % len(initial["screens"])
            area = initial["screens"][screen]
            setup.append(dict(xid=xid, desktop=n+1, screen=screen,
                              geometry=dict(x=area["x"]+100+n*30, y=area["y"]+100+n*40, width=700+n*40, height=450+n*30),
                              mode=3 if n == 1 else 0, minimized=n == 2))
        control("setup", windows=setup)
        settle(.6)
        saved = actual()
        report["saved"] = saved
        with tempfile.TemporaryDirectory(prefix="krect-workspace-validation-") as temporary:
            store_path = Path(temporary) / "workspaces.json"
            manager = WorkspaceController(backend, store_path)
            manager.startup_scheduled = True
            manager.capture()
            wait_for(lambda: not manager.busy, "capture")
            assert sum(len(p["windows"]) for p in manager.store.profiles) == 4, manager.message
            assert [p["windows"][0]["mode"] for p in manager.store.profiles] == [0, 3, 0, 0], manager.store.profiles
            assert store_path.stat().st_mode & 0o777 == 0o600
            manager.store = PresetStore(store_path)

            def perturb():
                changed = deepcopy(setup)
                for n, row in enumerate(changed):
                    row.update(desktop=4-n, screen=(row["screen"]+1) % len(initial["screens"]), mode=0, minimized=False)
                    area = initial["screens"][row["screen"]]
                    row["geometry"] = dict(x=area["x"]+200, y=area["y"]+300, width=600, height=380)
                control("setup", windows=changed)
                settle()
                state = actual()
                assert comparable(state) != comparable(saved), "Perturbation did not move test windows"
                return state

            def check_restored(label, before):
                wait_for(lambda: not manager.busy and not backend.pending, label)
                settle()
                after = actual()
                report["scenarios"].append(dict(name=label, message=manager.message,
                                                results=manager.results, before=before, after=after))
                assert len(manager.results) == 4 and set(manager.results.values()) == {"restored"}, report["scenarios"][-1]
                assert comparable(after) == comparable(saved), report["scenarios"][-1]
                assert after["desktop"] == before["desktop"] and after["active"] == before["active"], "Restore changed desktop/focus"
                props = subprocess.check_output(["xprop", "-id", str(ids[1]), "_NET_WM_STATE"], text=True)
                assert "_NET_WM_STATE_MAXIMIZED_HORZ" in props and "_NET_WM_STATE_MAXIMIZED_VERT" in props, props

            before = perturb()
            manager.restore([p["id"] for p in manager.store.profiles])
            check_restored("manual restore across D1-D4 and both monitors", before)

            before = perturb()
            manager.startup_scheduled = False
            manager.observe(backend.status)
            wait_for(lambda: manager.busy, "scheduled startup restoration")
            check_restored("automatic startup restore from persisted presets", before)

            # A fresh engine session forces app/title matching instead of live IDs.
            for p in manager.store.profiles:
                p["session"] = "previous-engine-session"
            manager.store.write(manager.store.profiles)
            before = perturb()
            manager.restore([p["id"] for p in manager.store.profiles])
            check_restored("previous-session app/title matching", before)
        report["passed"] = True
    finally:
        if manager:
            manager.timer.stop()
        if loaded:
            scripting.unloadScript(SCRIPT)
        for w in windows:
            w.close()
        settle(.2)
        report["cleanup"] = dict(testScriptUnloaded=not bool(scripting.isScriptLoaded(SCRIPT)),
                                 installedScriptUnchanged=bool(scripting.isScriptLoaded("krect")) == installed_loaded,
                                 testWindowsClosed=all(not w.isVisible() for w in windows))
        (EVIDENCE / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        assert all(report["cleanup"].values()), report["cleanup"]
    print(json.dumps(dict(passed=report["passed"], scenarios=[s["name"] for s in report["scenarios"]], cleanup=report["cleanup"])))


if __name__ == "__main__":
    main()
