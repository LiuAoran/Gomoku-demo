"""Time-bounded iterative deepening with incremental evaluation and threat extensions."""
from threading import Event
from time import monotonic

from ai.difficulty import get_difficulty
from ai.evaluation import DIRECTIONS, WIN_SCORE, evaluate, line_score, placement_score
from models.data_model import Point
from tools.macros import Player


class SearchStopped(Exception):
    pass


def candidate_moves(board):
    size = len(board)
    occupied = [(x, y) for x in range(size) for y in range(size) if board[x][y] is not None]
    if not occupied:
        return [(size // 2, size // 2)]
    return sorted({
        (a, b) for x, y in occupied
        for a in range(max(0, x - 2), min(size, x + 3))
        for b in range(max(0, y - 2), min(size, y + 3))
        if board[a][b] is None
    })


class Position:
    """Only rescore the four lines touched by a move."""
    def __init__(self, board):
        self.board = [row[:] for row in board]
        self.paths = []
        self.at = {(x, y): [] for x in range(len(board)) for y in range(len(board))}
        size = len(board)
        for dx, dy in DIRECTIONS:
            for x, y in self.at:
                if 0 <= x - dx < size and 0 <= y - dy < size:
                    continue
                path = []
                a, b = x, y
                while 0 <= a < size and 0 <= b < size:
                    path.append((a, b))
                    a, b = a + dx, b + dy
                if len(path) >= 5:
                    for point in path:
                        self.at[point].append(len(self.paths))
                    self.paths.append(path)
        self.scores = [self.score_line(index) for index in range(len(self.paths))]
        self.total = sum(b - w for b, w in self.scores)

    def score_line(self, index):
        line = [self.board[x][y] for x, y in self.paths[index]]
        return line_score(line, Player.BLACK), line_score(line, Player.WHITE)

    def push(self, point, side):
        x, y = point
        previous = [(index, self.scores[index]) for index in self.at[point]]
        self.board[x][y] = side
        for index, (black, white) in previous:
            b, w = self.score_line(index)
            self.scores[index] = (b, w)
            self.total += b - w - black + white
        return previous

    def pop(self, point, previous):
        self.board[point[0]][point[1]] = None
        for index, (black, white) in previous:
            b, w = self.scores[index]
            self.total += black - white - b + w
            self.scores[index] = (black, white)

    def value(self):
        for b, w in self.scores:
            if b >= WIN_SCORE:
                return WIN_SCORE
            if w >= WIN_SCORE:
                return -WIN_SCORE
        return max(-WIN_SCORE + 1, min(WIN_SCORE - 1, self.total))


def choose_move(board, player, cancel=None, time_limit=None, depth=None,
                difficulty="normal", stats=None):
    if difficulty == "jev":
        raise ValueError("Jev 必须通过 API 调用")
    profile = get_difficulty(difficulty)
    depth = max(1, profile.depth if depth is None else depth)
    time_limit = profile.seconds if time_limit is None else time_limit
    cancel = cancel or Event()
    if cancel.is_set() or abs(evaluate(board)) == WIN_SCORE:
        return None
    deadline = monotonic() + time_limit
    position = Position(board)
    board = position.board
    order_cache = {}
    completed_depth = nodes = 0

    def check_stop(timed=True):
        if cancel.is_set() or (timed and monotonic() >= deadline):
            raise SearchStopped

    def ordered(side, timed=True):
        key = (side, tuple(tuple(row) for row in board))
        if key in order_cache:
            return order_cache[key]
        wins, blocks, scored = [], [], []
        center = len(board) // 2
        for x, y in candidate_moves(board):
            check_stop(timed)
            attack = placement_score(board, x, y, side)
            defense = placement_score(board, x, y, side.opposite())
            if attack >= WIN_SCORE:
                wins.append((x, y))
            if defense >= WIN_SCORE:
                blocks.append((x, y))
            scored.append((attack + defense * 1.1, -abs(x - center) - abs(y - center), x, y))
        result = (wins or blocks or [(x, y) for _, _, x, y in sorted(scored, reverse=True)[:profile.candidates]],
                  bool(wins or blocks))
        order_cache[key] = result
        return result

    def search(side, remaining, alpha, beta, ply, extensions):
        nonlocal nodes
        nodes += 1
        check_stop()
        value = position.value()
        relative = value if side == Player.BLACK else -value
        if abs(value) == WIN_SCORE:
            return relative - ply if relative > 0 else relative + ply
        if remaining <= 0 and extensions <= 0:
            return relative
        moves, forced = ordered(side)
        if not moves:
            return 0
        if remaining <= 0:
            if not forced:
                return relative
            extensions -= 1
        best = -float("inf")
        for point in moves:
            previous = position.push(point, side)
            try:
                value = -search(side.opposite(), remaining - 1, -beta, -alpha, ply + 1, extensions)
            finally:
                position.pop(point, previous)
            best, alpha = max(best, value), max(alpha, value)
            if alpha >= beta:
                break
        return best

    try:
        # Never skip an immediate win or block because the ordinary search timed out.
        moves, _ = ordered(player, timed=False)
        if not moves:
            return None
        best_move = moves[0]
        for limit in range(1, depth + 1):
            iteration_move = best_move
            best_value = -float("inf")
            alpha = -float("inf")
            root_moves = [best_move] + [point for point in moves if point != best_move]
            for point in root_moves:
                check_stop()
                previous = position.push(point, player)
                try:
                    value = -search(player.opposite(), limit - 1, -float("inf"), -alpha,
                                    1, 2 if difficulty == "hard" else 0)
                finally:
                    position.pop(point, previous)
                if value > best_value:
                    best_value, iteration_move = value, point
                alpha = max(alpha, value)
            # Only adopt a fully completed iteration, not a partially searched root.
            best_move, completed_depth = iteration_move, limit
            if best_value >= WIN_SCORE - 20:
                break
    except SearchStopped:
        if cancel.is_set():
            return None
    if stats is not None:
        stats.update(completed_depth=completed_depth, nodes=nodes)
    return Point(*best_move)
