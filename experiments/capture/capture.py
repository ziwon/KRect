"""Native captures through KWin's interactive API, with no screenshot application."""
import datetime
import math
import os
from pathlib import Path
import select
import time

import dbus

from krect.model import tr
from krect.qt import QtCore as C, QtGui as G, QtWidgets as W, Signal

SERVICE = "org.kde.KWin.ScreenShot2"
MAX_BYTES = 256 * 1024 * 1024


def frame_layout(metadata):
    """Validate KWin's raw-image description before reading or allocating pixels."""
    width, height, stride = (int(metadata.get(key, 0)) for key in ("width", "height", "stride"))
    image_format = G.QImage.Format(int(metadata.get("format", 0)))
    if metadata.get("type") != "raw" or min(width, height, stride) <= 0:
        raise ValueError("Invalid screenshot dimensions")
    if width > 32768 or height > 32768 or stride * height > MAX_BYTES:
        raise ValueError("Screenshot is too large")
    # A one-pixel probe obtains Qt's format depth without allocating a full frame.
    probe = G.QImage(1, 1, image_format)
    if probe.isNull() or stride < (width * probe.depth() + 7) // 8:
        raise ValueError("Invalid screenshot pixel format or stride")
    return width, height, stride, image_format


def read_frame(pipe, metadata):
    width, height, stride, image_format = frame_layout(metadata)
    size = stride * height
    data = bytearray()
    deadline = time.monotonic() + 15
    while len(data) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([pipe], [], [], remaining)[0]:
            raise TimeoutError("Screenshot transfer timed out")
        chunk = os.read(pipe, min(1024 * 1024, size - len(data)))
        if not chunk:
            raise ValueError("Screenshot transfer was incomplete")
        data.extend(chunk)
    image = G.QImage(bytes(data), width, height, stride, image_format).copy()
    if image.isNull():
        raise ValueError("Could not decode the screenshot")
    return image


def crop_image(image, selection, display_size):
    """Map logical selection coordinates to original pixels, independent of scale."""
    if image.isNull() or display_size.width() <= 0 or display_size.height() <= 0:
        return G.QImage()
    rect = C.QRectF(selection).normalized().intersected(C.QRectF(C.QPointF(), C.QSizeF(display_size)))
    if rect.isEmpty():
        return G.QImage()
    sx, sy = image.width() / display_size.width(), image.height() / display_size.height()
    left, top = math.floor(rect.x() * sx), math.floor(rect.y() * sy)
    right, bottom = math.ceil((rect.x() + rect.width()) * sx), math.ceil((rect.y() + rect.height()) * sy)
    return image.copy(left, top, right - left, bottom - top)


class CaptureJob(C.QThread):
    captured = Signal(object, object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, kind, pointer=False, decoration=True, parent=None):
        super().__init__(parent)
        self.kind, self.pointer, self.decoration = kind, pointer, decoration

    def run(self):
        read_pipe, write_pipe = os.pipe()
        bus = None
        try:
            # Interactive selection is authorized by the user's click. Do not
            # grant screenshot access to the shared Python interpreter.
            bus = dbus.SessionBus(private=True)
            metadata = bus.call_blocking(
                SERVICE, "/org/kde/KWin/ScreenShot2", SERVICE, "CaptureInteractive", "ua{sv}h",
                (dbus.UInt32(0 if self.kind == "window" else 1),
                 {"include-cursor": dbus.Boolean(self.pointer),
                  "include-decoration": dbus.Boolean(self.decoration),
                  "include-shadow": dbus.Boolean(False), "native-resolution": dbus.Boolean(True)},
                 dbus.types.UnixFd(write_pipe)), timeout=120)
            os.close(write_pipe)
            write_pipe = -1
            self.captured.emit(read_frame(read_pipe, metadata), dict(metadata))
        except dbus.DBusException as error:
            if error.get_dbus_name().endswith(".Cancelled"):
                self.cancelled.emit()
            else:
                self.failed.emit(tr("KWin could not capture the screen. Press Esc to leave selection and try again.",
                                    "화면을 캡처하지 못했어요. 선택 화면이 남아 있다면 Esc를 누르고 다시 시도하세요.") + "\n" + str(error))
        except (OSError, ValueError, TypeError, OverflowError, TimeoutError) as error:
            self.failed.emit(tr("Could not read the screenshot: ", "캡처 이미지를 읽지 못했어요: ") + str(error))
        finally:
            os.close(read_pipe)
            if write_pipe >= 0:
                os.close(write_pipe)
            if bus is not None:
                bus.close()


