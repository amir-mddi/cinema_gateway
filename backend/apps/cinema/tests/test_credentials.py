"""Pure multi-bot secret lookup test (no database or Django runtime needed)."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend.apps.cinema.adapters.bot_credentials import token_for


class CredentialTests(unittest.TestCase):
    def test_isolated_token_names_and_missing_token(self):
        a = SimpleNamespace(key="bot01")
        b = SimpleNamespace(key="bot02")
        with patch.dict(os.environ, {"BOT_TOKEN_BOT01": "secret-one", "BOT_TOKEN_BOT02": "secret-two"}):
            self.assertEqual(token_for(a), "secret-one")
            self.assertEqual(token_for(b), "secret-two")
        with patch.dict(os.environ, {"BOT_TOKEN_BOT01": "", "BOT_TOKEN_BOT02": ""}):
            with self.assertRaises(RuntimeError):
                token_for(a)

    def test_unsafe_key_rejected(self):
        with self.assertRaises(ValueError):
            token_for(SimpleNamespace(key="../other"))
