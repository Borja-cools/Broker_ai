"""Bewijs dat ook async brokerorders de bestaande risk engine passeren."""

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from broker_ai.brokers import LocalPaperBrokerAdapter
from broker_ai.domain import Currency, Exchange, Instrument, MarketPrice, Order, OrderSide, Portfolio
from broker_ai.risk import AsyncRiskManagedBroker, RiskContext, RiskEngine, RiskRejectedError


class AsyncRiskGatewayTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
        self.portfolio = Portfolio(Decimal("10000"))
        quote = MarketPrice(self.instrument, Decimal("100"), datetime.now(timezone.utc))
        self.adapter = LocalPaperBrokerAdapter(self.portfolio, {"ASML": quote})
        self.engine = RiskEngine()
        self.gateway = AsyncRiskManagedBroker(self.adapter, self.engine)
        self.context = RiskContext(
            self.portfolio,
            Decimal("10000"),
            Decimal("10000"),
            {"ASML": Decimal("100")},
        )

    async def test_approved_order_is_submitted(self) -> None:
        result = await self.gateway.submit_order(
            Order(self.instrument, OrderSide.BUY, 10, Decimal("100")),
            self.context,
        )
        self.assertEqual(result.status.value, "submitted")
        self.assertTrue(self.engine.audit_log[0].approved)

    async def test_rejected_order_never_reaches_adapter(self) -> None:
        with self.assertRaises(RiskRejectedError):
            await self.gateway.submit_order(
                Order(self.instrument, OrderSide.BUY, 30, Decimal("100")),
                self.context,
            )
        self.assertEqual(await self.adapter.reconcile_orders(), ())


if __name__ == "__main__":
    unittest.main()
