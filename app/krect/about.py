"""Native application information, using the same version as the CLI and package."""
from . import VERSION
from .model import tr
from .qt import QtCore as C, QtWidgets as W


class AboutDialog(W.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("About KRect", "KRect 정보"))
        self.setWindowIcon(parent.windowIcon())
        self.setMinimumWidth(400)
        layout = W.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        header = W.QHBoxLayout()
        header.setSpacing(16)
        logo = W.QLabel()
        logo.setPixmap(self.windowIcon().pixmap(64, 64))
        header.addWidget(logo)
        identity = W.QVBoxLayout()
        name = W.QLabel("KRect")
        font = name.font()
        font.setPointSizeF(font.pointSizeF() * 1.5)
        font.setBold(True)
        name.setFont(font)
        identity.addWidget(name)
        self.version = W.QLabel(tr("Version {version}", "버전 {version}").format(version=VERSION))
        self.version.setTextInteractionFlags(C.Qt.TextInteractionFlag.TextSelectableByMouse |
                                             C.Qt.TextInteractionFlag.TextSelectableByKeyboard)
        identity.addWidget(self.version)
        header.addLayout(identity, 1)
        layout.addLayout(header)

        description = W.QLabel(tr("Window management for KDE Plasma.", "KDE Plasma를 위한 창 배치 도구."))
        description.setWordWrap(True)
        layout.addWidget(description)
        links = W.QLabel(
            '<a href="https://krect.pages.dev/">' + tr("Website", "웹사이트") + '</a> · '
            '<a href="https://github.com/ziwon/KRect">GitHub</a> · '
            '<a href="https://github.com/ziwon/KRect/blob/main/LICENSE">MIT License</a>')
        links.setOpenExternalLinks(True)
        layout.addWidget(links)
        buttons = W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Close)
        buttons.button(W.QDialogButtonBox.StandardButton.Close).setText(tr("Close", "닫기"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
