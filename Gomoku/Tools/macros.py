from enum import Enum

class GameMode(Enum):
    AI = 0
    TWO_PLAYERS = 1

class Player(Enum):
    BLACK = 0
    WHITE = 1
    def opposite(self):
        return Player.BLACK if self == Player.WHITE else Player.WHITE

class PlaceResult(Enum):
    INVALID = 0      # 不能落子
    PLAYING = 1     # 落子成功，游戏继续
    WIN = 2           # 获胜
    DRAW = 3          # 和棋

PLAYER_NAME = {
    Player.BLACK: "黑方",
    Player.WHITE: "白方",
}

class Const:
    CELL_SIZE = 36
    BOARD_SIZE = 15
    OFFSET_SIZE = CELL_SIZE / 2