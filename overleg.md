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

### 2. Slimmer scrapen (efficiëntie) — hash-caching + parallelle requests GEBOUWD 2026-08-16
- Huidige situatie: elke scraper haalt bij elke run alle pagina's opnieuw op (bv. drenthe.nl: 34+ pagina's, duurde >3 min).
- Idee (rsync/delta-achtig) afgewogen:
  - **Early-stop bij eerste "alles al bekend"-pagina** — simpel, maar riskant: nieuwe events kunnen ook op oudere pagina's worden ingevoegd (niet gegarandeerd chronologisch/append-only). Bewust niet gekozen.
  - **Hash-caching** — blijft elke pagina ophalen (dus niets gemist), slaat alleen parse/DB-stap over bij ongewijzigde data. Bespaart CPU/DB-tijd, niet netwerktijd.
  - **Parallelle requests** — waarschijnlijk de grootste tijdswinst als de bottleneck vooral het aantal sequentiële HTTP-requests is (lijkt hier het geval). Uitgewerkt 2026-08-16, zie hieronder.
- **2026-08-14**: `page_cache.py` gebouwd (hash-cache in `events.db`, zie ARCHITECTURE.md §Change-detection) en uitgerold naar alle 30 live-scrapende `scrape_*.py`-bestanden — Michiel akkoord: "changedetection voor 31 scripts: prima" (31e, `scrape_handmatig.py`, bewust overgeslagen: vaste jaarevents, niets te cachen). Getest en werkt zoals bedoeld.

**Parallelle requests — vastgelegd én gebouwd 2026-08-16** (eerst "alleen vastleggen", direct daarna alsnog "dit gaan we bouwen nu"). Twee onafhankelijke niveaus, beide gebouwd (A+B), zie decisions.md 2026-08-16 voor de volledige bouw-geschiedenis inclusief een echte bug die onderweg gevonden is:

