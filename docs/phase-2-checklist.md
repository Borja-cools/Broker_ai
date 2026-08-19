# Fase 2 — Datalaag en backtesting

## Doel

Strategieën reproduceerbaar testen op historische data, zonder toekomstinformatie te
lekken en zonder netwerk, echte broker of echt geld.

## Afgeronde deliverables

- [x] Historische OHLCV-bars met financiële en chronologische validatie.
- [x] Lokale CSV-import met duidelijke foutregels.
- [x] Onveranderlijke dataset voor precies één instrument.
- [x] Strategie-interface die geen portefeuille of broker kan aanpassen.
- [x] Eenvoudige moving-average-referentiestrategie.
- [x] Uitvoering van een signaal op de volgende openingskoers.
- [x] Configureerbare vaste transactiekosten en slippage.
- [x] Equity curve en buy-and-holdbenchmark.
- [x] Totaalrendement, volatiliteit, maximale drawdown en Sharpe-achtige maatstaf.
- [x] Vaste terminaldemo die zonder internet werkt.
- [x] Automatische tests voor validatie, tijdsvolgorde en reproduceerbaarheid.
- [x] Uitleg over look-ahead bias, survivorship bias en overfitting.

## Bewuste grenzen

- Eén instrument en één EUR-portefeuille per backtest.
- Alleen gehele aandelen en market-fills op de volgende opening.
- Geen dividend, belasting, rente, corporate actions of ontbrekende handelsdagen.
- Geen externe marktdata: CSV-data wordt door de gebruiker aangeleverd.
- De Sharpe-achtige maatstaf gebruikt dagelijkse rendementen en 0% risicovrije rente.
- Train/test-splits worden verplicht zodra strategieparameters echt worden onderzocht.

## Klaar wanneer

Een gevalideerde testdataset loopt van bron tot rapport, alle resultaten zijn bij een
herhaling gelijk en alle automatische tests slagen.
