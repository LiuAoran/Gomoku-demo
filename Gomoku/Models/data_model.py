from ast import List
from dataclasses import dataclass, field

from Tools.macros import Player, GameMode

@dataclass
class Point:
    x: int = -1
    y: int = -1
    def __init__(self, x, y):
        self.x = x
        self.y = y

@dataclass
class Move:
    point: Point | None
    player: Player | None
    step: int = 0

@dataclass
class GameModel:
    game_id: str = ""
    current_player: Player = Player.BLACK
    moves: list[Move] = field(default_factory=list)
    board:  list[list[Player | None]] = field(
            default_factory=lambda: [
                [None] * 15 for _ in range(15)
            ]
        )
    game_mode: GameMode | None =field(default=None)
    winner: Player | None = None

    def init_new_game(self, game_mode: GameMode):
        self.game_mode = game_mode
        self.winner = None
        self.game_id = ""
        self.moves = []
        self.board = [[None] * 15 for _ in range(15)]


