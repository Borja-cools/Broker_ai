"""Startpunt van de Broker AI-applicatie."""

import argparse
from collections.abc import Sequence
import logging

from broker_ai.config import Settings
from broker_ai.observability import configure_logging
from broker_ai.simulation.demo import run_demo


LOGGER = logging.getLogger(__name__)


def build_startup_message(settings: Settings) -> str:
    """Maak een leesbaar statusbericht van gevalideerde instellingen."""

    live_status = "AAN" if settings.live_trading_enabled else "UIT"
    return (
        "Broker AI veilig gestart\n"
        f"Modus: {settings.mode.value.upper()}\n"
        f"Live trading: {live_status}"
    )


def build_parser() -> argparse.ArgumentParser:
    """Beschrijf de expliciete commando's van onze terminalapplicatie."""

    parser = argparse.ArgumentParser(
        prog="broker-ai",
        description="Veilige leeromgeving voor Broker AI.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("demo",),
        help="Voer 'demo' uit voor een lokale voorbeeldtransactie.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Laad instellingen en voer alleen een expliciet gekozen commando uit."""

    settings = Settings.from_environment()
    configure_logging(settings.log_level)
    arguments = build_parser().parse_args(argv)
    LOGGER.info(
        "Applicatie gestart in modus=%s; live_trading=%s",
        settings.mode.value,
        settings.live_trading_enabled,
    )
    print(build_startup_message(settings))

    if arguments.command == "demo":
        print()
        print(run_demo())


if __name__ == "__main__":
    main()