- **Niveau A — tussen scrapers**: `run_weekly_refresh.py`'s hoofdlus draait 56 `scrape_*.py`-subprocessen nu via een `ThreadPoolExecutor` i.p.v. na elkaar, met **aparte concurrency-limieten per scraper-type**: 8 gelijktijdig voor plain-HTTP, 3 gelijktijdig voor Playwright (11 stuks, elk een eigen Chromium-proces — herkend door het bestand te grep'en op `"playwright"`, geen aparte config per script). Instelbaar via `--max-plain`/`--max-playwright` (op 1 zetten = oude sequentiële gedrag, handige noodrem).
- **Niveau B — binnen één scraper**: nieuwe helper `parallel_fetch.py` (`fetch_many()` voor bekend-aantal-pagina's-vooraf, `fetch_batches()` voor ontdek-terwijl-je-gaat), toegepast op de 7 scrapers met een echte multi-request paginaloop: `scrape_drenthe.py`, `scrape_friesland.py`, `scrape_visitgroningen.py`, `scrape_forum.py`, `scrape_kielzog.py`, `scrape_posthuistheater.py`, `scrape_paard.py`. Concertgebouw/GelreDome (Playwright-paginering) bewust buiten scope gehouden.
- **Randvoorwaarde, gebouwd**: `events_db.py`'s `get_conn()` gebruikt nu `PRAGMA journal_mode=WAL` + `busy_timeout=30000` — voorkomt "database is locked" bij gelijktijdig schrijvende scrapers.
- **Belangrijke bug gevonden tijdens het bouwen** (zie decisions.md): het eerste ontwerp van `fetch_batches()` gebruikte "0 events op de pagina" als stopsignaal — bleek voor drenthe.nl/visitgroningen.nl onbetrouwbaar (de site geeft voorbij het echte einde gewoon een fallback-pagina terug, dus "0 events" kwam nooit voor, en het ophalen liep door tot de veiligheidsgrens: 105 pagina's i.p.v. de echte ~41 bij drenthe.nl, 3m34s i.p.v. de uiteindelijke 13s). Gefixt door het stopsignaal te baseren op het ontbreken van een "volgende pagina"-link — dat signaal bleek wél altijd betrouwbaar. Les vastgelegd in `parallel_fetch.py`'s docstring voor toekomstige scrapers met hetzelfde patroon.
- **Resultaat, geverifieerd met een echte volle `run_weekly_refresh.py`-run** (2026-08-16, geen `--dry-run`): 56/56 scrapers OK, geen "database is locked"-fouten, geen self-healing-hernoemingen, drenthe.nl 3m34s → 13s (16x), visitgroningen.nl bleek met de fix zelfs ~70-80 pagina's te hebben i.p.v. de eerder aangenomen kleinere schatting (was eerst per ongeluk afgekapt op 60 pagina's, ook gefixt). Events-count na deze run: 6634 → 7734 (+1100, vooral visitgroningen +416 en friesland +346 die nu voor het eerst hun volledige dataset ophalen i.p.v. een deel te missen door de oude timeout-gevoelige sequentiële aanpak).

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

### 12. forum.nl: doorlopende exposities als losse rij per dag — OPGELOST 2026-08-17
- Bij de eerste volle refresh ná de Exposities-bouw (parallelle-requests-sessie) bleek Exposities plotseling van 4 naar 41 events te springen. Oorzaak: `forum.nl` levert "Marilyn Expositie" en "Storyworld" (2 doorlopende exposities) als een **aparte agenda-rij per dag** — 36 van de 41 expo-rijen waren dus eigenlijk maar 2 exposities, elk uitgesmeerd over tientallen dagelijkse duplicaten.
- Was hiervoor onzichtbaar: deze rijen zaten al die tijd al in de data (forum.nl scraped al sinds sessie 2026-08-13), maar gingen onopgemerkt schuil tussen duizenden Uitjes-events. Nu Exposities een kleine, aparte sectie is, viel dit meteen op.
- **Gekozen: optie A** — `scrape_forum.py` groepeert nu per slug **opeenvolgende kalenderdagen** tot één event met `date`/`date_end` via een nieuwe `merge_consecutive_days()`-functie (`date_end` alleen gezet bij een run >1 dag). Het genoemde risico (een exhibitie die tussentijds een dag dicht is) is netjes ondervangen: zo'n gat splitst automatisch in twee losse runs i.p.v. het gat te overbruggen — in de praktijk bleek dit zelfs meteen te gebeuren (Marilyn Expositie/Storyworld hebben een echt gat op 31 augustus, geverifieerd door 2x te fetchen: consistent afwezig, dus geen toevallige netwerk-hik). Bewust **niet** optie B (centrale dedup in `gen_uitjes.py`) — de per-slug-opeenvolgende-dagen-logica hoort bij deze ene bron, geen generiek patroon dat andere bronnen ook nodig hebben (nog).
- Bijkomend voordeel: de merge-logica raakt ALLE forum.nl-events met opeenvolgende dagen, niet alleen de 2 expo's — bv. "Taalhuis" (4 opeenvolgende dagen) werd ook 1 rij i.p.v. 4. Wekelijks-terugkerende dingen (Informatieplein-*, Rooftop Cinema — niet-opeenvolgende dagen) blijven terecht losse rijen.
- Resultaat: Exposities 41 → 9 (2x Marilyn Expositie + 2x Storyworld — elk gesplitst door het echte gat op 31 augustus —, 2x Groninger Museum, Geke Hoogstins, Concertgebouw, en een nieuwe Friesland-expo die met de volledigere data meekwam). Stale oude daily-duplicate-rijen (95 rijen) opgeruimd uit de DB, `page_hash` voor forum.nl meegewist (bekende valkuil, zie ARCHITECTURE.md §Change-detection). Zie decisions.md 2026-08-17 voor de volledige technische uitwerking.

### 13. Exposities uitbreiden: meer musea/galerieën als bron — KUNSTPUNT GEBOUWD 2026-08-17
- Michiel's idee: nu Exposities werkt, meer bronnen toevoegen dan de huidige 5 (groningermuseum, gekehoogstins.nl, en de 3 die toevallig via andere bronnen meekwamen). Genoemd: "Scheepvaartmuseum Groningen" en kunstgalerieën in het algemeen ("zijn er vast veel van").
- **Onderzoek gedaan (websearch, 2026-08-17) — een paar dingen gevonden die de keuze beïnvloeden:**
  - Het "Noordelijk Scheepvaartmuseum" heet niet meer zo: het is aan het transformeren naar **Museum aan de A** (breder museum over de stad/provincie, niet meer puur maritiem) en is **dicht tot minstens medio 2027** (verbouwing). Nu bouwen zou dus niets opleveren — pas relevant zodra het heropent. ([museumaandea.nl](https://museumaandea.nl/over-ons), [igogroningen.nl](https://www.igogroningen.nl/wat-te-doen/kunst-cultuur/noordelijk-scheepvaartmuseum-naar-museum-aan-de-a/))
  - Andere musea in Groningen stad die wél nu bestaan en niet in SCRAPERS.md staan: **GRID Grafisch Museum**, **Universiteitsmuseum Groningen**, **Synagoge Groningen** (Joodse geschiedenis/cultuur).
  - Kunstgalerieën blijken inderdaad talrijk — alleen al in Groningen stad: De Stadsgalerie, Kunstpunt, Noorderlicht Fotogalerie, Kunsthandel Richard ter Borg, Erik Zwezerijnen, ART & LEF, Block C, Fotogalerie Lichtzone, Galerie Forma Aktua, Galerie MooiMan, Galerie Noord, galerie with tsjalling, GalerieH200, Kunstlievend Genootschap Pictura, en waarschijnlijk meer — en dat is dan nog zonder Drenthe/Friesland meegeteld. Michiels vermoeden klopt dus: te veel om allemaal apart een scraper voor te bouwen volgens de bestaande "één bestand per bron"-aanpak. ([visitgroningen.nl](https://www.visitgroningen.nl/nl/blogs/10x-galeries-in-groningen), [kunstinzicht.nl](https://www.kunstinzicht.nl/kunst/regio/galeries/groningen.html))
  - **Veelbelovende kortere weg gevonden**: **Kunstpunt Groningen** (kunstpuntgroningen.nl) lijkt zelf een soort aggregator/agenda te zijn die exposities/events van meerdere Groninger kunstinstellingen tegelijk bundelt ("een kunstagenda... van alle Groninger's institutions", zie hun `/art-calendar/`-pagina). Als dat klopt en het scrapebaar is, dekt één scraper mogelijk een flink deel van "veel galerieën" tegelijk — vergelijkbaar met hoe drenthe.nl/friesland.nl/visitgroningen al werken als regionale aggregators voor Uitjes. Nog niet geverifieerd of de pagina server-rendered is en of de data er structureel/regex-baar uitziet.
- **Kunstpunt Groningen geverifieerd en gebouwd (2026-08-17)** — bleek inderdaad server-rendered en regex-baar. `scrape_kunstpuntgroningen.py`: 22-25 exposities per run (schommelt met het seizoen), toegevoegd aan `AGGREGATOR_SOURCES` (Michiels expliciete eis: "venue gaat boven de aggregator, zoals bij de uitjes" — werkt via dezelfde mechaniek als drenthe.nl/friesland.nl/visitgroningen). Dekt in de praktijk al Groninger Museum, Museum Nienoord, Synagoge Groningen, en tientallen kleine galerieën (K38, De Stadsgalerie, Galerie Noord, SIGN, Kunstruimte De Smederij, e.v.a.) in één keer — precies de kortere weg die gehoopt was. Zie decisions.md 2026-08-17 voor de volledige technische uitwerking, inclusief 2 bugs die onderweg gevonden zijn (een `classify()`-ontwerpfout die het `cats`-genre-signaal onbetrouwbaar maakte, en een cross-taal-dedup-gat dat "venue boven aggregator" ondanks de eis toch één keer liet falen).
- **Link-check (Michiels tweede eis) uitgevoerd**: de meeste kleine galerieën linken zelf alleen naar hun algemene homepage (geen eigen expositie-pagina) — Kunstpunt's eigen artikel-URL per expositie is daarom de specifiekste beschikbare link, en is wat de scraper gebruikt.
- **Nog te bepalen voor een eventuele volgende ronde:**
  - Scope: alleen Groningen stad (waar Kunstpunt vooral zit, al kwam Museum Belvédère in Friesland ook voorbij), of gerichter Drenthe/Friesland-musea en -galerieën apart zoeken (sluit aan bij overleg.md punt 6)?
  - GRID Grafisch Museum/Universiteitsmuseum Groningen: nog niet gecheckt of Kunstpunt die ook dekt of dat een aparte scraper nodig is.
  - Museum aan de A (voorheen Scheepvaartmuseum): pas relevant zodra het heropent (nu dicht tot medio 2027, zie hierboven).
- **Vervolgvraag Michiel (2026-08-17): "hebben we ook Appingedam/Hoogezand/Assen/Veendam/Grootegast/Leeuwarden/Emmen?"** — geen "Kunstpunt <stad>"-equivalent bestaat voor deze plaatsen (die merknaam is uniek voor Groningen). Bevindingen per plaats:
  - Appingedam/Hoogezand: deels al onbedoeld gedekt — Kunstpunt Groningen's bereik bleek al breder dan de stad (K38/Roden, Kunstruimte De Smederij bij Sappemeer/Hoogezand zaten er al in). Appingedam heeft een eigen galerie (De Kunsthof) die soms al via Kunstpunt meekomt.
  - Assen/Veendam/Grootegast/Leeuwarden/Emmen: geen aggregator gevonden met die naam, wel losse galerieën per plaats (CAMPIS/Assen, Galerie Zichtlijn/Grootegast, H47 & SPOONK ART/Leeuwarden, DIEP Emmen).
  - **Veelbelovender spoor**: **kunstinzicht.nl** kwam in bijna elke zoekopdracht terug — blijkt een landelijke kunstagenda te zijn, georganiseerd per provincie/plaats (`/kunst-agenda/groningen/`, `/kunst-agenda/emmen/`, etc.), met echte exposities + einddatum (niet alleen een galerielijst — kort gecheckt, werkt als agenda). Als dit klopt en scrapebaar is, dekt dit mogelijk Drenthe/Friesland/Groningen-breed in één keer — potentieel nog groter dan Kunstpunt. **Nog niet technisch verkend** (server-rendered? regex-baar? hoeveel bronnen dubbelen met wat we al hebben?).

## Status
Sessie 2026-08-15: GitHub gesynchroniseerd (17 commits ingehaald), punt 1 opgelost (Taakplanner-taak ma/wo/za 04:00), kritieke SSL-bug gefixt, 31 → 7 AI/Chrome-bronnen opgelost (26 nieuwe scrapers, zie SCRAPERS.md/decisions.md/plan.md — resterende 7 bewust geparkeerd als "moeilijk"), punt 4 (kapotte links) daarmee ook volledig afgesloten, Ticketmaster-API-key veilig opgezet. Sessie afgesloten met een productbrainstorm: 3 nieuwe topniveau-knoppen (Exposities/Favorieten/Admin) — richting bepaald, zie punten 9-11.

Sessie 2026-08-16: **Exposities gebouwd** (punt 10 nu volledig afgesloten) — zie ARCHITECTURE.md §Exposities/decisions.md voor de uitwerking, inclusief 2 bijgevangen bugs (`classify()`'s `'strip'`-substring-fout, en een ontbrekende `apply()`-call bij page-load die sportwedstrijden liet meerenderen in Uitjes-modus). Favorieten (punt 9) en Admin (punt 11) nog niet gebouwd. Nog openstaande discussiepunten: 2 (parallelle requests, niet gestart), 5, 6 (ideeschetsen, nog niet uitgewerkt).

Sessie 2026-08-17: **Parallelle requests gebouwd** (punt 2 afgesloten, zie decisions.md — inclusief een bug in het stopsignaal van `fetch_batches()` die drenthe.nl 16x langzamer maakte dan nodig, gefixt). **forum.nl-duplicaten opgelost** en **Geke Hoogstins-scraper gebouwd** (punt 12 afgesloten) — Exposities ging 4 → 41 (bug) → 9 (forum.nl-fix) → 11 (Geke Hoogstins + een bijgevangen `export_json()`-bug die "al begonnen, nog lopende" exposities onzichtbaar hield). SCRAPERS.md's "Kan zonder AI"-lijst is nu leeg (57/57 bronnen geautomatiseerd). Nieuw punt 13 vastgelegd (Exposities uitbreiden met meer musea/galerieën) — nog niet gebouwd, scope-vragen open.
