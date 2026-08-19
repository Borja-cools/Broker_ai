# Beslissing 0007 — Alpaca Paper vóór IBKR

## Status

Geaccepteerd.

## Context

Broker AI moet eerst met een echte externe API leren omgaan zonder financieel risico.
Alpaca biedt een afzonderlijke paperomgeving en een API die geschikt is voor deze stap.
Voor uiteindelijke live handel blijft Interactive Brokers een mogelijke keuze.

## Beslissing

- Alpaca Paper wordt de eerste externe brokerintegratie.
- De adapter weigert iedere andere trading-base-URL, inclusief Alpaca Live.
- Alle orders blijven door de centrale risk engine lopen.
- Strategieën, bots en mobiele clients kennen geen Alpaca-specifieke details.
- IBKR wordt later als tweede adapter achter hetzelfde `BrokerInterface` gebouwd.
- Live trading wordt niet geactiveerd door alleen een URL of sleutel te wijzigen.

## Gevolgen

We kunnen netwerkgedrag, orderstatussen en reconciliatie realistisch oefenen. Voor
Alpaca-aandelen ondersteunen we USD. Fractionele hoeveelheden en crypto vragen later
een bewuste uitbreiding van de financiële modellen en risicoregels.
