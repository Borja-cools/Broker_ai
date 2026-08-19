"""Volledig lokale demonstratie van de asynchrone paper-brokerstroom."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from broker_ai.brokers.local import LocalPaperBrokerAdapter
from broker_ai.brokers.reliable import ReliabilityPolicy, ReliableBrokerClient
from broker_ai.domain import Currency, Exchange, Instrument, MarketPrice, Order, OrderSide, Portfolio
from broker_ai.risk import AsyncRiskManagedBroker, RiskContext, RiskEngine


def run_broker_demo() -> str:
    """Bied een eenvoudig synchroon terminalcommando rond de async demo."""

    return asyncio.run(_run_broker_demo())


async def _run_broker_demo() -> str:
    instrument = Instrument("ASML", "ASML Holding", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
    portfolio = Portfolio(Decimal("10000.00"))
    quote = MarketPrice(instrument, Decimal("100.00"), datetime.now(timezone.utc))
    adapter = LocalPaperBrokerAdapter(
        portfolio,
        {instrument.symbol: quote},
        fee_per_order=Decimal("1.00"),
    )
    reliable = ReliableBrokerClient(
        adapter,
        ReliabilityPolicy(timeout_seconds=1, max_attempts=3, retry_delay_seconds=0),
    )
    risk_engine = RiskEngine()
    safe_broker = AsyncRiskManagedBroker(reliable, risk_engine)
    order = Order(instrument, OrderSide.BUY, 10, Decimal("100.00"))
    context = _context(portfolio, instrument.symbol)

    first = await safe_broker.submit_order(order, context)
    repeated = await safe_broker.submit_order(order, context)
    reconciled = (await reliable.reconcile_orders())[0]
    account = await reliable.get_account()
    status = await reliable.get_status()

    cancel_order = Order(instrument, OrderSide.BUY, 1, Decimal("100.00"))
    cancel_context = _context(portfolio, instrument.symbol)
    cancellable = await safe_broker.submit_order(cancel_order, cancel_context)
    cancelled = await reliable.cancel_order(cancellable.broker_order_id)

    return "\n".join(
        (
            "BROKER DEMO — lokale paper-adapter, geen extern account",
            f"Verbinding: {status.connection.value.upper()}",
            f"Eerste status: {first.status.value.upper()}",
            f"Zelfde order opnieuw: {'GEEN DUPLICAAT' if first.broker_order_id == repeated.broker_order_id else 'FOUT'}",
            f"Na reconciliatie: {reconciled.status.value.upper()}",
            f"Positie in paper-account: {account.positions[0].quantity} aandelen",
            f"Tweede order: {cancelled.status.value.upper()}",
            f"Risicocontroles in auditlog: {len(risk_engine.audit_log)}",
            "Veiligheid: geen netwerk, API-sleutel, brokeraccount of echt geld gebruikt",
        )
    )


def _context(portfolio: Portfolio, symbol: str) -> RiskContext:
    position = portfolio.get_position(symbol)
    price = Decimal("100.00")
    equity = portfolio.cash_balance + (position.quantity * price if position else 0)
    return RiskContext(
        portfolio,
        equity,
        Decimal("10000.00"),
        {symbol: price},
        Decimal("1.00"),
    )
