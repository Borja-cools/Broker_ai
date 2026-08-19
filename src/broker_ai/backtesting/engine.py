"""Een kleine event-driven backtest-engine met expliciete tijdsvolgorde."""

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_DOWN
from math import sqrt
from uuid import NAMESPACE_URL, uuid5

from broker_ai.brokers import Execution, SimulatedBroker
from broker_ai.data import HistoricalDataset
from broker_ai.domain import MarketPrice, Order, OrderSide, Portfolio
from broker_ai.strategies import Signal, Strategy


@dataclass(frozen=True)
class BacktestConfig:
    """Alle aannames die een backtest reproduceerbaar maken."""

    initial_cash: Decimal = Decimal("10000.00")
    fee_per_order: Decimal = Decimal("1.00")
    slippage_rate: Decimal = Decimal("0.001")

    def __post_init__(self) -> None:
        _positive_decimal(self.initial_cash, "Beginkapitaal")
        _non_negative_decimal(self.fee_per_order, "Transactiekosten")
        _non_negative_decimal(self.slippage_rate, "Slippage")
        if self.slippage_rate >= Decimal("1"):
            raise ValueError("Slippage moet kleiner zijn dan 100%.")


@dataclass(frozen=True)
class EquityPoint:
    """Totale portefeuillewaarde na de slotkoers van één handelsdag."""

    trading_date: date
    equity: Decimal


@dataclass(frozen=True)
class PerformanceMetrics:
    """Samenvatting van rendement en risico van één equity curve."""

    total_return: Decimal
    annualized_volatility: Decimal
    maximum_drawdown: Decimal
    sharpe_ratio: Decimal | None


@dataclass(frozen=True)
class BacktestResult:
    """Volledig en onveranderlijk resultaat van één backtestrun."""

    strategy_name: str
    config: BacktestConfig
    equity_curve: tuple[EquityPoint, ...]
    executions: tuple[Execution, ...]
    metrics: PerformanceMetrics
    benchmark_metrics: PerformanceMetrics
    final_cash: Decimal
    final_quantity: int


