"""Heuristic board scores, always positive for Black and negative for White."""
import re
from functools import lru_cache

from tools.macros import Player

WIN_SCORE = 1_000_000
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))


def line_score(line, player):
    text = "2" + "".join("0" if p is None else "1" if p == player else "2" for p in line) + "2"
    return text_score(text)


@lru_cache(maxsize=50_000)
def text_score(text):
    score = 0
    for match in re.finditer(r"1+", text):
        length = len(match.group())
        if length >= 5:
            return WIN_SCORE
        openings = (text[match.start() - 1] == "0") + (text[match.end()] == "0")
        if openings:
            score += {
                4: (0, 10_000, 100_000), 3: (0, 500, 5_000),
                2: (0, 20, 200), 1: (0, 1, 2),
            }[length][openings]
    # Broken fours and open broken threes also create tactical threats.
    for start in range(len(text) - 4):
        window = text[start:start + 5]
        if window in ("11011", "10111", "11101"):
            score += 10_000
    for pattern in ("011010", "010110"):
        score += text.count(pattern) * 5_000
    return score


def lines(board):
    size = len(board)
    for dx, dy in DIRECTIONS:
        for x in range(size):
            for y in range(size):
                if 0 <= x - dx < size and 0 <= y - dy < size:
                    continue
                line = []
                a, b = x, y
                while 0 <= a < size and 0 <= b < size:
                    line.append(board[a][b])
                    a, b = a + dx, b + dy
                if len(line) >= 5:
                    yield line


def evaluate(board):
    black = white = 0
    for line in lines(board):
        b, w = line_score(line, Player.BLACK), line_score(line, Player.WHITE)
        if b >= WIN_SCORE:
            return WIN_SCORE
        if w >= WIN_SCORE:
            return -WIN_SCORE
        black += b
        white += w
    return max(-WIN_SCORE + 1, min(WIN_SCORE - 1, black - white))


def advantage(board):
    raw = evaluate(board)
    if abs(raw) == WIN_SCORE:
        return 100.0 if raw > 0 else -100.0
    if all(p is not None for row in board for p in row):
        return 0.0
    # A bounded heuristic index, not a win probability.
    return max(-99.0, min(99.0, 100 * raw / (abs(raw) + 5_000)))


def placement_score(board, x, y, player):
    """Score the four lines through a hypothetical stone without mutating board."""
    size = len(board)
    total = 0
    fours = threes = 0
    for dx, dy in DIRECTIONS:
        a, b = x, y
        while 0 <= a - dx < size and 0 <= b - dy < size:
            a, b = a - dx, b - dy
        line = []
        while 0 <= a < size and 0 <= b < size:
            line.append(player if (a, b) == (x, y) else board[a][b])
            a, b = a + dx, b + dy
        if len(line) >= 5:
            score = line_score(line, player)
            if score >= WIN_SCORE:
                return WIN_SCORE
            # Measure the new stone's contribution, not unrelated patterns on its line.
            # Recover the point's index from the line's start.
            start_x, start_y = x, y
            while 0 <= start_x - dx < size and 0 <= start_y - dy < size:
                start_x, start_y = start_x - dx, start_y - dy
            index = (x - start_x) if dx else (y - start_y)
            line[index] = None
            gain = max(0, score - line_score(line, player))
            total += gain
            fours += gain >= 10_000
            threes += 5_000 <= gain < 10_000
    if fours >= 2:
        total += 200_000
    elif fours and threes:
        total += 120_000
    elif threes >= 2:
        total += 30_000
    return total
