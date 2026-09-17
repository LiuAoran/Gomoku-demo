from enum import Enum

class GameMode(Enum):
    AI = "ai"
    TWO_PLAYERS = "two_players"

class Const:
    CELL_SIZE = 36
    BOARD_SIZE = 15
    OFFSET_SIZE = CELL_SIZE / 2