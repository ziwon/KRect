"""The small Qt 5/6 compatibility boundary; application code uses scoped enums."""
try:
    from PyQt6 import QtCore, QtGui, QtWidgets, QtDBus
    QT_MAJOR = 6
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets, QtDBus
    QT_MAJOR = 5

Signal = QtCore.pyqtSignal
Slot = QtCore.pyqtSlot
Action = QtGui.QAction if QT_MAJOR == 6 else QtWidgets.QAction


def run(app):
    return app.exec() if QT_MAJOR == 6 else app.exec_()
