from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    label: str
    depth: int
    candidates: int
    seconds: float
    description: str


DIFFICULTIES = {
    "easy": Difficulty("简单", 1, 6, 0.25, "适合入门：判断当前攻防，优先取胜与挡五。"),
    "normal": Difficulty("普通", 2, 10, 0.8, "考虑对手的回应，兼顾进攻与防守。"),
    "hard": Difficulty("困难", 4, 14, 2.5, "更深入搜索，重点防范双重威胁；复杂局面可能思考约 2.5 秒。"),
    "jev": Difficulty("Jev · 联网", 0, 24, 12, "通过 TypeSafe API 选择落点，需要 API Key；棋力待实测。"),
}


def get_difficulty(key):
    return DIFFICULTIES.get(key, DIFFICULTIES["normal"])
