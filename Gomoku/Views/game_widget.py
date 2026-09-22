from PySide6.QtCore import Qt, QElapsedTimer, QThreadPool, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from views.chess_board_widget import ChessBoardWidget
from views.game_toolbar import GameToolbar
from views.record_panel import RecordPanel
from tools.macros import PLAYER_NAME, GameMode, Player
from tools.signals import nav_signal
from ai.worker import SearchTask
from ai.difficulty import DIFFICULTIES


class GameWidget(QWidget):
    AI_DELAY_MS = 1000

    def __init__(self, mode=GameMode.TWO_PLAYERS, difficulty="normal", api_key="", jev_model="jev-latest"):
        super().__init__()
        self.ai_difficulty = difficulty if difficulty in DIFFICULTIES else "normal"
        self.jev_api_key = api_key
        self.jev_model = jev_model
        self.active = True
        self.search_task = None
        self.search_token = 0
        self.search_kind = None
        self.search_key = None
        self.search_error = ""
        self.search_clock = QElapsedTimer()
        self.pending_move = None
        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)
        self.move_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.move_timer.timeout.connect(self.apply_pending_move)

        # 整体纵向布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = GameToolbar()
        main_layout.addWidget(self.toolbar)

        # Toolbar 下方的内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 0, 16, 0)
        content_layout.setSpacing(16)

        # 左侧棋盘区域
        board_area = QWidget()
        board_layout = QVBoxLayout(board_area)
        board_layout.setContentsMargins(0, 0, 0, 0)

        self.chess_board = ChessBoardWidget(mode)

        board_layout.addWidget(
            self.chess_board,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 右侧棋谱区域
        self.record_panel = RecordPanel()

        # 添加到横向布局
        content_layout.addWidget(board_area)
        content_layout.addWidget(self.record_panel, 1, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(content_widget)

        canvas = self.chess_board.piece_area
        canvas.game_changed.connect(self.on_game_changed)
        self.toolbar.new_game_button.clicked.connect(canvas.restart_game)
        self.toolbar.undo_button.clicked.connect(canvas.undo_move)
        self.toolbar.back_button.clicked.connect(nav_signal.nav_to_start_widget_signal.emit)
        self.toolbar.hint_button.clicked.connect(self.request_hint)
        self.refresh_game()

    def state_key(self):
        model = self.chess_board.piece_area.play_game_controller.game_model
        return model.game_id, model.revision, model.current_player

    def set_difficulty(self, difficulty, api_key="", jev_model="jev-latest"):
        if difficulty not in DIFFICULTIES or (difficulty, api_key, jev_model) == (self.ai_difficulty, self.jev_api_key, self.jev_model):
            return
        self.ai_difficulty = difficulty
        self.jev_api_key = api_key
        self.jev_model = jev_model
        kind = self.search_kind
        controller = self.chess_board.piece_area.play_game_controller
        if kind is None and controller.game_model.game_mode == GameMode.AI and controller.game_model.current_player == Player.WHITE and not controller.is_game_over():
            kind = "ai"
        self.cancel_search()
        self.chess_board.piece_area.hint_point = None
        self.chess_board.piece_area.update()
        self.refresh_game()
        if kind is not None and self.active:
            self.start_search(kind)

    def cancel_search(self):
        self.move_timer.stop()
        self.pending_move = None
        self.search_token += 1
        if self.search_task is not None:
            self.search_task.cancel.set()
        self.search_task = None
        self.search_kind = None

    def deactivate(self):
        self.active = False
        self.cancel_search()

    def on_game_changed(self):
        self.cancel_search()
        self.search_error = ""
        self.refresh_game()
        controller = self.chess_board.piece_area.play_game_controller
        model = controller.game_model
        if (self.active and model.game_mode == GameMode.AI
                and model.current_player == Player.WHITE and not controller.is_game_over()):
            self.start_search("ai")

    def request_hint(self):
        controller = self.chess_board.piece_area.play_game_controller
        if not self.active or self.search_kind is not None or controller.is_game_over():
            return
        model = controller.game_model
        kind = "ai" if model.game_mode == GameMode.AI and model.current_player == Player.WHITE else "hint"
        self.start_search(kind)

    def start_search(self, kind):
        self.cancel_search()
        self.search_kind = kind
        self.search_clock.start()
        self.search_key = self.state_key()
        self.search_error = ""
        model = self.chess_board.piece_area.play_game_controller.game_model
        task = SearchTask(self.search_token, model.board, model.current_player, self.ai_difficulty,
                          api_key=self.jev_api_key, model=self.jev_model)
        self.search_task = task
        task.signals.finished.connect(self.on_search_finished)
        self.refresh_game()
        QThreadPool.globalInstance().start(task)

    @Slot(int, object, str)
    def on_search_finished(self, token, point, error):
        if not self.active or token != self.search_token or self.search_key != self.state_key():
            return
        kind = self.search_kind
        self.search_task = None
        if error or point is None:
            self.search_kind = None
            self.search_error = error if self.ai_difficulty == "jev" and error else "计算失败，请重试"
            self.toolbar.hint_button.setToolTip(error or "未获得推荐落点")
            self.refresh_game()
            return
        canvas = self.chess_board.piece_area
        if kind == "ai":
            self.pending_move = (token, self.search_key, point)
            remaining = max(0, self.AI_DELAY_MS - self.search_clock.elapsed())
            if remaining:
                self.move_timer.start(remaining)
                self.refresh_game()
            else:
                self.apply_pending_move()
        else:
            self.search_kind = None
            canvas.hint_point = point
            canvas.update()
            self.refresh_game()

    def apply_pending_move(self):
        pending = self.pending_move
        self.pending_move = None
        if pending is None:
            return
        token, key, point = pending
        if not self.active or token != self.search_token or key != self.state_key():
            return
        self.search_kind = None
        self.chess_board.piece_area.place_stone(point)

    def refresh_game(self):
        controller = self.chess_board.piece_area.play_game_controller
        model = controller.game_model
        if model.winner is not None:
            status = f"{PLAYER_NAME[model.winner]}获胜"
        elif controller.is_board_full():
            status = "本局和棋"
        else:
            status = f"{PLAYER_NAME[model.current_player]}回合"
        if self.search_kind is not None:
            status = "AI 思考中…" if self.search_kind == "ai" else "正在分析推荐落点…"
            if self.ai_difficulty == "jev":
                status = "Jev 联网思考中…"
        elif self.search_error:
            status = self.search_error
        self.toolbar.status_label.setText(status)
        self.toolbar.undo_button.setEnabled(bool(model.moves))
        self.toolbar.hint_button.setEnabled(not controller.is_game_over() and self.search_kind is None)
        self.toolbar.hint_button.setText("重试" if self.search_error else "提示")
        self.record_panel.refresh(model.moves, model.evaluations)
