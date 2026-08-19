# Beslissing 0004 — Verplichte risicopoort vóór brokeruitvoering

## Status

Geaccepteerd voor Fase 3.

## Context

Strategieën en toekomstige AI kunnen fouten maken of te agressieve orders voorstellen.
Risicobeheer mag daarom niet in een strategie verstopt zitten en mag niet optioneel
worden wanneer later een andere brokeradapter wordt aangesloten.

## Beslissing

- Applicatie- en backtestorders lopen via `RiskManagedBroker`.
- De `RiskEngine` evalueert iedere regel en schrijft altijd één `RiskAssessment`.
- Alleen volledige goedkeuring geeft toegang tot de brokeradapter.
- Een onverwachte regelfout wordt fail-safe als afwijzing behandeld.
- De kill switch blokkeert zowel koop- als verkooporders.
- Blootstellings- en verlieslimieten blokkeren aankopen, maar laten risicoreducerende
  verkopen toe zolang de kill switch uitstaat.
- De context controleert zelf of equity overeenkomt met cash en actuele positieprijzen.

## Standaardparameters

- Maximale kooporder: €2.500.
- Maximale positie: €5.000.
- Maximale concentratie: 25%.
- Minimale cashreserve: 10%.
- Maximaal dagverlies voor nieuwe aankopen: 3%.

Deze waarden zijn conservatieve softwarestandaarden voor de simulator, geen persoonlijk
beleggingsadvies. Voor paper trading worden ze opnieuw expliciet gekozen.

## Gevolgen

Een strategie kan risico niet zelfstandig uitschakelen. Toekomstige API- en brokerlagen
moeten dezelfde poort gebruiken. Een operationele liquidatie terwijl de kill switch
actief is vereist later een afzonderlijke, streng geauthenticeerde beheerprocedure.
