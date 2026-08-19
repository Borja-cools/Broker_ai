# Beslissing 0005 — Asynchroon en idempotent brokercontract

## Status

Geaccepteerd voor Fase 4.

## Context

Een echte broker-API kan traag zijn, tijdelijk uitvallen of een antwoord verliezen nadat
de order al werd aangenomen. Bovendien is indienen niet hetzelfde als uitvoeren: een
order kan enige tijd submitted blijven, geannuleerd worden of later worden afgewezen.

## Beslissing

- Alle brokerbewerkingen volgen één asynchroon `BrokerInterface`.
- Het contract bevat status, marktprijs, account, indienen, opvragen, annuleren en
  reconciliëren.
- De interne `order_id` is de idempotency-sleutel.
- Dezelfde ID plus dezelfde inhoud geeft exact dezelfde brokerorder terug.
- Dezelfde ID plus andere inhoud levert een expliciet conflict op.
- Iedere bewerking heeft een time-out en maximaal drie pogingen bij tijdelijke fouten.
- Annuleren en reconciliëren zijn eveneens idempotent.
- De bestaande risk engine blijft vóór async orderindiening verplicht.

## Gevolgen

Strategieën en riskregels kennen geen brokerspecifieke API. Een toekomstige externe
paper-adapter kan de lokale adapter vervangen zonder die lagen aan te passen. Retries
zijn alleen veilig omdat orderindiening idempotent is. Alle statussen worden later in
de database opgeslagen en via het dashboard zichtbaar gemaakt.
