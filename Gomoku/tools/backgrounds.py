from PIL import Image, ImageFilter
from PySide6.QtGui import QImage


def prepare_background(image, blur=False):
    if image.isNull() or not blur:
        return image.copy()
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    source = Image.frombytes("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()))
    result = source.filter(ImageFilter.GaussianBlur(radius=12))
    return QImage(result.tobytes(), result.width, result.height, QImage.Format.Format_RGBA8888).copy()
