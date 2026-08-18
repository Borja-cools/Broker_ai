"""Automatische controles voor de belangrijkste veiligheidsinstelling."""

import os
import unittest
from unittest.mock import patch

from broker_ai.config import AppMode, LogLevel, Settings
from broker_ai.main import build_startup_message


class SettingsTest(unittest.TestCase):
    def test_default_mode_is_safe_simulation(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(settings.mode, AppMode.SIMULATION)
        self.assertEqual(settings.log_level, LogLevel.INFO)
        self.assertFalse(settings.live_trading_enabled)

    def test_unknown_mode_is_rejected(self) -> None:
        with patch.dict(os.environ, {"BROKER_AI_MODE": "live"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Ongeldige BROKER_AI_MODE"):
                Settings.from_environment()

    def test_unknown_log_level_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {"BROKER_AI_LOG_LEVEL": "EVERYTHING"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "BROKER_AI_LOG_LEVEL"):
                Settings.from_environment()

    def test_startup_message_shows_live_trading_is_off(self) -> None:
        message = build_startup_message(Settings())

        self.assertIn("Modus: SIMULATION", message)
        self.assertIn("Live trading: UIT", message)


if __name__ == "__main__":
    unittest.main()
