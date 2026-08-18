"""Centrale, herhaalbare loggingconfiguratie."""

import logging

from broker_ai.config import LogLevel


def configure_logging(level: LogLevel) -> None:
    """Configureer consolelogging zonder bestaande handlers te dupliceren."""

    logging.basicConfig(
        level=level.value,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
