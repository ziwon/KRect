"""Capture, startup restoration and bounded waiting for application windows."""
from copy import deepcopy
from pathlib import Path
import re
import shutil
import subprocess
import time

from .model import tr
from .qt import QtCore as C, Signal
from .workspaces import PresetStore, plan_restore, validate_snapshot


def launch_application(application):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", application):
        raise ValueError(tr("This app has no launchable desktop entry.", "자동 실행 가능한 앱 항목이 없어요."))
    filename = application if application.endswith(".desktop") else application + ".desktop"
    path = C.QStandardPaths.locate(C.QStandardPaths.StandardLocation.ApplicationsLocation, filename)
    if not path:
        raise ValueError(tr("The saved application is not installed.", "저장한 프로그램이 설치되어 있지 않아요."))
    entry = C.QSettings(path, C.QSettings.Format.IniFormat)
    if entry.value("Desktop Entry/Type") != "Application" or str(entry.value("Desktop Entry/Hidden", "false")).lower() == "true":
        raise ValueError(tr("This desktop entry cannot be launched.", "이 앱 항목은 실행할 수 없어요."))
    gio = shutil.which("gio")
    if not gio:
        raise RuntimeError(tr("Install libglib2.0-bin to enable app launching.", "앱 자동 실행에는 libglib2.0-bin 패키지가 필요해요."))
    # GIO handles desktop-entry quoting, field codes and D-Bus activation.
    # Captions and process command lines are never executed.
    return subprocess.Popen([gio, "launch", str(Path(path))], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)


