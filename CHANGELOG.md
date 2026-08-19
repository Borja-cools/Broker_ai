# Changelog

Alle belangrijke wijzigingen aan Broker AI worden hier per projectfase bijgehouden.

## 0.3.0 — Fase 2

- Lokale CSV-import en validatie van historische OHLCV-data.
- Vast strategiecontract en moving-average-referentiestrategie.
- Backtest-engine zonder look-ahead bias: signalen vullen op de volgende opening.
- Instelbare transactiekosten en slippage voor gehele aandelen.
- Reproduceerbare equity curve met buy-and-holdbenchmark.
- Rapportage van rendement, volatiliteit, maximale drawdown en Sharpe-achtige maatstaf.
- Veilige terminaldemo via `broker-ai backtest` en tests voor tijdsvolgorde.

## 0.2.0 — Fase 1

- Volledige instrument-, order-, positie- en portefeuillemodellen.
- Gesimuleerde koop en verkoop met transactiekosten.
- Tijdzonebewuste marktprijzen en portefeuillewaardering.
- Gerealiseerde, ongerealiseerde en totale winst.
- Unieke order- en transactie-ID's en een onveranderlijk auditlog.
- Atomaire afwijzing bij ongeldige orders of auditmetadata.
- Uitgebreide terminaldemo en tests voor financiële randgevallen.

## 0.1.0 — Fase 0

- Veilige Python-projectbasis en virtuele omgeving.
- Uitsluitend simulatiemodus; live trading afwezig.
- Centrale configuratie, logging, documentatie en GitHub Actions.
