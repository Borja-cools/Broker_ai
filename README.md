# Broker AI

Broker AI is een stapsgewijs leerproject voor een veilige, testbare Python-backend
rond beleggingssimulatie. De huidige versie bevat een geteste, maar nog niet met echte
sleutels verbonden Alpaca Paper-adapter. Live trading is technisch uitgesloten.

> **Veiligheidsstatus:** lokale simulatie en Alpaca Paper zijn toegestaan. AI en live
> trading zijn nog niet aangesloten.

## Wat werkt al? (Fase 5 + Alpaca-fundament)

- Gevalideerde configuratie met veilige standaardwaarden.
- Cashportefeuille en posities met `Decimal`-berekeningen.
- Koop- en verkooporders voor gehele aandelen.
- Lokale simulated broker met configureerbare transactiekosten.
- Gerealiseerde en ongerealiseerde winstberekening.
- Tijdzonebewuste marktprijzen en volledige portefeuillewaardering.
- Unieke order- en transactie-ID's met een onveranderlijk auditlog.
- Expliciet terminaldemoscenario en automatische tests.
- Centrale logging en documentatie van architectuurkeuzes.
- Import en strikte validatie van lokale historische OHLCV-data.
- Strategiecontract en eenvoudige moving-average-referentiestrategie.
- Reproduceerbare backtest met uitvoering op de volgende handelsdag.
- Transactiekosten, slippage en buy-and-holdbenchmark.
- Rendement, volatiliteit, maximale drawdown en Sharpe-achtige maatstaf.
- Centrale risk engine die strategie en broker van elkaar scheidt.
- Limieten voor orderwaarde, positiewaarde, concentratie, cashreserve en dagverlies.
- Fail-safe kill switch en veilige afwijzing wanneer een risicoregel faalt.
- Uitlegbare afwijzingsredenen en onveranderlijk auditlog van iedere controle.
- Verplichte risicopoort in de transactie- en backtestdemo.
- Async `BrokerInterface` voor status, marktdata, account, orders en annulering.
- Verwisselbare simulator- en volledig lokale paper-adapter.
- Asynchrone orderstatus: submitted, filled, cancelled of rejected.
- Idempotente indiening en annulering zonder dubbele orderuitvoering.
- Begrensde retries, time-outs en vertaling van tijdelijke brokerfouten.
- Statusreconciliatie en gedeelde contracttests voor iedere adapter.
- Lokale FastAPI-server met versiebeheer onder `/api/v1` en OpenAPI-documentatie.
- SQLite-migratie en tabellen voor gebruikers, bots, snapshots, analyses en orders.
- Bearer-authenticatie, admin/viewer-autorisatie en rate limiting.
- Gespecialiseerde bots met `manual`, `automatic_limited` of `disabled` goedkeuring.
- Auditlog, request-ID's, gestructureerde logging, metrics en health check.
- Consistente SQLite-back-up en Docker/deploymentconfiguratie.
- USD-instrumenten op NASDAQ, NYSE en NYSE Arca.
- Strikt paper-only Alpaca-adapter voor account, posities, IEX-koersdata en orders.
- Expliciete vertaling van netwerk-, authenticatie- en brokerfouten.
- Veilige alleen-lezen accountcontrole zonder orders te plaatsen.

## Vereisten

- Python 3.11 of nieuwer
- PyCharm of een andere Python-IDE
- Git voor versiebeheer

## Installatie

Open een terminal in de projectmap:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
```

Windows gebruikt voor activering doorgaans:

```powershell
.venv\Scripts\activate
```

## Gebruik

Toon alleen de veilige opstartstatus:

```bash
broker-ai
```

Voer een volledig lokale voorbeeldsimulatie uit:

```bash
broker-ai demo
```

Voer de vaste historische backtestdemo uit:

```bash
broker-ai backtest
```

Bekijk goedkeuring, afwijzing en de kill switch:

```bash
broker-ai risk-demo
```

Bekijk de lokale asynchrone paper-brokerstroom:

```bash
broker-ai broker-demo
```

Controleer later een gekoppeld Alpaca Paper-account zonder een order te plaatsen:

```bash
export ALPACA_API_KEY_ID="jouw-paper-key"
export ALPACA_API_SECRET_KEY="jouw-paper-secret"
broker-ai alpaca-check
```

De adapter accepteert uitsluitend `https://paper-api.alpaca.markets`. Een live Alpaca-URL
wordt vóór iedere netwerkverbinding geweigerd. Zet sleutels nooit in broncode of Git.

