from uuid import uuid4
from dataclasses import dataclass, field

from tools.macros import Player, GameMode

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
    revision: int = 0
    evaluations: list[float] = field(default_factory=lambda: [0.0])

    def init_new_game(self, game_mode: GameMode):
        self.game_mode = game_mode
        self.winner = None
        self.current_player = Player.BLACK
        self.game_id = uuid4().hex
        self.revision += 1
        self.evaluations = [0.0]
        self.moves = []
        self.board = [[None] * 15 for _ in range(15)]

