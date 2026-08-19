# Fase 3 — Risk engine

## Doel

Risico onafhankelijk van strategie of toekomstige AI afdwingen voordat een order de
uitvoerende brokeradapter kan bereiken.

## Afgeronde deliverables

- [x] Centraal, gevalideerd `RiskPolicy` met veilige standaardwaarden.
- [x] Maximale kooporderwaarde.
- [x] Maximale absolute positiewaarde.
- [x] Maximale concentratie per instrument.
- [x] Minimale cashreserve na aankoop.
- [x] Dagverlieslimiet voor nieuw kooprisico.
- [x] Kill switch die iedere order blokkeert.
- [x] Samenstelbare regels met stabiele codes en leesbare redenen.
- [x] Fail-safe afwijzing wanneer een regel technisch faalt.
- [x] Onveranderlijk auditlog van goedkeuringen én afwijzingen.
- [x] Controle van equity tegen cash en actuele positieprijzen.
- [x] Verplichte risicopoort in demo en backtest.
- [x] Scenario-, grens- en stresstests.
- [x] Zichtbare terminaldemo met goedkeuring, afwijzing en noodstop.

## Bewuste grenzen

- Verkooporders mogen blootstelling reduceren ondanks normale limieten of dagverlies.
- Een actieve kill switch blokkeert ook verkopen; beheerdersliquidatie komt later.
- Dagverlies wordt door de aanroepende sessie ten opzichte van een vast dagstartpunt
  aangeleverd en door de context op type en geldigheid gecontroleerd.
- Geen sector-, correlatie-, volatiliteits- of liquiditeitslimieten in deze fase.
- Geen gebruikersspecifieke profielen totdat authenticatie en accounts bestaan.

## Klaar wanneer

Geen applicatie- of backtestorder bereikt de simulator zonder geslaagde controle, iedere
uitkomst is achteraf uitlegbaar en alle automatische tests slagen.
