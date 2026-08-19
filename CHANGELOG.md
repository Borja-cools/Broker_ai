# Changelog

Alle belangrijke wijzigingen aan Broker AI worden hier per projectfase bijgehouden.

## 0.8.0 — Automatische Paper-monitoring

- Optionele achtergrondwerker voor periodieke Alpaca Paper-synchronisatie.
- Veilige standaard: automatisch synchroniseren staat uit.
- Minimuminterval van 60 seconden en geen overlappende runs.
- Fouten stoppen de server niet en worden als status zichtbaar gemaakt.
- Netjes stoppen van de achtergrondtaak bij afsluiten van de server.
- Beveiligd endpoint `/api/v1/broker-sync-status` voor monitoring.

## 0.7.2 — Swagger Bearer-login

- Officiële HTTP Bearer-securitydefinitie aan OpenAPI toegevoegd.
- Eén algemene `Authorize`-knop in `/docs` in plaats van een defect los headerveld.
- Authenticatie en OpenAPI-securityschema met regressietests afgedekt.

## 0.7.1 — Alpaca Paper-reconciliatie

- Bestaande Alpaca-orders uit eerdere processen ophalen en normaliseren.
- Idempotente opslag van brokerorders, actuele posities en synchronisatieruns.
- Status, gevuld aantal, limitprijs en gemiddelde uitvoeringsprijs vastleggen.
- Iedere geslaagde synchronisatie als auditgebeurtenis bewaren.
- Lees-API voor brokerorders, brokerposities en synchronisatiehistoriek.
- Handmatig `broker-ai alpaca-sync` als veilige basis voor latere automatisering.

## 0.7.0 — Alpaca Paper-fundament

- Strikt paper-only Alpaca-adapter achter het bestaande `BrokerInterface`.
- USD, NASDAQ, NYSE en NYSE Arca toegevoegd zonder bestaande EUR-stromen te breken.
- Account-, positie-, IEX-marktdata-, order-, annulering- en reconciliatievertaling.
- Idempotente orderindiening en expliciete broker- en netwerkfouten.
- Alleen-lezen `broker-ai alpaca-check` voor een toekomstige accountkoppeling.
- Begeleide eerste AAPL-paper-order met harde limieten en exacte bevestiging.
- Contracttests met een volledig nagebootste Alpaca API; geen echte sleutels vereist.

## 0.6.0 — Fase 5

- Lokale FastAPI REST API onder `/api/v1` met OpenAPI-documentatie.
- SQLite-schema en migratie voor gebruikers, bots, snapshots, analyses en voorstellen.
- Bearer-authenticatie, admin/viewer-autorisatie en rate limiting van inlogpogingen.
- Botmodi voor handmatige, beperkt automatische of uitgeschakelde goedkeuring.
- Gevalideerde ordervoorstellen, beslissingen en persistent auditlog.
- Health check, metrics, request-ID's en gestructureerde HTTP-logging.
- Geteste SQLite-back-ups en containerconfiguratie voor latere deployment.

## 0.5.0 — Fase 4

- Stabiel asynchroon `BrokerInterface` voor marktdata, account en orderlevenscyclus.
- Verwisselbare simulator- en lokale paper-adapter zonder extern account.
- Brokerneutrale verbindings-, account- en orderstatusmodellen.
- Idempotente orderindiening en annulering met expliciete ID-conflicten.
- Begrensde retries, time-outs en foutvertaling via `ReliableBrokerClient`.
- Orderreconciliatie van submitted naar filled of rejected.
- Async risicopoort vóór iedere paper-brokerorder.
- Gedeelde adaptercontracttests, storingstests en lokale `broker-demo`.

## 0.4.0 — Fase 3

- Onafhankelijke risk engine vóór iedere order in applicatie- en backteststromen.
- Centrale limieten voor order, positie, concentratie, cashreserve en dagverlies.
- Fail-safe kill switch en veilige afwijzing van defecte risicoregels.
- Uitlegbare risicocodes, afwijzingsredenen en volledig auditlog.
- Validatie dat opgegeven equity overeenkomt met cash en alle actuele posities.
- Risicobeperkte ordergrootte in backtests en aparte `risk-demo`.
- Scenario-, grens-, stress- en regressietests voor de volledige risicopoort.

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
