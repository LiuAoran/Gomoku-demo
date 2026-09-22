from PySide6.QtWidgets import QMainWindow

from tools.macros import GameMode
from tools.helpers import Helper
from views import start_widget, game_widget

from tools.signals import nav_signal
from tools.settings import SettingsStore
from tools.audio import AudioManager
from views.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, settings_store=None, audio_enabled=True):
        super().__init__()
        self.settings_store = settings_store or SettingsStore(parent=self)
        self.sound_enabled = False
        self.settings_store.changed.connect(self.apply_background)
        self.settings_store.changed.connect(self.apply_difficulty)
        self.audio = AudioManager(self.settings_store, self) if audio_enabled else None
        if self.audio is not None:
            self.audio.error.connect(lambda message: self.statusBar().showMessage(message, 8000))

        self.game_widget = None
        Helper.load_stylesheet(self, "main_window.qss")

        self.setWindowTitle("Gomoku")
        self.setFixedSize(900, 700)

        self.start_widget = start_widget.StartWidget()
        self.setCentralWidget(self.start_widget)

        self.start_widget.start_game_signal.connect(self.start_game)
        self.start_widget.settings_requested.connect(self.open_settings)
        nav_signal.nav_to_start_widget_signal.connect(self.nav_to_start_widget)
        self.apply_background()

    def start_game(self, mode: GameMode):
        if self.game_widget is not None:
            self.game_widget.deactivate()
        self.game_widget = game_widget.GameWidget(mode, self.settings_store.values.ai_difficulty,
                                                  self.settings_store.jev_api_key,
                                                  self.settings_store.values.jev_model)
        self.game_widget.toolbar.settings_button.clicked.connect(self.open_settings)
        self.game_widget.toolbar.sound_button.setChecked(self.sound_enabled)
        self.game_widget.toolbar.sound_button.toggled.connect(self.set_sound_enabled)
        if self.audio is not None:
            canvas = self.game_widget.chess_board.piece_area
            canvas.game_finished.connect(self.audio.play_result)
            canvas.game_changed.connect(self.on_game_state_changed)
        self.setCentralWidget(self.game_widget)
        self.apply_background()

    def set_sound_enabled(self, enabled):
        self.sound_enabled = enabled
        if self.audio is not None:
            self.audio.set_enabled(enabled)

    def nav_to_start_widget(self):
        if self.audio is not None:
            self.audio.stop_effect()
        if self.game_widget is not None:
            self.game_widget.deactivate()
            self.game_widget = None
        self.start_widget = start_widget.StartWidget()
        self.setCentralWidget(self.start_widget)
        self.start_widget.start_game_signal.connect(self.start_game)
        self.start_widget.settings_requested.connect(self.open_settings)

    def on_game_state_changed(self):
        if self.game_widget is not None and not self.game_widget.chess_board.piece_area.play_game_controller.is_game_over():
            self.audio.stop_effect()

    def open_settings(self):
        dialog = SettingsDialog(self.settings_store, self)
        dialog.exec()
        dialog.deleteLater()

    def apply_background(self):
        if self.game_widget is not None:
            values = self.settings_store.values
            self.game_widget.chess_board.set_background(values.background_path, values.background_blur)

    def apply_difficulty(self):
        if self.game_widget is not None:
            self.game_widget.set_difficulty(self.settings_store.values.ai_difficulty,
                                            self.settings_store.jev_api_key,
                                            self.settings_store.values.jev_model)

    def closeEvent(self, event):
        if self.audio is not None:
            self.audio.stop()
        if self.game_widget is not None:
            self.game_widget.deactivate()
        super().closeEvent(event)
