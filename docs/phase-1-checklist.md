# Fase 1 — Afrondingschecklist

## Domeinmodellen

- [x] Instrument met symbool, naam, beurs, valuta en type.
- [x] Tijdzonebewuste, positieve marktprijs.
- [x] Unieke en onveranderlijke koop- en verkooporder.
- [x] Positie met gewogen gemiddelde kostprijs.
- [x] Portefeuille met cash, posities en gerealiseerde winst.
- [x] Onveranderlijke transactie met orderkoppeling en uitvoeringstijdstip.

## Simulator

- [x] Koop en verkoop met volledige pre-validatie.
- [x] Onvoldoende cash of aandelen wordt zonder mutatie afgewezen.
- [x] Configureerbare vaste transactiekosten.
- [x] Kosten worden correct in kostbasis en resultaat verwerkt.
- [x] Iedere geslaagde order levert precies één auditrecord op.
- [x] Foutieve klok of dubbele transactie-ID verandert de portefeuille niet.

## Waardering

- [x] Positiewaarde en kostbasis.
- [x] Cash plus posities als totale portefeuillewaarde.
- [x] Gerealiseerde, ongerealiseerde en totale winst.
- [x] Ontbrekende of verkeerd gekoppelde marktprijs wordt geweigerd.

## Leren en kwaliteit

- [x] Terminaldemo toont koop, verkoop, kosten, waardering en auditlog.
- [x] Automatische tests dekken succes- en foutpaden.
- [x] Architectuur, beslissingen en begrippenlijst zijn bijgewerkt.
- [x] Geen netwerk-, broker-, AI- of databaseafhankelijkheid.

## Exitcriterium

Fase 1 is gereed wanneer alle tests slagen, de demo reproduceerbaar is en iedere
portefeuillemutatie via een gevalideerde simulatieorder en transactie te reconstrueren is.
Daarna kan Fase 2 historische marktdata, strategiecontracten en backtesting toevoegen.
