# ADR 0001 — Simulation-first en live trading afwezig

- Status: geaccepteerd
- Datum: 2026-08-18

## Context

Broker AI wordt gebouwd als leerproject en kan later financiële acties ondersteunen.
Een onvolwassen systeem rechtstreeks met een broker verbinden creëert onnodig risico.

## Beslissing

Fase 0 ondersteunt uitsluitend `simulation`. Live trading is niet alleen uitgeschakeld;
de benodigde modus en adapter bestaan niet. Orders worden alleen verwerkt door een
lokale `SimulatedBroker` en gegevens verdwijnen na het stoppen van het proces.

## Gevolgen

- Verkeerde configuratie kan live trading niet activeren.
- Domeinlogica kan veilig en deterministisch worden getest.
- Een toekomstige paper/live adapter moet hetzelfde contract en extra controles krijgen.
- Iedere uitbreiding behoudt menselijke controle en een fail-closed standaard.
