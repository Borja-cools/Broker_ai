"""Veilige applicatie-instellingen.

In deze eerste fase bestaat er bewust maar één toegestane modus: simulatie.
Daardoor kan een typefout of omgevingsvariabele live trading niet activeren.
"""

from dataclasses import dataclass
from enum import Enum
import os


class AppMode(str, Enum):
    """Alle modi die Broker AI momenteel daadwerkelijk ondersteunt."""

    SIMULATION = "simulation"


class LogLevel(str, Enum):
    """Ondersteunde hoeveelheden diagnostische informatie."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Settings:
    """Onveranderlijke instellingen voor één applicatiestart."""

    mode: AppMode = AppMode.SIMULATION
    log_level: LogLevel = LogLevel.INFO

    @property
    def live_trading_enabled(self) -> bool:
        """Live trading blijft in Fase 0 altijd uitgeschakeld."""

        return False

    @classmethod
    def from_environment(cls) -> "Settings":
        """Lees en valideer de modus uit een omgevingsvariabele."""

        raw_mode = os.getenv("BROKER_AI_MODE", AppMode.SIMULATION.value)
        raw_log_level = os.getenv("BROKER_AI_LOG_LEVEL", LogLevel.INFO.value)

        try:
            mode = AppMode(raw_mode.strip().lower())
        except ValueError as error:
            allowed = ", ".join(mode.value for mode in AppMode)
            raise ValueError(
                f"Ongeldige BROKER_AI_MODE: {raw_mode!r}. Toegestaan: {allowed}."
            ) from error

        try:
            log_level = LogLevel(raw_log_level.strip().upper())
        except ValueError as error:
            allowed = ", ".join(level.value for level in LogLevel)
            raise ValueError(
                "Ongeldige BROKER_AI_LOG_LEVEL: "
                f"{raw_log_level!r}. Toegestaan: {allowed}."
            ) from error

        return cls(mode=mode, log_level=log_level)
