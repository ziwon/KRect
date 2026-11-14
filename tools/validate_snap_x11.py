#!/usr/bin/python3
"""Opt-in live drag checks on a disposable client in the current KDE/X11 session.

Uses an isolated KWin script/service, does not register shortcuts or change config,
and restores the pointer/focus on exit. Run with the distribution Python.
"""
import ctypes as F
import ctypes.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from krect.backend import DesktopBridge
from krect.qt import QtCore as C, QtWidgets as W, QtDBus as D, Slot
from krect.snap import SnapBar
import dbus

SERVICE = "org.krect.SnapValidation"
SCRIPT = "krect-snap-validation"
EVIDENCE = ROOT / "dist/snap-validation"


class Bridge(DesktopBridge):
    def __init__(self):
        super().__init__()
        self.queue, self.replies, self.logs, self.models = [], {}, [], []
        self.snap_updated.connect(self.models.append)

    @Slot(result=str)
    def TestTake(self):
        return json.dumps(self.queue.pop(0) if self.queue else {})

    @Slot(str)
    def TestUpdate(self, raw):
        result = json.loads(raw)
        self.replies[result["token"]] = result

    @Slot(str)
    def TestLog(self, message):
        self.logs.append(message)


def main():
    if os.environ.get("XDG_SESSION_TYPE") != "x11":
        raise SystemExit("This live input harness is for KDE/X11 only.")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    app = W.QApplication(["krect"])
    app.setDesktopFileName("org.krect.KRect")
    app.setQuitOnLastWindowClosed(False)
    bridge, bar = Bridge(), SnapBar()
    bridge.snap_updated.connect(bar.receive)
    qtbus = D.QDBusConnection.sessionBus()
    assert qtbus.registerService(SERVICE), "Another validation is running"
    assert qtbus.registerObject("/KRect", SERVICE, bridge, D.QDBusConnection.RegisterOption.ExportAllSlots)
    bus = dbus.SessionBus()
    scripting = dbus.Interface(bus.get_object("org.kde.KWin", "/Scripting"), "org.kde.kwin.Scripting")
    if scripting.isScriptLoaded(SCRIPT):
        raise SystemExit("A previous validation script is still loaded; inspect it before retrying.")
    source = "var module = { exports: {} };\n" + (ROOT / "src/main.js").read_text()
    source += '''
var previous = workspace.activeClient;
function send(method, value) { callDBus("org.krect.SnapValidation", "/KRect", "org.krect.SnapValidation", method, value); }
var controller = module.exports.start({ workspace: workspace, KWin: KWin,
    readConfig: function (key, fallback) { return key === "Gap" ? 8 : fallback; },
    createTimer: function () { return new QTimer(); }, registerShortcut: function () {},
    callDBus: function (service, path, iface, method, raw) { send(method, raw); },
    log: function (message) { send("TestLog", message); }
});
function geometry(w) { return module.exports.rect(w.frameGeometry); }
function target() { return workspace.clientList().filter(function (w) { return String(w.caption) === "KRect Snap Validation Client"; })[0]; }
var poll = new QTimer(); poll.interval = 40;
poll.timeout.connect(function () {
    callDBus("org.krect.SnapValidation", "/KRect", "org.krect.SnapValidation", "TestTake", function (raw) {
        var c = JSON.parse(raw); if (!c.token) { return; }
        var w = target(), result = { token: c.token };
        try {
            if (c.action === "focus-back") { if (previous && !previous.deleted) { workspace.activeClient = previous; } }
            else {
                if (!w) { throw new Error("Validation client not found"); }
                if (c.action === "setup") { w.setMaximize(false, false); w.frameGeometry = c.geometry; workspace.activeClient = w; }
                if (c.action === "restore") { result.restored = controller.execute("restore", w); }
                if (c.action === "maximize") { controller.execute("maximize", w); }
                result.geometry = geometry(w); result.move = w.move;
                result.active = workspace.activeClient === w; result.caption = String(workspace.activeClient && workspace.activeClient.caption); result.noBorder = w.noBorder; result.clientGeometry = module.exports.rect(w.clientGeometry || w.frameGeometry);
                result.maximized = { horizontal: w.maximizedHorizontally, vertical: w.maximizedVertically };
                result.area = module.exports.rect(workspace.clientArea(KWin.MaximizeArea, w));
                result.screens = [];
                for (var i = 0; i < workspace.numScreens; i++) {
                    result.screens.push(module.exports.rect(workspace.clientArea(KWin.MaximizeArea, i, workspace.currentDesktop)));
                }
                var overlays = workspace.clientList().filter(function (x) { return String(x.caption) === "KRect Snap Bar"; });
                result.overlays = overlays.map(function (x) { return { geometry: geometry(x), app: String(x.resourceClass), above: x.keepAbove }; });
            }
        } catch (error) { result.error = String(error); }
        send("TestUpdate", JSON.stringify(result));
    });
}); poll.start();
'''
    path = EVIDENCE / "engine.js"
    path.write_text(source)
    x = F.CDLL(ctypes.util.find_library("X11"))
    xt = F.CDLL(ctypes.util.find_library("Xtst"))
    x.XOpenDisplay.restype = F.c_void_p
    x.XOpenDisplay.argtypes = [F.c_char_p]
    display = x.XOpenDisplay(None)
    assert display
    for name, args in [("XFlush", [F.c_void_p]), ("XCloseDisplay", [F.c_void_p]),
                       ("XDefaultRootWindow", [F.c_void_p]), ("XKeysymToKeycode", [F.c_void_p, F.c_ulong])]:
        getattr(x, name).argtypes = args
    x.XDefaultRootWindow.restype = F.c_ulong
    x.XQueryPointer.argtypes = [F.c_void_p, F.c_ulong, F.POINTER(F.c_ulong), F.POINTER(F.c_ulong)] + [F.POINTER(F.c_int)] * 4 + [F.POINTER(F.c_uint)]
    xt.XTestFakeMotionEvent.argtypes = [F.c_void_p, F.c_int, F.c_int, F.c_int, F.c_ulong]
    xt.XTestFakeButtonEvent.argtypes = [F.c_void_p, F.c_uint, F.c_int, F.c_ulong]
    xt.XTestFakeKeyEvent.argtypes = [F.c_void_p, F.c_uint, F.c_int, F.c_ulong]
    root_return, child_return = F.c_ulong(), F.c_ulong()
    pointer_x, pointer_y, win_x, win_y, mask = F.c_int(), F.c_int(), F.c_int(), F.c_int(), F.c_uint()
    x.XQueryPointer(display, x.XDefaultRootWindow(display), F.byref(root_return), F.byref(child_return),
                    F.byref(pointer_x), F.byref(pointer_y), F.byref(win_x), F.byref(win_y), F.byref(mask))
    saved_pointer = (pointer_x.value, pointer_y.value)

    def wait(seconds=.2):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(.01)

    sequence = 0

    def command(action="query", **kwargs):
        nonlocal sequence
        sequence += 1
        bridge.queue.append(dict(token=sequence, action=action, **kwargs))
        end = time.monotonic() + 3
        while sequence not in bridge.replies and time.monotonic() < end:
            wait(.02)
        assert sequence in bridge.replies, f"KWin bridge timeout: {bridge.logs}"
        result = bridge.replies.pop(sequence)
        assert "error" not in result, result
        return result

    def move(px, py):
        xt.XTestFakeMotionEvent(display, -1, round(px), round(py), 0); x.XFlush(display); wait()

    def button(pressed):
        xt.XTestFakeButtonEvent(display, 1, int(pressed), 0); x.XFlush(display); wait()

    def escape():
        code = x.XKeysymToKeycode(display, 0xff1b)
        xt.XTestFakeKeyEvent(display, code, 1, 0); xt.XTestFakeKeyEvent(display, code, 0, 0)
        x.XFlush(display); wait()

    initial = None
    landscape_index = None

    def begin(action="left", screen=None, maximized=False):
        command("setup", geometry=initial); wait(.5)
        before = command()
        assert before["active"] and before["geometry"] == initial, before
        if maximized:
            command("maximize"); wait(.4)
            before = command()
        g = before["geometry"]
        move(g["x"] + g["width"] / 2, g["y"] + 16)
        button(True)
        move(g["x"] + g["width"] / 2 + 40, g["y"] - 25)
        assert command()["move"], {"reason": "Title bar gesture did not start a real KWin move", "before": before, "after": command()}
        a = before["screens"][landscape_index if screen is None else screen]
        move(a["x"] + a["width"] / 2, a["y"] + 10); wait(.4)
        state = command()
        assert bar.isVisible(), {"reason": "Snap bar did not appear", "state": state, "models": bridge.models[-2:], "logs": bridge.logs}
        model = bridge.models[-1]
        assert state["active"], "Overlay stole focus"
        assert state["overlays"] and state["overlays"][0]["geometry"] == model["geometry"], state
        cell = next(c["rect"] for c in model["cells"] if c["action"] == action)
        g = model["geometry"]
        move(g["x"] + cell["x"] + cell["width"] / 2, g["y"] + cell["y"] + cell["height"] / 2)
        assert bridge.models[-1]["selected"] >= 0, {"state": command(), "models": bridge.models[-2:]}
        return before, a

    client = None
    loaded = False
    checks = []
    try:
        script_id = bus.call_blocking("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", "loadScript", "ss", [str(path), SCRIPT])
        assert script_id >= 0
        loaded = True
        dbus.Interface(bus.get_object("org.kde.KWin", f"/{script_id}"), "org.kde.kwin.Script").run()
        client = subprocess.Popen(["/usr/bin/python3", "-c", '''
from PyQt5 import QtWidgets as W, QtCore as C
app=W.QApplication(["krect-snap-validation-client"])
w=W.QLabel("KRect drag validation — temporary window")
w.setWindowTitle("KRect Snap Validation Client")
w.resize(700,450);w.show();C.QTimer.singleShot(90000,app.quit);app.exec_()
'''], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait(.8)
        screens = command()["screens"]
        landscape_index = next((i for i, a in enumerate(screens) if a["width"] > a["height"]), None)
        portrait_index = next((i for i, a in enumerate(screens) if a["height"] > a["width"]), None)
        assert landscape_index is not None and portrait_index is not None, "This check needs a landscape and portrait display"
        area = screens[landscape_index]
        initial = dict(x=area["x"]+round(area["width"]/3), y=area["y"]+round(area["height"]/3),
                       width=min(900, area["width"]//2), height=min(600, area["height"]//2))
        before, area = begin()
        bar.grab().save(str(EVIDENCE / "bar-landscape.png"))
        button(False); wait(.3)
        after = command()
        expected = dict(x=area["x"]+8, y=area["y"]+8, width=round(area["width"]/2)-12, height=area["height"]-16)
        assert after["geometry"] == expected, (after, expected, bridge.logs)
        assert not bar.isVisible()
        command("restore"); wait()
        assert command()["geometry"] == before["geometry"]
        checks.append("landscape drop, exact gap, focus preservation and restore")

        before, _ = begin("right")
        escape(); button(False); wait()
        assert command()["geometry"] == before["geometry"], command()
        assert not bar.isVisible()
        checks.append("Esc cancellation")

        before, _ = begin("right", maximized=True)
        escape(); button(False); wait()
        assert command()["geometry"] == before["geometry"], command()
        checks.append("Esc from a maximized window")

        begin("left")
        move(initial["x"]+initial["width"]//2, initial["y"])
        assert not bar.isVisible()
        normal = command()["geometry"]
        button(False); wait()
        assert command()["geometry"] == normal
        checks.append("leave strip and release without snapping")

        before, area = begin("center-third", screen=portrait_index)
        bar.grab().save(str(EVIDENCE / "bar-portrait.png"))
        button(False); wait(.3)
        after = command()["geometry"]
        expected = dict(x=area["x"]+8, y=round(area["y"]+area["height"]/3+4),
                        width=area["width"]-16, height=round(area["y"]+area["height"]*2/3-4)-round(area["y"]+area["height"]/3+4))
        assert after == expected, (after, expected)
        command("restore"); wait()
        assert command()["geometry"] == before["geometry"]
        checks.append("portrait monitor transfer, vertical thirds and restore")
        assert not bridge.logs, bridge.logs
        (EVIDENCE / "results.json").write_text(json.dumps(dict(checks=checks, logs=bridge.logs), indent=2)+"\n")
        print(json.dumps(dict(passed=len(checks), checks=checks), ensure_ascii=False))
    finally:
        if client:
            escape(); button(False)
        if loaded:
            try:
                command("focus-back")
            finally:
                scripting.unloadScript(SCRIPT)
        if client:
            client.terminate(); client.wait(timeout=5)
        move(*saved_pointer)
        bar.dismiss()
        x.XCloseDisplay(display)


if __name__ == "__main__":
    main()
