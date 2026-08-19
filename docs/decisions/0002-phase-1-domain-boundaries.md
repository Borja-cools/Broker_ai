# ADR 0002 — Domeingrenzen van Fase 1

- Status: geaccepteerd
- Datum: 2026-08-19

## Context

Fase 1 moet de financiële kern betrouwbaar maken zonder keuzes over externe brokers,
dataleveranciers of opslag te vroeg vast te zetten.

## Beslissing

De simulator ondersteunt voorlopig:

- uitsluitend EUR;
- uitsluitend gehele aantallen aandelen;
- koop en verkoop tegen een expliciet opgegeven positieve prijs;
- onmiddellijke, volledige uitvoering of volledige afwijzing;
- vaste transactiekosten per order;
- één tijdzonebewuste marktprijs per instrument voor een waarderingsmoment;
- een onveranderlijk transactielog in het geheugen.

## Gevolgen

- Resultaten zijn deterministisch en eenvoudig te testen.
- Fractionele aandelen, meerdere valuta, partial fills, spread en slippage zijn nog niet
  ondersteund.
- De expliciete orderprijs is simulatie-invoer en geen actuele marktprijs uit een feed.
- Het auditlog verdwijnt na processtop; duurzame opslag komt in een latere fase.
- De volgende fase kan historische prijzen en backtesting toevoegen zonder de kernmodellen
  afhankelijk te maken van een dataleverancier.
