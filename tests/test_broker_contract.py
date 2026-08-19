"""Dezelfde contracttests voor iedere lokale brokeradapter."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from broker_ai.brokers import (
    BrokerInterface,
    BrokerIdempotencyConflictError,
    BrokerOrderStateError,
    BrokerOrderStatus,
    ConnectionState,
    LocalPaperBrokerAdapter,
    SimulatorBrokerAdapter,
)
from broker_ai.domain import Currency, Exchange, Instrument, MarketPrice, Order, OrderSide, Portfolio


class BrokerContract:
    adapter_type = SimulatorBrokerAdapter

    async def asyncSetUp(self) -> None:
        self.instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
        self.portfolio = Portfolio(Decimal("10000"))
        quote = MarketPrice(
            self.instrument,
            Decimal("100"),
            datetime(2025, 1, 2, 16, tzinfo=timezone.utc),
        )
        self.adapter = self.adapter_type(
            self.portfolio,
            {"ASML": quote},
            fee_per_order=Decimal("1"),
        )

    async def test_implements_common_interface(self) -> None:
        self.assertIsInstance(self.adapter, BrokerInterface)

    async def test_exposes_status_market_data_and_account(self) -> None:
        status = await self.adapter.get_status()
        quote = await self.adapter.get_market_price(self.instrument)
        account = await self.adapter.get_account()

        self.assertIs(status.connection, ConnectionState.CONNECTED)
        self.assertEqual(quote.price, Decimal("100"))
        self.assertEqual(account.cash_balance, Decimal("10000"))

    async def test_submit_is_idempotent_and_reconciliation_fills_once(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 2, Decimal("100"))
        first = await self.adapter.submit_order(order)
        second = await self.adapter.submit_order(order)

        self.assertEqual(first.broker_order_id, second.broker_order_id)
        reconciled = await self.adapter.reconcile_orders()
        self.assertEqual(len(reconciled), 1)
        self.assertIs(reconciled[0].status, BrokerOrderStatus.FILLED)
        account = await self.adapter.get_account()
        self.assertEqual(account.positions[0].quantity, 2)

    async def test_disconnected_adapter_fails_closed(self) -> None:
        self.adapter.set_connected(False)
        status = await self.adapter.get_status()
        self.assertIs(status.connection, ConnectionState.DISCONNECTED)
        with self.assertRaisesRegex(RuntimeError, "niet beschikbaar"):
            await self.adapter.get_account()

    async def test_same_client_id_with_other_content_is_rejected(self) -> None:
        first = Order(self.instrument, OrderSide.BUY, 1, Decimal("100"))
        changed = Order(
            self.instrument,
            OrderSide.BUY,
            2,
            Decimal("100"),
            order_id=first.order_id,
        )
        await self.adapter.submit_order(first)
        with self.assertRaises(BrokerIdempotencyConflictError):
            await self.adapter.submit_order(changed)


class SimulatorBrokerContractTest(BrokerContract, unittest.IsolatedAsyncioTestCase):
    adapter_type = SimulatorBrokerAdapter

    async def test_filled_order_cannot_be_cancelled(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 1, Decimal("100"))
        submitted = await self.adapter.submit_order(order)
        with self.assertRaises(BrokerOrderStateError):
            await self.adapter.cancel_order(submitted.broker_order_id)


class PaperBrokerContractTest(BrokerContract, unittest.IsolatedAsyncioTestCase):
    adapter_type = LocalPaperBrokerAdapter

    async def test_submitted_order_can_be_cancelled_idempotently(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 1, Decimal("100"))
        submitted = await self.adapter.submit_order(order)
        cancelled = await self.adapter.cancel_order(submitted.broker_order_id)
        repeated = await self.adapter.cancel_order(submitted.broker_order_id)

        self.assertIs(cancelled.status, BrokerOrderStatus.CANCELLED)
        self.assertEqual(cancelled, repeated)
        await self.adapter.reconcile_orders()
        self.assertIsNone(self.portfolio.get_position("ASML"))


if __name__ == "__main__":
    unittest.main()
