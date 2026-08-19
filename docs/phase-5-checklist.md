# Fase 5 — API, database en lokale server

## Afgeronde deliverables

- [x] FastAPI REST API met `/api/v1` en interactieve OpenAPI-documentatie.
- [x] SQLite-schema met expliciete migratieversie.
- [x] Opslag voor gebruikers, bots, snapshots, analyses, voorstellen en auditlogs.
- [x] Bearer-authenticatie met alleen gehashte tokens in de database.
- [x] Admin/viewer-autorisatie en rate limiting, ook voor mislukte aanmeldingen.
- [x] Strikte JSON- en financiële invoervalidatie.
- [x] Handmatige, beperkt automatische en uitgeschakelde botmodus.
- [x] Grotere automatische voorstellen vallen veilig terug naar handmatig.
- [x] Health check, metrics, request-ID en gestructureerde logging.
- [x] Geteste consistente SQLite-back-up.
- [x] Dockerfile, lokale compose-configuratie, non-root gebruiker en container-healthcheck.
- [x] API-tests van bron tot database en auditlog.

## Bewuste grenzen

- De server bindt standaard alleen aan `127.0.0.1`.
- API-token komt uitsluitend uit de omgeving en telt minimaal 32 tekens.
- Geen CORS, publieke registratie of wachtwoordlogin zolang er geen dashboard is.
- `auto_approved` voert nog niets uit; risk engine en broker blijven een aparte stap.
- SQLite is voor lokale ontwikkeling; PostgreSQL wordt gebruikt bij echte hosting.
- Dockerconfiguratie is voorbereiding en publiceert niets zelfstandig.

## Klaar wanneer

Een geauthenticeerde client kan veilig lezen, een bot aanmaken, een gevalideerd voorstel
indienen, dit laten beslissen en iedere actie in de database en auditlog terugvinden.
