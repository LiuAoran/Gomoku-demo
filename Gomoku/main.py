# This Python file uses the following encoding: utf-8
import sys
from PySide6.QtWidgets import QApplication

from views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # ...
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
