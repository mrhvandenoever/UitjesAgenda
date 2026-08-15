# Overleg — UitjesAgenda

Werkdocument voor het plan-overleg. Vul aan tijdens het gesprek.

## Aanleiding
- Andere pc (met de wekelijkse Cowork scheduled task "uitjes-agenda-refresh") moet gerepareerd worden.
- Deze laptop is tijdelijk (of structureel?) ingericht om dezelfde refresh te kunnen draaien: Python geïnstalleerd, repo gecloned naar `C:\dev\uitjesagenda`.
- Laatste live update: commit van 6 juli 2026 — ruim 5 weken oud.

## Open vragen / te bespreken

### 1. Waar draait de wekelijkse refresh voortaan? — OPGELOST 2026-08-15
- **Besluit**: structureel op deze laptop (`C:\dev\uitjesagenda`), niet de andere pc.
- Windows Taakplanner-taak "uitjes-agenda-refresh" opnieuw ingesteld: **ma/wo/za 04:00** (was maandag 08:04), draait `weekly_refresh.ps1`, `LogonType S4U` (draait ongeacht inlogstatus, geen wachtwoord opgeslagen). Zie `decisions.md` en ARCHITECTURE.md §Wekelijkse refresh.

### 2. Slimmer scrapen (efficiëntie) — hash-caching GEBOUWD 2026-08-14
- Huidige situatie: elke scraper haalt bij elke run alle pagina's opnieuw op (bv. drenthe.nl: 34+ pagina's, duurde >3 min).
- Idee (rsync/delta-achtig) afgewogen:
  - **Early-stop bij eerste "alles al bekend"-pagina** — simpel, maar riskant: nieuwe events kunnen ook op oudere pagina's worden ingevoegd (niet gegarandeerd chronologisch/append-only). Bewust niet gekozen.
  - **Hash-caching** — blijft elke pagina ophalen (dus niets gemist), slaat alleen parse/DB-stap over bij ongewijzigde data. Bespaart CPU/DB-tijd, niet netwerktijd.
  - **Parallelle requests** — waarschijnlijk de grootste tijdswinst als de bottleneck vooral het aantal sequentiële HTTP-requests is (lijkt hier het geval). Nog niet gebouwd, apart punt.
- **2026-08-14**: `page_cache.py` gebouwd (hash-cache in `events.db`, zie ARCHITECTURE.md §Change-detection) en uitgerold naar alle 30 live-scrapende `scrape_*.py`-bestanden — Michiel akkoord: "changedetection voor 31 scripts: prima" (31e, `scrape_handmatig.py`, bewust overgeslagen: vaste jaarevents, niets te cachen). Getest en werkt zoals bedoeld.
- **Nog open**: parallelle requests (aparte, grotere wijziging — netwerktijd i.p.v. CPU/DB-tijd) is niet meegenomen in deze ronde.

### 3. SPOT Groningen — Oosterpoort vs Stadsschouwburg — OPGELOST 2026-08-11
- Bleek geen extra request per event nodig: SPOT's eigen programma-pagina heeft de locatie al in een `data-location`-attribuut per event (plus een genre-signaal via `data-genres`/`data-subgenres`). Nieuwe `scrape_spotgroningen.py` gebouwd, zie `decisions.md`.

