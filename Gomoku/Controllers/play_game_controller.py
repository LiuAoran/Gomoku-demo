from Tools import macros
from Tools.macros import GameMode, Player
from Models import data_model

class PlayGameController:
    _instance = None
    current_player: Player

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlayGameController, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self.game_model = data_model.GameModel()
        self.current_player = data_model.Player.BLACK

        self._initialized = True

    def play_new_game(self, game_mode: macros.GameMode):
        self.game_model.init_new_game(game_mode)

    def is_exist_stone(self, point: data_model.Point) -> bool:
        return self.game_model.board[point.x][point.y] is not None

    def place_stone(self, point: data_model.Point):
        if self.is_exist_stone(point):
            return
        self.game_model.board[point.x][point.y] = self.current_player
        self.record_history(point)
        self.current_player = self.current_player.opposite()

    def record_history(self, point: data_model.Point):
        self.game_model.moves.append(
            data_model.Move(
                point=point,
                player=self.current_player,
                step=len(self.game_model.moves) + 1
            )
        )


