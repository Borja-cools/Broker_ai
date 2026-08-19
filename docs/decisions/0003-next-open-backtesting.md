# Beslissing 0003 — Signalen uitvoeren op de volgende opening

## Status

Geaccepteerd voor Fase 2.

## Context

Een strategie berekent haar advies met afgesloten dagkoersen. De slotkoers is pas na
het einde van die handelsdag volledig bekend. Uitvoering tegen diezelfde slotkoers zou
de simulator een onrealistische informatievoorsprong geven.

## Beslissing

- De strategie ontvangt alleen bars tot en met het huidige beslismoment.
- Het resulterende signaal wordt pas op de openingskoers van de volgende bar uitgevoerd.
- Koopprijzen worden verhoogd en verkoopprijzen verlaagd met configureerbare slippage.
- Vaste transactiekosten blijven bij iedere geslaagde order van toepassing.
- Aantallen blijven in deze fase gehele aandelen.

## Gevolgen

De resultaten zijn conservatiever en de tijdsvolgorde is eenvoudig te testen. Intraday-
strategieën, limietorders, gedeeltelijke fills en meerdere instrumenten vallen buiten
Fase 2 en kunnen later via nieuwe modellen worden toegevoegd.
