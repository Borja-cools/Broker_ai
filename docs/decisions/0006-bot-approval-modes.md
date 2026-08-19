# Beslissing 0006 — Gespecialiseerde bots met goedkeuringsmodi

## Status

Geaccepteerd voor Fase 5.

## Beslissing

Iedere bot krijgt een identiteit, specialisatie, status, automatische orderlimiet en één
van drie modi: `manual`, `automatic_limited` of `disabled`. Kleine voorstellen van een
actieve beperkt-automatische bot kunnen `auto_approved` worden. Een groter voorstel valt
terug naar `pending_approval`; een gepauzeerde of uitgeschakelde bot wordt geweigerd.

Automatische goedkeuring is nadrukkelijk geen brokeruitvoering. De centrale risk engine
blijft vóór iedere uiteindelijke order verplicht. Daardoor kunnen snelle bots handelen
zonder menselijke vertraging, maar alleen binnen vooraf goedgekeurde grenzen.

## Gevolgen

Het dashboard kan iedere bot apart tonen en pauzeren. Orders, analyses en auditlogs zijn
aan een `bot_id` gekoppeld. Crypto-specifieke fractionele hoeveelheden zijn al mogelijk
in API-voorstellen, terwijl het bestaande aandelendomein voorlopig gehele aandelen houdt.
