# Fase 0 — Afrondingschecklist

## Ontwikkelbasis

- [x] Python 3.11+ en lokale `.venv` gedocumenteerd.
- [x] Installeerbaar `src`-project met `pyproject.toml`.
- [x] Terminalcommando `broker-ai`.
- [x] `.gitignore` voor omgevingen, secrets en gegenereerde bestanden.
- [x] Voorbeeldconfiguratie zonder echte geheimen.

## Veiligheid en kwaliteit

- [x] Alleen simulatiemodus toegestaan.
- [x] Live trading bestaat niet als uitvoerbare optie.
- [x] Geldberekeningen gebruiken `Decimal`.
- [x] Automatische tests voor normaal en foutgedrag.
- [x] Centrale loggingconfiguratie.
- [x] GitHub Actions-testworkflow.

## Leren en overdracht

- [x] Uitgebreide README met installatie en gebruik.
- [x] Architectuuroverzicht.
- [x] Eerste architecture decision record.
- [x] Begrippenlijst.
- [x] Expliciet demoscenario zonder echte orders.

## Exitcriterium

Fase 0 is gereed wanneer de lokale tests en GitHub Actions slagen en de hoofdbranch
de volledige startbasis bevat. Daarna begint Fase 1 met verdere domein- en
simulatiemodellen; externe brokers blijven buiten scope.
