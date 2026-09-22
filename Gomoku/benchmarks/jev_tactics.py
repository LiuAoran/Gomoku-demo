"""Small reproducible tactical probe, not an Elo or full-game strength benchmark.

Run from project root:
  PYTHONPATH=. .venv/bin/python benchmarks/jev_tactics.py --live
Uses the local .env key, makes 16 paid requests, never logs credentials.
"""
import argparse
import json
from pathlib import Path
import ssl
from time import monotonic
from urllib.request import Request, HTTPSHandler, build_opener
from urllib.error import HTTPError, URLError

import certifi
from ai.engine import candidate_moves, choose_move
from ai.evaluation import evaluate, WIN_SCORE
from ai.jev import ENDPOINT, NoRedirect, build_request
from tools.credentials import load_jev_key
from tools.macros import Player

FILL = [(0, 0), (0, 5), (0, 10), (3, 2), (3, 11), (12, 12)]
CASES = [
    ('win_four', '一步成五', [(7, c) for c in (4, 5, 6, 7)], [(7, 3)] + FILL[:3], Player.BLACK, [(7, 8)]),
    ('block_four', '阻挡一步成五', [(7, c) for c in (4, 5, 6, 7)], [(7, 3)] + FILL[:2], Player.WHITE, [(7, 8)]),
    ('win_broken_four', '补跳四取胜', [(7, c) for c in (4, 5, 7, 8)], FILL[:4], Player.BLACK, [(7, 6)]),
    ('block_diagonal_four', '阻挡斜向跳四', [(i, i) for i in (4, 5, 7, 8)], FILL[:3], Player.WHITE, [(6, 6)]),
    ('create_open_four', '活三形成活四', [(7, c) for c in (5, 6, 7)], FILL[:3], Player.BLACK, [(7, 4), (7, 8)]),
    ('defend_open_three', '阻止对手形成活四', [(7, c) for c in (5, 6, 7)], FILL[:2], Player.WHITE, [(7, 4), (7, 8)]),
    ('create_double_four', '制造双四', [(7, 5), (7, 6), (7, 8), (5, 7), (6, 7), (8, 7)], FILL[:6], Player.BLACK, [(7, 7)]),
    ('defend_double_four', '阻止对手制造双四', [(7, 5), (7, 6), (7, 8), (5, 7), (6, 7), (8, 7)], FILL[:5], Player.WHITE, [(7, 7)]),
]


def make_board(case):
    _, _, blacks, whites, player, expected = case
    board = [[None] * 15 for _ in range(15)]
    for points, side in ((blacks, Player.BLACK), (whites, Player.WHITE)):
        for x, y in points:
            assert board[x][y] is None
            board[x][y] = side
    assert len(blacks) == len(whites) + (player == Player.WHITE)
    assert abs(evaluate(board)) != WIN_SCORE
    assert all(board[x][y] is None for x, y in expected)
    return board


def call_api(payload, key):
    context = ssl.create_default_context()
    context.load_verify_locations(certifi.where())
    request = Request(ENDPOINT, data=json.dumps(payload).encode(), headers={
        'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, method='POST')
    start = monotonic()
    try:
        with build_opener(NoRedirect(), HTTPSHandler(context=context)).open(request, timeout=15) as response:
            result = json.loads(response.read(1_048_576))
        answer = result['answers']['move']
        return {'answer': answer, 'model': result.get('model'), 'usage': result.get('usage'),
                'seconds': round(monotonic() - start, 3)}
    except HTTPError as error:
        return {'error': f'HTTP {error.code}'}
    except (URLError, OSError, ValueError, KeyError, TypeError):
        return {'error': 'connection or response failure'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', default='benchmarks/jev_tactics_results.json')
    args = parser.parse_args()
    if not args.live:
        print('Prepared 8 cases: 8 current-pipeline + 4 unfiltered controls + 4 deeper-case repeats = 16 API calls. Use --live to run.')
        return
    key = load_jev_key()
    if not key:
        raise SystemExit('No TypeSafe key configured')
    report = {'scope': '8 curated tactical positions; not full games or a strength rating', 'cases': [], 'runs': []}
    for case in CASES:
        board = make_board(case)
        start = monotonic()
        local = choose_move(board, case[4], difficulty='hard')
        report['cases'].append({'id': case[0], 'name': case[1], 'black': case[2], 'white': case[3],
                                'to_move': case[4].name, 'expected': case[5],
                                'local_hard': [local.x, local.y], 'local_pass': (local.x, local.y) in case[5],
                                'local_seconds': round(monotonic()-start, 3)})
        print(json.dumps({'case': case[0], 'local_pass': report['cases'][-1]['local_pass']}), flush=True)
    tasks = [(case, 'current', 1) for case in CASES]
    tasks += [(case, 'unfiltered', 1) for case in CASES[:4]]
    tasks += [(case, 'current', 2) for case in CASES[4:]]
    for case, mode, repetition in tasks:
        board = make_board(case)
        payload, options = build_request(board, case[4], 'jev-latest')
        if mode == 'unfiltered':
            options = {f'r{x}_c{y}': (x, y) for x, y in candidate_moves(board)}
            payload['questions']['move']['criteria'] = {name: f'Place at row {x}, column {y}.' for name, (x, y) in options.items()}
        answer = call_api(payload, key)
        choice = answer.get('answer', {}).get('choice')
        point = options.get(choice) if isinstance(choice, str) else None
        if point is not None and not isinstance(point, tuple):
            point = (point.x, point.y)
        expected_keys = [f'r{x}_c{y}' for x, y in case[5]]
        run = {'case': case[0], 'mode': mode, 'repetition': repetition,
               'option_count': len(options), 'expected_in_options': [k for k in expected_keys if k in options],
               'selected': point, 'legal': point is not None, 'pass': point in case[5], **answer}
        report['runs'].append(run)
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in run.items() if k not in ('answer', 'usage')}, ensure_ascii=False), flush=True)
    print('Report:', args.output, flush=True)


if __name__ == '__main__':
    main()
