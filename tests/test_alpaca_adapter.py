"""Contract- en veiligheidstests voor de Alpaca Paper-adapter."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

import httpx

from broker_ai.brokers import (
    AlpacaPaperBrokerAdapter,
    BrokerError,
    BrokerIdempotencyConflictError,
    BrokerOrderStatus,
    ConnectionState,
)
from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide


ORDER_ID = "ca6d44fb-d169-4f34-bb82-73aaf4418467"
NOW = "2026-08-19T12:00:00Z"


class FakeAlpaca:
    def __init__(self) -> None:
        self.order_status = "new"
        self.order_posts = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v2/account":
            return httpx.Response(200, json={"cash": "100000.00"})
        if path == "/v2/positions":
            return httpx.Response(
                200,
                json=[{"symbol": "AAPL", "qty": "2", "avg_entry_price": "190.50"}],
            )
        if path == "/v2/stocks/AAPL/trades/latest":
            return httpx.Response(200, json={"trade": {"p": 201.25, "t": NOW}})
        if path == "/v2/orders" and request.method == "POST":
            self.order_posts += 1
            return httpx.Response(200, json=self._order())
        if path == f"/v2/orders/{ORDER_ID}" and request.method == "DELETE":
            self.order_status = "canceled"
            return httpx.Response(204)
        if path == f"/v2/orders/{ORDER_ID}":
            return httpx.Response(200, json=self._order())
        return httpx.Response(404, json={"message": "not found"})

    def _order(self) -> dict[str, str | None]:
        filled = self.order_status == "filled"
        return {
            "id": ORDER_ID,
            "status": self.order_status,
            "submitted_at": NOW,
            "updated_at": NOW,
            "filled_at": NOW if filled else None,
            "filled_qty": "2" if filled else "0",
            "filled_avg_price": "200.00" if filled else None,
        }


class AlpacaPaperBrokerAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.fake = FakeAlpaca()
        transport = httpx.MockTransport(self.fake.handle)
        self.client = httpx.AsyncClient(transport=transport)
        self.adapter = AlpacaPaperBrokerAdapter("paper-key", "paper-secret", client=self.client)
        self.instrument = Instrument(
            "AAPL", "Apple", Exchange.NASDAQ, Currency.USD
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_rejects_every_non_paper_trading_endpoint(self) -> None:
        with self.assertRaisesRegex(ValueError, "uitsluitend Alpaca Paper"):
            AlpacaPaperBrokerAdapter(
                "key", "secret", trading_base_url="https://api.alpaca.markets"
            )

    async def test_status_account_and_iex_market_data(self) -> None:
        status = await self.adapter.get_status()
        account = await self.adapter.get_account()
        quote = await self.adapter.get_market_price(self.instrument)

        self.assertIs(status.connection, ConnectionState.CONNECTED)
        self.assertIs(account.currency, Currency.USD)
        self.assertEqual(account.cash_balance, Decimal("100000.00"))
        self.assertEqual(account.positions[0].quantity, 2)
        self.assertEqual(quote.price, Decimal("201.25"))

    async def test_submit_is_idempotent_and_uses_broker_uuid(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 2, Decimal("200"))
        first = await self.adapter.submit_order(order)
        second = await self.adapter.submit_order(order)

        self.assertEqual(first.broker_order_id, UUID(ORDER_ID))
        self.assertEqual(first.broker_order_id, second.broker_order_id)
        self.assertEqual(self.fake.order_posts, 1)

    async def test_changed_order_with_same_client_id_is_rejected(self) -> None:
        first = Order(self.instrument, OrderSide.BUY, 2, Decimal("200"))
        await self.adapter.submit_order(first)
        changed = Order(
            self.instrument, OrderSide.BUY, 3, Decimal("200"), order_id=first.order_id
        )
        with self.assertRaises(BrokerIdempotencyConflictError):
            await self.adapter.submit_order(changed)

    async def test_cancel_and_reconcile_translate_status(self) -> None:
        submitted = await self.adapter.submit_order(
            Order(self.instrument, OrderSide.BUY, 2, Decimal("200"))
        )
        cancelled = await self.adapter.cancel_order(submitted.broker_order_id)
        reconciled = await self.adapter.reconcile_orders()

        self.assertIs(cancelled.status, BrokerOrderStatus.CANCELLED)
        self.assertIs(reconciled[0].status, BrokerOrderStatus.CANCELLED)

    async def test_filled_order_creates_execution_evidence(self) -> None:
        submitted = await self.adapter.submit_order(
            Order(self.instrument, OrderSide.BUY, 2, Decimal("200"))
        )
        self.fake.order_status = "filled"
        filled = await self.adapter.get_order(submitted.broker_order_id)

        self.assertIs(filled.status, BrokerOrderStatus.FILLED)
        self.assertEqual(filled.execution.executed_value, Decimal("400.00"))

    async def test_euro_instrument_fails_before_network_call(self) -> None:
        instrument = Instrument(
            "ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR
        )
        with self.assertRaisesRegex(BrokerError, "alleen USD"):
            await self.adapter.get_market_price(instrument)


if __name__ == "__main__":
    unittest.main()
