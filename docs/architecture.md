# Architectuur van Broker AI

## Doel

De kernlogica blijft onafhankelijk van terminal, API, database, mobiele app en echte
broker. Daardoor kunnen die onderdelen later worden toegevoegd zonder de financiële
regels opnieuw te schrijven.

## Transactiesimulatie

```text
Terminalcommando
      ↓
Configuratievalidatie
      ↓
Expliciet demoscenario
      ↓
Order → RiskManagedBroker → SimulatedBroker → Portfolio + Transaction
      ↓
MarketPrice → PortfolioValuation → terminalrapport
```

Vanaf Fase 3 lopen applicatieorders via `RiskManagedBroker`. `SimulatedBroker` blijft
een lage-level adapter die afzonderlijk getest wordt, maar wordt niet rechtstreeks door
de demo- of backteststroom aangeroepen.

## Historische backtest

```text
Lokaal CSV-bestand → HistoricalDataset → gevalideerde OHLCV-bars
                                             ↓
Afgesloten bars → Strategy → signaal → volgende openingskoers
                                             ↓
                   RiskManagedBroker → SimulatedBroker → Portfolio
                                             ↓
                    Equity curve → metrics + benchmark → rapport
```

Een strategie ontvangt na iedere slotkoers alleen de historie die op dat moment bekend
zou zijn. Een signaal wordt op zijn vroegst tegen de volgende openingskoers uitgevoerd.
Transactiekosten en slippage maken de simulatie minder optimistisch.

## Verantwoordelijkheden

- `domain`: financiële begrippen en invarianten; geen externe verbindingen.
- `brokers`: atomaire uitvoering en auditlog; nu uitsluitend lokaal.
- `simulation`: expliciete voorbeeldscenario's voor leren en testen.
- `data`: historische koersmodellen en lokale CSV-import.
- `strategies`: zuivere beslislogica zonder toegang tot geld of broker.
- `backtesting`: tijdsvolgorde, orderuitvoering, equity curve en statistieken.
- `risk`: centraal beleid, samenstelbare regels, auditlog en verplichte brokerpoort.
- `config`: veilige, gevalideerde instellingen.
- `observability`: uniforme diagnostische informatie.
- `main`: dun startpunt dat invoer naar de juiste use-case leidt.
- `server`: lokale REST API, authenticatie, SQLite-opslag en clientcontracten.

## Verplichte pre-tradecontrole

```text
Strategie of applicatie
        ↓ order + actuele context
RiskManagedBroker
        ↓
RiskEngine → alle regels → RiskAssessment → auditlog
        ↓ alleen bij volledige goedkeuring
SimulatedBroker → Portfolio + Transaction
```

Een technische fout in één regel wordt als afwijzing opgeslagen. De kill switch
blokkeert iedere order. Normale blootstellingslimieten blokkeren nieuwe kooprisico's,
maar laten verkopen toe zodat een positie bij verlies kan worden afgebouwd.

## Brokeradaptergrens

`BrokerInterface` is asynchroon en bevat marktdata, accountinformatie, verbindingsstatus,
indienen, opvragen, annuleren en reconciliëren. Zowel `SimulatorBrokerAdapter` als
`LocalPaperBrokerAdapter` en `AlpacaPaperBrokerAdapter` volgen ditzelfde contract. De lokale paper-adapter geeft een order
eerst `submitted` en verwerkt hem pas tijdens reconciliatie.

```text
AsyncRiskManagedBroker
          ↓
ReliableBrokerClient  → time-out + begrensde retry
          ↓
BrokerInterface
      ┌───┴────────────────┐
SimulatorAdapter    LocalPaperAdapter    AlpacaPaperAdapter
```

De interne order-ID is de idempotency-sleutel. Herhaling met identieke inhoud geeft
dezelfde brokerorder terug; dezelfde ID met andere inhoud wordt als conflict geweigerd.
Dit voorkomt dubbele orders wanneer een extern antwoord later verloren zou gaan.

## Toekomstige mobiele app

De iOS/SwiftUI-app wordt later een client van een beveiligde server-API. Zij krijgt
geen brokergeheimen en voert geen kernlogica lokaal uit. Iedere order blijft op de
server authenticatie, validatie, risicocontrole en auditlogging doorlopen.

## Lokale server en gespecialiseerde bots

FastAPI biedt `/api/v1` als stabiel contract en genereert OpenAPI-documentatie. SQLite
is lokaal de bron van waarheid; geldbedragen worden als decimale tekst opgeslagen om
float-afwijkingen te vermijden. Iedere bot heeft een specialisatie en goedkeuringsmodus:

- `manual`: ieder voorstel wacht op menselijke goedkeuring;
- `automatic_limited`: alleen voorstellen onder de botlimiet worden automatisch gemarkeerd;
- `disabled`: ieder voorstel wordt geweigerd.

`auto_approved` betekent nog geen brokeruitvoering. In een volgende integratiestap moet
ook zo'n voorstel door de centrale risk engine en brokeradapter.

```text
Web/mobile client → Bearer auth → /api/v1 → SQLite
                                      ↓
                         bot → order proposal → auditlog
```

## Domeinmodellen na Fase 1

- `Instrument`: identiteit, beurs, valuta en instrumenttype.
- `MarketPrice`: positieve koers gekoppeld aan instrument en tijdzonebewust tijdstip.
- `Order`: onveranderlijk koop- of verkoopverzoek met unieke ID.
- `Transaction`: onveranderlijk auditrecord van een geslaagde uitvoering.
- `Position`: aantal en gewogen gemiddelde kostprijs.
- `Portfolio`: cash, posities en gerealiseerde winst.
- `PortfolioValuation`: cash, marktwaarde, equity en (on)gerealiseerd resultaat.

## Atomaire uitvoering

De simulator valideert order, valuta, saldo/positie en auditmetadata voordat hij een
portefeuille wijzigt. Een geweigerde order levert geen cashmutatie, positiewijziging of
transactie op. Een geslaagde order levert precies één `Transaction` op.

## Alpaca Paper als eerste externe broker

De Alpaca-adapter ondersteunt voorlopig uitsluitend Amerikaanse USD-aandelen met gehele
aantallen. Hij staat alleen de officiële paper-URL toe. Credentials komen uit de
omgeving, worden niet gelogd en worden nooit aan web- of mobiele clients gegeven.

```text
Bot/strategie → risk engine → ReliableBrokerClient → AlpacaPaperBrokerAdapter
                                                        ├── Trading API (paper)
                                                        └── Market Data API (IEX)
```

De adapter is verwisselbaar: een latere IBKR-adapter implementeert hetzelfde contract.
Een overgang naar IBKR vereist daardoor geen herschrijving van bots en risicoregels.

Reconciliatie haalt recente orders en de volledige actuele positieset opnieuw bij Alpaca
op. `broker_orders` gebruikt het brokerorder-ID als primaire sleutel, zodat een volgende
run de status bijwerkt in plaats van een duplicaat te maken. Posities worden per
geslaagde run atomair vervangen. Iedere run en voltooiing worden afzonderlijk bewaard.

```text
Alpaca Paper → alpaca-sync → SQLite → lokale REST API → later web/iOS-dashboard
```

## Grenzen na versie 0.7

Nog geen echte Alpaca-credentials, AI of live broker. Fractionele aandelen en crypto
zijn nog niet in het kerndomein gemodelleerd. De API bindt lokaal aan `127.0.0.1`;
SQLite is niet bedoeld voor meerdere productieservers. Externe deployment volgt later
met PostgreSQL, HTTPS, rotatie van secrets en beheerde back-ups.
