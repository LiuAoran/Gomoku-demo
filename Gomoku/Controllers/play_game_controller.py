from Tools import macros
from Tools.macros import GameMode, Player,PlaceResult
from Models import data_model

class PlayGameController:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlayGameController, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self.game_model = data_model.GameModel()

        self._initialized = True

    def play_new_game(self, game_mode: macros.GameMode):
        self.game_model.init_new_game(game_mode)

    def is_exist_stone(self, point: data_model.Point) -> bool:
        return self.game_model.board[point.x][point.y] is not None

    def place_stone(self, point: data_model.Point):
        if self.is_exist_stone(point):
            return PlaceResult.INVALID
        self.game_model.board[point.x][point.y] = self.game_model.current_player
        self.record_history(point)

        if self.check_winner(point):
            self.game_model.winner = self.game_model.current_player
            return PlaceResult.WIN

        self.game_model.current_player = self.game_model.current_player.opposite()
        return PlaceResult.PLAYING

    def _is_same_stone(self, x: int, y: int, player: Player | None) -> bool:
        board = self.game_model.board

        if not (0 <= x < len(board)):
            return False

        if not (0 <= y < len(board[x])):
            return False

        return board[x][y] == player

    def check_winner(self, point: data_model.Point) -> bool:
        player = self.game_model.board[point.x][point.y]

        directions = [
            (1, 0),  # 横向
            (0, 1),  # 纵向
            (1, 1),  # /
            (1, -1),  # \
        ]

        for dx, dy in directions:
            count = 1

            # 正方向
            x, y = point.x + dx, point.y + dy
            while self._is_same_stone(x, y, player):
                count += 1
                x += dx
                y += dy

            # 反方向
            x, y = point.x - dx, point.y - dy
            while self._is_same_stone(x, y, player):
                count += 1
                x -= dx
                y -= dy

            if count >= 5:
                return True

        return False


    def record_history(self, point: data_model.Point):
        self.game_model.moves.append(
            data_model.Move(
                point=point,
                player=self.game_model.current_player,
                step=len(self.game_model.moves) + 1
            )
        )


