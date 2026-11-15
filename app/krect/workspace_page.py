"""Desktop-specific workspace snapshots in the native settings window."""
from .model import tr
from .qt import QtCore as C, QtWidgets as W


def label(text):
    widget = W.QLabel(text)
    widget.setTextFormat(C.Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    return widget


class WorkspacePage(W.QWidget):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.manager = backend.workspaces
        self.signature = None
        self.desktop_signature = None
        box = W.QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 12)
        box.setSpacing(10)
        box.addWidget(label(tr("Save the windows on each virtual desktop as a workspace. Restore them together when KRect starts.",
                               "가상 데스크톱마다 열린 창을 작업 공간으로 저장하고, KRect 시작 시 함께 복원하세요.")))
        form = W.QFormLayout()
        self.desktops = W.QComboBox()
        self.desktops.setAccessibleName(tr("Virtual desktop", "가상 데스크톱"))
        form.addRow(tr("Desktop", "데스크톱"), self.desktops)
        self.name = W.QLineEdit()
        self.name.setMaxLength(100)
        self.name.setPlaceholderText(tr("Development, study, trading, work…", "개인 개발, 학습, 트레이딩, 회사 일…"))
        form.addRow(tr("Workspace name", "작업 공간 이름"), self.name)
        box.addLayout(form)
        self.auto = W.QCheckBox(tr("Restore this workspace when KRect starts", "KRect 시작 시 이 작업 공간 복원"))
        self.launch = W.QCheckBox(tr("Launch missing applications", "실행되지 않은 프로그램도 열기"))
        box.addWidget(self.auto)
        box.addWidget(self.launch)
        box.addWidget(label(tr("Apps restore their own documents and browser tabs. Indistinguishable windows are left in place. Enable login startup in Preferences to restore after login.",
                               "문서와 브라우저 탭은 각 앱의 세션 복원 기능을 따라요. 구분이 어려운 창은 옮기지 않아요. 로그인 시 복원하려면 환경설정에서 로그인 시 실행도 켜세요.")))
        self.summary = label("")
        box.addWidget(self.summary)
        self.windows = W.QListWidget()
        self.windows.setAccessibleName(tr("Saved windows", "저장된 창"))
        self.windows.setMinimumHeight(150)
        self.windows.setTextElideMode(C.Qt.TextElideMode.ElideRight)
        box.addWidget(self.windows, 1)
        grid = W.QGridLayout()
        actions = [
            ("capture", tr("Save desktop layout", "이 데스크톱 배치 저장"), self.capture),
            ("capture_all", tr("Save all desktop layouts", "모든 데스크톱 배치 저장"), lambda: self.manager.capture()),
            ("restore", tr("Restore workspace", "이 작업 공간 복원"), self.restore),
            ("restore_all", tr("Restore all workspaces", "모든 작업 공간 복원"), lambda: self.manager.restore([p["id"] for p in self.profiles()])),
            ("save", tr("Save name and options", "이름·옵션 저장"), self.save_options),
            ("remove", tr("Delete saved workspace", "저장한 작업 공간 삭제"), self.remove),
        ]
        self.buttons = {}
        for index, (key, title, callback) in enumerate(actions):
            button = W.QPushButton(title)
            button.clicked.connect(lambda checked=False, fn=callback: self.perform(fn))
            grid.addWidget(button, index // 2, index % 2)
            self.buttons[key] = button
        box.addLayout(grid)
        self.stop = W.QPushButton(tr("Stop restoration", "복원 중단"))
        self.stop.clicked.connect(self.manager.cancel)
        box.addWidget(self.stop)
        self.status = label("")
        self.status.setAccessibleName(tr("Workspace status", "작업 공간 상태"))
        box.addWidget(self.status)
        self.desktops.currentIndexChanged.connect(self.selection_changed)
        self.manager.changed.connect(self.refresh)
        self.refresh()

    def profiles(self):
        activity = self.backend.status.get("activity", "")
        return [p for p in self.manager.store.profiles if p["activity"] == activity]

    def selected(self):
        return next((p for p in self.profiles() if p["desktop"]["id"] == self.desktops.currentData()), None)

    def selection_changed(self):
        self.signature = None
        self.refresh()

    def refresh(self):
        desktops = list(self.backend.status.get("desktops", []))
        for p in self.profiles():
            if not any(d["id"] == p["desktop"]["id"] for d in desktops):
                desktops.append(dict(p["desktop"], missing=True))
        ds = [(d["id"], d["name"], d.get("missing", False)) for d in desktops]
        if ds != self.desktop_signature:
            chosen = self.desktops.currentData() or self.backend.status.get("currentDesktop")
            self.desktops.blockSignals(True)
            self.desktops.clear()
            for d in desktops:
                suffix = tr(" (unavailable)", " (사용 불가)") if d.get("missing") else ""
                self.desktops.addItem(f"D{d['number']} · {d['name']}{suffix}", d["id"])
            index = self.desktops.findData(chosen)
            self.desktops.setCurrentIndex(max(0, index))
            self.desktops.blockSignals(False)
            self.desktop_signature = ds
        p = self.selected()
        signature = (self.desktops.currentData(), str(p), str(self.manager.results))
        if signature != self.signature:
            d = next((d for d in desktops if d["id"] == self.desktops.currentData()), {})
            self.name.setText(p["name"] if p else d.get("name", ""))
            self.auto.setChecked(p["restoreOnStart"] if p else True)
            self.launch.setChecked(p["launchMissing"] if p else False)
            self.windows.clear()
            statuses = {"restored": tr("Restored", "복원 완료"), "missing": tr("Waiting for window", "창 대기 중"),
                        "ambiguous": tr("Cannot identify window", "창을 구분할 수 없음"),
                        "desktop-or-activity-missing": tr("Desktop/activity unavailable", "데스크톱·활동 없음"),
                        "changed": tr("Window changed; skipped", "창 상태 변경으로 건너뜀"),
                        "size-limit": tr("Window size constraint", "창 크기 제한"),
                        "failed": tr("Placement refused", "배치 실패"), "cancelled": tr("Cancelled", "중단됨")}
            for index, w in enumerate(p["windows"] if p else []):
                g = w["geometry"]
                result = self.manager.results.get(f"{p['id']}:{index}")
                suffix = " · " + statuses.get(result, tr("Not restored", "미복원")) if result else ""
                item = W.QListWidgetItem(f"{w['caption'] or w['application'] or w['resourceClass']}\n{w['application'] or w['resourceClass']} · {round(g['width'])} × {round(g['height'])} · {w['output']}{suffix}")
                item.setToolTip(item.text())
                self.windows.addItem(item)
            saved_at = C.QDateTime.fromString(p["updated"], C.Qt.DateFormat.ISODate).toLocalTime().toString("yyyy-MM-dd HH:mm") if p else ""
            self.summary.setText(tr("{n} saved windows · {when}", "저장된 창 {n}개 · {when}").format(n=len(p["windows"]), when=saved_at) if p else
                                 tr("No saved layout for this desktop yet.", "아직 이 데스크톱에 저장한 배치가 없어요."))
            self.signature = signature
        available = self.manager.ready() and not self.manager.busy and not self.backend.pending and not self.manager.store.error
        present = any(d["id"] == self.desktops.currentData() for d in self.backend.status.get("desktops", []))
        for key, button in self.buttons.items():
            enabled = available
            if key in ("save", "remove", "restore"):
                enabled = enabled and p is not None
            if key == "capture":
                enabled = enabled and present
            if key == "restore_all":
                enabled = enabled and bool(self.profiles())
            button.setEnabled(bool(enabled))
        self.stop.setVisible(self.manager.busy)
        self.desktops.setEnabled(not self.manager.busy)
        self.name.setEnabled(not self.manager.busy)
        self.auto.setEnabled(not self.manager.busy)
        self.launch.setEnabled(not self.manager.busy)
        self.status.setText(self.manager.message)

    def perform(self, callback):
        try:
            callback()
        except (ValueError, RuntimeError, OSError, StopIteration) as error:
            self.backend.message.emit(str(error), True)

    def capture(self):
        self.manager.capture(self.desktops.currentData(), self.name.text(), (self.auto.isChecked(), self.launch.isChecked()))

    def restore(self):
        if self.selected():
            self.manager.restore([self.selected()["id"]])

    def save_options(self):
        if self.selected():
            self.manager.update(self.selected()["id"], self.name.text(), self.auto.isChecked(), self.launch.isChecked())

    def remove(self):
        p = self.selected()
        if p and W.QMessageBox.question(self, tr("Delete workspace", "작업 공간 삭제"),
                                       tr("Delete the saved layout for {name}? Open windows stay in place.", "{name}의 저장된 배치를 삭제할까요? 열린 창은 그대로 유지해요.").format(name=p["name"])) == W.QMessageBox.StandardButton.Yes:
            self.manager.remove(p["id"])
