import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tools.audio import AudioManager
from tools.backgrounds import prepare_background
from tools.macros import GameMode, Player
from tools.settings import Settings, SettingsStore
from views.image_crop_dialog import SquareCropWidget
from views.main_window import MainWindow
from views.settings_dialog import SettingsDialog
from models.data_model import Point


class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store = SettingsStore(Path(self.temp.name) / "preferences")

    def tearDown(self):
        self.temp.cleanup()

    def test_defaults_and_persistence(self):
        self.assertEqual(Path(self.store.values.music_path).name, "667.mp3")
        self.assertEqual(Path(self.store.values.win_path).name, "5553.mp3")
        self.assertEqual(Path(self.store.values.lose_path).name, "5538.mp3")
        self.assertTrue(self.store.values.music_loop)
        values = replace(self.store.values, music_loop=False, music_volume=18, background_blur=True)
        self.store.save(values)
        self.assertEqual(SettingsStore(self.store.directory).values, values)

    def test_imported_audio_survives_original_removal(self):
        original = Path(self.temp.name) / "custom.mp3"
        original.write_bytes(Path(Settings().win_path).read_bytes())
        self.store.save(replace(self.store.values, win_path=str(original)))
        original.unlink()
        restored = SettingsStore(self.store.directory)
        self.assertTrue(Path(restored.values.win_path).is_file())
        self.assertEqual(Path(restored.values.win_path).read_bytes(), Path(Settings().win_path).read_bytes())

    def test_invalid_config_and_failed_save_preserve_preferences(self):
        self.store.directory.mkdir()
        self.store.path.write_text('{"music_volume":500,"music_loop":"bad","win_path":"missing"}')
        restored = SettingsStore(self.store.directory)
        self.assertEqual(restored.values.music_volume, 100)
        self.assertTrue(restored.values.music_loop)
        self.assertEqual(restored.values.win_path, Settings().win_path)
        self.store.save(Settings())
        with self.assertRaises(OSError):
            self.store.save(replace(Settings(), music_path="missing.mp3"))
        self.assertEqual(SettingsStore(self.store.directory).values, Settings())

    def test_dialog_cancel_save_and_restore(self):
        dialog = SettingsDialog(self.store)
        dialog.music_volume.setValue(12)
        dialog.music_loop.setChecked(False)
        dialog.cropped_image = QImage(20, 20, QImage.Format.Format_RGB32)
        dialog.blur.setChecked(True)
        dialog.reject()
        self.assertEqual(self.store.values, Settings())
        dialog = SettingsDialog(self.store)
        dialog.music_volume.setValue(12)
        dialog.music_loop.setChecked(False)
        dialog.accept()
        self.assertEqual(self.store.values.music_volume, 12)
        self.assertFalse(self.store.values.music_loop)
        dialog = SettingsDialog(self.store)
        dialog.restore_defaults()
        dialog.accept()
        self.assertEqual(self.store.values, Settings())

    @patch("views.main_window.SettingsDialog")
    def test_settings_entry_points_on_menu_and_game(self, dialog_class):
        window = MainWindow(self.store, audio_enabled=False)
        window.start_widget.settings_button.click()
        self.assertEqual(dialog_class.return_value.exec.call_count, 1)
        window.start_game(GameMode.TWO_PLAYERS)
        window.game_widget.toolbar.settings_button.click()
        self.assertEqual(dialog_class.return_value.exec.call_count, 2)
        window.nav_to_start_widget()
        window.start_widget.settings_button.click()
        self.assertEqual(dialog_class.return_value.exec.call_count, 3)
        window.close()
        window.deleteLater()

    @patch("views.main_window.AudioManager")
    def test_finished_game_triggers_sound_once_and_restart_stops_it(self, audio_class):
        window = MainWindow(self.store)
        window.start_game(GameMode.TWO_PLAYERS)
        canvas = window.game_widget.chess_board.piece_area
        for col in range(4):
            canvas.place_stone(Point(0, col))
            canvas.place_stone(Point(2, col * 2))
        audio_class.return_value.play_result.assert_not_called()
        canvas.place_stone(Point(0, 4))
        audio_class.return_value.play_result.assert_called_once_with(Player.BLACK, GameMode.TWO_PLAYERS)
        canvas.msg_box.reject()
        audio_class.return_value.stop_effect.reset_mock()
        canvas.restart_game()
        audio_class.return_value.stop_effect.assert_called_once()
        window.close()
        audio_class.return_value.stop.assert_called_once()
        window.deleteLater()

    def test_square_crop_drag_stays_in_bounds_and_blur_preserves_source(self):
        image = QImage(800, 400, QImage.Format.Format_RGBA8888)
        image.fill(QColor("white"))
        for x in range(400):
            for y in range(400):
                image.setPixelColor(x, y, QColor("black"))
        crop = SquareCropWidget(image)
        crop.resize(500, 400)
        crop.show()
        crop.set_crop_percent(50)
        center = crop.rect().center()
        QTest.mousePress(crop, Qt.MouseButton.LeftButton, pos=center)
        QTest.mouseMove(crop, QPoint(499, 399))
        QTest.mouseRelease(crop, Qt.MouseButton.LeftButton, pos=QPoint(499, 399))
        self.assertGreaterEqual(crop.selection.x(), 0)
        self.assertGreaterEqual(crop.selection.y(), 0)
        self.assertLessEqual(crop.selection.right(), 800)
        self.assertLessEqual(crop.selection.bottom(), 400)
        result = crop.cropped_image()
        self.assertEqual(result.size().width(), 200)
        self.assertEqual(result.size().height(), 200)
        blurred = prepare_background(image, True)
        self.assertEqual(image.pixelColor(399, 200), QColor("black"))
        self.assertGreater(blurred.pixelColor(399, 200).red(), 0)
        self.assertLess(blurred.pixelColor(400, 200).red(), 255)
        self.assertEqual(prepare_background(image, False), image)
        crop.close()

    def test_background_only_updates_board_and_survives_navigation(self):
        image = QImage(120, 120, QImage.Format.Format_RGB32)
        image.fill(QColor("#348877"))
        window = MainWindow(self.store, audio_enabled=False)
        window.show()
        self.app.processEvents()
        menu_before = window.grab().toImage()
        self.store.save(replace(self.store.values, background_blur=True), image)
        self.app.processEvents()
        self.assertEqual(window.grab().toImage(), menu_before)
        window.start_game(GameMode.TWO_PLAYERS)
        self.app.processEvents()
        board = window.game_widget.chess_board
        self.assertFalse(board.background.isNull())
        self.assertEqual(board.grab().toImage().pixelColor(5, 5), QColor("#348877"))
        self.assertEqual(window.grab().toImage().pixelColor(5, 100), QColor("#9A7653"))
        restored = SettingsStore(self.store.directory)
        self.assertEqual(QImage(restored.values.background_path).size(), image.size())
        self.assertTrue(restored.values.background_blur)
        window.nav_to_start_widget()
        window.start_game(GameMode.TWO_PLAYERS)
        board = window.game_widget.chess_board
        self.assertFalse(board.background.isNull())
        self.store.save(replace(self.store.values, background_path=""))
        self.assertTrue(board.background.isNull())
        self.assertEqual(board.grab().toImage().pixelColor(5, 5), QColor("#E6D2A5"))
        window.close()
        window.deleteLater()

    @patch("tools.audio.QAudioOutput")
    @patch("tools.audio.QMediaPlayer")
    def test_audio_defaults_result_mapping_and_mute(self, player_class, output_class):
        player_class.Loops = QMediaPlayer.Loops
        player_class.PlaybackState = QMediaPlayer.PlaybackState
        from unittest.mock import MagicMock
        music, effect = MagicMock(), MagicMock()
        player_class.side_effect = [music, effect]
        manager = AudioManager(self.store)
        music.play.assert_not_called()
        manager.play_result(Player.BLACK, GameMode.AI)
        effect.play.assert_not_called()
        manager.set_enabled(True)
        music.play.assert_called_once()
        music.setLoops.assert_called_with(QMediaPlayer.Loops.Infinite)
        self.assertEqual(music.setSource.call_args.args[0].toLocalFile(), Settings().music_path)
        for winner, mode, path in ((Player.BLACK, GameMode.AI, Settings().win_path),
                                   (Player.WHITE, GameMode.AI, Settings().lose_path),
                                   (Player.WHITE, GameMode.TWO_PLAYERS, Settings().win_path)):
            manager.play_result(winner, mode)
            self.assertEqual(effect.setSource.call_args.args[0].toLocalFile(), path)
        manager.set_enabled(False)
        music.stop.assert_called()
        effect.stop.assert_called()
        effect.reset_mock()
        manager.play_result(Player.BLACK, GameMode.AI)
        effect.play.assert_not_called()
        self.store.save(replace(self.store.values, music_volume=42))
        self.assertFalse(manager.enabled)
        manager.set_enabled(True)
        manager.play_result(None, GameMode.TWO_PLAYERS)
        effect.play.assert_not_called()
        self.store.save(replace(self.store.values, music_enabled=False, effects_enabled=False, music_loop=False))
        music.stop.assert_called()
        music.setLoops.assert_called_with(QMediaPlayer.Loops.Once)
        manager.play_result(Player.BLACK, GameMode.AI)
        effect.play.assert_not_called()

    @patch("views.main_window.AudioManager")
    def test_toolbar_sound_switch_defaults_off_and_survives_navigation(self, audio_class):
        window = MainWindow(self.store)
        window.start_game(GameMode.TWO_PLAYERS)
        button = window.game_widget.toolbar.sound_button
        self.assertFalse(button.isChecked())
        self.assertEqual(button.text(), "声音：关")
        button.click()
        audio_class.return_value.set_enabled.assert_called_with(True)
        self.assertEqual(button.text(), "声音：开")
        window.nav_to_start_widget()
        window.start_game(GameMode.TWO_PLAYERS)
        button = window.game_widget.toolbar.sound_button
        self.assertTrue(button.isChecked())
        button.click()
        audio_class.return_value.set_enabled.assert_called_with(False)
        self.assertEqual(button.text(), "声音：关")
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
