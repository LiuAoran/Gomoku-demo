from PySide6 import QtWidgets
from PySide6.QtCore import QObject, Signal

class NavSignal(QObject):
    nav_to_start_widget_signal = Signal()

nav_signal = NavSignal()
