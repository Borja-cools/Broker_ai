"""Zichtbare demonstratie van goedkeuring, afwijzing en noodstop."""

from decimal import Decimal

from broker_ai.brokers import SimulatedBroker
from broker_ai.domain import Currency, Exchange, Instrument, Order, OrderSide, Portfolio
from broker_ai.risk.engine import RiskEngine
from broker_ai.risk.gateway import RiskManagedBroker, RiskRejectedError
from broker_ai.risk.models import RiskContext


def run_risk_demo() -> str:
    """Toon drie beslissingen zonder externe verbinding of echt geld."""

    instrument = Instrument("ASML", "ASML Holding", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
    portfolio = Portfolio(Decimal("10000.00"))
    engine = RiskEngine()
    broker = RiskManagedBroker(SimulatedBroker(Decimal("1.00")), engine)

    first = Order(instrument, OrderSide.BUY, 10, Decimal("100.00"))
    broker.execute(first, portfolio, _context(portfolio, instrument.symbol))

    oversized = Order(instrument, OrderSide.BUY, 20, Decimal("100.00"))
    concentration_reason = _rejection_reason(
        broker,
        oversized,
        portfolio,
        _context(portfolio, instrument.symbol),
    )

    engine.kill_switch.activate()
    emergency_test = Order(instrument, OrderSide.SELL, 1, Decimal("100.00"))
    kill_switch_reason = _rejection_reason(
        broker,
        emergency_test,
        portfolio,
        _context(portfolio, instrument.symbol),
    )

    return "\n".join(
        (
            "RISK DEMO — geen echte orders",
            "Order 1: GOEDGEKEURD — 10 aandelen binnen alle limieten",
            f"Order 2: GEWEIGERD — {concentration_reason}",
            f"Order 3: GEWEIGERD — {kill_switch_reason}",
            f"Risicobeslissingen in auditlog: {len(engine.audit_log)}",
            "Veiligheid: slechts één goedgekeurde simulatieorder bereikte de broker",
        )
    )


def _context(portfolio: Portfolio, symbol: str) -> RiskContext:
    position = portfolio.get_position(symbol)
    equity = portfolio.cash_balance + (position.quantity * Decimal("100") if position else 0)
    return RiskContext(
        portfolio,
        equity,
        Decimal("10000.00"),
        {symbol: Decimal("100.00")},
        Decimal("1.00"),
    )


def _rejection_reason(
    broker: RiskManagedBroker,
    order: Order,
    portfolio: Portfolio,
    context: RiskContext,
) -> str:
    try:
        broker.execute(order, portfolio, context)
    except RiskRejectedError as exc:
        return exc.assessment.rejection_reasons[0]
    raise RuntimeError("Risk demo verwachtte een afwijzing.")
