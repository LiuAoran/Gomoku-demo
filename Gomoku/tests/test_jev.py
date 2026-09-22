import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
import json
import ssl
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from PySide6.QtWidgets import QApplication

from ai.jev import ENDPOINT, JevError, build_request, choose_jev_move
from ai.worker import SearchTask
from models.data_model import Point
from tools.macros import GameMode, Player
from tools.settings import SettingsStore
from views.main_window import MainWindow
from views.settings_dialog import SettingsDialog


class JevTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.board = [[None] * 15 for _ in range(15)]
        self.board[7][7] = Player.BLACK

    @patch("ai.jev.build_opener")
    def test_valid_choice_request_and_snapshot_preserved(self, opener):
        body, options = build_request(self.board, Player.WHITE, "jev-latest")
        key = next(iter(options))
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"answers": {"move": {"type": "choice", "choice": key}}}).encode()
        before = [row[:] for row in self.board]
        result = choose_jev_move(self.board, Player.WHITE, "test-key")
        self.assertEqual(result, options[key])
        self.assertEqual(self.board, before)
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        sent = json.loads(request.data)
        self.assertEqual(sent["questions"]["move"]["type"], "choice")
        self.assertNotIn("r7_c7", sent["questions"]["move"]["criteria"])
        self.assertEqual(json.loads(sent["state"])["to_move"], "white")
        self.assertNotIn("test-key", request.data.decode())
        context = opener.call_args.args[1]._context
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    @patch("ai.jev.build_opener")
    def test_malformed_and_illegal_choices_are_rejected(self, opener):
        response = opener.return_value.open.return_value.__enter__.return_value
        for raw in (b"not json", b"{}", b'{"answers":{"move":{"type":"choice","choice":"r7_c7"}}}',
                    b'{"answers":{"move":{"type":"score","choice":"r0_c0"}}}'):
            response.read.return_value = raw
            with self.assertRaises(JevError):
                choose_jev_move(self.board, Player.WHITE, "test-key")

    @patch("ai.jev.build_opener")
    def test_missing_key_cancellation_and_network_failures(self, opener):
        with self.assertRaisesRegex(JevError, "API Key"):
            choose_jev_move(self.board, Player.WHITE, "")
        opener.assert_not_called()
        cancel = Event()
        cancel.set()
        self.assertIsNone(choose_jev_move(self.board, Player.WHITE, "key", cancel=cancel))
        opener.assert_not_called()
        for error in (HTTPError(ENDPOINT, 401, "secret-key", {}, None),
                      HTTPError(ENDPOINT, 429, "secret-key", {}, None), URLError("secret-key"),
                      URLError(ssl.SSLCertVerificationError("secret-key")), TimeoutError()):
            opener.return_value.open.side_effect = error
            with self.assertRaises(JevError) as caught:
                choose_jev_move(self.board, Player.WHITE, "secret-key")
            self.assertNotIn("secret-key", str(caught.exception))

    @patch("ai.jev.build_opener")
    def test_result_arriving_after_cancel_is_discarded(self, opener):
        cancel = Event()
        def read(_):
            cancel.set()
            return b'{"answers":{"move":{"type":"choice","choice":"r7_c8"}}}'
        opener.return_value.open.return_value.__enter__.return_value.read.side_effect = read
        self.assertIsNone(choose_jev_move(self.board, Player.WHITE, "key", cancel=cancel))

    def test_candidate_rules_prioritize_win_and_block(self):
        for col in range(4):
            self.board[0][col] = Player.BLACK
        for player in (Player.BLACK, Player.WHITE):
            _, options = build_request(self.board, player, "jev-latest")
            self.assertEqual(list(options.values()), [Point(0, 4)])

    @patch("ai.worker.choose_move")
    @patch("ai.worker.choose_jev_move")
    def test_worker_dispatches_to_jev_without_local_fallback(self, jev, local):
        jev.return_value = Point(7, 8)
        task = SearchTask(1, self.board, Player.WHITE, "jev", "key", "jev-latest")
        results = []
        task.signals.finished.connect(lambda *args: results.append(args))
        task.run()
        self.assertEqual(results, [(1, Point(7, 8), "")])
        jev.side_effect = JevError("Jev 连接失败或超时，请重试")
        task.run()
        self.assertIsNone(results[-1][1])
        self.assertIn("连接失败", results[-1][2])
        local.assert_not_called()

    def test_api_key_is_session_only_and_cancel_does_not_change_it(self):
        with TemporaryDirectory() as root, patch.dict(os.environ, {"TYPESAFE_API_KEY": "env-test-key"}):
            store = SettingsStore(root)
            self.assertEqual(store.jev_api_key, "env-test-key")
            dialog = SettingsDialog(store)
            dialog.jev_key.setText("cancelled-key")
            dialog.reject()
            self.assertEqual(store.jev_api_key, "env-test-key")
            dialog = SettingsDialog(store)
            dialog.difficulty_buttons["jev"].click()
            dialog.jev_key.setText("session-test-key")
            dialog.accept()
            self.assertEqual(store.values.ai_difficulty, "jev")
            self.assertEqual(store.jev_api_key, "session-test-key")
            self.assertNotIn("session-test-key", store.path.read_text())
            self.assertNotIn("env-test-key", store.path.read_text())
            self.assertEqual(SettingsStore(root).jev_api_key, "env-test-key")

    @patch("views.settings_dialog.QMessageBox.warning")
    def test_no_key_blocks_selecting_jev(self, warning):
        with TemporaryDirectory() as root, patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            store = SettingsStore(root)
            dialog = SettingsDialog(store)
            dialog.difficulty_buttons["jev"].click()
            dialog.accept()
            warning.assert_called_once()
            self.assertEqual(store.values.ai_difficulty, "normal")

    @patch("views.game_widget.QThreadPool.globalInstance")
    def test_switching_away_from_jev_discards_pending_reply(self, pool):
        with TemporaryDirectory() as root:
            store = SettingsStore(root)
            store.save(replace(store.values, ai_difficulty="jev"), jev_api_key="test-key")
            window = MainWindow(store, audio_enabled=False)
            window.start_game(GameMode.AI)
            game = window.game_widget
            canvas = game.chess_board.piece_area
            canvas.place_stone(Point(7, 7))
            old = game.search_task
            self.assertEqual(old.api_key, "test-key")
            store.save(replace(store.values, ai_difficulty="hard"))
            self.assertTrue(old.cancel.is_set())
            game.on_search_finished(old.token, Point(7, 8), "")
            self.assertEqual(len(canvas.play_game_controller.game_model.moves), 1)
            self.assertEqual(game.search_task.difficulty, "hard")
            window.close()
            window.deleteLater()
