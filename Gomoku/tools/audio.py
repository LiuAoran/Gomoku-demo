from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from tools.macros import GameMode, Player


class AudioManager(QObject):
    error = Signal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.enabled = False
        self.music = QMediaPlayer(self)
        self.effect = QMediaPlayer(self)
        self.music_output = QAudioOutput(self)
        self.effect_output = QAudioOutput(self)
        self.music.setAudioOutput(self.music_output)
        self.effect.setAudioOutput(self.effect_output)
        self.music.errorOccurred.connect(lambda *_: self.error.emit("背景音乐无法播放：" + self.music.errorString()))
        self.effect.errorOccurred.connect(lambda *_: self.error.emit("音效无法播放：" + self.effect.errorString()))
        store.changed.connect(self.apply_settings)
        self.apply_settings()

    def apply_settings(self):
        values = self.store.values
        self.music_output.setVolume(values.music_volume / 100)
        self.effect_output.setVolume(values.effects_volume / 100)
        self.music.setLoops(QMediaPlayer.Loops.Infinite if values.music_loop else QMediaPlayer.Loops.Once)
        source = QUrl.fromLocalFile(values.music_path)
        changed = source != self.music.source()
        was_stopped = self.music.playbackState() != QMediaPlayer.PlaybackState.PlayingState
        if changed:
            self.music.setSource(source)
        if self.enabled and values.music_enabled:
            if changed or was_stopped:
                self.music.play()
        else:
            self.music.stop()
        if not self.enabled or not values.effects_enabled:
            self.effect.stop()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.apply_settings()

    def play_result(self, winner, mode):
        if not self.enabled or winner is None or not self.store.values.effects_enabled:
            return
        lost = mode == GameMode.AI and winner == Player.WHITE
        path = self.store.values.lose_path if lost else self.store.values.win_path
        self.effect.stop()
        self.effect.setSource(QUrl.fromLocalFile(path))
        self.effect.play()

    def stop_effect(self):
        self.effect.stop()

    def stop(self):
        self.music.stop()
        self.effect.stop()
