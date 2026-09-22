from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPalette, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSlider, QStyleFactory, QTabWidget, QVBoxLayout, QWidget,
)

from tools.backgrounds import prepare_background
from tools.settings import Settings
from tools.helpers import Helper
from ai.difficulty import DIFFICULTIES
from views.image_crop_dialog import ImageCropDialog


class SettingsDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.draft = replace(store.values)
        self.cropped_image = None
        self.setWindowTitle("设置")
        self.resize(620, 650)
        self.setObjectName("settingsDialog")
        # Use one local control style and palette on both light and dark desktops.
        self.control_style = QStyleFactory.create("Fusion")
        self.control_style.setParent(self)
        palette = self.control_style.standardPalette()
        for role, color in (
            (QPalette.ColorRole.Window, "#F1DFC0"),
            (QPalette.ColorRole.WindowText, "#4A3424"),
            (QPalette.ColorRole.Base, "#FBF4E6"),
            (QPalette.ColorRole.Text, "#4A3424"),
            (QPalette.ColorRole.Button, "#EAD6B5"),
            (QPalette.ColorRole.ButtonText, "#4A3424"),
            (QPalette.ColorRole.Highlight, "#795538"),
            (QPalette.ColorRole.HighlightedText, "#FFFFFF"),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)
        Helper.load_stylesheet(self, "settings_dialog.qss")
        check_icon = Path(__file__).resolve().parents[1] / "src" / "icons" / "check.svg"
        self.setStyleSheet(self.styleSheet().replace("CHECK_ICON", check_icon.as_posix()))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        game_page = QWidget()
        game_page.setObjectName("settingsPage")
        game_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        game_layout = QVBoxLayout(game_page)
        game_layout.setContentsMargins(18, 20, 18, 20)
        game_layout.setSpacing(16)
        game_layout.addWidget(QLabel("AI 对弈难度"))
        self.difficulty_group = QButtonGroup(self)
        self.difficulty_group.setExclusive(True)
        self.difficulty_buttons = {}
        summaries = {
            "easy": "基础攻防 · 适合入门练习",
            "normal": "预判对手回应 · 日常对弈",
            "hard": "深入搜索与连续威胁判断 · 更具挑战",
            "jev": "TypeSafe API · 独立联网对手，棋力待实测",
        }
        for key, profile in DIFFICULTIES.items():
            card = QPushButton(f"{profile.label}\n{summaries[key]}")
            card.setObjectName("difficultyCard")
            card.setCheckable(True)
            card.setMinimumHeight(58)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(profile.description)
            self.difficulty_group.addButton(card)
            self.difficulty_buttons[key] = card
            game_layout.addWidget(card)
        explanation = QLabel("保存后立即生效，无需重新开局。\n提示功能也使用所选难度。\nAI 在玩家落子后至少等待 1 秒；复杂局面可能需要更久。")
        explanation.setWordWrap(True)
        game_layout.addWidget(explanation)
        game_layout.addStretch()
        tabs.addTab(game_page, "对弈")
        jev_page = QWidget()
        jev_page.setObjectName("settingsPage")
        jev_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        jev_layout = QFormLayout(jev_page)
        jev_layout.setContentsMargins(18, 20, 18, 20)
        jev_layout.setVerticalSpacing(18)
        self.jev_key = QLineEdit()
        self.jev_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.jev_key.setPlaceholderText("填写 TypeSafe API Key")
        self.jev_model = QLineEdit()
        self.jev_model.setReadOnly(True)
        jev_layout.addRow("API Key", self.jev_key)
        jev_layout.addRow("模型", self.jev_model)
        api_note = QLabel("官方接口：https://api.typesafe.ai/v1/systemone\n\n"
                          "启动时自动读取项目 .env 的 TYPESAFE_API_KEY。\n"
                          "也支持同名环境变量（优先于 .env）。\n"
                          "此处修改密钥仅本次运行有效，不写入设置文件。\n\n"
                          "联网对弈与提示会向 TypeSafe 发送棋盘和候选落点，\n"
                          "消耗 API 额度。请求失败会提示重试，不替换成本地 AI。")
        api_note.setWordWrap(True)
        jev_layout.addRow(api_note)
        tabs.addTab(jev_page, "Jev API")
        audio_page = QWidget()
        audio_page.setObjectName("settingsPage")
        audio_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        audio_layout = QFormLayout(audio_page)
        audio_layout.setContentsMargins(18, 20, 18, 20)
        audio_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        audio_layout.setVerticalSpacing(18)
        self.music_enabled = QCheckBox("播放背景音乐")
        self.music_loop = QCheckBox("循环播放")
        self.effects_enabled = QCheckBox("播放输赢音效")
        audio_layout.addRow(self.music_enabled)
        self.path_labels = {}
        for key, label in (("music_path", "背景音乐"), ("win_path", "获胜音效"), ("lose_path", "失败音效")):
            row = QHBoxLayout()
            name = QLabel()
            name.setMinimumWidth(160)
            self.path_labels[key] = name
            button = QPushButton("选择音频…")
            button.clicked.connect(lambda checked=False, key=key: self.choose_audio(key))
            row.addWidget(name, 1)
            row.addWidget(button)
            audio_layout.addRow(label, row)
        audio_layout.addRow(self.music_loop)
        self.music_volume = self.volume_slider(audio_layout, "音乐音量")
        audio_layout.addRow(self.effects_enabled)
        self.effects_volume = self.volume_slider(audio_layout, "音效音量")
        note = QLabel("AI 对弈：玩家执黑，按玩家输赢播放。\n双人对弈：分出胜负时播放获胜音效；和棋不播放。")
        note.setWordWrap(True)
        audio_layout.addRow(note)
        tabs.addTab(audio_page, "音乐与音效")

        image_page = QWidget()
        image_page.setObjectName("settingsPage")
        image_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        image_layout = QVBoxLayout(image_page)
        image_layout.setContentsMargins(18, 20, 18, 20)
        image_layout.addWidget(QLabel("选择方形区域作为棋盘背景，图片铺满棋盘区域。"))
        self.preview = QLabel("使用默认棋盘背景")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedSize(300, 300)
        self.preview.setStyleSheet("background: #E6D2A5; color: #4A3424; border-radius: 8px;")
        image_layout.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignHCenter)
        row = QHBoxLayout()
        choose = QPushButton("选择并裁剪图片…")
        clear = QPushButton("使用默认棋盘背景")
        choose.clicked.connect(self.choose_background)
        clear.clicked.connect(self.clear_background)
        row.addWidget(choose)
        row.addWidget(clear)
        image_layout.addLayout(row)
        self.blur = QCheckBox("高斯模糊")
        self.blur.toggled.connect(self.update_preview)
        image_layout.addWidget(self.blur)
        image_layout.addStretch()
        tabs.addTab(image_page, "棋盘背景")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存设置")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("saveSettings")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        defaults = buttons.addButton("恢复默认", QDialogButtonBox.ButtonRole.ResetRole)
        defaults.clicked.connect(self.restore_defaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setStyle(self.control_style)
        for widget in self.findChildren(QWidget):
            widget.setStyle(self.control_style)
        self.load_controls()

    def volume_slider(self, layout, title):
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        value = QLabel("0%")
        value.setFixedWidth(40)
        slider.valueChanged.connect(lambda number: value.setText(f"{number}%"))
        row.addWidget(slider)
        row.addWidget(value)
        layout.addRow(title, row)
        return slider

    def load_controls(self):
        self.jev_key.setText(self.store.jev_api_key)
        self.jev_model.setText(self.draft.jev_model)
        self.difficulty_buttons.get(self.draft.ai_difficulty, self.difficulty_buttons["normal"]).setChecked(True)
        for key in ("music_enabled", "music_loop", "effects_enabled"):
            getattr(self, key).setChecked(getattr(self.draft, key))
        self.music_volume.setValue(self.draft.music_volume)
        self.effects_volume.setValue(self.draft.effects_volume)
        for key, label in self.path_labels.items():
            path = getattr(self.draft, key)
            label.setText(label.fontMetrics().elidedText(Path(path).name, Qt.TextElideMode.ElideMiddle, 230))
            label.setToolTip(path)
        self.blur.setChecked(self.draft.background_blur)
        self.update_preview()

    def choose_audio(self, key):
        path, _ = QFileDialog.getOpenFileName(self, "选择音频", "", "音频 (*.mp3 *.wav *.ogg *.m4a *.flac)")
        if path:
            setattr(self.draft, key, path)
            label = self.path_labels[key]
            label.setText(label.fontMetrics().elidedText(Path(path).name, Qt.TextElideMode.ElideMiddle, 230))
            label.setToolTip(path)

    def choose_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择棋盘背景图", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        size = reader.size()
        if max(size.width(), size.height()) > 4096:
            reader.setScaledSize(size.scaled(4096, 4096, Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "无法打开图片", reader.errorString())
            return
        dialog = ImageCropDialog(image, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cropped_image = dialog.crop.cropped_image()
            self.update_preview()

    def clear_background(self):
        self.draft.background_path = ""
        self.cropped_image = None
        self.update_preview()

    def update_preview(self):
        image = self.cropped_image if self.cropped_image is not None else (
            QImage(self.draft.background_path) if self.draft.background_path else QImage())
        if image.isNull():
            self.preview.clear()
            self.preview.setText("使用默认棋盘背景")
            return
        image = prepare_background(image, self.blur.isChecked())
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def restore_defaults(self):
        self.draft = Settings()
        self.cropped_image = None
        self.load_controls()

    def accept(self):
        self.draft.ai_difficulty = next(key for key, button in self.difficulty_buttons.items() if button.isChecked())
        self.draft.jev_model = "jev-latest"
        if self.draft.ai_difficulty == "jev" and not self.jev_key.text().strip():
            QMessageBox.warning(self, "需要 API Key", "请在 Jev API 页填写密钥后再选择联网对弈。")
            return
        for key in ("music_enabled", "music_loop", "effects_enabled"):
            setattr(self.draft, key, getattr(self, key).isChecked())
        self.draft.music_volume = self.music_volume.value()
        self.draft.effects_volume = self.effects_volume.value()
        self.draft.background_blur = self.blur.isChecked()
        try:
            self.store.save(self.draft, self.cropped_image, jev_api_key=self.jev_key.text().strip())
        except OSError as error:
            QMessageBox.warning(self, "设置保存失败", str(error))
            return
        super().accept()
