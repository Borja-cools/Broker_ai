"""Lokale adapters die hetzelfde contract volgen als een toekomstige broker-API."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from broker_ai.brokers.interface import (
    BrokerIdempotencyConflictError,
    BrokerOrderNotFoundError,
    BrokerOrderStateError,
    BrokerUnavailableError,
)
from broker_ai.brokers.models import (
    AccountSnapshot,
    BrokerMode,
    BrokerOrder,
    BrokerOrderStatus,
    BrokerStatus,
    ConnectionState,
    PositionSnapshot,
)
from broker_ai.brokers.simulated import SimulatedBroker
from broker_ai.domain import Instrument, MarketPrice, Order, Portfolio


class _LocalBrokerAdapter:
    """Gedeeld betrouwbaar gedrag voor beide lokale adapters."""

    mode: BrokerMode

    def __init__(
        self,
        portfolio: Portfolio,
        market_prices: dict[str, MarketPrice],
        *,
        fee_per_order: Decimal = Decimal("0.00"),
    ) -> None:
        self.portfolio = portfolio
        self._prices = {symbol.strip().upper(): price for symbol, price in market_prices.items()}
        self._broker = SimulatedBroker(fee_per_order)
        self._connected = True
        self._orders_by_broker_id: dict[UUID, BrokerOrder] = {}
        self._broker_id_by_client_id: dict[UUID, UUID] = {}

    def set_connected(self, connected: bool) -> None:
        """Testbare lokale nabootsing van verbinding en storing."""

        if not isinstance(connected, bool):
            raise TypeError("Verbindingsstatus moet een bool zijn.")
        self._connected = connected

    async def get_status(self) -> BrokerStatus:
        state = ConnectionState.CONNECTED if self._connected else ConnectionState.DISCONNECTED
        return BrokerStatus(self.mode, state, self._now(), "Lokale adapter; geen extern netwerk.")

    async def get_market_price(self, instrument: Instrument) -> MarketPrice:
        self._require_connection()
        quote = self._prices.get(instrument.symbol)
        if quote is None or quote.instrument != instrument:
            raise BrokerUnavailableError(f"Geen lokale marktprijs voor {instrument.symbol}.")
        return quote

    async def get_account(self) -> AccountSnapshot:
        self._require_connection()
        positions = tuple(
            PositionSnapshot(symbol, position.quantity, position.average_price)
            for symbol, position in sorted(self.portfolio.positions.items())
        )
        return AccountSnapshot(
            self.portfolio.cash_balance,
            self.portfolio.currency,
            positions,
            self._now(),
        )

    async def get_order(self, order_id: UUID) -> BrokerOrder:
        self._require_connection()
        try:
            return self._orders_by_broker_id[order_id]
        except KeyError as exc:
            raise BrokerOrderNotFoundError(f"Brokerorder {order_id} bestaat niet.") from exc

    async def cancel_order(self, order_id: UUID) -> BrokerOrder:
        self._require_connection()
        existing = await self.get_order(order_id)
        if existing.status is BrokerOrderStatus.CANCELLED:
            return existing
        if existing.status is not BrokerOrderStatus.SUBMITTED:
            raise BrokerOrderStateError(
                f"Order met status {existing.status.value} kan niet worden geannuleerd."
            )
        cancelled = replace(
            existing,
            status=BrokerOrderStatus.CANCELLED,
            updated_at=self._now(),
            status_message="Order lokaal geannuleerd.",
        )
        self._orders_by_broker_id[order_id] = cancelled
        return cancelled

    async def reconcile_orders(self) -> tuple[BrokerOrder, ...]:
        self._require_connection()
        return tuple(self._orders_by_broker_id.values())

    def _existing_for(self, order: Order) -> BrokerOrder | None:
        broker_id = self._broker_id_by_client_id.get(order.order_id)
        existing = self._orders_by_broker_id.get(broker_id) if broker_id else None
        if existing is not None and existing.order != order:
            raise BrokerIdempotencyConflictError(
                f"Client-order-ID {order.order_id} hoort al bij andere orderinhoud."
            )
        return existing

    def _new_submitted_order(self, order: Order) -> BrokerOrder:
        now = self._now()
        broker_id = uuid5(NAMESPACE_URL, f"broker-ai:{self.mode.value}:{order.order_id}")
        record = BrokerOrder(
            broker_order_id=broker_id,
            order=order,
            status=BrokerOrderStatus.SUBMITTED,
            submitted_at=now,
            updated_at=now,
            status_message="Order lokaal ingediend en wacht op reconciliatie.",
        )
        self._broker_id_by_client_id[order.order_id] = broker_id
        self._orders_by_broker_id[broker_id] = record
        return record

    def _require_connection(self) -> None:
        if not self._connected:
            raise BrokerUnavailableError("Lokale brokerverbinding is niet beschikbaar.")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


class SimulatorBrokerAdapter(_LocalBrokerAdapter):
    """Adapter rond de bestaande simulator; orders vullen onmiddellijk."""

    mode = BrokerMode.SIMULATION

    async def submit_order(self, order: Order) -> BrokerOrder:
        self._require_connection()
        if existing := self._existing_for(order):
            return existing

        execution = self._broker.execute(order, self.portfolio)
        broker_id = uuid5(NAMESPACE_URL, f"broker-ai:{self.mode.value}:{order.order_id}")
        filled = BrokerOrder(
            broker_order_id=broker_id,
            order=order,
            status=BrokerOrderStatus.FILLED,
            execution=execution,
            submitted_at=execution.transaction.executed_at,
            updated_at=execution.transaction.executed_at,
            status_message="Order onmiddellijk door lokale simulator uitgevoerd.",
        )
        self._broker_id_by_client_id[order.order_id] = broker_id
        self._orders_by_broker_id[broker_id] = filled
        return filled


class LocalPaperBrokerAdapter(_LocalBrokerAdapter):
    """Offline paper-adapter: indienen nu, vullen bij reconciliatie."""

    mode = BrokerMode.PAPER

    async def submit_order(self, order: Order) -> BrokerOrder:
        self._require_connection()
        if existing := self._existing_for(order):
            return existing
        return self._new_submitted_order(order)

    async def reconcile_orders(self) -> tuple[BrokerOrder, ...]:
        self._require_connection()
        for broker_id, record in tuple(self._orders_by_broker_id.items()):
            if record.status is not BrokerOrderStatus.SUBMITTED:
                continue
            try:
                execution = self._broker.execute(record.order, self.portfolio)
                updated = replace(
                    record,
                    status=BrokerOrderStatus.FILLED,
                    execution=execution,
                    updated_at=execution.transaction.executed_at,
                    status_message="Paper-order tijdens reconciliatie uitgevoerd.",
                )
            except (TypeError, ValueError) as exc:
                updated = replace(
                    record,
                    status=BrokerOrderStatus.REJECTED,
                    updated_at=self._now(),
                    status_message=f"Paper-order geweigerd tijdens reconciliatie: {exc}",
                )
            self._orders_by_broker_id[broker_id] = updated
        return tuple(self._orders_by_broker_id.values())
