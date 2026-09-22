import os
import unittest
from threading import Event
from time import monotonic
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QThreadPool, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ai.engine import choose_move
from ai.evaluation import advantage, evaluate
from models.data_model import Point
from tools.macros import GameMode, Player
from views.main_window import MainWindow


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.board = [[None] * 15 for _ in range(15)]

    def test_center_full_board_and_cancellation(self):
        self.assertEqual(choose_move(self.board, Player.BLACK), Point(7, 7))
        full = [[Player.BLACK] * 15 for _ in range(15)]
        self.assertIsNone(choose_move(full, Player.WHITE))
        cancel = Event()
        cancel.set()
        self.assertIsNone(choose_move(self.board, Player.BLACK, cancel))

    def test_winning_and_blocking_all_directions_at_edges(self):
        for dx, dy, start in [(1, 0, (0, 0)), (0, 1, (0, 0)),
                              (1, 1, (0, 0)), (1, -1, (0, 14))]:
            for side in (Player.BLACK, Player.WHITE):
                with self.subTest(direction=(dx, dy), side=side):
                    board = [[None] * 15 for _ in range(15)]
                    x, y = start
                    for step in range(4):
                        board[x + dx * step][y + dy * step] = side
                    target = Point(x + dx * 4, y + dy * 4)
                    self.assertEqual(choose_move(board, side), target)
                    self.assertEqual(choose_move(board, side.opposite()), target)

    def test_own_win_before_block_and_no_input_mutation(self):
        for col in range(4):
            self.board[0][col] = Player.WHITE
            self.board[2][col] = Player.BLACK
        snapshot = [row[:] for row in self.board]
        self.assertEqual(choose_move(self.board, Player.WHITE), Point(0, 4))
        self.assertEqual(self.board, snapshot)

    def test_broken_four_defense_and_zero_budget_fallback(self):
        for col in (0, 1, 3, 4):
            self.board[0][col] = Player.BLACK
        self.assertEqual(choose_move(self.board, Player.WHITE, time_limit=0), Point(0, 2))

    def test_search_defends_open_three_and_preserves_snapshot(self):
        for col in (6, 7, 8):
            self.board[7][col] = Player.BLACK
        snapshot = [row[:] for row in self.board]
        move = choose_move(self.board, Player.WHITE, time_limit=2)
        self.assertIn(move, (Point(7, 5), Point(7, 9)))
        self.assertEqual(self.board, snapshot)

    def test_advantage_sign_symmetry_terminal_and_draw(self):
        self.assertEqual(advantage(self.board), 0)
        for col in range(4):
            self.board[7][col + 5] = Player.BLACK
        inverted = [[p.opposite() if p is not None else None for p in row] for row in self.board]
        self.assertGreater(advantage(self.board), 0)
        self.assertEqual(evaluate(inverted), -evaluate(self.board))
        self.assertEqual(advantage(inverted), -advantage(self.board))
        self.board[7][9] = Player.BLACK
        self.assertEqual(advantage(self.board), 100)
        self.assertIsNone(choose_move(self.board, Player.WHITE))
        inverted[7][9] = Player.WHITE
        self.assertEqual(advantage(inverted), -100)
        full = [[Player.BLACK if (r + 2*c) % 4 < 2 else Player.WHITE
                 for c in range(15)] for r in range(15)]
        self.assertEqual(advantage(full), 0)


class AIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(audio_enabled=False)
        self.window.start_game(GameMode.AI)
        self.window.show()
        self.app.processEvents()
        self.game = self.window.game_widget
        self.canvas = self.game.chess_board.piece_area
        self.model = self.canvas.play_game_controller.game_model

    def tearDown(self):
        self.window.close()
        QThreadPool.globalInstance().waitForDone(3000)
        self.window.deleteLater()
        self.app.processEvents()

    def click(self, row, col):
        QTest.mouseClick(self.canvas, Qt.MouseButton.LeftButton,
                         pos=QPoint(col * 36 + 18, row * 36 + 18))

    def test_real_worker_response_and_pair_undo(self):
        started = monotonic()
        self.click(7, 7)
        deadline = monotonic() + 4
        QTest.qWait(200)
        self.assertEqual(len(self.model.moves), 1)
        while self.game.search_kind is not None and monotonic() < deadline:
            QTest.qWait(10)
        self.assertGreaterEqual(monotonic() - started, 1.0)
        self.assertIsNone(self.game.search_task)
        self.assertEqual(len(self.model.moves), 2)
        self.assertEqual(self.model.current_player, Player.BLACK)
        self.assertEqual(self.model.game_mode, GameMode.AI)
        self.assertEqual(len(self.game.record_panel.chart.values), 3)
        self.game.toolbar.undo_button.click()
        self.assertEqual(self.model.moves, [])
        self.assertEqual(self.game.record_panel.chart.values, [0.0])
        self.assertEqual(self.model.current_player, Player.BLACK)

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_thinking_locks_human_and_undo_discards_old_result(self, pool):
        self.click(7, 7)
        task = self.game.search_task
        self.click(7, 8)
        self.assertEqual(len(self.model.moves), 1)
        self.game.toolbar.undo_button.click()
        self.assertTrue(task.cancel.is_set())
        self.game.on_search_finished(task.token, Point(7, 8), "")
        self.assertEqual(self.model.moves, [])
        self.assertEqual(self.model.evaluations, [0.0])

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_new_game_discards_old_result_and_preserves_mode(self, pool):
        self.click(7, 7)
        task, old_id = self.game.search_task, self.model.game_id
        self.game.toolbar.new_game_button.click()
        self.assertNotEqual(self.model.game_id, old_id)
        self.game.on_search_finished(task.token, Point(7, 8), "")
        self.assertEqual(self.model.moves, [])
        self.assertEqual(self.model.game_mode, GameMode.AI)
        self.assertEqual(self.game.record_panel.chart.values, [0.0])

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_return_to_menu_discards_old_result(self, pool):
        self.click(7, 7)
        task = self.game.search_task
        self.game.toolbar.back_button.click()
        self.assertTrue(task.cancel.is_set())
        self.window.start_game(GameMode.TWO_PLAYERS)
        self.game.on_search_finished(task.token, Point(7, 8), "")
        self.assertEqual(self.model.moves, [])

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_hint_marks_only_and_is_invalidated_by_move(self, pool):
        self.game.toolbar.hint_button.click()
        task = self.game.search_task
        self.game.on_search_finished(task.token, Point(7, 7), "")
        self.assertEqual(self.canvas.hint_point, Point(7, 7))
        self.assertEqual(self.model.moves, [])
        self.assertEqual(self.model.evaluations, [0.0])
        self.game.toolbar.hint_button.click()
        task = self.game.search_task
        self.click(6, 6)
        self.game.on_search_finished(task.token, Point(7, 7), "")
        self.assertIsNone(self.canvas.hint_point)
        self.assertEqual(len(self.model.moves), 1)

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_worker_error_can_retry(self, pool):
        self.click(7, 7)
        task = self.game.search_task
        self.game.on_search_finished(task.token, None, "test failure")
        self.assertEqual(self.game.toolbar.hint_button.text(), "重试")
        self.assertTrue(self.game.toolbar.hint_button.isEnabled())
        self.game.toolbar.hint_button.click()
        self.assertEqual(self.game.search_kind, "ai")
        self.assertNotEqual(self.game.search_token, task.token)

    def test_two_player_chart_undo_and_new_branch(self):
        self.window.start_game(GameMode.TWO_PLAYERS)
        game = self.window.game_widget
        canvas = game.chess_board.piece_area
        for point in (Point(7, 7), Point(6, 6), Point(7, 8)):
            canvas.place_stone(point)
        before = self.model.evaluations[:]
        self.assertEqual(len(before), 4)
        game.toolbar.undo_button.click()
        self.assertEqual(game.record_panel.chart.values, before[:-1])
        canvas.place_stone(Point(2, 2))
        self.assertEqual(len(game.record_panel.chart.values), 4)
        self.assertEqual(game.record_panel.chart.values[:-1], before[:-1])
        self.assertNotEqual(game.record_panel.chart.values[-1], before[-1])

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_ai_win_dialog_chart_and_play_again(self, pool):
        self.game.AI_DELAY_MS = 0
        for col in range(5):
            self.click(2, col * 2)
            token = self.game.search_task.token
            self.game.on_search_finished(token, Point(0, col), "")
        self.assertEqual(self.model.winner, Player.WHITE)
        self.assertEqual(self.game.toolbar.status_label.text(), "白方获胜")
        self.assertEqual(self.game.record_panel.chart.values[-1], -100)
        self.assertEqual(len(self.game.record_panel.chart.values), 11)
        self.assertIsNone(self.game.search_task)
        self.canvas.continue_button.click()
        self.assertEqual(self.model.game_mode, GameMode.AI)
        self.assertEqual(self.model.moves, [])
        self.assertEqual(self.game.record_panel.chart.values, [0.0])

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_ready_result_waits_and_cancels_on_undo_restart_or_exit(self, pool):
        for action in ("undo", "restart", "exit"):
            with self.subTest(action=action):
                self.click(7, 7)
                token = self.game.search_task.token
                self.game.on_search_finished(token, Point(7, 8), "")
                self.assertEqual(len(self.model.moves), 1)
                self.assertTrue(self.game.move_timer.isActive())
                self.assertFalse(self.game.toolbar.hint_button.isEnabled())
                self.click(7, 9)
                self.assertEqual(len(self.model.moves), 1)
                if action == "undo":
                    self.game.toolbar.undo_button.click()
                elif action == "restart":
                    self.game.toolbar.new_game_button.click()
                else:
                    self.game.toolbar.back_button.click()
                self.assertFalse(self.game.move_timer.isActive())
                self.assertIsNone(self.game.pending_move)
                QTest.qWait(1050)
                self.assertIsNone(self.model.board[7][8])
                if action != "exit":
                    self.assertEqual(self.model.moves, [])


if __name__ == "__main__":
    unittest.main()
