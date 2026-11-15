"""Capture transfer failures, scaled crops, and native clipboard/file output."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
try:
    from capture import CapturePanel, RegionSelector, crop_image, frame_layout, read_frame
    from krect.qt import QtCore as C, QtGui as G, QtWidgets as W
except ImportError:
    CapturePanel = None


@unittest.skipUnless(CapturePanel, "Needs distribution PyQt and python3-dbus")
class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = W.QApplication.instance() or W.QApplication(["krect-capture-test"])

    def setUp(self):
        self.owner = W.QWidget()
        self.panel = CapturePanel(self.owner)

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()

    def test_native_raw_frame_preserves_pixels_and_rejects_incomplete_pipe(self):
        fmt = G.QImage.Format.Format_RGB32
        metadata = dict(type="raw", width=2, height=1, stride=8, format=int(fmt.value if hasattr(fmt, "value") else fmt))
        for data in [b"\x33\x22\x11\xff\x66\x55\x44\xff", b"\x33\x22"]:
            read_pipe, write_pipe = os.pipe()
            try:
                os.write(write_pipe, data)
                os.close(write_pipe)
                if len(data) == 8:
                    image = read_frame(read_pipe, metadata)
                    self.assertEqual(image.pixelColor(0, 0).name(), "#112233")
                    self.assertEqual(image.pixelColor(1, 0).name(), "#445566")
                else:
                    with self.assertRaisesRegex(ValueError, "incomplete"):
                        read_frame(read_pipe, metadata)
            finally:
                os.close(read_pipe)

    def test_invalid_or_oversized_frames_are_rejected_before_allocation(self):
        fmt = G.QImage.Format.Format_RGB32
        metadata = dict(type="raw", width=2, height=1, stride=8, format=int(fmt.value if hasattr(fmt, "value") else fmt))
        for change in [dict(width=0), dict(stride=1), dict(type="png"), dict(height=32769), dict(stride=300000000)]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                frame_layout(dict(metadata, **change))

    def test_scaled_and_reversed_region_selects_original_pixels(self):
        image = G.QImage(200, 100, G.QImage.Format.Format_RGB32)
        image.fill(G.QColor("red"))
        painter = G.QPainter(image)
        painter.fillRect(50, 20, 100, 60, G.QColor("blue"))
        painter.end()
        result = crop_image(image, C.QRectF(C.QPointF(75, 40), C.QPointF(25, 10)), C.QSize(100, 50))
        self.assertEqual(result.size(), C.QSize(100, 60))
        self.assertEqual(result.pixelColor(0, 0).name(), "#0000ff")
        self.assertEqual(result.pixelColor(99, 59).name(), "#0000ff")
        self.assertTrue(crop_image(image, C.QRectF(-30, -20, 10, 5), C.QSize(100, 50)).isNull())

    def test_cancel_and_failure_preserve_previous_capture(self):
        image = G.QImage(40, 30, G.QImage.Format.Format_RGB32)
        image.fill(G.QColor("blue"))
        self.panel.accept_image(image)
        for finish in [self.panel.cancelled, lambda: self.panel.failed("Unavailable")]:
            self.panel.set_busy(True)
            self.assertFalse(self.panel.copy_button.isEnabled())
            finish()
            self.assertEqual(self.panel.image.size(), image.size())
            self.assertTrue(self.panel.copy_button.isEnabled())
            self.assertTrue(self.owner.isVisible())

    def test_copy_and_png_save_use_original_resolution(self):
        image = G.QImage(80, 60, G.QImage.Format.Format_RGB32)
        image.fill(G.QColor("#2187b9"))
        self.panel.accept_image(image)
        self.panel.copy_image()
        self.assertEqual(self.app.clipboard().image().size(), image.size())
        with tempfile.TemporaryDirectory() as folder:
            output = str(Path(folder) / "capture.png")
            self.assertTrue(self.panel.save_png(output))
            saved = G.QImage(output)
            self.assertEqual(saved.size(), image.size())
            self.assertEqual(saved.pixelColor(0, 0).name(), "#2187b9")
            self.assertFalse(self.panel.save_png(str(Path(folder) / "missing/capture.png")))


if __name__ == "__main__":
    unittest.main()