class WorkspaceController(C.QObject):
    changed = Signal()

    def __init__(self, backend, path, parent=None, launcher=launch_application, clock=time.monotonic):
        super().__init__(parent)
        self.backend = backend
        self.store = PresetStore(path)
        self.launcher, self.clock = launcher, clock
        self.operation = None
        self.startup_scheduled = False
        self.message = self.store.error or ""
        self.results = {}
        self.timer = C.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.poll)
        backend.workspace_result.connect(self.receive)
        backend.changed.connect(self.observe)

    @property
    def busy(self):
        return self.operation is not None

    def ready(self):
        return self.backend.enabled and self.backend.status.get("workspacePresets") == 1

    def observe(self, status):
        if self.busy and not self.backend.enabled:
            self.operation = None
            self.timer.stop()
        if self.ready() and not self.startup_scheduled:
            self.startup_scheduled = True
            C.QTimer.singleShot(1500, self.startup)
        self.changed.emit()

    def startup(self):
        if not self.ready() or self.busy or self.backend.pending or self.store.error:
            return
        ids = [p["id"] for p in self.store.profiles if p["restoreOnStart"] and
               p["activity"] == self.backend.status.get("activity", "")]
        if ids:
            self.restore(ids)

    def require_ready(self):
        if not self.ready() or self.backend.pending or self.busy:
            raise RuntimeError(tr("Enable KRect and wait for the current operation to finish.", "KRect를 켜고 진행 중인 작업이 끝날 때까지 기다려 주세요."))
        if self.store.error:
            raise ValueError(self.store.error)

    def capture(self, desktop_id=None, name=None, preferences=None):
        self.require_ready()
        self.operation = dict(kind="capture", desktop=desktop_id, name=name, preferences=preferences)
        self.results = {}
        self.message = tr("Reading open windows…", "열린 창을 읽고 있어요…")
        self.backend.submit(dict(kind="workspace-snapshot"))
        self.changed.emit()

    def restore(self, ids):
        self.require_ready()
        profiles = deepcopy([p for p in self.store.profiles if p["id"] in ids])
        if not profiles:
            return
        self.results = {}
        self.operation = dict(kind="restore", profiles=profiles, deadline=self.clock()+30,
                              done=set(), used=set(), launched=set(), restored=0, skipped=0,
                              launch_errors=0, processes=[], waiting=[], phase="snapshot")
        self.message = tr("Restoring workspaces; waiting up to 30 seconds for windows…", "작업 공간 복원 중이에요. 창이 열리기를 최대 30초 기다려요…")
        self.poll()
        self.changed.emit()

    def cancel(self):
        self.operation = None
        self.timer.stop()
        self.backend.cancel_command()
        if self.ready():
            self.backend.submit(dict(kind="workspace-cancel"))
        self.message = tr("Restoration stopped. Completed placements are kept.", "복원을 중단했어요. 이미 복원한 배치는 유지해요.")
        self.changed.emit()

    def poll(self):
        op = self.operation
        if not op or op["kind"] != "restore":
            return
        remaining = []
        for process in op["processes"]:
            code = process.poll()
            if code is None:
                remaining.append(process)
            else:
                op["launch_errors"] += code != 0
        op["processes"] = remaining
        if self.clock() >= op["deadline"] or not self.ready():
            self.finish()
        elif self.backend.pending:
            self.timer.start()
        else:
            op["phase"] = "snapshot"
            self.backend.submit(dict(kind="workspace-snapshot"))

    def finish(self):
        op = self.operation
        if not op:
            return
        missing = sum(len(p["windows"]) for p in op["profiles"]) - op["restored"]
        self.message = tr("Restored {n} windows · {m} not restored · {e} launch errors.",
                          "창 {n}개 복원 · {m}개 미복원 · 앱 실행 오류 {e}개.").format(
                              n=op["restored"], m=missing, e=op["launch_errors"])
        self.operation = None
        self.timer.stop()
        self.changed.emit()
        self.backend.message.emit(self.message, bool(missing))

    def receive(self, result):
        op = self.operation
        if not op:
            return
        try:
            if not result.get("success"):
                raise RuntimeError(tr("KWin did not complete the workspace request.", "KWin이 작업 공간 요청을 완료하지 못했어요."))
            if op["kind"] == "capture":
                snapshot = validate_snapshot(result.get("snapshot"))
                if snapshot.get("truncated"):
                    raise ValueError(tr("Too many windows to save (maximum 256).", "저장 가능한 창 수(256개)를 넘었어요."))
                self.store.save(snapshot, op["desktop"], op["name"], op["preferences"])
                self.operation = None
                self.message = tr("Workspace snapshot saved locally.", "현재 작업 공간을 이 컴퓨터에 저장했어요.")
                self.changed.emit()
                return
            if op["phase"] == "apply":
                for row in result.get("rows", []):
                    op["done"].add(row["key"])
                    op["used"].add(row["id"])
                    op["restored"] += row["status"] == "restored"
                    self.results[row["key"]] = row["status"]
                self.changed.emit()
                if op["waiting"]:
                    self.timer.start()
                else:
                    self.finish()
                return
            snapshot = validate_snapshot(result.get("snapshot"))
            placements, waiting, skipped = plan_restore(op["profiles"], snapshot, op["done"], op["used"], self.store.profiles)
            op["done"].update(row["key"] for row in skipped)
            op["waiting"] = waiting
            self.results.update({row["key"]: row["reason"] for row in waiting + skipped})
            running = {a.removesuffix(".desktop") for a in snapshot.get("runningApplications", [])}
            for row in waiting:
                if not row["launch"] or not row["application"] or any(alias in running for alias in row["aliases"]) or row["identity"] in op["launched"]:
                    continue
                op["launched"].add(row["identity"])
                try:
                    process = self.launcher(row["application"])
                    if process is not None:
                        op["processes"].append(process)
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                    op["launch_errors"] += 1
            if placements:
                op["phase"] = "apply"
                self.backend.submit(dict(kind="workspace-restore", session=snapshot["session"], activity=snapshot["activity"], placements=placements))
            elif waiting:
                self.timer.start()
            else:
                self.finish()
            self.changed.emit()
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as error:
            self.operation = None
            self.timer.stop()
            self.message = str(error)
            self.backend.message.emit(self.message, True)
            self.changed.emit()

    def update(self, profile_id, name, restore_on_start, launch_missing):
        if self.busy:
            return
        self.store.update(profile_id, name, restore_on_start, launch_missing)
        self.changed.emit()

    def remove(self, profile_id):
        if not self.busy:
            self.store.remove(profile_id)
            self.changed.emit()
