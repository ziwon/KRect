#!/usr/bin/python3
"""Read-only KWin snapshot probe. Does not register shortcuts or restore windows."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import dbus
from krect.backend import Backend
from krect.qt import QtCore as C, QtDBus as D, Slot, run
from krect.workspaces import validate_snapshot

SERVICE = "org.krect.WorkspaceProbe"
SCRIPT = "krect-workspace-probe"


class Receiver(C.QObject):
    snapshot = None

    @Slot(str)
    def Update(self, raw):
        result = json.loads(raw).get("result") or {}
        if result.get("snapshot"):
            self.snapshot = result["snapshot"]
            C.QCoreApplication.quit()


def main():
    app = C.QCoreApplication(["krect-workspace-probe"])
    receiver = Receiver()
    qtbus = D.QDBusConnection.sessionBus()
    assert qtbus.registerService(SERVICE), "Another workspace probe is active"
    assert qtbus.registerObject("/KRect", SERVICE, receiver, D.QDBusConnection.RegisterOption.ExportAllSlots)
    bus = dbus.SessionBus()
    scripting = dbus.Interface(bus.get_object("org.kde.KWin", "/Scripting"), "org.kde.kwin.Scripting")
    assert not scripting.isScriptLoaded(SCRIPT), "An earlier probe must be inspected first"
    source = "var module = { exports: {} };\n" + (ROOT / "src/main.js").read_text()
    source += '''
var request;
module.exports.start({ workspace: workspace, KWin: KWin,
    readConfig: function (key, fallback) { return fallback; },
    createTimer: function () { return new QTimer(); },
    registerShortcut: function (name, label, key, callback) {
        if (name === "KRect-app-command") { request = callback; }
    },
    callDBus: function (service, path, iface, method, raw) {
        if (method === "TakeCommand") { raw('{"kind":"workspace-snapshot","token":"probe"}'); }
        else if (method === "Update") {
            callDBus("org.krect.WorkspaceProbe", "/KRect", "org.krect.WorkspaceProbe", "Update", raw);
        }
    }
});
request();
'''
    path = ROOT / "dist/workspace-probe.js"
    path.parent.mkdir(exist_ok=True)
    path.write_text(source)
    script_id = int(bus.call_blocking("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting",
                                      "loadScript", "ss", [str(path), SCRIPT]))
    assert script_id >= 0, "KWin rejected the read-only probe"
    try:
        major = Backend.plasma_major()
        address = f"/{script_id}" if major == 5 else f"/Scripting/Script{script_id}"
        dbus.Interface(bus.get_object("org.kde.KWin", address), "org.kde.kwin.Script").run()
        C.QTimer.singleShot(5000, app.quit)
        run(app)
        snapshot = validate_snapshot(receiver.snapshot)
        report = dict(schema=snapshot["schema"], desktops=[dict(number=d["number"], name=d["name"],
                      windows=sum(w["desktop"] == d["id"] for w in snapshot["windows"])) for d in snapshot["desktops"]],
                      total_windows=len(snapshot["windows"]), truncated=snapshot.get("truncated", False))
        (ROOT / "dist/workspace-probe-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        scripting.unloadScript(SCRIPT)


if __name__ == "__main__":
    main()
