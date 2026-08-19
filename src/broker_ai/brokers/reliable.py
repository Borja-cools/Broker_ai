"""Time-outs en begrensde retries rond een idempotente brokeradapter."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from broker_ai.brokers.interface import (
    BrokerInterface,
    BrokerTimeoutError,
    BrokerTransientError,
)
from broker_ai.brokers.models import AccountSnapshot, BrokerOrder, BrokerStatus
from broker_ai.domain import Instrument, MarketPrice, Order


T = TypeVar("T")


@dataclass(frozen=True)
class ReliabilityPolicy:
    timeout_seconds: float = 2.0
    max_attempts: int = 3
    retry_delay_seconds: float = 0.05

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("Broker-time-out moet groter zijn dan nul.")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise TypeError("Maximaal aantal pogingen moet een geheel getal zijn.")
        if self.max_attempts <= 0:
            raise ValueError("Er moet minimaal één brokerpoging zijn.")
        if self.retry_delay_seconds < 0:
            raise ValueError("Retryvertraging mag niet negatief zijn.")


class ReliableBrokerClient:
    """Pas dezelfde betrouwbaarheidspolitiek toe op iedere adapterbewerking."""

    def __init__(
        self,
        adapter: BrokerInterface,
        policy: ReliabilityPolicy | None = None,
    ) -> None:
        if not isinstance(adapter, BrokerInterface):
            raise TypeError("Adapter moet het BrokerInterface-contract ondersteunen.")
        self._adapter = adapter
        self.policy = policy or ReliabilityPolicy()

    async def get_status(self) -> BrokerStatus:
        return await self._call(self._adapter.get_status)

    async def get_market_price(self, instrument: Instrument) -> MarketPrice:
        return await self._call(lambda: self._adapter.get_market_price(instrument))

    async def get_account(self) -> AccountSnapshot:
        return await self._call(self._adapter.get_account)

    async def submit_order(self, order: Order) -> BrokerOrder:
        return await self._call(lambda: self._adapter.submit_order(order))

    async def get_order(self, order_id: UUID) -> BrokerOrder:
        return await self._call(lambda: self._adapter.get_order(order_id))

    async def cancel_order(self, order_id: UUID) -> BrokerOrder:
        return await self._call(lambda: self._adapter.cancel_order(order_id))

    async def reconcile_orders(self) -> tuple[BrokerOrder, ...]:
        return await self._call(self._adapter.reconcile_orders)

    async def _call(self, operation: Callable[[], Awaitable[T]]) -> T:
        last_error: BrokerTransientError | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return await asyncio.wait_for(
                    operation(),
                    timeout=self.policy.timeout_seconds,
                )
            except TimeoutError:
                last_error = BrokerTimeoutError(
                    f"Broker antwoordde niet binnen {self.policy.timeout_seconds} seconden."
                )
            except BrokerTransientError as exc:
                last_error = exc
            except OSError as exc:
                last_error = BrokerTransientError(f"Tijdelijke netwerkfout: {exc}")

            if attempt < self.policy.max_attempts:
                await asyncio.sleep(self.policy.retry_delay_seconds)

        if last_error is None:
            raise RuntimeError("Brokerbewerking eindigde zonder resultaat of fout.")
        raise last_error
