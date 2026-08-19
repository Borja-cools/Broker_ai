# Fase 4 — Broker-adapter

## Doel

Brokerafhankelijkheid isoleren achter één stabiel contract en betrouwbare externe
communicatie nabootsen zonder account, netwerk of echt geld.

## Afgeronde deliverables

- [x] Async brokercontract voor marktdata, account, status en orders.
- [x] Brokerneutrale account-, positie-, verbinding- en ordermodellen.
- [x] Simulatoradapter met onmiddellijke lokale uitvoering.
- [x] Lokale paper-adapter met submitted-status en latere reconciliatie.
- [x] Orderstatus opvragen en open paperorders annuleren.
- [x] Idempotente indiening, annulering en reconciliatie.
- [x] Conflict bij hergebruik van dezelfde ID voor andere orderinhoud.
- [x] Begrensde retries voor tijdelijke fouten en verloren antwoorden.
- [x] Time-outs en vertaling naar stabiele interne fouttypes.
- [x] Verbindingsstatus en fail-closed gedrag bij disconnectie.
- [x] Async risk gateway vóór iedere paper-order.
- [x] Dezelfde contracttests voor simulator- en paper-adapter.
- [x] Tests voor time-out, retries en dubbele-orderpreventie.
- [x] Veilige terminaldemo zonder extern account.

## Bewuste grenzen

- `LocalPaperBrokerAdapter` is offline en geen koppeling met een echte broker.
- Brokerstatus en orders leven nog in het geheugen en verdwijnen bij herstart.
- Geen gedeeltelijke fills, limietorders, streaming koersen of beurskalender.
- Geen API-sleutels of brokerkeuze nodig in deze fase.
- Een externe paper-adapter volgt pas na beoordeling van beschikbaarheid, kosten,
  regelgeving, paper-functies en API-kwaliteit.

## Klaar wanneer

Simulator en lokale paper-adapter door dezelfde contracttests komen, retries nooit
dubbele orders maken, statusreconciliatie werkt en riskcode niet brokerspecifiek is.
