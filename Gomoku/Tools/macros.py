from enum import Enum

class GameMode(Enum):
    AI = 0
    TWO_PLAYERS = 1

class Player(Enum):
    BLACK = 0
    WHITE = 1
    def opposite(self):
        return Player.BLACK if self == Player.WHITE else Player.WHITE

class Const:
    CELL_SIZE = 36
    BOARD_SIZE = 15
    OFFSET_SIZE = CELL_SIZE / 2