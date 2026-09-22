import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from controllers.play_game_controller import PlayGameController
from models.data_model import Point
from tools.macros import Const, GameMode, PlaceResult, Player
from views.chess_piece_canvas import ChessPieceCanvas
from views.main_window import MainWindow
from views.start_widget import StartWidget


def almost_draw(controller):
    # Each direction alternates before reaching five consecutive stones.
    controller.game_model.board = [
        [Player.BLACK if (row + 2 * col) % 4 < 2 else Player.WHITE
         for col in range(Const.BOARD_SIZE)]
        for row in range(Const.BOARD_SIZE)
    ]
    controller.game_model.current_player = controller.game_model.board[14][14]
    controller.game_model.board[14][14] = None


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = PlayGameController()
        self.controller.play_new_game(GameMode.TWO_PLAYERS)

    def test_invalid_moves_preserve_state(self):
        controller = self.controller
        for x, y in [(-1, 0), (0, -1), (15, 0), (0, 15)]:
            self.assertEqual(controller.place_stone(Point(x, y)), PlaceResult.INVALID)
            self.assertFalse(controller.check_winner(Point(x, y)))
        self.assertFalse(controller.check_winner(Point(0, 0)))
        self.assertEqual(controller.game_model.moves, [])
        self.assertEqual(controller.game_model.current_player, Player.BLACK)
        self.assertEqual(controller.place_stone(Point(0, 0)), PlaceResult.PLAYING)
        self.assertEqual(controller.place_stone(Point(0, 0)), PlaceResult.INVALID)
        self.assertEqual(len(controller.game_model.moves), 1)
        self.assertEqual(controller.game_model.current_player, Player.WHITE)

    def test_four_winning_directions_and_end_lock(self):
        controller = self.controller
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            with self.subTest(direction=(dx, dy)):
                controller.play_new_game(GameMode.TWO_PLAYERS)
                for offset in [-2, -1, 1, 2]:
                    controller.game_model.board[7 + offset * dx][7 + offset * dy] = Player.BLACK
                self.assertEqual(controller.place_stone(Point(7, 7)), PlaceResult.WIN)
                self.assertEqual(controller.game_model.winner, Player.BLACK)
                self.assertEqual(controller.place_stone(Point(0, 0)), PlaceResult.INVALID)
                self.assertIsNone(controller.game_model.board[0][0])
                self.assertEqual(len(controller.game_model.moves), 1)

    def test_draw_and_restart(self):
        controller = self.controller
        almost_draw(controller)
        for row in range(15):
            for col in range(15):
                self.assertFalse(controller.check_winner(Point(row, col)))
        self.assertEqual(controller.place_stone(Point(14, 14)), PlaceResult.DRAW)
        self.assertTrue(controller.is_game_over())
        self.assertIsNone(controller.game_model.winner)
        self.assertEqual(controller.place_stone(Point(0, 0)), PlaceResult.INVALID)
        controller.play_new_game(GameMode.TWO_PLAYERS)
        self.assertFalse(controller.is_game_over())
        self.assertEqual(controller.game_model.moves, [])
        self.assertEqual(controller.place_stone(Point(0, 0)), PlaceResult.PLAYING)

    def test_last_cell_win_takes_priority_over_draw(self):
        controller = self.controller
        almost_draw(controller)
        controller.game_model.current_player = Player.BLACK
        for col in range(10, 14):
            controller.game_model.board[14][col] = Player.BLACK
        self.assertEqual(controller.place_stone(Point(14, 14)), PlaceResult.WIN)

    def test_undo_empty_board_and_reuse_move_number(self):
        controller = self.controller
        self.assertFalse(controller.undo_move())
        controller.place_stone(Point(0, 0))
        controller.place_stone(Point(0, 1))
        self.assertTrue(controller.undo_move())
        self.assertIsNone(controller.game_model.board[0][1])
        self.assertEqual(controller.game_model.current_player, Player.WHITE)
        controller.place_stone(Point(1, 1))
        self.assertEqual([move.step for move in controller.game_model.moves], [1, 2])


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.canvas = ChessPieceCanvas()
        self.canvas.show()
        self.app.processEvents()
        self.controller = self.canvas.play_game_controller

    def tearDown(self):
        self.canvas.close()
        self.canvas.deleteLater()
        self.app.processEvents()

    def click(self, row, col):
        QTest.mouseClick(
            self.canvas, Qt.MouseButton.LeftButton,
            pos=QPoint(int(col * Const.CELL_SIZE + Const.OFFSET_SIZE),
                       int(row * Const.CELL_SIZE + Const.OFFSET_SIZE)),
        )
        self.app.processEvents()

    def test_click_without_hover_renders_and_clears_hover(self):
        self.click(0, 0)
        self.assertEqual(self.controller.game_model.board[0][0], Player.BLACK)
        self.assertFalse(self.canvas.can_place)
        self.assertEqual((self.canvas.hover_row, self.canvas.hover_col), (-1, -1))
        pixmap = self.canvas.grab()
        center = int(Const.OFFSET_SIZE * pixmap.devicePixelRatio())
        self.assertEqual(pixmap.toImage().pixelColor(center, center).name(), "#000000")
        self.click(0, 0)
        self.assertEqual(len(self.controller.game_model.moves), 1)
        self.click(0, 1)
        self.assertEqual(self.controller.game_model.board[0][1], Player.WHITE)

    def test_win_dialog_restart_and_lock_after_dismissal(self):
        for col in range(4):
            self.controller.game_model.board[0][col] = Player.BLACK
        self.click(0, 4)
        self.assertEqual(self.canvas.msg_box.text(), "黑方获胜！")
        self.canvas.msg_box.reject()
        self.click(1, 0)
        self.assertIsNone(self.controller.game_model.board[1][0])
        self.assertFalse(self.canvas.can_place)
        self.canvas.restart_game()
        self.click(1, 0)
        self.assertEqual(self.controller.game_model.board[1][0], Player.BLACK)

    def test_draw_dialog_and_play_again(self):
        almost_draw(self.controller)
        self.click(14, 14)
        self.assertEqual(self.canvas.msg_box.text(), "棋盘已满，本局和棋！")
        self.canvas.continue_button.click()
        self.app.processEvents()
        self.assertFalse(self.controller.is_game_over())
        self.assertEqual(self.controller.game_model.moves, [])
        self.assertFalse(self.canvas.can_place)


class GameWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(audio_enabled=False)
        self.window.start_game(GameMode.TWO_PLAYERS)
        self.window.show()
        self.app.processEvents()
        self.game = self.window.game_widget
        self.canvas = self.game.chess_board.piece_area
        self.controller = self.canvas.play_game_controller
        self.table = self.game.record_panel.table

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def click(self, row, col):
        QTest.mouseClick(
            self.canvas, Qt.MouseButton.LeftButton,
            pos=QPoint(int(col * Const.CELL_SIZE + Const.OFFSET_SIZE),
                       int(row * Const.CELL_SIZE + Const.OFFSET_SIZE)),
        )
        self.app.processEvents()

    def test_record_coordinates_turn_undo_and_new_game(self):
        self.assertFalse(self.game.toolbar.undo_button.isEnabled())
        self.click(0, 0)
        self.assertEqual(self.game.toolbar.status_label.text(), "白方回合")
        self.assertEqual([self.table.item(0, col).text() for col in range(3)],
                         ["1", "黑方", "O1"])
        self.click(14, 14)
        self.assertEqual(self.table.item(1, 2).text(), "A15")
        self.game.toolbar.undo_button.click()
        self.assertEqual(self.table.rowCount(), 1)
        self.assertEqual(self.game.toolbar.status_label.text(), "白方回合")
        self.assertIsNone(self.controller.game_model.board[14][14])
        self.click(7, 7)
        self.assertEqual([self.table.item(1, col).text() for col in range(3)],
                         ["2", "白方", "H8"])
        self.game.toolbar.new_game_button.click()
        self.assertEqual(self.table.rowCount(), 0)
        self.assertEqual(self.game.toolbar.status_label.text(), "黑方回合")
        self.assertFalse(self.game.toolbar.undo_button.isEnabled())
        self.assertTrue(self.game.record_panel.empty_label.isVisible())
        self.assertFalse(self.canvas.can_place)

    def test_win_status_and_undo_resumes_play(self):
        for col in range(4):
            self.click(0, col)
            self.click(1, col)
        self.click(0, 4)
        self.assertEqual(self.game.toolbar.status_label.text(), "黑方获胜")
        self.assertEqual(self.table.rowCount(), 9)
        self.canvas.msg_box.reject()
        self.game.toolbar.undo_button.click()
        self.assertEqual(self.game.toolbar.status_label.text(), "黑方回合")
        self.assertEqual(self.table.rowCount(), 8)
        self.assertFalse(self.controller.is_game_over())
        self.click(2, 4)
        self.assertEqual(self.game.toolbar.status_label.text(), "白方回合")

    def test_draw_status_undo_and_dialog_restart_sync(self):
        almost_draw(self.controller)
        self.click(14, 14)
        self.assertEqual(self.game.toolbar.status_label.text(), "本局和棋")
        self.canvas.msg_box.reject()
        self.game.toolbar.undo_button.click()
        self.assertFalse(self.controller.is_game_over())
        self.assertEqual(self.game.toolbar.status_label.text(), "白方回合")
        self.click(14, 14)
        self.canvas.continue_button.click()
        self.assertEqual(self.table.rowCount(), 0)
        self.assertEqual(self.game.toolbar.status_label.text(), "黑方回合")

    def test_back_to_menu_and_reenter_starts_fresh(self):
        self.click(0, 0)
        self.game.toolbar.back_button.click()
        self.assertIsInstance(self.window.centralWidget(), StartWidget)
        self.window.start_widget.start_game_signal.emit(GameMode.TWO_PLAYERS)
        game = self.window.game_widget
        self.assertEqual(game.record_panel.table.rowCount(), 0)
        self.assertEqual(game.toolbar.status_label.text(), "黑方回合")
        self.assertFalse(game.toolbar.undo_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
