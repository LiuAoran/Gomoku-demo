import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.credentials import load_jev_key


class CredentialsTests(unittest.TestCase):
    def test_file_formats_and_environment_priority(self):
        with TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            path = Path(root) / ".env"
            self.assertEqual(load_jev_key(path), "")
            for content in ('TYPESAFE_API_KEY=test-key',
                            'export TYPESAFE_API_KEY="test-key" # comment',
                            "# comment\nTYPESAFE_API_KEY='test-key'\nUNRELATED=value"):
                path.write_text(content)
                self.assertEqual(load_jev_key(path), "test-key")
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "env-key"}):
                self.assertEqual(load_jev_key(path), "env-key")
            for content in ('TYPESAFE_API_KEY=', 'TYPESAFE_API_KEY="unclosed'):
                path.write_text(content)
                self.assertEqual(load_jev_key(path), "")