De begeleide eerste paper-order gebruikt één AAPL-aandeel, de actuele IEX-koers als
limitprijs, strikte onboardinglimieten en een exacte terminalbevestiging:

```bash
broker-ai alpaca-first-order
```

Dit commando is uitsluitend bedoeld nadat `alpaca-check` geslaagd is. Het kan geen live
order plaatsen, maar verandert bij bevestiging wel de gesimuleerde Alpaca-portefeuille.

Synchroniseer daarna recente orders, uitvoeringsprijzen en actuele posities naar SQLite:

```bash
broker-ai alpaca-sync
```

De gegevens zijn na een herstart van de lokale server zichtbaar via `/docs` onder
`broker-orders`, `broker-positions` en `broker-sync-runs`. Herhaald synchroniseren werkt
dezelfde order bij en maakt geen duplicaat.

Start de lokale API nadat je een geheim van minimaal 32 tekens hebt ingesteld:

```bash
export BROKER_AI_API_TOKEN="vervang-dit-door-een-lang-willekeurig-geheim"
broker-ai serve
```

Open daarna [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) voor de interactieve
API-documentatie. De server luistert standaard uitsluitend op je eigen computer.
Gebruik daar bovenaan **Authorize** en vul alleen het token in; Swagger voegt zelf het
woord `Bearer` toe aan ieder beveiligd verzoek.

Toon beschikbare opties:

```bash
broker-ai --help
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Een wijziging is pas klaar wanneer alle tests slagen. GitHub Actions voert dezelfde
testopdracht bij iedere push automatisch uit.

## Veilige configuratie

Kopieer `.env.example` alleen als voorbeeld; de applicatie leest momenteel rechtstreeks
uit omgevingsvariabelen. Zet nooit echte sleutels of wachtwoorden in Git.

```text
BROKER_AI_MODE=simulation
BROKER_AI_LOG_LEVEL=INFO
```

Toegestane logniveaus zijn `DEBUG`, `INFO`, `WARNING` en `ERROR`. Een onbekende modus
of onbekend logniveau stopt de applicatie met een duidelijke fout.

## Projectstructuur

```text
broker-ai/
├── docs/                    architectuur, beslissingen en leernotities
├── src/broker_ai/
│   ├── brokers/             lokale simulator; later broker-adapters
│   ├── backtesting/         engine, prestatiemeting en veilige demo
│   ├── config/              gevalideerde instellingen
│   ├── data/                historische OHLCV-import en validatie
│   ├── domain/              instrumenten, orders en portefeuille
│   ├── observability/       logging; later metrics en alerts
│   ├── risk/                beleid, regels, auditlog en verplichte brokerpoort
│   ├── simulation/          expliciete, lokale scenario's
│   └── strategies/          strategiecontract en referentiestrategieën
├── tests/                   automatische veiligheidstests
└── pyproject.toml           pakket- en commando-instellingen
```

## Documentatie

- [Architectuur](docs/architecture.md)
- [Fase 0-checklist](docs/phase-0-checklist.md)
- [Fase 1-checklist](docs/phase-1-checklist.md)
- [Fase 2-checklist](docs/phase-2-checklist.md)
- [Fase 3-checklist](docs/phase-3-checklist.md)
- [Fase 4-checklist](docs/phase-4-checklist.md)
- [Fase 5-checklist](docs/phase-5-checklist.md)
- [Beslissing: simulation-first](docs/decisions/0001-simulation-first.md)
- [Beslissing: scope van Fase 1](docs/decisions/0002-phase-1-domain-boundaries.md)
- [Beslissing: tijdsvolgorde van backtests](docs/decisions/0003-next-open-backtesting.md)
- [Beslissing: verplichte risicopoort](docs/decisions/0004-mandatory-risk-gateway.md)
- [Beslissing: asynchroon brokercontract](docs/decisions/0005-async-broker-contract.md)
- [Beslissing: gespecialiseerde bots en goedkeuring](docs/decisions/0006-bot-approval-modes.md)
- [Beslissing: Alpaca Paper vóór IBKR](docs/decisions/0007-alpaca-paper-before-ibkr.md)
- [Alpaca-integratiechecklist](docs/alpaca-integration-checklist.md)
- [Begrippenlijst](docs/learning-notes/glossary.md)
- [Changelog](CHANGELOG.md)

## Disclaimer

Dit project is educatieve software en geen financieel advies. Simulatieresultaten zijn
geen voorspelling of garantie van toekomstig rendement.
