"""services.config tests: defaults, .env parsing, shell precedence, redaction."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from services.config import DEFAULT_BASE_URL, DEFAULT_MODEL, load_settings, read_dotenv

ENV_VARS = (
    "ELEC5620_API_KEY",
    "ELEC5620_BASE_URL",
    "ELEC5620_MODEL",
    "ELEC5620_LLM_TIMEOUT_SECONDS",
    "ELEC5620_RUNTIME_DIR",
)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        clean = {k: v for k, v in os.environ.items() if k not in ENV_VARS}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = Path(tempfile.mkdtemp())

    def test_defaults_without_env_or_file(self):
        s = load_settings(self.tmp / "missing.env")
        self.assertFalse(s.has_api_key)
        self.assertEqual(s.base_url, DEFAULT_BASE_URL)
        self.assertEqual(s.model, DEFAULT_MODEL)
        self.assertEqual(s.llm_timeout_seconds, 15.0)

    def test_dotenv_file_is_read(self):
        env = self.tmp / ".env"
        env.write_text('ELEC5620_API_KEY="fake-key-for-test"\n# comment\nELEC5620_MODEL=other-model\n')
        s = load_settings(env)
        self.assertTrue(s.has_api_key)
        self.assertEqual(s.model, "other-model")
        self.assertEqual(read_dotenv(env)["ELEC5620_API_KEY"], "fake-key-for-test")

    def test_shell_environment_overrides_dotenv(self):
        env = self.tmp / ".env"
        env.write_text("ELEC5620_MODEL=from-file\n")
        os.environ["ELEC5620_MODEL"] = "from-env"
        self.assertEqual(load_settings(env).model, "from-env")

    def test_invalid_timeout_is_reported(self):
        os.environ["ELEC5620_LLM_TIMEOUT_SECONDS"] = "soon"
        with self.assertRaises(ValueError):
            load_settings(self.tmp / "missing.env")

    def test_key_never_appears_in_redacted_view_or_repr(self):
        os.environ["ELEC5620_API_KEY"] = "super-secret"
        s = load_settings(self.tmp / "missing.env")
        self.assertNotIn("super-secret", str(s.redacted()))
        self.assertNotIn("super-secret", repr(s))
        self.assertEqual(s.redacted()["api_key"], "set")


if __name__ == "__main__":
    unittest.main()
