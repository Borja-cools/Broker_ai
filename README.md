# Broker AI

Broker AI is een stapsgewijs leerproject voor een veilige, testbare Python-backend
rond beleggingssimulatie. De huidige versie werkt uitsluitend lokaal en bevat geen
verbinding met een broker, geen echte marktorders en geen live trading.

> **Veiligheidsstatus:** alleen `simulation` is toegestaan. AI, paper trading en live
> trading maken geen deel uit van Fase 0.

## Wat werkt al? (Fase 1)

- Gevalideerde configuratie met veilige standaardwaarden.
- Cashportefeuille en posities met `Decimal`-berekeningen.
- Koop- en verkooporders voor gehele aandelen.
- Lokale simulated broker met configureerbare transactiekosten.
- Gerealiseerde en ongerealiseerde winstberekening.
- Tijdzonebewuste marktprijzen en volledige portefeuillewaardering.
- Unieke order- en transactie-ID's met een onveranderlijk auditlog.
- Expliciet terminaldemoscenario en automatische tests.
- Centrale logging en documentatie van architectuurkeuzes.

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
│   ├── config/              gevalideerde instellingen
│   ├── domain/              instrumenten, orders en portefeuille
│   ├── observability/       logging; later metrics en alerts
│   └── simulation/          expliciete, lokale scenario's
├── tests/                   automatische veiligheidstests
└── pyproject.toml           pakket- en commando-instellingen
```

## Documentatie

- [Architectuur](docs/architecture.md)
- [Fase 0-checklist](docs/phase-0-checklist.md)
- [Fase 1-checklist](docs/phase-1-checklist.md)
- [Beslissing: simulation-first](docs/decisions/0001-simulation-first.md)
- [Beslissing: scope van Fase 1](docs/decisions/0002-phase-1-domain-boundaries.md)
- [Begrippenlijst](docs/learning-notes/glossary.md)
- [Changelog](CHANGELOG.md)

## Disclaimer

Dit project is educatieve software en geen financieel advies. Simulatieresultaten zijn
geen voorspelling of garantie van toekomstig rendement.
