# Alpaca Paper-integratiechecklist

## Nu voltooid

- [x] Alpaca achter het brokerneutrale async contract geplaatst.
- [x] Live Alpaca-endpoint technisch geweigerd.
- [x] Credentials uitsluitend via omgevingsvariabelen.
- [x] USD en voornaamste Amerikaanse beurzen toegevoegd.
- [x] Account, posities en IEX-latest trade vertaald.
- [x] Limitorder met client-order-ID geïmplementeerd.
- [x] Orderstatus, annulering en reconciliatie geïmplementeerd.
- [x] Tijdelijke fouten geschikt gemaakt voor begrensde retries.
- [x] Volledig offline getest met nagebootste API-antwoorden.

## Na het aanmaken van een Alpaca Paper-account

- [x] Paper API-sleutels lokaal instellen; nooit opslaan in Git.
- [x] Alleen-lezen `broker-ai alpaca-check` uitvoeren.
- [x] Begeleide eerste order met exacte bevestiging en verplichte risk engine bouwen.
- [x] Eén kleine handmatig bevestigde paper-order uitvoeren.
- [x] Orderuitvoering in het Alpaca-dashboard controleren.
- [x] Idempotente orders, posities en sync-runs naar SQLite synchroniseren.
- [ ] Gesynchroniseerde order met Broker AI-API en auditlog vergelijken.
- [ ] Annulering, gedeeltelijke uitvoering en markt-sluiting observeren.
- [ ] Dagelijkse reconciliatie en waarschuwingen activeren.
- [ ] Minimaal meerdere weken zonder echt geld evalueren.

## Bewust nog niet toegestaan

- Alpaca Live Trading.
- Een order rechtstreeks vanuit een bot naar Alpaca sturen.
- API-sleutels in de mobiele app plaatsen.
- Fractionele aandelen of crypto zonder aangepaste domein- en risicomodellen.
- Migratie naar IBKR voordat paper trading aantoonbaar betrouwbaar is.
