"""A passive canvas: KWin owns drag input, hit testing and global positioning."""
from .model import LABELS, tr
from .qt import QtCore as C, QtGui as G, QtWidgets as W


class SnapBar(W.QWidget):
    def __init__(self):
        flags = (C.Qt.WindowType.Tool | C.Qt.WindowType.FramelessWindowHint |
                 C.Qt.WindowType.WindowStaysOnTopHint | C.Qt.WindowType.WindowDoesNotAcceptFocus |
                 C.Qt.WindowType.WindowTransparentForInput)
        super().__init__(None, flags)
        self.setWindowTitle("KRect Snap Bar")
        self.setAccessibleName(tr("KRect snap layouts", "KRect 드래그 배치"))
        self.setAttribute(C.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(C.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(C.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(C.Qt.FocusPolicy.NoFocus)
        self.model = {}
        self.watchdog = C.QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.setInterval(2000)
        self.watchdog.timeout.connect(self.dismiss)

    def dismiss(self):
        self.watchdog.stop()
        self.hide()
        self.model = {}

    def receive(self, model):
        if not model.get("visible"):
            self.dismiss()
            return
        self.model = model
        if not self.isVisible():
            geometry = model["geometry"]
            self.resize(round(geometry["width"]), round(geometry["height"]))
            self.show()
            # KWin positions the mapped window; Qt cannot do this on Wayland.
        self.watchdog.start()
        self.update()

    def paintEvent(self, event):
        if not self.model:
            return
        p = G.QPainter(self)
        p.setRenderHint(G.QPainter.RenderHint.Antialiasing)
        geometry = self.model["geometry"]
        width, height = geometry["width"], geometry["height"]
        p.scale(self.width() / width, self.height() / height)
        palette = self.palette()
        p.setPen(G.QPen(palette.color(G.QPalette.ColorRole.Mid), 1))
        p.setBrush(palette.color(G.QPalette.ColorRole.Window))
        p.drawRoundedRect(C.QRectF(0.5, 0.5, width - 1, height - 1), 12, 12)
        selected = self.model.get("selected", -1)
        cells = self.model["cells"]
        label = (LABELS[cells[selected]["action"]] if 0 <= selected < len(cells) else
                 tr("Drag into a region, then release", "영역으로 끌어온 뒤 마우스를 놓으세요"))
        p.setPen(palette.color(G.QPalette.ColorRole.WindowText))
        p.drawText(C.QRectF(12, 6, width - 24, 26), C.Qt.AlignmentFlag.AlignCenter, label)
        for i, cell in enumerate(cells):
            r = cell["rect"]
            active = i == selected
            border = palette.color(G.QPalette.ColorRole.HighlightedText if active else G.QPalette.ColorRole.WindowText)
            border.setAlphaF(.9 if active else .4)
            p.setPen(G.QPen(border, 2 if active else 1))
            p.setBrush(palette.color(G.QPalette.ColorRole.Highlight if active else G.QPalette.ColorRole.Base))
            p.drawRoundedRect(C.QRectF(r["x"], r["y"], r["width"], r["height"]), 3, 3)
        p.end()
