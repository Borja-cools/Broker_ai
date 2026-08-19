"""Een kleine, volledig vaste dataset voor de terminaldemo."""

from datetime import date, timedelta
from decimal import Decimal

from broker_ai.backtesting import BacktestConfig, BacktestEngine, BacktestResult
from broker_ai.data import HistoricalBar, HistoricalDataset
from broker_ai.domain import Currency, Exchange, Instrument
from broker_ai.strategies import MovingAverageStrategy


def run_backtest_demo() -> str:
    """Draai steeds exact dezelfde educatieve backtest."""

    instrument = Instrument("ASML", "ASML Holding", Exchange.EURONEXT_AMSTERDAM, Currency.EUR)
    closes = ("100", "99", "98", "99", "101", "104", "106", "103", "100", "97", "96", "99")
    start = date(2025, 1, 2)
    bars = tuple(
        HistoricalBar(
            trading_date=start + timedelta(days=index),
            open=Decimal(close) - Decimal("0.50"),
            high=Decimal(close) + Decimal("1.00"),
            low=Decimal(close) - Decimal("1.00"),
            close=Decimal(close),
            volume=1000 + index * 10,
        )
        for index, close in enumerate(closes)
    )
    result = BacktestEngine().run(
        HistoricalDataset(instrument, bars),
        MovingAverageStrategy(short_window=2, long_window=3),
        BacktestConfig(
            initial_cash=Decimal("10000.00"),
            fee_per_order=Decimal("1.00"),
            slippage_rate=Decimal("0.001"),
        ),
    )
    return format_backtest_report(result)


def format_backtest_report(result: BacktestResult) -> str:
    """Maak een compact Nederlands rapport van een backtestresultaat."""

    sharpe = (
        "n.v.t."
        if result.metrics.sharpe_ratio is None
        else f"{result.metrics.sharpe_ratio:.2f}"
    )
    return "\n".join(
        (
            "BACKTEST — uitsluitend historische simulatie",
            f"Strategie: {result.strategy_name}",
            f"Periode: {result.equity_curve[0].trading_date} t/m {result.equity_curve[-1].trading_date}",
            f"Startkapitaal: €{result.config.initial_cash:.2f}",
            f"Eindwaarde: €{result.equity_curve[-1].equity:.2f}",
            f"Rendement strategie: {_percentage(result.metrics.total_return)}",
            f"Rendement benchmark: {_percentage(result.benchmark_metrics.total_return)}",
            f"Maximale drawdown: {_percentage(result.metrics.maximum_drawdown)}",
            f"Volatiliteit op jaarbasis: {_percentage(result.metrics.annualized_volatility)}",
            f"Sharpe-achtige maatstaf: {sharpe}",
            f"Uitgevoerde orders: {len(result.executions)}",
            "Veiligheid: geen netwerk, broker of echt geld gebruikt",
        )
    )


def _percentage(value: Decimal) -> str:
    return f"{value * Decimal('100'):.2f}%"
