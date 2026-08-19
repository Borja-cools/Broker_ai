# Architectuur van Broker AI

## Doel

De kernlogica blijft onafhankelijk van terminal, API, database, mobiele app en echte
broker. Daardoor kunnen die onderdelen later worden toegevoegd zonder de financiële
regels opnieuw te schrijven.

## Huidige stroom

```text
Terminalcommando
      ↓
Configuratievalidatie
      ↓
Expliciet demoscenario
      ↓
Order → SimulatedBroker → Portfolio + Transaction
      ↓
MarketPrice → PortfolioValuation → terminalrapport
```

## Verantwoordelijkheden

- `domain`: financiële begrippen en invarianten; geen externe verbindingen.
- `brokers`: atomaire uitvoering en auditlog; nu uitsluitend lokaal.
- `simulation`: expliciete voorbeeldscenario's voor leren en testen.
- `config`: veilige, gevalideerde instellingen.
- `observability`: uniforme diagnostische informatie.
- `main`: dun startpunt dat invoer naar de juiste use-case leidt.

## Toekomstige mobiele app

De iOS/SwiftUI-app wordt later een client van een beveiligde server-API. Zij krijgt
geen brokergeheimen en voert geen kernlogica lokaal uit. Iedere order blijft op de
server authenticatie, validatie, risicocontrole en auditlogging doorlopen.

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

## Grenzen na Fase 1

Geen database, externe marktdata, netwerkverkeer, backtest-engine, AI, paper broker of
live broker. Alle portfolio- en transactie-informatie leeft tijdelijk in het geheugen.