class RegionSelector(W.QDialog):
    selected = Signal(object)

    def __init__(self, image, screen):
        super().__init__()
        self.image, self.origin, self.selection = image, None, C.QRectF()
        self.setWindowTitle(tr("KRect — select a region", "KRect — 캡처 영역 선택"))
        self.setWindowFlags(C.Qt.WindowType.FramelessWindowHint | C.Qt.WindowType.WindowStaysOnTopHint)
        self.setCursor(C.Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.winId()
        self.windowHandle().setScreen(screen)
        self.setGeometry(screen.geometry())

    def paintEvent(self, event):
        painter = G.QPainter(self)
        painter.drawImage(self.rect(), self.image)
        shade = G.QPainterPath()
        shade.addRect(C.QRectF(self.rect()))
        if not self.selection.isEmpty():
            shade.addRect(self.selection)
        shade.setFillRule(C.Qt.FillRule.OddEvenFill)
        painter.fillPath(shade, G.QColor(0, 0, 0, 125))
        painter.setPen(G.QPen(self.palette().highlight().color(), 2))
        painter.drawRect(self.selection)
        painter.fillRect(C.QRect(0, 0, self.width(), 52), G.QColor(0, 0, 0, 185))
        painter.setPen(C.Qt.GlobalColor.white)
        painter.drawText(C.QRect(12, 0, self.width() - 24, 52), C.Qt.AlignmentFlag.AlignCenter,
                         tr("Drag to select an area · Esc or right-click to cancel",
                            "드래그해서 영역 선택 · Esc 또는 오른쪽 클릭으로 취소"))

    def mousePressEvent(self, event):
        if event.button() == C.Qt.MouseButton.RightButton:
            self.reject()
        elif event.button() == C.Qt.MouseButton.LeftButton:
            self.origin = C.QPointF(event.pos())
            self.selection = C.QRectF()
            self.update()

    def mouseMoveEvent(self, event):
        if self.origin is not None:
            self.selection = C.QRectF(self.origin, C.QPointF(event.pos())).normalized().intersected(C.QRectF(self.rect()))
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != C.Qt.MouseButton.LeftButton or self.origin is None:
            return
        self.mouseMoveEvent(event)
        self.origin = None
        if self.selection.width() >= 3 and self.selection.height() >= 3:
            self.selected.emit(crop_image(self.image, self.selection, self.size()))
            self.accept()


class CapturePanel(W.QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.job, self.selector = owner, None, None
        self.image = G.QImage()
        self.busy = False
        self.kind = None
        box = W.QVBoxLayout(self)
        box.setContentsMargins(20, 20, 20, 16)
        box.setSpacing(14)
        description = W.QLabel(tr("Capture a window, a region, or one display — directly in KRect.",
                                  "KRect에서 창, 영역, 모니터 한 화면을 바로 캡처하세요."))
        description.setWordWrap(True)
        box.addWidget(description)
        row = W.QHBoxLayout()
        self.capture_buttons = []
        for kind, title in [("region", tr("Select region", "영역 캡처")),
                            ("window", tr("Select window", "창 캡처")),
                            ("screen", tr("Select display", "화면 캡처"))]:
            button = W.QPushButton(title)
            button.clicked.connect(lambda checked=False, k=kind: self.begin(k))
            row.addWidget(button)
            self.capture_buttons.append(button)
        box.addLayout(row)
        help_text = W.QLabel(tr("Choose a window or display when prompted. For a region, choose the display first, then drag over the area. Esc cancels.",
                                "안내가 나오면 창이나 모니터를 선택하세요. 영역 캡처는 모니터를 먼저 고른 뒤 원하는 범위를 드래그해요. Esc로 취소할 수 있어요."))
        help_text.setWordWrap(True)
        box.addWidget(help_text)
        options = W.QHBoxLayout()
        self.pointer = W.QCheckBox(tr("Include pointer", "마우스 포인터 포함"))
        self.decoration = W.QCheckBox(tr("Include window border", "창 테두리 포함"))
        self.decoration.setChecked(True)
        options.addWidget(self.pointer)
        options.addWidget(self.decoration)
        options.addStretch()
        box.addLayout(options)
        self.preview = W.QLabel(tr("Your screenshot will appear here.", "캡처한 이미지가 여기에 표시돼요."))
        self.preview.setAlignment(C.Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(1, 180)
        self.preview.setSizePolicy(W.QSizePolicy.Policy.Ignored, W.QSizePolicy.Policy.Expanding)
        self.preview.setFrameShape(W.QFrame.Shape.StyledPanel)
        self.preview.setAccessibleName(tr("Screenshot preview", "캡처 미리보기"))
        box.addWidget(self.preview, 1)
        self.status = W.QLabel("")
        self.status.setTextFormat(C.Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        box.addWidget(self.status)
        actions = W.QHBoxLayout()
        actions.addStretch()
        self.copy_button = W.QPushButton(tr("Copy image", "이미지 복사"))
        self.copy_button.clicked.connect(self.copy_image)
        self.save_button = W.QPushButton(tr("Save PNG…", "PNG 저장…"))
        self.save_button.clicked.connect(self.save_image)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        box.addLayout(actions)
        self.set_busy(False)

    def set_busy(self, busy):
        self.busy = busy
        for button in self.capture_buttons:
            button.setEnabled(not busy)
        self.copy_button.setEnabled(not busy and not self.image.isNull())
        self.save_button.setEnabled(not busy and not self.image.isNull())

    def begin(self, kind):
        if self.busy or self.job is not None:
            return
        self.kind = kind
        self.set_busy(True)
        self.owner.hide()
        C.QTimer.singleShot(300, self.start_job)

    def start_job(self):
        self.job = CaptureJob(self.kind, self.pointer.isChecked(), self.decoration.isChecked(), self)
        self.job.captured.connect(self.captured)
        self.job.cancelled.connect(self.cancelled)
        self.job.failed.connect(self.failed)
        self.job.finished.connect(self.job_finished)
        self.job.start()

    def job_finished(self):
        job, self.job = self.job, None
        if job is not None:
            job.deleteLater()

    def restore(self):
        self.set_busy(False)
        self.owner.show()
        self.owner.raise_()
        self.owner.activateWindow()

    def captured(self, image, metadata):
        if self.kind == "region":
            screen = next((s for s in G.QGuiApplication.screens() if s.name() == str(metadata.get("screen", ""))), None)
            if screen is None:
                self.failed(tr("The selected display is no longer available. Try again.", "선택한 모니터를 찾지 못했어요. 다시 시도하세요."))
                return
            self.selector = RegionSelector(image, screen)
            self.selector.selected.connect(self.accept_image)
            self.selector.rejected.connect(self.cancelled)
            self.selector.finished.connect(self.selector.deleteLater)
            self.selector.showFullScreen()
            self.selector.activateWindow()
        else:
            self.accept_image(image)

    def accept_image(self, image):
        self.image = image
        self.status.setText(tr("{w} × {h} pixels · Copy or save your screenshot.",
                               "{w} × {h} 픽셀 · 이미지를 복사하거나 저장하세요.").format(w=image.width(), h=image.height()))
        self.restore()
        self.update_preview()

    def cancelled(self):
        self.status.setText(tr("Capture cancelled. If selection never appeared, close other menus and try again.",
                               "캡처를 취소했어요. 선택 화면이 나오지 않았다면 열린 메뉴를 닫고 다시 시도하세요."))
        self.restore()

    def failed(self, message):
        self.status.setText(message)
        self.restore()

    def update_preview(self):
        if not self.image.isNull():
            pixmap = G.QPixmap.fromImage(self.image).scaled(self.preview.size(), C.Qt.AspectRatioMode.KeepAspectRatio,
                                                          C.Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def copy_image(self):
        if not self.image.isNull():
            W.QApplication.clipboard().setImage(self.image)
            self.status.setText(tr("Image copied to the clipboard.", "이미지를 클립보드에 복사했어요."))

    def save_image(self):
        if self.image.isNull():
            return
        pictures = C.QStandardPaths.writableLocation(C.QStandardPaths.StandardLocation.PicturesLocation) or str(Path.home())
        filename = "KRect-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".png"
        dialog = W.QFileDialog(self, tr("Save screenshot", "캡처 저장"), str(Path(pictures) / filename), "PNG (*.png)")
        dialog.setAcceptMode(W.QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix("png")
        from .qt import run
        if run(dialog) and dialog.selectedFiles():
            self.save_png(dialog.selectedFiles()[0])

    def save_png(self, path):
        output = C.QSaveFile(path)
        if output.open(C.QIODevice.OpenModeFlag.WriteOnly) and self.image.save(output, "PNG") and output.commit():
            self.status.setText(tr("Saved: ", "저장했어요: ") + path)
            return True
        output.cancelWriting()
        self.status.setText(tr("Could not save the image. Choose another folder.", "이미지를 저장하지 못했어요. 다른 폴더를 선택하세요."))
        return False
