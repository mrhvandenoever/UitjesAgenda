# Overleg — UitjesAgenda

Werkdocument voor het plan-overleg. Vul aan tijdens het gesprek.

## Aanleiding
- Andere pc (met de wekelijkse Cowork scheduled task "uitjes-agenda-refresh") moet gerepareerd worden.
- Deze laptop is tijdelijk (of structureel?) ingericht om dezelfde refresh te kunnen draaien: Python geïnstalleerd, repo gecloned naar `C:\dev\uitjesagenda`.
- Laatste live update: commit van 6 juli 2026 — ruim 5 weken oud.

## Open vragen / te bespreken

### 1. Waar draait de wekelijkse refresh voortaan?
- Tijdelijk op deze laptop tot de andere pc terug is?
- Structureel verhuizen?
- Scheduled task ("uitjes-agenda-refresh", maandag 08:04) moet dan ook verhuisd/opnieuw ingesteld worden.
- **2026-08-14**: als de andere pc vandaag gerepareerd is, draait de refresh daar weer — nog niet bevestigd, voorlopig dus.

### 2. Slimmer scrapen (efficiëntie)
- Huidige situatie: elke scraper haalt bij elke run alle pagina's opnieuw op (bv. drenthe.nl: 34+ pagina's, duurde >3 min).
- Idee (rsync/delta-achtig) afgewogen:
  - **Early-stop bij eerste "alles al bekend"-pagina** — simpel, maar riskant: nieuwe events kunnen ook op oudere pagina's worden ingevoegd (niet gegarandeerd chronologisch/append-only).
  - **Per-pagina hash-caching** — blijft elke pagina ophalen (dus niets gemist), slaat alleen parse/DB-stap over bij ongewijzigde pagina-inhoud. Bespaart CPU/DB-tijd, niet netwerktijd.
  - **Parallelle requests** — waarschijnlijk de grootste tijdswinst als de bottleneck vooral het aantal sequentiële HTTP-requests is (lijkt hier het geval).
  - Voorstel: hash-caching + parallelisatie combineren, geen early-stop.

### 3. SPOT Groningen — Oosterpoort vs Stadsschouwburg — OPGELOST 2026-08-11
- Bleek geen extra request per event nodig: SPOT's eigen programma-pagina heeft de locatie al in een `data-location`-attribuut per event (plus een genre-signaal via `data-genres`/`data-subgenres`). Nieuwe `scrape_spotgroningen.py` gebouwd, zie `decisions.md`.

