"""Scenario- en stresstests voor de onafhankelijke risk engine."""

from decimal import Decimal
import unittest

from broker_ai.brokers import SimulatedBroker
from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide, Portfolio
from broker_ai.risk import (
    RiskCode,
    RiskContext,
    RiskEngine,
    RiskManagedBroker,
    RiskOutcome,
    RiskPolicy,
    RiskRejectedError,
)


class BrokenRule:
    def evaluate(self, order, context):
        raise RuntimeError("testfout")


class RiskEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.instrument = Instrument("ASML", "ASML", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
        self.portfolio = Portfolio(Decimal("10000.00"))
        self.raw_broker = SimulatedBroker(Decimal("1.00"))
        self.engine = RiskEngine()
        self.broker = RiskManagedBroker(self.raw_broker, self.engine)

    def context(
        self,
        *,
        current_equity: Decimal = Decimal("10000.00"),
        day_start_equity: Decimal = Decimal("10000.00"),
    ) -> RiskContext:
        return RiskContext(
            self.portfolio,
            current_equity,
            day_start_equity,
            {"ASML": Decimal("100.00")},
            Decimal("1.00"),
        )

    def test_approved_order_reaches_broker_and_is_audited(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 10, Decimal("100.00"))

        execution = self.broker.execute(order, self.portfolio, self.context())

        self.assertEqual(execution.order, order)
        self.assertEqual(len(self.raw_broker.transactions), 1)
        self.assertTrue(self.engine.audit_log[0].approved)

    def test_order_above_limit_never_reaches_broker(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 26, Decimal("100.00"))

        with self.assertRaises(RiskRejectedError) as raised:
            self.broker.execute(order, self.portfolio, self.context())

        rejected_codes = {
            outcome.code for outcome in raised.exception.assessment.outcomes
            if not outcome.approved
        }
        self.assertIn(RiskCode.MAX_ORDER_VALUE, rejected_codes)
        self.assertEqual(self.portfolio.cash_balance, Decimal("10000.00"))
        self.assertEqual(self.raw_broker.transactions, ())

    def test_kill_switch_blocks_every_order(self) -> None:
        self.engine.kill_switch.activate()
        order = Order(self.instrument, OrderSide.BUY, 1, Decimal("100.00"))

        with self.assertRaises(RiskRejectedError) as raised:
            self.broker.execute(order, self.portfolio, self.context())

        self.assertIn("Kill switch", str(raised.exception))
        self.assertEqual(self.raw_broker.transactions, ())

    def test_daily_loss_blocks_new_risk(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 1, Decimal("100.00"))

        with self.assertRaises(RiskRejectedError) as raised:
            self.broker.execute(
                order,
                self.portfolio,
                self.context(day_start_equity=Decimal("10310.00")),
            )

        rejected = [item.code for item in raised.exception.assessment.outcomes if not item.approved]
        self.assertIn(RiskCode.DAILY_LOSS, rejected)

    def test_concentration_limit_is_enforced(self) -> None:
        policy = RiskPolicy(
            max_order_value=Decimal("10000"),
            max_position_value=Decimal("10000"),
            max_concentration=Decimal("0.25"),
        )
        broker = RiskManagedBroker(self.raw_broker, RiskEngine(policy))
        order = Order(self.instrument, OrderSide.BUY, 30, Decimal("100"))

        with self.assertRaises(RiskRejectedError) as raised:
            broker.execute(order, self.portfolio, self.context())

        rejected = [item.code for item in raised.exception.assessment.outcomes if not item.approved]
        self.assertIn(RiskCode.MAX_CONCENTRATION, rejected)

    def test_absolute_position_limit_is_enforced(self) -> None:
        policy = RiskPolicy(
            max_order_value=Decimal("10000"),
            max_position_value=Decimal("5000"),
            max_concentration=Decimal("1"),
        )
        broker = RiskManagedBroker(self.raw_broker, RiskEngine(policy))
        order = Order(self.instrument, OrderSide.BUY, 51, Decimal("100"))

        with self.assertRaises(RiskRejectedError) as raised:
            broker.execute(order, self.portfolio, self.context())

        rejected = [item.code for item in raised.exception.assessment.outcomes if not item.approved]
        self.assertIn(RiskCode.MAX_POSITION_VALUE, rejected)

    def test_cash_reserve_is_enforced(self) -> None:
        policy = RiskPolicy(
            max_order_value=Decimal("10000"),
            max_position_value=Decimal("10000"),
            max_concentration=Decimal("1"),
            min_cash_reserve=Decimal("0.50"),
        )
        broker = RiskManagedBroker(self.raw_broker, RiskEngine(policy))
        order = Order(self.instrument, OrderSide.BUY, 60, Decimal("100"))

        with self.assertRaises(RiskRejectedError) as raised:
            broker.execute(order, self.portfolio, self.context())

        rejected = [item.code for item in raised.exception.assessment.outcomes if not item.approved]
        self.assertIn(RiskCode.CASH_RESERVE, rejected)

    def test_rule_failure_rejects_fail_safe_and_is_audited(self) -> None:
        engine = RiskEngine(extra_rules=(BrokenRule(),))
        assessment = engine.assess(
            Order(self.instrument, OrderSide.BUY, 1, Decimal("100")),
            self.context(),
        )

        self.assertFalse(assessment.approved)
        self.assertEqual(assessment.outcomes[-1].code, RiskCode.RULE_ERROR)
        self.assertEqual(engine.audit_log, (assessment,))

    def test_exact_policy_boundary_is_allowed(self) -> None:
        order = Order(self.instrument, OrderSide.BUY, 25, Decimal("100"))
        execution = self.broker.execute(order, self.portfolio, self.context())
        self.assertEqual(execution.order.total_value, Decimal("2500"))

    def test_large_daily_loss_still_allows_risk_reducing_sale(self) -> None:
        self.raw_broker.execute(
            Order(self.instrument, OrderSide.BUY, 10, Decimal("100")),
            self.portfolio,
        )
        sale = Order(self.instrument, OrderSide.SELL, 10, Decimal("50"))
        context = RiskContext(
            self.portfolio,
            Decimal("9499"),
            Decimal("10000"),
            {"ASML": Decimal("50")},
            Decimal("1"),
        )

        execution = self.broker.execute(sale, self.portfolio, context)

        self.assertEqual(execution.order.side, OrderSide.SELL)

    def test_context_rejects_invented_equity(self) -> None:
        with self.assertRaisesRegex(ValueError, "komt niet overeen"):
            self.context(current_equity=Decimal("11000"))

    def test_context_must_belong_to_same_portfolio(self) -> None:
        other = Portfolio(Decimal("10000"))
        order = Order(self.instrument, OrderSide.BUY, 1, Decimal("100"))
        with self.assertRaisesRegex(ValueError, "niet bij"):
            self.broker.execute(order, other, self.context())


if __name__ == "__main__":
    unittest.main()
