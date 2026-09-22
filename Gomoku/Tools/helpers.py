from PySide6.QtWidgets import QWidget, QApplication
from pathlib import Path

class Helper:

    @staticmethod
    def load_stylesheet(widget:QWidget, filename: str):
        project_root = Path(__file__).resolve().parents[1]
        qss_path = project_root / "src" / "qss" / filename

        with open(qss_path, "r", encoding="utf-8") as file:
            widget.setStyleSheet(file.read())