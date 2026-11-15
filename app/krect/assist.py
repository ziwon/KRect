"""A dismissible window chooser; KWin validates and applies every placement."""
import os
import re

from .model import tr
from .qt import QtCore as C, QtGui as G, QtWidgets as W, Signal


def application_icon(application):
    fallback = G.QIcon.fromTheme("application-x-executable")
    if re.fullmatch(r"[A-Za-z0-9_.-]+", application):
        filename = application if application.endswith(".desktop") else application + ".desktop"
        path = C.QStandardPaths.locate(C.QStandardPaths.StandardLocation.ApplicationsLocation, filename)
        if path:
            entry = C.QSettings(path, C.QSettings.Format.IniFormat)
            name = entry.value("Desktop Entry/Icon", "")
            if isinstance(name, str) and name:
                icon = G.QIcon(name) if os.path.isabs(name) else G.QIcon.fromTheme(name)
                if not icon.isNull():
                    return icon
    return G.QIcon.fromTheme(application, fallback)


class SnapAssist(W.QFrame):
    command = Signal(str, str)

    def __init__(self):
        flags = (C.Qt.WindowType.Window | C.Qt.WindowType.FramelessWindowHint |
                 C.Qt.WindowType.WindowStaysOnTopHint)
        super().__init__(None, flags)
        self.setWindowTitle("KRect Fill Space")
        self.setAccessibleName(tr("Choose a window for the other half", "다른 쪽에 놓을 창 선택"))
        self.setAttribute(C.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFrameShape(W.QFrame.Shape.StyledPanel)
        self.session = None
        self.dismissed_session = None
        self.entries = []
        box = W.QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 12)
        box.setSpacing(12)
        self.heading = W.QLabel()
        self.heading.setWordWrap(True)
        font = self.heading.font()
        font.setBold(True)
        self.heading.setFont(font)
        box.addWidget(self.heading)
        self.hint = W.QLabel()
        self.hint.setWordWrap(True)
        box.addWidget(self.hint)
        self.windows = W.QListWidget()
        self.windows.setAccessibleName(tr("Available windows", "배치할 수 있는 창"))
        self.windows.setIconSize(C.QSize(32, 32))
        self.windows.setTextElideMode(C.Qt.TextElideMode.ElideRight)
        self.windows.setHorizontalScrollBarPolicy(C.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.windows.itemClicked.connect(self.choose)
        self.windows.itemActivated.connect(self.choose)
        box.addWidget(self.windows, 1)
        self.skip_button = W.QPushButton(tr("Skip (Esc)", "건너뛰기 (Esc)"))
        self.skip_button.clicked.connect(self.skip)
        box.addWidget(self.skip_button, 0, C.Qt.AlignmentFlag.AlignRight)
        self.watchdog = C.QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.setInterval(2500)
        self.watchdog.timeout.connect(self.skip)

    def receive(self, model):
        if not model.get("visible"):
            self.dismiss()
            return
        if model["session"] == self.dismissed_session:
            return
        fresh = self.session != model["session"]
        self.session = model["session"]
        titles = {"left": tr("Choose a window for the left half", "왼쪽에 놓을 창을 선택하세요"),
                  "right": tr("Choose a window for the right half", "오른쪽에 놓을 창을 선택하세요"),
                  "top": tr("Choose a window for the top half", "위쪽에 놓을 창을 선택하세요"),
                  "bottom": tr("Choose a window for the bottom half", "아래쪽에 놓을 창을 선택하세요"),
                  "swap": tr("Choose a window to swap with", "서로 자리를 바꿀 창을 선택하세요")}
        self.heading.setText(titles[model["action"]])
        self.setAccessibleName(titles[model["action"]])
        swapping = model["action"] == "swap"
        self.hint.setText(tr("Both windows exchange position and size. Enter to swap.", "두 창의 위치와 크기를 서로 바꿔요. Enter로 교환하세요.") if swapping else
                          tr("Open windows on this display. Enter to place.", "같은 모니터의 열린 창이에요. Enter로 배치하세요."))
        self.skip_button.setText(tr("Cancel (Esc)", "취소 (Esc)") if swapping else tr("Skip (Esc)", "건너뛰기 (Esc)"))
        if fresh or self.entries != model["candidates"]:
            current = self.windows.currentItem()
            selected = current.data(C.Qt.ItemDataRole.UserRole) if current and not fresh else None
            self.windows.clear()
            self.entries = model["candidates"]
            for candidate in self.entries:
                caption = candidate["caption"] or tr("Untitled window", "제목 없는 창")
                application = candidate["application"]
                icon = application_icon(application)
                item = W.QListWidgetItem(icon, caption + ("\n" + application if application else ""))
                item.setData(C.Qt.ItemDataRole.UserRole, candidate["id"])
                item.setToolTip(caption)
                item.setSizeHint(C.QSize(0, self.fontMetrics().height() * 2 + 16))
                self.windows.addItem(item)
                if candidate["id"] == selected:
                    self.windows.setCurrentItem(item)
            if self.windows.currentRow() < 0:
                self.windows.setCurrentRow(0)
        if fresh:
            g = model["geometry"]
            self.resize(round(g["width"]), round(g["height"]))
            self.show()
            self.windows.setFocus()
            # The engine positions and activates the mapped window on both sessions.
        self.watchdog.start()

    def dismiss(self):
        self.session = None
        self.watchdog.stop()
        self.hide()

    def finish(self, target):
        if not self.session:
            return
        session = self.session
        self.dismissed_session = session
        self.dismiss()
        self.command.emit(session, target)

    def choose(self, item):
        self.finish(item.data(C.Qt.ItemDataRole.UserRole))

    def skip(self):
        self.finish("")

    def keyPressEvent(self, event):
        if event.key() == C.Qt.Key.Key_Escape:
            self.skip()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.skip()
        event.accept()

    def event(self, event):
        if event.type() == C.QEvent.Type.WindowDeactivate and getattr(self, "session", None):
            self.skip()
        return super().event(event)