class BacktestEngine:
    """Voer signalen pas op de opening van de volgende handelsdag uit."""

    def run(
        self,
        dataset: HistoricalDataset,
        strategy: Strategy,
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        settings = config or BacktestConfig()
        portfolio = Portfolio(cash_balance=settings.initial_cash)
        executions: list[Execution] = []
        equity_curve: list[EquityPoint] = []
        pending_signal = Signal.HOLD

        for index, bar in enumerate(dataset.bars):
            if pending_signal is not Signal.HOLD:
                execution = self._execute_signal(
                    pending_signal,
                    bar.open,
                    dataset,
                    portfolio,
                    settings,
                    bar.trading_date,
                )
                if execution is not None:
                    executions.append(execution)

            quote_time = datetime.combine(bar.trading_date, time(16), timezone.utc)
            valuation = portfolio.value(
                {
                    dataset.instrument.symbol: MarketPrice(
                        dataset.instrument,
                        bar.close,
                        quote_time,
                    )
                }
                if portfolio.positions
                else {}
            )
            equity_curve.append(EquityPoint(bar.trading_date, valuation.total_equity))

            history = dataset.bars[: index + 1]
            has_position = portfolio.get_position(dataset.instrument.symbol) is not None
            pending_signal = strategy.decide(history, has_position)
            if not isinstance(pending_signal, Signal):
                raise TypeError("Strategie moet een Signal teruggeven.")

        benchmark_curve = _build_benchmark_curve(dataset, settings)
        return BacktestResult(
            strategy_name=strategy.name,
            config=settings,
            equity_curve=tuple(equity_curve),
            executions=tuple(executions),
            metrics=calculate_metrics(tuple(equity_curve), settings.initial_cash),
            benchmark_metrics=calculate_metrics(benchmark_curve, settings.initial_cash),
            final_cash=portfolio.cash_balance,
            final_quantity=(
                position.quantity
                if (position := portfolio.get_position(dataset.instrument.symbol))
                else 0
            ),
        )

    @staticmethod
    def _execute_signal(
        signal: Signal,
        opening_price: Decimal,
        dataset: HistoricalDataset,
        portfolio: Portfolio,
        config: BacktestConfig,
        trading_date: date,
    ) -> Execution | None:
        if signal is Signal.BUY:
            fill_price = opening_price * (Decimal("1") + config.slippage_rate)
            spendable = portfolio.cash_balance - config.fee_per_order
            quantity = int((spendable / fill_price).to_integral_value(rounding=ROUND_DOWN))
            if quantity <= 0:
                return None
            side = OrderSide.BUY
        elif signal is Signal.SELL:
            position = portfolio.get_position(dataset.instrument.symbol)
            if position is None:
                return None
            fill_price = opening_price * (Decimal("1") - config.slippage_rate)
            quantity = position.quantity
            side = OrderSide.SELL
        else:
            return None

        dated_broker = SimulatedBroker(
            fee_per_order=config.fee_per_order,
            clock=lambda: datetime.combine(trading_date, time(9), timezone.utc),
            transaction_id_factory=lambda: uuid5(
                NAMESPACE_URL,
                f"broker-ai:transaction:{dataset.instrument.symbol}:{trading_date}:{side.value}",
            ),
        )
        execution = dated_broker.execute(
            Order(
                dataset.instrument,
                side,
                quantity,
                fill_price,
                order_id=uuid5(
                    NAMESPACE_URL,
                    f"broker-ai:order:{dataset.instrument.symbol}:{trading_date}:{side.value}",
                ),
            ),
            portfolio,
        )
        return execution


def calculate_metrics(
    curve: tuple[EquityPoint, ...],
    initial_cash: Decimal,
) -> PerformanceMetrics:
    """Bereken deterministische, dag-gebaseerde kernstatistieken."""

    if not curve:
        raise ValueError("Een equity curve mag niet leeg zijn.")

    total_return = curve[-1].equity / initial_cash - Decimal("1")
    peak = curve[0].equity
    maximum_drawdown = Decimal("0")
    returns: list[float] = []
    previous = initial_cash

    for point in curve:
        peak = max(peak, point.equity)
        drawdown = point.equity / peak - Decimal("1")
        maximum_drawdown = min(maximum_drawdown, drawdown)
        returns.append(float(point.equity / previous - Decimal("1")))
        previous = point.equity

    average = sum(returns) / len(returns)
    variance = sum((item - average) ** 2 for item in returns) / len(returns)
    daily_volatility = sqrt(variance)
    annualized_volatility = Decimal(str(daily_volatility * sqrt(252)))
    sharpe = None
    if daily_volatility > 0:
        sharpe = Decimal(str((average / daily_volatility) * sqrt(252)))

    return PerformanceMetrics(
        total_return=total_return,
        annualized_volatility=annualized_volatility,
        maximum_drawdown=maximum_drawdown,
        sharpe_ratio=sharpe,
    )


def _build_benchmark_curve(
    dataset: HistoricalDataset,
    config: BacktestConfig,
) -> tuple[EquityPoint, ...]:
    buy_price = dataset.bars[0].open * (Decimal("1") + config.slippage_rate)
    spendable = config.initial_cash - config.fee_per_order
    quantity = int((spendable / buy_price).to_integral_value(rounding=ROUND_DOWN))
    cash = config.initial_cash - buy_price * quantity
    if quantity > 0:
        cash -= config.fee_per_order
    return tuple(
        EquityPoint(bar.trading_date, cash + bar.close * quantity)
        for bar in dataset.bars
    )


def _positive_decimal(value: Decimal, name: str) -> None:
    _non_negative_decimal(value, name)
    if value == Decimal("0"):
        raise ValueError(f"{name} moet groter zijn dan nul.")


def _non_negative_decimal(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} moet een Decimal zijn.")
    if not value.is_finite() or value < Decimal("0"):
        raise ValueError(f"{name} moet eindig en niet-negatief zijn.")
