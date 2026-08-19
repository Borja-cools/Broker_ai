"""Een zichtbaar demoscenario zonder externe verbindingen of echt geld."""

from datetime import datetime, timezone
from decimal import Decimal

from broker_ai.brokers import SimulatedBroker
from broker_ai.domain import (
    Currency,
    Exchange,
    Instrument,
    MarketPrice,
    Order,
    OrderSide,
    Portfolio,
)
from broker_ai.risk import RiskContext, RiskEngine, RiskManagedBroker, RiskPolicy


def format_euro(amount: Decimal) -> str:
    """Formatteer een bedrag eenvoudig als eurotekst met twee decimalen."""

    return f"€{amount:.2f}"


def run_demo() -> str:
    """Voer een vaste koop en verkoop uit en geef een leesbaar rapport terug."""

    portfolio = Portfolio(cash_balance=Decimal("5000.00"))
    asml = Instrument(
        symbol="ASML",
        name="ASML Holding",
        exchange=Exchange.EURONEXT_AMSTERDAM,
        currency=Currency.EUR,
    )
    buy_order = Order(
        instrument=asml,
        side=OrderSide.BUY,
        quantity=3,
        price=Decimal("600.00"),
    )

    sell_order = Order(
        instrument=asml,
        side=OrderSide.SELL,
        quantity=1,
        price=Decimal("700.00"),
    )
    current_price = Decimal("650.00")
    valuation_time = datetime(2026, 8, 19, 16, 0, tzinfo=timezone.utc)

    broker = SimulatedBroker(fee_per_order=Decimal("1.00"))
    risk_engine = RiskEngine(RiskPolicy(max_concentration=Decimal("0.50")))
    safe_broker = RiskManagedBroker(broker, risk_engine)
    buy_execution = safe_broker.execute(
        buy_order,
        portfolio,
        RiskContext(
            portfolio,
            Decimal("5000.00"),
            Decimal("5000.00"),
            {"ASML": buy_order.price},
            broker.fee_per_order,
        ),
    )
    sell_execution = safe_broker.execute(
        sell_order,
        portfolio,
        RiskContext(
            portfolio,
            portfolio.cash_balance + Decimal("3") * sell_order.price,
            Decimal("5000.00"),
            {"ASML": sell_order.price},
            broker.fee_per_order,
        ),
    )
    position = portfolio.get_position("ASML")

    if position is None:
        raise RuntimeError("Demo-uitvoering leverde onverwacht geen positie op.")

    quote = MarketPrice(asml, current_price, valuation_time)
    valuation = portfolio.value({"ASML": quote})

    return (
        "DEMO — geen echte order\n"
        f"Instrument: {position.instrument.name} ({position.instrument.symbol})\n"
        f"Gekocht: {buy_order.quantity} aandelen à {format_euro(buy_order.price)}\n"
        f"Koopwaarde: {format_euro(buy_execution.executed_value)}\n"
        f"Kosten kooporder: {format_euro(buy_execution.fee)}\n"
        f"Verkocht: {sell_order.quantity} aandeel à {format_euro(sell_order.price)}\n"
        f"Verkoopwaarde: {format_euro(sell_execution.executed_value)}\n"
        f"Kosten verkooporder: {format_euro(sell_execution.fee)}\n"
        f"Resterende positie: {position.quantity} aandelen\n"
        f"Resterende cash: {format_euro(portfolio.cash_balance)}\n"
        f"Aangenomen actuele prijs: {format_euro(current_price)}\n"
        f"Actuele positiewaarde: {format_euro(valuation.position_value)}\n"
        f"Totale portefeuillewaarde: {format_euro(valuation.total_equity)}\n"
        f"Gerealiseerde winst: {format_euro(portfolio.realized_profit)}\n"
        f"Ongerealiseerde winst: {format_euro(valuation.unrealized_profit)}\n"
        f"Totaal resultaat: {format_euro(valuation.total_profit)}\n"
        f"Totale transactiekosten: {format_euro(buy_execution.fee + sell_execution.fee)}\n"
        f"Transacties in auditlog: {len(broker.transactions)}\n"
        f"Risicocontroles in auditlog: {len(risk_engine.audit_log)}\n"
        f"Status: {sell_execution.status.value.upper()}"
    )
