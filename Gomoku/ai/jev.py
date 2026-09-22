"""TypeSafe Choice API adapter. No implicit substitution with the local engine.

Protocol: https://docs.typesafe.ai/introduction/quickstart
"""
import json
import ssl
import certifi
from threading import Event
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from ai.engine import candidate_moves
from ai.evaluation import WIN_SCORE, evaluate, placement_score
from models.data_model import Point
from tools.macros import Player

ENDPOINT = "https://api.typesafe.ai/v1/systemone"


class JevError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_request(board, player, model):
    scored, wins, blocks = [], [], []
    for x, y in candidate_moves(board):
        attack = placement_score(board, x, y, player)
        defense = placement_score(board, x, y, player.opposite())
        if attack >= WIN_SCORE:
            wins.append((x, y))
        if defense >= WIN_SCORE:
            blocks.append((x, y))
        scored.append((attack + defense * 1.1, x, y))
    candidates = wins or blocks or [(x, y) for _, x, y in sorted(scored, reverse=True)[:24]]
    options = {f"r{x}_c{y}": Point(x, y) for x, y in candidates}
    state = {
        "game": "Gomoku, 15x15, five or more in a row wins, no forbidden moves",
        "coordinates": "zero-based row and column; row 0 is top; column 0 is left",
        "to_move": "black" if player == Player.BLACK else "white",
        "legend": {"B": "black", "W": "white", ".": "empty"},
        "board": ["".join("." if p is None else "B" if p == Player.BLACK else "W" for p in row) for row in board],
    }
    criteria = {name: f"Place at row {p.x}, column {p.y}."
                for name, p in options.items()}
    payload = {
        "model": model,
        "state": json.dumps(state, ensure_ascii=False),
        "questions": {"move": {
            "type": "choice",
            "instructions": "Choose the best legal move for to_move. Win immediately if possible, prevent an immediate loss, then build forcing threats and defend against forks.",
            "criteria": criteria,
        }},
    }
    return payload, options


def choose_jev_move(board, player, api_key, model="jev-latest", cancel=None):
    cancel = cancel or Event()
    if cancel.is_set() or abs(evaluate(board)) == WIN_SCORE:
        return None
    if not api_key.strip():
        raise JevError("请在设置 → Jev API 中填写 API Key")
    payload, options = build_request(board, player, model)
    if not options or cancel.is_set():
        return None
    request = Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json",
    }, method="POST")
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=certifi.where())
        with build_opener(NoRedirect(), HTTPSHandler(context=context)).open(request, timeout=12) as response:
            raw = response.read(1_048_577)
            if len(raw) > 1_048_576:
                raise JevError("Jev 响应过大，请重试")
        if cancel.is_set():
            return None
        result = json.loads(raw)
        answer = result["answers"]["move"]
        choice = answer["choice"]
        if answer.get("type") != "choice" or not isinstance(choice, str) or choice not in options:
            raise JevError("Jev 返回的落点无效，请重试")
        point = options[choice]
        if board[point.x][point.y] is not None:
            raise JevError("Jev 返回的位置已有棋子")
        return point
    except HTTPError as error:
        if cancel.is_set():
            return None
        message = {401: "API Key 无效", 403: "无访问权限", 429: "请求过于频繁或额度不足"}.get(error.code, f"服务返回 HTTP {error.code}")
        raise JevError(f"Jev：{message}") from None
    except URLError as error:
        if cancel.is_set():
            return None
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            raise JevError("Jev TLS 证书校验失败，请检查证书或网络代理") from None
        raise JevError("Jev 连接失败或超时，请重试") from None
    except (TimeoutError, OSError):
        if cancel.is_set():
            return None
        raise JevError("Jev 连接失败或超时，请重试") from None
    except (ValueError, KeyError, TypeError):
        raise JevError("Jev 响应格式不正确，请重试") from None
