"""Begrensde achtergrondwerker voor uitsluitend-lezen brokersynchronisatie."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import logging


LOGGER = logging.getLogger(__name__)
SyncOperation = Callable[[], Awaitable[dict[str, object]]]


class BrokerSyncWorker:
    def __init__(self, operation: SyncOperation, interval_seconds: int = 300) -> None:
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int):
            raise TypeError("Synchronisatie-interval moet een geheel getal zijn.")
        if interval_seconds < 60:
            raise ValueError("Automatische synchronisatie mag niet vaker dan elke 60 seconden.")
        self.operation = operation
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self.running = False
        self.last_started_at: str | None = None
        self.last_success_at: str | None = None
        self.last_error: str | None = None
        self.consecutive_failures = 0
        self.runs_completed = 0

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="alpaca-paper-sync")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def run_once(self) -> dict[str, object] | None:
        if self.running:
            return None
        self.running = True
        self.last_started_at = _now()
        try:
            result = await self.operation()
        except Exception as exc:
            self.consecutive_failures += 1
            self.last_error = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("Automatische Alpaca Paper-synchronisatie mislukt")
            return None
        else:
            self.runs_completed += 1
            self.consecutive_failures = 0
            self.last_error = None
            self.last_success_at = _now()
            return result
        finally:
            self.running = False

    def status(self, *, enabled: bool) -> dict[str, object]:
        return {
            "enabled": enabled,
            "paper_only": True,
            "interval_seconds": self.interval_seconds,
            "running": self.running,
            "runs_completed": self.runs_completed,
            "consecutive_failures": self.consecutive_failures,
            "last_started_at": self.last_started_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
        }

    async def _loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