### 4. Generieke/kapotte event-links (26 van ~50 bronnen) — grotendeels opgelost
- **denieuwekolk.nl**: opgelost bij de scraper-herbouw (2026-08-13), zie decisions.md.
- **2026-08-14 opgelost**: FC Twente, SC Cambuur, Go Ahead Eagles, PEC Zwolle (ESPN.nl bleek een `"id"`-veld per wedstrijd te hebben → `https://www.espn.nl/voetbal/wedstrijd/_/gameId/{id}`, i.p.v. steeds de teampagina) en Martiniplaza (theater.nl's JSON-LD had de echte URL niet in het `url`-veld maar in `@id` — simpele fix).
- **Resterend, bewust ongewijzigd**: E&O, Hurry-Up, FC Groningen, Donar en de overige sportclubs linken naar een algemene wedstrijdkalender omdat er geen aparte per-wedstrijd-pagina beschikbaar is — dat is prima, geen fix nodig.
- **Resterend, nog kapot**: de grote landelijke podia (TivoliVredenburg, Melkweg, Atlastheater, Doornroosje, 013, Effenaar, Ahoy, Koornbeurs, Vera, Ziggo Dome, Paradiso, Neushoorn) — vallen samen met de AI/Chrome-lijst (zie punt 6-achtig probleem: zonder JS-rendering komen we sowieso niet aan hun events, laat staan aan per-event-links). Wordt in principe vanzelf meegenomen zodra die bronnen met Chrome MCP aangepakt worden.

### 5. Nationale sportteams toevoegen
- Idee van Michiel: naast clubs ook de nationale selecties meenemen (bv. Oranje Dames volleybal — https://www.volleybal.nl/volleybal/oranje-dames/programma). Concreet aanleiding: ze oefenen komend weekend in Groningen (Martiniplaza).
- Te bepalen: alleen wedstrijden die daadwerkelijk in Noord-Nederland/landelijke podia gespeeld worden (zoals dit Martiniplaza-voorbeeld), of alle interlands/toernooien ongeacht locatie? Dat laatste past minder bij de regionale insteek van de tool.
- Welke bonden/sporten: alleen volleybal, of ook handbal/korfbal/basketbal/hockey nationale teams als ze in de regio spelen?
- Nevobo (volleybal) gebruikt dezelfde API-structuur als de clubteams (api.nevobo.nl RSS) — waarschijnlijk ook bruikbaar voor het nationale team, even checken.

### 6. Landelijke uitbreiding
- Ambitie: de tool op termijn landelijk maken (nu vooral Noord-Nederland + een aantal landelijke podia).
- Nader te bepalen: schaal (hoeveel bronnen/pagina's erbij), of de huidige scraper-architectuur dat aankan, prioritering t.o.v. de andere open items.

### 7. Weekelijkse-refresh-script laten meegroeien
- Nu (in `ARCHITECTURE.md`): elke scraper apart bij naam genoemd in de Cowork-scheduled-task-commandolijst. Bij 40+ losse `scrape_<naam>.py`-bestanden (zie punt 8 / `SCRAPERS.md`) wordt dat een lange, makkelijk-te-vergeten-lijst.
- Idee: omzetten naar `for f in scrape_*.py: python $f` (met evt. een expliciete uitzonderingslijst voor scripts die niet standaard wekelijks moeten draaien). Nog niet besloten/gebouwd.

### 8. Scraper-architectuur: één bestand per venue — AFGESPROKEN 2026-08-11
- Michiel's voorstel: voor elke venue een eigen, klein `scrape_<naam>.py`-bestand, ook als dat duplicatie tussen scripts betekent — makkelijker te debuggen (fout = precies dat ene bestand) en veiliger te editen dan één groot gedeeld scraper-bestand.
- Akkoord, sluit aan bij de KRITIEKE REGEL over `gen_uitjes.py`-truncatie in ARCHITECTURE.md. Vastgelegd in `decisions.md`.
- `SCRAPERS.md` toegevoegd: overzicht per bron of er al een script is, of het zonder AI kan (recipe klaar), of het AI/Chrome vereist (client-rendered site), of nog nooit geprobeerd.
- Einddoel: wekelijkse refresh volledig zonder AI — AI alleen eenmalig gebruiken om een scrape-methode te ontdekken (zoals bij SPOT/handbal.nl gebeurde), niet structureel bij elke run.

### 9. Favorieten: volg een specifieke act/team
- Idee van Michiel: een sportteam, band, theatergezelschap, cabaretier of andere act kunnen selecteren als "favoriet", en dan zien waar en wanneer die optreedt — over alle bronnen/venues heen.
- Interessante ontwerpvragen:
  - Hoe herken je "dezelfde act" over verschillende bronnen heen als de titeltekst steeds anders is (bv. "Peter Bernstein Quartet" bij SPOT vs. een net iets andere titel bij een aggregator)? Zelfde soort matching-probleem als bij de cross-source dedup, maar dan voor identiteit i.p.v. duplicaten.
  - UI: een simpele naam-zoekfunctie/autocomplete over alle titels, of een echte "favorieten"-lijst die lokaal (browser) wordt opgeslagen?
  - Notificatie erbij (bv. "nieuw optreden toegevoegd voor favoriet X"), of alleen een filter/overzicht?
  - Sport past hier natuurlijk al goed bij (club-filter bestaat al) — dit zou het generaliseren naar willekeurige artiesten/gezelschappen ook buiten sport.
- Nog niet uitgewerkt, puur een ideeschets.

## Status
Sessie 2026-08-10/11 afgerond — zie `plan.md` voor het volledige overzicht van wat gedaan is. Volgende sessie: verder met de scraper-uitbreiding (zie `plan.md` en `SCRAPERS.md`) en de nog openstaande discussiepunten hierboven (1, 2, 4, 5, 6, 7).
