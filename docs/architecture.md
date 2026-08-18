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
Order → SimulatedBroker → Portfolio
      ↓
Execution en terminalrapport
```

## Verantwoordelijkheden

- `domain`: financiële begrippen en invarianten; geen externe verbindingen.
- `brokers`: uitvoering achter een brokergrens; nu uitsluitend lokaal.
- `simulation`: expliciete voorbeeldscenario's voor leren en testen.
- `config`: veilige, gevalideerde instellingen.
- `observability`: uniforme diagnostische informatie.
- `main`: dun startpunt dat invoer naar de juiste use-case leidt.

## Toekomstige mobiele app

De iOS/SwiftUI-app wordt later een client van een beveiligde server-API. Zij krijgt
geen brokergeheimen en voert geen kernlogica lokaal uit. Iedere order blijft op de
server authenticatie, validatie, risicocontrole en auditlogging doorlopen.

## Grenzen van Fase 0

Geen database, actuele marktdata, netwerkverkeer, AI, paper broker of live broker.
Alle portfolio-informatie leeft tijdelijk in het geheugen.
