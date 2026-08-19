"""Tests voor retries, time-outs en verloren antwoorden."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from broker_ai.brokers import (
    BrokerTimeoutError,
    BrokerTransientError,
    ReliabilityPolicy,
    ReliableBrokerClient,
    SimulatorBrokerAdapter,
)
from broker_ai.domain import Currency, Exchange, Instrument, MarketPrice, Order, OrderSide, Portfolio


class DelegatingAdapter:
    def __init__(self, inner):
        self.inner = inner

    async def get_status(self): return await self.inner.get_status()
    async def get_market_price(self, instrument): return await self.inner.get_market_price(instrument)
    async def get_account(self): return await self.inner.get_account()
    async def submit_order(self, order): return await self.inner.submit_order(order)
    async def get_order(self, order_id): return await self.inner.get_order(order_id)
    async def cancel_order(self, order_id): return await self.inner.cancel_order(order_id)
    async def reconcile_orders(self): return await self.inner.reconcile_orders()


class FlakyStatusAdapter(DelegatingAdapter):
    def __init__(self, inner):
        super().__init__(inner)
        self.attempts = 0

    async def get_status(self):
        self.attempts += 1
        if self.attempts < 3:
            raise BrokerTransientError("tijdelijk")
        return await self.inner.get_status()


class LostSubmitResponseAdapter(DelegatingAdapter):
    def __init__(self, inner):
        super().__init__(inner)
        self.attempts = 0

    async def submit_order(self, order):
        self.attempts += 1
        result = await self.inner.submit_order(order)
        if self.attempts == 1:
            raise BrokerTransientError("antwoord verloren")
        return result


class SlowStatusAdapter(DelegatingAdapter):
    async def get_status(self):
        await asyncio.sleep(0.05)
        return await self.inner.get_status()


class BrokerReliabilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
        self.portfolio = Portfolio(Decimal("10000"))
        quote = MarketPrice(self.instrument, Decimal("100"), datetime.now(timezone.utc))
        self.inner = SimulatorBrokerAdapter(self.portfolio, {"ASML": quote})
        self.policy = ReliabilityPolicy(
            timeout_seconds=0.01,
            max_attempts=3,
            retry_delay_seconds=0,
        )

    async def test_transient_failure_is_retried_with_limit(self) -> None:
        flaky = FlakyStatusAdapter(self.inner)
        status = await ReliableBrokerClient(flaky, self.policy).get_status()
        self.assertEqual(flaky.attempts, 3)
        self.assertEqual(status.mode.value, "simulation")

    async def test_lost_submit_response_does_not_duplicate_order(self) -> None:
        adapter = LostSubmitResponseAdapter(self.inner)
        client = ReliableBrokerClient(adapter, self.policy)
        order = Order(self.instrument, OrderSide.BUY, 2, Decimal("100"))

        result = await client.submit_order(order)

        self.assertEqual(adapter.attempts, 2)
        self.assertEqual(result.order.order_id, order.order_id)
        self.assertEqual(self.portfolio.get_position("ASML").quantity, 2)

    async def test_timeout_is_translated_after_bounded_retries(self) -> None:
        client = ReliableBrokerClient(SlowStatusAdapter(self.inner), self.policy)
        with self.assertRaises(BrokerTimeoutError):
            await client.get_status()


if __name__ == "__main__":
    unittest.main()
