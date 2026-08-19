"""Stabiel async contract waar iedere brokeradapter aan moet voldoen."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from broker_ai.brokers.models import AccountSnapshot, BrokerOrder, BrokerStatus
from broker_ai.domain import Instrument, MarketPrice, Order


class BrokerError(RuntimeError):
    """Basistype voor vertaalde brokerfouten."""


class BrokerTransientError(BrokerError):
    """Tijdelijke storing waarbij een veilige retry mogelijk is."""


class BrokerTimeoutError(BrokerTransientError):
    """De broker antwoordde niet binnen de afgesproken tijd."""


class BrokerUnavailableError(BrokerError):
    """De verbinding is bewust of langdurig niet beschikbaar."""


class BrokerOrderNotFoundError(BrokerError):
    """De gevraagde order bestaat niet bij deze adapter."""


class BrokerOrderStateError(BrokerError):
    """De gevraagde statusovergang is niet toegestaan."""


class BrokerIdempotencyConflictError(BrokerError):
    """Dezelfde client-ID werd voor verschillende orderinhoud gebruikt."""


@runtime_checkable
class BrokerInterface(Protocol):
    """Async grens voor marktdata, account, orders, status en annulering."""

    async def get_status(self) -> BrokerStatus: ...

    async def get_market_price(self, instrument: Instrument) -> MarketPrice: ...

    async def get_account(self) -> AccountSnapshot: ...

    async def submit_order(self, order: Order) -> BrokerOrder: ...

    async def get_order(self, order_id: UUID) -> BrokerOrder: ...

    async def cancel_order(self, order_id: UUID) -> BrokerOrder: ...

    async def reconcile_orders(self) -> tuple[BrokerOrder, ...]: ...
