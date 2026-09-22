from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QSlider, QVBoxLayout, QWidget


class SquareCropWidget(QWidget):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        side = min(image.width(), image.height())
        self.selection = QRectF((image.width() - side) / 2, (image.height() - side) / 2, side, side)
        self.drag_offset = None
        self.setMinimumSize(480, 380)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def image_rect(self):
        available = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        scale = min(available.width() / self.image.width(), available.height() / self.image.height())
        size = self.image.size() * scale
        return QRectF(available.center().x() - size.width() / 2,
                      available.center().y() - size.height() / 2, size.width(), size.height())

    def set_crop_percent(self, percent):
        side = min(self.image.width(), self.image.height()) * percent / 100
        center = self.selection.center()
        self.selection = QRectF(center.x() - side / 2, center.y() - side / 2, side, side)
        self.clamp_selection()
        self.update()

    def clamp_selection(self):
        self.selection.moveLeft(max(0, min(self.selection.x(), self.image.width() - self.selection.width())))
        self.selection.moveTop(max(0, min(self.selection.y(), self.image.height() - self.selection.height())))

    def source_point(self, position):
        rect = self.image_rect()
        return QPointF((position.x() - rect.x()) * self.image.width() / rect.width(),
                       (position.y() - rect.y()) * self.image.height() / rect.height())

    def mousePressEvent(self, event):
        point = self.source_point(event.position())
        if event.button() == Qt.MouseButton.LeftButton and self.selection.contains(point):
            self.drag_offset = point - self.selection.topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            self.selection.moveTopLeft(self.source_point(event.position()) - self.drag_offset)
            self.clamp_selection()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def cropped_image(self):
        side = max(1, int(self.selection.width()))
        rect = QRect(int(self.selection.x()), int(self.selection.y()), side, side)
        cropped = self.image.copy(rect)
        if side > 1600:
            cropped = cropped.scaled(1600, 1600, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        return cropped

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#252321"))
        rect = self.image_rect()
        painter.drawImage(rect, self.image)
        scale = rect.width() / self.image.width()
        crop = QRectF(rect.x() + self.selection.x() * scale, rect.y() + self.selection.y() * scale,
                      self.selection.width() * scale, self.selection.height() * scale)
        painter.fillRect(rect, QColor(0, 0, 0, 140))
        painter.drawImage(crop, self.image, self.selection)
        painter.setPen(QPen(QColor("#F7DFC0"), 2))
        painter.drawRect(crop)
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        for fraction in (1/3, 2/3):
            x, y = crop.x() + crop.width() * fraction, crop.y() + crop.height() * fraction
            painter.drawLine(QPointF(x, crop.top()), QPointF(x, crop.bottom()))
            painter.drawLine(QPointF(crop.left(), y), QPointF(crop.right(), y))


class ImageCropDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪背景图")
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("拖动方形选区调整位置，滑动下方滑块调整大小。"))
        self.crop = SquareCropWidget(image)
        layout.addWidget(self.crop, 1)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(10, 100)
        self.size_slider.setValue(100)
        self.size_slider.valueChanged.connect(self.crop.set_crop_percent)
        layout.addWidget(self.size_slider)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("使用此裁剪")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
