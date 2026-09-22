import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from ai.engine import Position, choose_move
from ai.evaluation import evaluate
from models.data_model import Point
from tools.macros import GameMode, Player
from tools.settings import SettingsStore
from views.main_window import MainWindow
from views.settings_dialog import SettingsDialog


class DifficultyEngineTests(unittest.TestCase):
    def test_three_levels_complete_different_search_depths(self):
        board = [[None] * 15 for _ in range(15)]
        for level, depth in (("easy", 1), ("normal", 2), ("hard", 4)):
            with self.subTest(level=level):
                stats = {}
                self.assertEqual(choose_move(board, Player.BLACK, difficulty=level,
                                             time_limit=10, stats=stats), Point(7, 7))
                self.assertEqual(stats["completed_depth"], depth)

    def test_every_level_takes_wins_and_blocks_immediate_loss(self):
        for level in ("easy", "normal", "hard"):
            board = [[None] * 15 for _ in range(15)]
            for y in range(4):
                board[0][y] = Player.BLACK
            with self.subTest(level=level):
                self.assertEqual(choose_move(board, Player.BLACK, difficulty=level), Point(0, 4))
                self.assertEqual(choose_move(board, Player.WHITE, difficulty=level), Point(0, 4))

    def test_hard_blocks_double_three_before_it_forms(self):
        board = [[None] * 15 for _ in range(15)]
        for x, y in ((7, 6), (7, 8), (6, 7), (8, 7)):
            board[x][y] = Player.BLACK
        snapshot = [row[:] for row in board]
        self.assertEqual(choose_move(board, Player.WHITE, difficulty="hard"), Point(7, 7))
        self.assertEqual(board, snapshot)

    def test_incremental_evaluation_matches_full_board_and_undo(self):
        board = [[None] * 15 for _ in range(15)]
        position = Position(board)
        history = []
        for index, point in enumerate(((7, 7), (6, 6), (7, 8), (6, 7), (7, 9), (6, 8), (7, 10), (6, 9), (7, 11))):
            history.append((point, position.push(point, Player.BLACK if index % 2 == 0 else Player.WHITE)))
            self.assertEqual(position.value(), evaluate(position.board))
        for point, state in reversed(history):
            position.pop(point, state)
            self.assertEqual(position.value(), evaluate(position.board))
        self.assertEqual(position.board, board)

    def test_timeout_keeps_a_legal_fallback(self):
        board = [[None] * 15 for _ in range(15)]
        board[7][7] = Player.BLACK
        stats = {}
        point = choose_move(board, Player.WHITE, difficulty="hard", time_limit=0, stats=stats)
        self.assertIsNone(board[point.x][point.y])
        self.assertEqual(stats["completed_depth"], 0)


class DifficultySettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store = SettingsStore(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_setting_cancel_save_reload_and_invalid_value(self):
        dialog = SettingsDialog(self.store)
        self.assertTrue(dialog.difficulty_buttons["normal"].isChecked())
        dialog.difficulty_buttons["hard"].click()
        self.assertFalse(dialog.difficulty_buttons["normal"].isChecked())
        dialog.reject()
        self.assertEqual(self.store.values.ai_difficulty, "normal")
        dialog = SettingsDialog(self.store)
        dialog.difficulty_buttons["hard"].click()
        dialog.accept()
        self.assertEqual(SettingsStore(self.temp.name).values.ai_difficulty, "hard")
        self.store.path.write_text('{"ai_difficulty":"unknown"}')
        self.assertEqual(SettingsStore(self.temp.name).values.ai_difficulty, "normal")

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_changing_difficulty_restarts_pending_ai_and_discards_old_result(self, pool):
        self.store.save(replace(self.store.values, ai_difficulty="easy"))
        window = MainWindow(self.store, audio_enabled=False)
        window.start_game(GameMode.AI)
        game = window.game_widget
        canvas = game.chess_board.piece_area
        canvas.place_stone(Point(7, 7))
        old_task = game.search_task
        self.assertEqual(old_task.difficulty, "easy")
        game.on_search_finished(old_task.token, Point(7, 8), "")
        self.assertTrue(game.move_timer.isActive())
        self.store.save(replace(self.store.values, ai_difficulty="hard"))
        self.assertFalse(game.move_timer.isActive())
        self.assertIsNone(game.pending_move)
        self.assertEqual(game.search_task.difficulty, "hard")
        game.on_search_finished(old_task.token, Point(7, 8), "")
        self.assertEqual(len(canvas.play_game_controller.game_model.moves), 1)
        window.close()
        window.deleteLater()

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_hint_uses_selected_difficulty(self, pool):
        self.store.save(replace(self.store.values, ai_difficulty="hard"))
        window = MainWindow(self.store, audio_enabled=False)
        window.start_game(GameMode.TWO_PLAYERS)
        window.game_widget.request_hint()
        self.assertEqual(window.game_widget.search_task.difficulty, "hard")
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