### 4. Generieke/kapotte event-links (26 van ~50 bronnen) — OPGELOST 2026-08-15
- **denieuwekolk.nl**: opgelost bij de scraper-herbouw (2026-08-13), zie decisions.md.
- **2026-08-14 opgelost**: FC Twente, SC Cambuur, Go Ahead Eagles, PEC Zwolle (ESPN.nl bleek een `"id"`-veld per wedstrijd te hebben → `https://www.espn.nl/voetbal/wedstrijd/_/gameId/{id}`, i.p.v. steeds de teampagina) en Martiniplaza (theater.nl's JSON-LD had de echte URL niet in het `url`-veld maar in `@id` — simpele fix).
- **Resterend, bewust ongewijzigd**: E&O, Hurry-Up, FC Groningen, Donar en de overige sportclubs linken naar een algemene wedstrijdkalender omdat er geen aparte per-wedstrijd-pagina beschikbaar is — dat is prima, geen fix nodig.
- **2026-08-15 alsnog opgelost**: de destijds nog kapotte grote landelijke podia (TivoliVredenburg, Melkweg, Atlastheater, Doornroosje, 013, Effenaar, Ahoy, Koornbeurs, Vera, Ziggo Dome, Paradiso, Neushoorn) hebben nu allemaal echte per-event-URL's — kwam vanzelf mee toen deze bronnen als onderdeel van de "31 AI/Chrome-bronnen"-marathon (zie SCRAPERS.md/decisions.md) een eigen scraper kregen (Ticketmaster-API of Playwright, geen echte AI/Chrome-MCP-inzet nodig gebleken). Punt is nu volledig afgesloten.

### 5. Nationale sportteams toevoegen
- Idee van Michiel: naast clubs ook de nationale selecties meenemen (bv. Oranje Dames volleybal — https://www.volleybal.nl/volleybal/oranje-dames/programma). Concreet aanleiding: ze oefenen komend weekend in Groningen (Martiniplaza).
- Te bepalen: alleen wedstrijden die daadwerkelijk in Noord-Nederland/landelijke podia gespeeld worden (zoals dit Martiniplaza-voorbeeld), of alle interlands/toernooien ongeacht locatie? Dat laatste past minder bij de regionale insteek van de tool.
- Welke bonden/sporten: alleen volleybal, of ook handbal/korfbal/basketbal/hockey nationale teams als ze in de regio spelen?
- Nevobo (volleybal) gebruikt dezelfde API-structuur als de clubteams (api.nevobo.nl RSS) — waarschijnlijk ook bruikbaar voor het nationale team, even checken.

### 6. Landelijke uitbreiding
- Ambitie: de tool op termijn landelijk maken (nu vooral Noord-Nederland + een aantal landelijke podia).
- Nader te bepalen: schaal (hoeveel bronnen/pagina's erbij), of de huidige scraper-architectuur dat aankan, prioritering t.o.v. de andere open items.

### 7. Weekelijkse-refresh-script laten meegroeien — OPGELOST 2026-08-14
- Was: elke scraper apart bij naam genoemd in de Cowork-scheduled-task-commandolijst — liep binnen twee sessies drie kwart achter (31 scrapers bestonden, de lijst noemde er nog 7).
- Nu: `run_weekly_refresh.py` — globt zelf alle `scrape_*.py`-bestanden, geen lijst meer om bij te houden. Uitzonderen kan door geen `scrape_`-prefix te gebruiken.
- Extra: zelf-herstellend gedrag. Een scraper met een harde fout (crash/fetch-failure) wordt automatisch hernoemd naar `fix_<naam>.py` — matcht de glob niet meer, dus wordt overgeslagen tot iemand het repareert. Scrapers die succesvol 0 events vinden worden niet hernoemd (kan legitiem zijn) maar wel gerapporteerd om te checken.
- Zie ARCHITECTURE.md §Wekelijkse refresh en de docstring van `run_weekly_refresh.py`.
- **Nog open**: change-detection/caching (zie punt 2 hierboven) — het mechanisme is nog niet gebouwd, alleen het idee (hash-cache per pagina) staat vast. Wordt apart opgepakt, niet meegenomen in deze refactor.

### 8. Scraper-architectuur: één bestand per venue — AFGESPROKEN 2026-08-11
- Michiel's voorstel: voor elke venue een eigen, klein `scrape_<naam>.py`-bestand, ook als dat duplicatie tussen scripts betekent — makkelijker te debuggen (fout = precies dat ene bestand) en veiliger te editen dan één groot gedeeld scraper-bestand.
- Akkoord, sluit aan bij de KRITIEKE REGEL over `gen_uitjes.py`-truncatie in ARCHITECTURE.md. Vastgelegd in `decisions.md`.
- `SCRAPERS.md` toegevoegd: overzicht per bron of er al een script is, of het zonder AI kan (recipe klaar), of het AI/Chrome vereist (client-rendered site), of nog nooit geprobeerd.
- Einddoel: wekelijkse refresh volledig zonder AI — AI alleen eenmalig gebruiken om een scrape-methode te ontdekken (zoals bij SPOT/handbal.nl gebeurde), niet structureel bij elke run.

### 9. Favorieten: volg een specifieke act/team — RICHTING BEVESTIGD 2026-08-15
- Idee van Michiel: een sportteam, band, theatergezelschap, cabaretier of andere act kunnen selecteren als "favoriet", en dan zien waar en wanneer die optreedt — over alle bronnen/venues heen. Bevestigd 2026-08-15 (naar aanleiding van de bredere "nog drie knoppen erbij"-brainstorm, zie ook punt 11) als één van drie nieuwe topniveau-knoppen naast Uitjes/Sport/Exposities.
- Interessante ontwerpvragen, nog open:
  - Hoe herken je "dezelfde act" over verschillende bronnen heen als de titeltekst steeds anders is (bv. "Peter Bernstein Quartet" bij SPOT vs. een net iets andere titel bij een aggregator)? Zelfde soort matching-probleem als bij de cross-source dedup, maar dan voor identiteit i.p.v. duplicaten.
  - UI: een simpele naam-zoekfunctie/autocomplete over alle titels, of een echte "favorieten"-lijst die lokaal (browser) wordt opgeslagen?
  - Notificatie erbij (bv. "nieuw optreden toegevoegd voor favoriet X"), of alleen een filter/overzicht?
  - Sport past hier natuurlijk al goed bij (club-filter bestaat al) — dit zou het generaliseren naar willekeurige artiesten/gezelschappen ook buiten sport.
- Nog niet technisch uitgewerkt — richting staat vast, ontwerp (matching, UI, opslag) nog te doen.

### 10. Exposities als eigen topniveau-modus — GEBOUWD 2026-08-16
- Aanleiding: `genre='expo'` bestaat al binnen "Uitjes", maar exposities zijn wezenlijk anders (lopen weken/maanden, geen vast tijdstip) en horen niet tussen concerten/wedstrijden op één dag.
- **Besloten**: eigen derde knop naast Uitjes en Sport (zie ook punt 11).
- **Het "verdwijn-probleem" opgelost middels route A** (Michiels voorkeur): exposities altijd tonen, tenzij er een bekende `date_end` is die al voorbij is. `date_end` staat al in het datamodel (DB-schema + export) maar wordt nog nergens door `gen_uitjes.py` gelezen/getoond — dode infrastructuur die hiervoor wakker gemaakt moet worden. Bijna geen enkele scraper vult 'm vandaag echt in (van 6669 events heeft er 1 een `date_end`, en die ziet eruit als een placeholder).
- **Sortering**: default op startdatum, met alfabetisch en op-einddatum als alternatieve sorteeropties (gebruiker kiest).
- **Afstandsfilter**: blijft gewoon werken, geen uitzondering voor Exposities.
- **Gebouwd 2026-08-16**: derde topniveau-knop "🖼️ Exposities", route A geïmplementeerd, sortering (startdatum/einddatum/alfabetisch) en provincie/afstandsfilter werken. Zie ARCHITECTURE.md §Exposities en decisions.md 2026-08-16 voor de volledige technische uitwerking, inclusief 2 bugs die tijdens de bouw gevonden en gefixt zijn.
- **Nog open**:
  - Welke scrapers eerst `date_end` laten invullen? Kandidaten: bestaande expo-bronnen (Groninger/Drents Museum zodra die ooit lukken) en het eerder bewust overgeslagen Geke Hoogstins (decisions.md: "maandenlange doorlopende exposities, geen losse datums, past niet in ons single-date-event-model" — deze beslissing kan nu mogelijk herzien worden, zie plan.md).

### 11. Twee extra topniveau-knoppen: Favorieten + Admin — RICHTING BEPAALD 2026-08-15
- Michiel wil in totaal 3 nieuwe knoppen naast Uitjes/Sport: **Exposities** (punt 10), **Favorieten** (punt 9) en **Admin**.
- **Admin — scope afgebakend**: alleen een lokale/read-only weergave (bv. scraper-status, event-aantallen per bron, laatst-gedraaide-refresh-informatie) — GEEN backend, GEEN mogelijkheid om events te bewerken/verwijderen via de site. Bewuste keuze om het "volledig statisch, geen backend"-architectuurprincipe (zie ARCHITECTURE.md/decisions.md) niet te doorbreken — dat zou inlog + een backend vereisen, een grote stap die nu niet gewenst is.
- **Nog open**: exacte inhoud/vormgeving van het Admin-scherm (welke metrics precies, hoe "lokaal-only" technisch werkt — bv. alleen zichtbaar op localhost, of een verborgen/niet-gelinkte URL op de live site, of een apart lokaal script/bestand los van `index.html`).
- Nog niets van deze 3 knoppen is gebouwd — dit is de vastgelegde richting uit een brainstormsessie, technische uitwerking volgt in een latere sessie.

## Status
Sessie 2026-08-15: GitHub gesynchroniseerd (17 commits ingehaald), punt 1 opgelost (Taakplanner-taak ma/wo/za 04:00), kritieke SSL-bug gefixt, 31 → 7 AI/Chrome-bronnen opgelost (26 nieuwe scrapers, zie SCRAPERS.md/decisions.md/plan.md — resterende 7 bewust geparkeerd als "moeilijk"), punt 4 (kapotte links) daarmee ook volledig afgesloten, Ticketmaster-API-key veilig opgezet. Sessie afgesloten met een productbrainstorm: 3 nieuwe topniveau-knoppen (Exposities/Favorieten/Admin) — richting bepaald, zie punten 9-11.

Sessie 2026-08-16: **Exposities gebouwd** (punt 10 nu volledig afgesloten) — zie ARCHITECTURE.md §Exposities/decisions.md voor de uitwerking, inclusief 2 bijgevangen bugs (`classify()`'s `'strip'`-substring-fout, en een ontbrekende `apply()`-call bij page-load die sportwedstrijden liet meerenderen in Uitjes-modus). Favorieten (punt 9) en Admin (punt 11) nog niet gebouwd. Nog openstaande discussiepunten: 2 (parallelle requests, niet gestart), 5, 6 (ideeschetsen, nog niet uitgewerkt).
