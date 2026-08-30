# Plan — to-do

Levend document. Vink af / verplaats naar "Later" zodra iets besproken of gedaan is.

## Sessie 2026-08-10/11 — afgerond
- [x] GitHub-toegang gecheckt
- [x] Cloudflare-account/project gecheckt (Chielemans@hotma…, project `uitjesagenda`)
- [x] Python geïnstalleerd op deze laptop
- [x] Repo gecloned naar `C:\dev\uitjesagenda`
- [x] 5 scrapers gedraaid (drenthe, visitgroningen, friesland, handmatig, naarzuidlaren)
- [x] `events_db.py export` + `gen_uitjes.py`
- [x] Cross-source dedup gebouwd en toegepast
- [x] Sport-audit: 19 clubs gecheckt, handbal (E&O + Hurry-Up) opgelost
- [x] Sport-genre-badge-bug gefixt ("Overig" → juiste sporticoon/label)
- [x] Afstand-handmatig-invoeren hersteld
- [x] SPOT herbouwd (verse data + venue-split + genre-signaal)
- [x] Kritieke insert-prioriteit-bug gefixt in `events_db.py`
- [x] `SCRAPERS.md` toegevoegd (status per bron: automatisch / kan zonder AI / AI-Chrome nodig)
- [x] Alles gecommit + gepusht (meerdere commits, telkens na review)

## Binnenkort — te overleggen (zie overleg.md)
- [x] Waar draait de wekelijkse refresh voortaan — OPGELOST 2026-08-15: deze laptop, zie hieronder.
- [ ] Scraper-efficiëntie: per-pagina hash-caching (gebouwd, zie sessie 2026-08-14) + parallelle requests (**aanpak uitgewerkt 2026-08-16, nog te bouwen** — zie hieronder) i.p.v. elke run alles opnieuw ophalen
- [ ] Documentatiestructuur compleet: readme / onboarding / architecture / overleg / plan / decisions — bijhouden wie wat update

## Parallelle requests — GEBOUWD 2026-08-16
Volledige uitwerking in overleg.md punt 2 en decisions.md 2026-08-16.
- [x] SQLite WAL-mode + busy_timeout in `events_db.py`'s `get_conn()`
- [x] Niveau A: `run_weekly_refresh.py`'s hoofdlus naar twee `ThreadPoolExecutor`-pools (plain-HTTP max 8, Playwright max 3, `--max-plain`/`--max-playwright` instelbaar)
- [x] Niveau B: nieuwe `parallel_fetch.py`-helper (`fetch_many()` + `fetch_batches()`), toegepast op alle 7 kandidaten: `scrape_drenthe.py`, `scrape_friesland.py`, `scrape_visitgroningen.py`, `scrape_forum.py`, `scrape_kielzog.py`, `scrape_posthuistheater.py`, `scrape_paard.py`
- [x] **Bug gevonden en gefixt onderweg**: `fetch_batches()`'s eerste stopsignaal ("0 events") bleek onbetrouwbaar voor drenthe.nl (site geeft fallback-content i.p.v. een lege pagina voorbij het echte einde) — vervangen door het "geen volgende-pagina-link"-signaal. Zie decisions.md voor de volledige diagnose (3m34s → 13s na de fix).
- [x] Bewust buiten scope gebleven: `scrape_concertgebouw.py`/`scrape_gelredome.py` (Playwright-paginering, ander soort wijziging) — evt. apart later.
- [x] Geverifieerd met een echte volle `run_weekly_refresh.py`-run (geen dry-run): 56/56 OK, 0 lock-fouten, 0 hernoemingen. Events na export/generate: 6634 → 7734.
- [ ] **Nieuw gevonden bijvangst, nog niet opgelost**: forum.nl's doorlopende exposities ("Marilyn Expositie"/"Storyworld") als losse rij per dag i.p.v. datumbereik — zie overleg.md punt 12, plan.md-item hierboven bij de Exposities-sectie.

## Sessie 2026-08-15
- [x] Lokale repo gesynchroniseerd met GitHub (17 commits achter, fast-forward — onderweg een stale `.git/HEAD.lock` opgeruimd)
- [x] Windows Taakplanner-taak "uitjes-agenda-refresh" ingesteld: ma/wo/za 04:00, draait `weekly_refresh.ps1` (nieuw, pure PowerShell/geen AI) → `run_weekly_refresh.py` + commit/push bij wijzigingen
- [x] Taak-principal op S4U gezet (draait ongeacht inlogstatus) — vereiste een handmatige stap door Michiel in een Administrator-PowerShell
- [x] `refresh_log.txt` toegevoegd aan `.gitignore`
- [x] `.gitignore` + `weekly_refresh.ps1` gecommit en gepusht
- [x] ARCHITECTURE.md / decisions.md / overleg.md bijgewerkt met de nieuwe taak-opzet
- [x] Afstand-bug (aggregators) gecheckt: bleek al opgelost in de ingehaalde commits, geverifieerd met het Annen/Zuidlaren-voorbeeld
- [x] **Kritieke bug gevonden en gefixt**: 24 van de 31 scrapers faalden stilzwijgend door `ssl.VERIFY_X509_STRICT` (Python 3.14 op deze laptop) — zie decisions.md voor de volledige analyse. Fix: nieuw `ssl_fix.py`, geïmporteerd via `page_cache.py`. Alle 24 opnieuw getest, werken weer.

## SSL-vervolg — OPGELOST 2026-08-15
- [x] 6 scrapers (`drenthe`, `friesland`, `handbal`, `naarzuidlaren`, `spotgroningen`, `visitgroningen`) gebruikten nog `ssl.CERT_NONE` (certificaatverificatie helemaal uit). Overgezet naar `ssl_fix.create_context()` (alleen VERIFY_X509_STRICT uit, verificatie blijft actief) en alle 6 opnieuw functioneel getest.

## Donar + Landstede Hammers (basketbal) — OPGELOST 2026-08-15
Michiel vroeg te checken of BNXT-clubsites of CMS-en (WordPress/Joomla) een
plugin met API gebruiken voor wedstrijdschema's. Geen generieke plugin
gevonden, maar wel iets beters: de BNXT League's eigen site draait op een
bespoke CMS "Sportpress" (bureau Webpont) met een publieke JSON-API. Nieuwe
`scrape_donar.py` + `scrape_landstede.py` (bijna-identiek, zelfde API/patroon
als de ESPN-familie). Zie SCRAPERS.md en decisions.md voor de volledige
vondst/API-mechaniek. 15 thuiswedstrijden per club, seizoen 2026-2027.
Onderweg 14 verouderde, losstaand-ingevoerde Donar-events (andere titelstijl,
geen los script) uit de database opgeruimd — die botsten niet met de nieuwe
rijen (net iets andere titeltekst) en gaven dus dubbele wedstrijden.

## 31 AI/Chrome-bronnen: eerste 4 opgelost zonder browser — sessie 2026-08-15
Zelfde methodiek als bij Donar toegepast op de "AI/Chrome nodig"-lijst:
JS-bundles/ruwe HTML doorzoeken op verborgen API's of over het hoofd geziene
server-rendering, i.p.v. meteen Chrome MCP inzetten. Resultaat: 4 nieuwe
scrapers (830 events samen):
- [x] `scrape_atlastheater.py` — Umbraco-ticketing-API (`GetPerformances`), 192 events
- [x] `scrape_podiumzuidhaege.py` — WP REST `event_listing` + tekst-regex voor datum, 22 events
- [x] `scrape_melkweg.py` — bleek toch server-rendered HTML (eerdere check miste dit), 257 events
- [x] `scrape_013.py` — zelfde als Melkweg, 154 events
- Bijvangst: 252 verlopen, ongedocumenteerde losse events opgeruimd bij deze 4 bronnen (zie decisions.md)
### Vervolg — tweede ronde, 2026-08-15
- [x] **FC Groningen opgelost** — `scrape_fcgroningen.py`, zelfde ESPN.nl-patroon als de andere Eredivisie-clubs (team-id 145). 18 verouderde/deels foute rijen opgeruimd uit een oude Chrome-pull.
- [x] Cloudflare-bot-check bij TivoliVredenburg herkend en bewust niet omzeild (principiële grens, geen praktisch "kan niet")
- [x] Webflow+Finsweet-platform herkend bij Neushoorn/GelreDome (CMS-collecties client-side gevuld, geen voor de hand liggende publieke API)
- [ ] **Vera/Simplon** — gedeeltelijke server-rendering (pagina 1, ~20/60 events), paginering blijkt te lopen via een admin-ajax-call die zonder browser een lege respons geeft (vermoedelijk Cloudflare op dat endpoint). Bewust niet gebouwd (te onvolledig). Evt. later met Chrome MCP de paginering-cookie/nonce achterhalen.
- [ ] **EM2 Groningen** — REST-API met custom `event`-post-type gevonden, maar datum staat inconsistent midden in vrije tekst. Kan later met een zorgvuldiger regex-patroon.
- [ ] **Effenaar** — veelbelovend (150 datum-strings gevonden) maar bleek CMS-content-block-metadata, niet afgerond, nog eens goed naar kijken
- [ ] **Ziggo Dome** — Next.js/Turbopack, na de Melkweg-ervaring (leek ook client-rendered maar was het niet) een goede kandidaat om alsnog grondig te checken
- [ ] Resterende bronnen zonder duidelijk vervolgpad (zie SCRAPERS.md voor details per bron): Grand Theatre, Winsinghhof (domein onbereikbaar), Koornbeurs, Groninger Museum, Drents Museum, Zummerbühne, OntdekPoort (403), Hunebedcentrum (403), GIJS Groningen (oud seizoen), Doornroosje, De Doelen, Ahoy, GelreDome, Paradiso, Concertgebouw, Rotown, Het Paard

### Vervolg — Hedon + TivoliVredenburg via tips van Michiel, Playwright toegevoegd
- [x] **Hedon Zwolle opgelost** — `scrape_hedon.py`, eigen `/api/events` (Yesplan-backed, tip van Michiel via LinkedIn-post van Hedon zelf). 118 events.
- [x] **TivoliVredenburg opgelost (gedeeltelijk)** — `scrape_tivolivredenburg.py` via songkick.com (tip Michiel). Alleen muziek/concerten, ~9 shows per run — de site zelf blijft een Cloudflare bot-challenge, bewust niet omzeild.
- [x] Bij het checken op oude data bleek `tivolivredenburg` al 401 toekomstige, waardevolle events te hebben (niet verouderd zoals bij eerdere gevallen) — bewust NIET opgeruimd, zie decisions.md voor de afweging.
- [x] **Playwright geïnstalleerd** (na akkoord Michiel) om de resterende niet-bot-beschermde JS-bronnen alsnog zonder AI te automatiseren — eerste externe dependency in het project.
- [x] Chromium geïnstalleerd, `scrape_neushoorn.py` gebouwd en werkt (110 events) — eerste Playwright-scraper.
- [x] `scrape_gelredome.py` gebouwd en werkt (21 events, Vitesse + concerten) — tweede Playwright-scraper, zelfde Webflow-platform als Neushoorn.
- [x] **Ziggo Dome opgelost** — uiteindelijk via podiuminfo.nl (tip Michiel, JSON-LD, geen Playwright nodig) i.p.v. de eerder onderzochte Playwright-scroll-aanpak (die werkte ook, maar podiuminfo is simpeler + heeft echte per-event-URL's). 25 events. Onderweg 13 near-duplicate "wees"-rijen opgeruimd + een `page_hash`-valkuil ontdekt (zie decisions.md/ARCHITECTURE.md §Change-detection).
- [x] **Simplon opgelost** — `scrape_simplon.py`, derde Playwright-scraper. Zelfde Stager-platform als Vera maar geen AJAX-paginering-probleem, simpel DOM-patroon. 48 events.
- [x] **Effenaar opgelost** — `scrape_effenaar.py`, vierde Playwright-scraper. Bleek een verkeerde-URL-fout in een eerdere sessie (`/programma` i.p.v. `/agenda`), geen echt "AI/Chrome nodig"-geval. 125 events.
- [x] **Winsinghhof opgelost** — `scrape_theaterroden.py`, geen Playwright nodig. Bleek een verkeerd domein (`winsinghhof.nl` bestaat niet meer, echte domein is `theaterroden.nl`). 68 events. podiuminfo.nl (tip Michiel) gaf hier maar 12/71 — bevestigt dat podiuminfo alleen concerten dekt, niet theater/cabaret.
- [x] **Koornbeurs opgelost** — `scrape_koornbeurs.py`, vijfde Playwright-scraper. Geen bijzondere reden waarom eerdere check niets vond (gewoon client-rendered zonder API). 117 events.
- [x] **Grand Theatre Groningen opgelost** — `scrape_grandtheatregroningen.py`, zesde Playwright-scraper. DOM-structuur bleek toch regex-baar (geen echte data-attributen, maar wel consistente `event-container`-blokken). 61 events.
- [x] **De Doelen opgelost** — `scrape_dedoelen.py`, achtste Playwright-scraper. Ook een verkeerde-URL-fout (`/programma` i.p.v. `/nl/agenda`). 49 events, grootste near-duplicate-opruiming tot nu toe (151 oude rijen).
- [ ] **Vera nog steeds niet opgelost** — enige overgebleven Stager-bron met het AJAX-paginering-probleem (zie decisions.md 2026-08-15). Zou met Chrome MCP (interactief een nonce/cookie achterhalen) alsnog kunnen, apart punt.
- [ ] Overweeg later: gedeelde browser-instance i.p.v. elke Playwright-scraper zijn eigen Chromium laten starten (opstarttijd ~7s per scraper, kan oplopen bij veel Playwright-scrapers) — zie ARCHITECTURE.md §Playwright-scrapers.

## Sport-audit (2026-08-10)
Van de 19 geconfigureerde clubs in `gen_uitjes.py` (`SPORT_CLUBS`):
- **Compleet, data klopt**: fcgroningen (16), fcemmen (18), heerenveen (24), cambuur (16), fctwente (17), goahead (16), peczwolle (16), donar (14) — volledig seizoen aug 2026 - mei 2027.
- **Klopt, maar seizoen nog niet compleet gepubliceerd**: lycurgus, sudosa, friso (volleybal) — Nevobo-RSS-feed zelf heeft nu maar 7 thuiswedstrijden (2e seizoenshelft nog niet vrijgegeven door de bond). Geen scraper-fout — later in het seizoen opnieuw scrapen.
- **OPGELOST 2026-08-10**: `hurryup` (14 thuiswedstrijden) + `eoemmen` (26 thuiswedstrijden) — Michiel wees erop dat de standaard datumfilter op handbal.nl maar 2 weken vooruit toont; met een ruimere `filters[date]`-range op de onderliggende Sportlink-API (`api.handbal.nl/.../program`) bleek het hele seizoen al gepubliceerd. Nieuwe scraper: `scrape_handbal.py` (plain requests, geen browser nodig). Lost ook Hurry-Up's oude 404-probleem structureel op (nieuwe bron: officiële NHV-clubpagina i.p.v. eigen site).
- **Nog altijd leeg** (filterknop bestaat, 0 events) — herchecked 2026-08-10, status per bron in `scraping_recipes.json`:
  - [ ] `landstede` (basketbal) — DNS-fout, domein lijkt niet meer te bestaan, juiste URL uitzoeken
  - [ ] `grizzlys` / GIJS Groningen (ijshockey) — site toont nog seizoen 2025-2026, 2026-2027 nog niet live
  - [ ] `flyers` (ijshockey) — schema nog niet gepubliceerd
  - [ ] `ogcapitals` (ijshockey) — redirect-loop, niet bereikbaar zonder browser (Chrome MCP proberen)
  - [ ] `ldodk` (korfbal) — site zegt expliciet "geen programma bekend"
  - [ ] `dos46` (korfbal) — mijn.korfbal.nl laadt leeg (JS-shell)

## Bug: afstandsberekening klopt niet voor aggregator-bronnen — OPGELOST (gevonden 2026-08-11, geverifieerd 2026-08-15)
- **Symptoom** (gemeld door Michiel): filter op 15km vanaf een locatie tussen Annen en Zuidlaren toont Ruinen, Diever, Nieuw-Dordrecht, Vledder, Alteveer, Meppel etc. — allemaal met exact "~13km", terwijl deze plaatsen in werkelijkheid zeer verschillende, deels veel grotere afstanden hebben.
- **Oorzaak**: `VENUE_LOC` in `gen_uitjes.py` had voor de 3 grote regionale aggregators (`drenthe.nl`, `visitgroningen`, `friesland.nl`) maar **één vast coördinaat per bron**, niet per stad.
- **Fix** (zat al in de 17 commits die op 2026-08-15 zijn ingehaald vanaf GitHub): `city_coords.json` (254 plaatsen, eenmalig geocoded, zie `build_city_coords.py`) + `gen_uitjes.py`/`event_html()` gebruikt nu `CITY_COORDS.get(e['city'])` per event, met `VENUE_LOC` alleen nog als fallback.
- **Geverifieerd 2026-08-15**: het exacte Annen/Zuidlaren-voorbeeld gecheckt in het live `index.html` — Ruinen/Diever/Meppel/Vledder hebben nu elk hun eigen `data-latlon`, niet meer hetzelfde bron-coördinaat.
- **Klein restpunt, nieuw gevonden**: 3 van de 256 plaatsen bij aggregators missen een match in `city_coords.json` — **"Winsum-Obergum"**, **"Zuidwest-Drenthe"**, **"8"** (1 event elk). Dit zijn zelf al foute city-extracties uit de scraper (regio-naam resp. letterlijk "8" i.p.v. een plaatsnaam), geen probleem in de lookup. Vallen terug op het oude bron-coördinaat — verwaarloosbare impact (3 van ~7000+ events), niet actief opgepakt.

## SPOT-scraper achterhaald + genre-classificatie te ambigu — OPGELOST 2026-08-11
- SPOT-data was verouderd (621 live vs 325 opgeslagen) — nieuwe `scrape_spotgroningen.py` gebouwd, leest ook `data-location` (Oosterpoort vs Stadsschouwburg) en `data-genres`/`data-subgenres` (echt genre-signaal, bv. "jazz") uit SPOT's eigen HTML.
- `classify()` in `gen_uitjes.py`: 'quartet'/'kwartet'/'trio'/'ensemble'/'kamer' weggehaald uit de klassiek-keywordlijst (genre-ambigu — jazz gebruikt dezelfde woorden); `jazz`/`pop` toegevoegd aan `cat_map` zodat SPOT's cats ze kunnen sturen. Peter Bernstein Quartet toont nu correct 🎷 Jazz / Blues.
- **Onderweg ontdekt en meteen gefixt**: de eigenlijke reden dat SPOT's herscrapete data eerst niet doorkwam was een dieper insert-prioriteit-probleem in `events_db.py` (zie `decisions.md`) — generiek gefixt, niet SPOT-specifiek.
- [ ] Overwegen: `cross-over`-subgenre (SPOT) bleek te dubbelzinnig om te mappen (zowel klassieke talentavonden als een punkoperette) — nu bewust ongemapt, kan later verfijnd worden als er een patroon in zit.

## Scrapers uitbreiden richting volledig automatisch (zie SCRAPERS.md)
Einddoel Michiel: wekelijkse refresh volledig zonder AI. Status per bron staat in
`SCRAPERS.md`.

### Sessie 2026-08-13 — 15 nieuwe scrapers gebouwd
- [x] FC Twente, SC Cambuur, Go Ahead Eagles, PEC Zwolle (ESPN.nl, gedeeld patroon)
- [x] SC Heerenveen (eigen site, embedded JSON)
- [x] FC Emmen (eigen site, WP-tabel)
- [x] Kielzog (JSON-API), Forum (met SKIP-lijst), Geert Teis, USVA (~6/10 events)
- [x] Martiniplaza (via theater.nl, JSON-LD — bleek 60 events i.p.v. verwachte 6-57)
- [x] De Tamboer, Posthuis, Bostheater, GC Zuidlaren
- 6786 → 6986 events na deze batch (na dedup)
- [x] Donar (basketbal) — 3 platforms onderzocht, toen nog niet opgelost (later wel, zie sessie 2026-08-15 hierboven).
- [ ] Zummerbühne, OntdekPoort, Hunebedcentrum — bleken bij nader inzien AI/Chrome nodig (ticketwidget resp. bot-bescherming), verplaatst in SCRAPERS.md.

### Sessie 2026-08-13 vervolg — nog 6 scrapers erbij
- [x] Nieuwe Kolk (denieuwekolk.nl) — eindelijk de per-event-URL opgelost, plus /bieb/-bibliotheekactiviteiten bewust uitgesloten (37 events)
- [x] Lycurgus, Sudosa, Friso (Nevobo RSS, zelfde patroon als eerder)
- [x] Dorpshuis Annen (Jimdo-site, tekst-pattern-matching)
- [x] Nienoord (oude regex was stuk door site-wijziging, herbouwd — kleiner dan verwacht: 3 i.p.v. ~9)
- 6986 → 7031 events na deze batch

### Sessie 2026-08-13 vervolg 2 — laatste 3 "kan zonder AI"-bronnen
- [x] Machinefabriek (via podiuminfo.nl), Noorderbron (WP Event Manager), AFAS Live (92 events)
- [x] Geke Hoogstins bewust NIET gebouwd — zijn doorlopende maandenlange exposities, geen losse datums, past niet in ons datamodel
- 7031 → 7067 events na deze batch
- **"Kan zonder AI"-lijst is nu leeg.** Resterende sporen: AI/Chrome nodig (16 bronnen) en nog nooit geprobeerd (15 bronnen), zie SCRAPERS.md.

### Sessie 2026-08-14 — landelijke podia gecheckt, blijken AI/Chrome nodig
- [x] Alle 15 "nooit geprobeerd"-bronnen (landelijke podia) gecheckt met plain requests — vrijwel allemaal zwaar client-rendered (Next.js/Vue), anders dan de kleine Noord-Nederlandse venues. Verplaatst naar AI/Chrome-categorie, details in SCRAPERS.md.
- [x] Donar opnieuw geprobeerd (NBB-API nog steeds leeg voor 2026-2027; livescore.com-tip van Michiel bekeken maar netwerkmonitoring ving de data-call niet) — blijft open, volgende keer grondiger met Chrome MCP (JS-state uitlezen i.p.v. netwerkverkeer).
- [ ] **31 bronnen "AI/Chrome nodig"** (was 16, nu + de 15 landelijke podia): zie SCRAPERS.md voor de volledige lijst en per-bron bevindingen.

### Kapotte/generieke links (overleg.md punt 4) — grotendeels opgelost 2026-08-14
- [x] FC Twente, SC Cambuur, Go Ahead Eagles, PEC Zwolle: ESPN.nl heeft een `"id"`-veld per wedstrijd, nu een echte per-wedstrijd-URL i.p.v. de teampagina.
- [x] Martiniplaza: theater.nl's JSON-LD had de echte URL in `@id`, niet in `url` — simpele scraper-fix.
- [x] Sportclubs zonder per-wedstrijd-pagina (E&O, Hurry-Up, FC Groningen, Donar) bewust ongewijzigd gelaten — geen betere URL beschikbaar.
- 7067 → 6999 events (klein netto verschil, ging vooral om URL-kwaliteit i.p.v. nieuwe events; daling komt door 1 dag datum-rollover + dat cambuur/martiniplaza wat verlopen/dubbele rijen kwijtraakten bij het verwijderen-en-herladen — oude rijen moesten eerst weg zodat de URL-update ook echt doorkwam, insert_event() update alleen bij aggregator-vs-directe-bron-botsingen).
- Resterende kapotte links vallen samen met de AI/Chrome-lijst (grote landelijke podia) — wordt vanzelf meegenomen zodra die aangepakt worden.
- [x] Weekelijkse-refresh-commandolijst → `run_weekly_refresh.py` (globt `scrape_*.py`, self-healing quarantaine naar `fix_*.py` bij harde fout). Zie ARCHITECTURE.md §Wekelijkse refresh, overleg.md punt 7.

### Sessie 2026-08-14 vervolg — run_weekly_refresh.py + change-detection
- [x] `run_weekly_refresh.py` gebouwd en écht gedraaid (niet alleen dry-run) — valideerde de self-healing logica met een geval uit de praktijk.
- [x] **Gevonden tijdens die run**: `scrape_friesland.py` werd onterecht gequarantained — bleek een te-strakke 300s-timeout te zijn (friesland.nl heeft ~69 pagina's à ~3s), geen kapotte scraper. Timeout naar 600s, script teruggezet. Zie decisions.md.
- [x] `page_cache.py` gebouwd (hash-based change-detection, skip parse/insert bij ongewijzigde data) en toegepast als werkend voorbeeld op `scrape_martiniplaza.py`. Zie ARCHITECTURE.md §Change-detection.
- [x] Rollout van `page_cache.py`-patroon naar alle 30 live-scrapende `scrape_*.py`-bestanden (31e, `scrape_handmatig.py`, bewust overgeslagen). Getest: tweede live run herkent "geen wijzigingen", `--dry-run` negeert de cache.
- [x] **Bijvangst**: tijdens de eerste échte `run_weekly_refresh.py`-run bleken `scrape_friesland.py` en `scrape_visitgroningen.py` onterecht gequarantained (300s-timeout te krap voor hun tientallen pagina's) — timeout naar 600s, beide teruggezet en opnieuw (succesvol) gedraaid. Zie decisions.md.
- [x] CLAUDE.md/decisions.md/overleg.md/ARCHITECTURE.md bijgewerkt.
- 6999 → 7055 events na deze sessie (friesland.nl +19 nieuw; rest van de bronnen grotendeels ongewijzigd t.o.v. vorige refresh).

## Later / open items (uit ARCHITECTURE.md)
- [x] Ticketmaster Discovery API-key aangemaakt en getest (2026-08-15) — werkt, echte data terug voor Groningen (Martiniplaza-events zoals Guus Meeuwis, The Nutcracker). `secrets.local.json` correct ingevuld en genegeerd door git.
  - Rate limits: 5.000 calls/dag, 5 requests/seconde, deep paging beperkt tot `size × page < 1000`.
  - [x] `ticketmaster.py`-helper gebouwd (venue-id-lookup + rate-limited events-fetch). Toegepast op **Ziggo Dome** (vervangt podiuminfo.nl, 83 vs 25 events) en **Ahoy** (nieuw, 41 events).
  - [x] Ook geprobeerd voor Paradiso/Concertgebouw (venue gevonden, 0 events — verkopen niet via Ticketmaster) en Rotown/Het Paard (geen venue-match, te klein). Niet bruikbaar voor deze 4.
- [x] **Het Paard opgelost** — `scrape_paard.py`, via denhaag.com/nl/paard (tip Michiel), geen Playwright nodig (gewone `?page=N`-paginering). 92 events.
- [x] **Paradiso opgelost** — `scrape_paradiso.py`, negende Playwright-scraper. Bleek verkeerde-URL-fout, niet echt AI/Chrome nodig. 100 events.
- [x] **Concertgebouw opgelost** — `scrape_concertgebouw.py`, tiende Playwright-scraper (juiste URL + paginering-tip van Michiel). **600 events**, grootste scraper van het project, ~1,5 min per run (1 browser-instance voor ~40 pagina's).
- [x] Zummerbühne en Groninger/Drents Museum verder onderzocht (2026-08-15): Zummerbühne's iframe bleek een ride-share-widget (geen ticketing), museum blijft leeg ook na cookiebanner-klik — beide bevestigde doodlopende paden, geen quick win meer te vinden.
- [x] **Rotown opgelost** — `scrape_rotown.py`, geen Playwright nodig (JSON-LD op de homepage). 97 events. **Alle 15 oorspronkelijke landelijke podia zijn nu opgelost.**
- [x] **Vera opgelost** — `scrape_vera.py`, elfde Playwright-scraper. Bleek géén Cloudflare-blokkade zoals eerder aangenomen, gewoon een infinite-scroll die curl niet kon triggeren — een echte browser-scroll laadt alles. 69 events.
- [x] Resterende 7 AI/Chrome-bronnen bewust geparkeerd als "moeilijk" (Michiel) — geen actieve vervolgstap, oppakken zodra er zin in is.

## Nieuwe feature-richting: 3 topniveau-knoppen (Exposities/Favorieten/Admin) — sessie 2026-08-15/16
Productbrainstorm afgerond 2026-08-15, richting vastgelegd in overleg.md punten 9-11.
- [x] **Exposities gebouwd (2026-08-16)**: `genre='expo'` volledig uit de Uitjes-stroom gehaald naar een eigen derde topniveau-knop. Route A geïmplementeerd (altijd tonen tenzij een bekende `date_end` al voorbij is — `date_end` wordt nu voor het eerst echt gelezen door `gen_uitjes.py`). Sortering: default startdatum (server-side), Einddatum/Alfabetisch als client-side herordening. Afstands- en provinciefilter werken mee (gedeeld filterblok, geen aparte code). Zie ARCHITECTURE.md §Exposities voor de volledige technische uitwerking.
  - Onderweg 2 bugs gevonden en gefixt: `classify()`'s losse keyword `'strip'` matchte per ongeluk "Striptease" (3 theatershows onterecht als expo); en `apply()` werd nooit aangeroepen bij het laden van de pagina, waardoor sportwedstrijden zichtbaar bleven tussen de Uitjes tot de eerste filterklik (bevestigd op de live site: 172 sportevents zichtbaar bij page-load, nu gefixt). Zie decisions.md.
  - Huidige omvang klein: 4 echte exposities (Groninger Museum x2, Geke Hoogstins, Concertgebouw) — geen aparte Bron-filter gebouwd, kan later als het aantal groeit.
- [x] **forum.nl doorlopende-exposities-bug OPGELOST (2026-08-17)**: `scrape_forum.py` groepeert nu opeenvolgende kalenderdagen per slug tot één event met `date_end` (`merge_consecutive_days()`), i.p.v. een losse rij per dag. Exposities 41 → 9. Zie overleg.md punt 12/decisions.md 2026-08-17 voor de volledige uitwerking, inclusief de stale-data-opruiming (95 oude daily-duplicate-rijen verwijderd).
- [x] **Geke Hoogstins-scraper GEBOUWD (2026-08-17)**: `scrape_gekehoogstins.py`, regex op de gestructureerde "EXPOSITIES `<jaar>`"-sectie (de rest van de site is vrije tekst, bewust genegeerd). 3 events/jaar. Onderweg bleek de bestaande handmatige DB-rij een foutieve `date_end` te hebben (placeholder, nu gecorrigeerd) en werd een aparte bug in `events_db.py`'s `export_json()` gevonden en gefixt (zie hieronder) — zonder die fix bleven "al begonnen, nog lopende" exposities onzichtbaar.
- [x] **Bug gevonden en gefixt: `events_db.py`'s `export_json()` had geen `date_end`-besef**: filterde events puur op startdatum (`date >= vandaag`), dus een expositie die vóór vandaag begon maar nog loopt viel al weg vóór `gen_uitjes.py`'s eigen (correcte) expo-logica er ooit aan toekwam. Bestond al sinds de Exposities-bouw (2026-08-16), was onzichtbaar tot de eerste "al begonnen, nog lopende" expositie (Geke Hoogstins) het blootlegde. Zie decisions.md 2026-08-17.
- [x] **Exposities uitgebreid: Kunstpunt Groningen GEBOUWD (2026-08-17, overleg.md punt 13)**: `scrape_kunstpuntgroningen.py`, nieuwe aggregator die tientallen Groningse musea/galerieën in één keer dekt (Groninger Museum, Museum Nienoord, Synagoge Groningen, K38, De Stadsgalerie, e.v.a.) — 22-25 exposities per run. Toegevoegd aan `AGGREGATOR_SOURCES` (venue-wint-van-aggregator-regel). Exposities 11 → 34.
  - Bonus: `gen_uitjes.py`'s `event_html()`/`expo_card_html()` uitgebreid met event-eigen `lat`/`lon`-prioriteit (was ongebruikte infrastructuur — events_db.py sloeg het al op, niks las het) — Kunstpunt levert precieze per-venue coördinaten.
  - Bug gevonden en gefixt: `classify()`'s `cats=='expositie'`-tak vereiste ten onrechte ALTIJD ook een Nederlandse titel-keyword-match, waardoor het cats-signaal in de praktijk nooit gezaghebbend was (Engelse titels als "Coach house" vielen terug op 'overig'). Niemand gebruikte dit pad eerder, dus zonder risico gefixt.
  - Bug gevonden en gefixt: "venue boven aggregator" werkte niet voor Galerie DSG — Kunstpunt's Engelse titel en Geke Hoogstins' Nederlandse titel voor dezelfde expositie hadden geen woord gemeenschappelijk, dus de fuzzy-dedup miste het. Opgelost met een gerichte `SKIP_VENUES`-uitzondering i.p.v. een generieke cross-taal-matcher.
  - Zie decisions.md 2026-08-17 voor de volledige technische uitwerking.
- [x] **kunstinzicht.nl onderzocht, bewust NIET gebouwd (2026-08-17)**: nationwide per-plaats-structuur (geen provincie-brede pagina's), dun verspreid (0-2 items per plaats), en geen startdatum in de data. Zie overleg.md punt 13.
- [x] **Uitzinnig.nl GEBOUWD (2026-08-17, derde expositie-aggregator)**: `scrape_uitzinnig.py`, dekt Drenthe/Groningen/Friesland-breed (i.p.v. vooral Groningen-stad zoals Kunstpunt) — 13 nieuwe exposities (Dwingeloo, Emmer-Compascuum, Zweeloo, Emmen, Borger, Delfzijl, Onstwedde, Sappemeer, Kantens, Leeuwarden). Bonus: eerste (deel-)win voor Hunebedcentrum (permanent-geparkeerde bot-beschermde bron) via een omweg, zonder de bot-bescherming te omzeilen. Toegevoegd aan `AGGREGATOR_SOURCES`. Exposities 34 → 47.
  - **Aggregator-vs-aggregator-dedup-gat 2e keer bevestigd** (na de DSG-episode bij Kunstpunt): `find_cross_source_duplicates()` in events_db.py mist structureel duplicaten zodra BEIDE botsende bronnen een aggregator zijn. 2 exposities ("Mimesis", "Aldrik Salverda en Lucas Klein") kwamen dubbel voor met Kunstpunt — opgelost met een gerichte `SKIP_TITLES`-uitzondering. Overwegen: een echte structurele fix als er een 3e aggregator bijkomt (zie decisions.md 2026-08-17).
- [x] **Kapotte links gemeld door Michiel: 3 gefixt + Groninger Museum eindelijk opgelost (2026-08-17)**: "The Architect & The Housewife" had een foutieve URL (handmatige invoer-fout, gecorrigeerd). "Filth"/"Alcest" (TivoliVredenburg) hadden helemaal geen URL — bleek een structurele bug (zie hieronder), niet incidenteel voor deze 2. Bij het uitzoeken kwam ook een echte oplossing voor **Groninger Museum** naar boven (was 5+ jaar "geparkeerd als moeilijk"): een Playwright-netwerkcheck legde een publieke JSON-API bloot (`/api/exhibitions`, `/api/activities`) — `scrape_groningermuseum.py` gebouwd, dekt ook Michiels gemelde ontbrekende "Groninger Museumnacht". SCRAPERS.md's "geparkeerd"-lijst: 7 → 6.
  - Bug gevonden en gefixt: ALLE 480 TivoliVredenburg-rijen hadden `url=NULL` — `insert_event()` update nooit een bestaande same-source-rij, dus Songkick's eigen (wél aanwezige) URL's landden al sinds die scraper bestaat nooit in de DB. Zorgvuldig gescoped gefixt (alleen de 8 rijen die matchten met Songkick's huidige aanbod, niet de hele 480-rijen-dataset).
  - **Grote herontdekking**: TivoliVredenburg's "bevestigde Cloudflare-blokkade" (2026-08-15) bleek niet (meer) te kloppen — een plain `urllib`-fetch werkt gewoon. `scrape_tivolivredenburg.py` volledig herzien naar een directe scraper (853 events, was 9 via Songkick) — geen bot-detectie omzeild, de blokkade bestond kennelijk niet. Michiel gaf expliciet akkoord om dit te bouwen. Oude 480-rijen-legacydataset vervangen na een stale-data-audit (~97% overlap, rest bleek waarschijnlijk afgelaste shows).
  - Bijvangst-dedup-gat (3e variant, cross-datum i.p.v. cross-taal): "Bakstain" kwam dubbel via Kunstpunt (05-08) en de nieuwe directe Groninger-Museum-scraper (05-09) — `find_cross_source_duplicates()` groepeert strikt per exacte datum, dus miste dit. Gefixt met `SKIP_VENUES` in Kunstpunt.
  - Restpunt, niet gefixt: `normalize_title()` strip geaccentueerde tekens i.p.v. ze te folden (bv. "Paco Peña" vs "Paco Pena") — kan elders ook near-duplicates laten glippen, nog niet structureel aangepakt.
  - Zie decisions.md 2026-08-17 voor de volledige technische uitwerking van alle vier onderdelen.
- [ ] **Favorieten**: act/team volgen over alle bronnen heen — matching-probleem (zelfde titel, andere spelling per bron) en UI/opslag nog te ontwerpen, zie overleg.md punt 9. Nog niet gebouwd.
- [ ] **Admin**: lokale/read-only statusweergave (scraper-status, event-aantallen per bron, laatste refresh) — geen backend, geen bewerkmogelijkheid. Exacte inhoud/vormgeving nog te bepalen, zie overleg.md punt 11. Nog niet gebouwd.
- [ ] Lycurgus/Sudosa/Friso — 2e seizoenshelft volleybal nog niet gepubliceerd door de bond, later herscrapen
- [ ] GIJS Groningen — URL is nu wel bekend (gijsgroningen.nl/gijs-eredivisie/), maar toont nog seizoen 2025-2026; herchecken zodra 2026-2027 live is
- [ ] Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- [ ] Overige scraping-recipes zonder werkende methode — zie `SCRAPERS.md` voor de actuele, volledige stand

## Meerdaagse events op drenthe.nl/friesland.nl/visitgroningen — OPGELOST 2026-08-17
Michiel vroeg of Zomerfeest Eext (drenthe.nl, vr 21 t/m zo 23 augustus) wel op
alle drie de dagen genoteerd stond. Bleek niet zo, op twee niveaus tegelijk:
- [x] **Parse-bug**: `parse_date()` in alle drie de "plaece.nl"-scrapers ving
  "21 t/m 23 augustus" alleen als startdag, gooide de einddag weg via een
  non-capturing regex-group. Nu herschreven naar een echt `(start, end)`-tuple
  met een nieuwe volledig-bereik-regextak. 102/252 "t/m"-gevallen op
  drenthe.nl waren zo'n volledig bereik (fixbaar); de overige 150 "t/m N
  maand"-teksten zonder zichtbare startdag blijven bewust ongewijzigd (ambigu
  — zie CLAUDE.md-regel over aannames).
- [x] **Zichtbaarheids-bug**: `event_is_valid()` gebruikte `date_end` alleen
  voor expo's — een gewoon (niet-expo) meerdaags event verdween na dag 1 alsnog
  uit de agenda. Nu ook voor gewone events: blijft zichtbaar t/m `date_end`,
  valt terug op de oude startdatum-regel als er geen `date_end` is.
- [x] Weergave uitgebreid: event-kaarten tonen nu "vr 21 t/m zo 23 aug" i.p.v.
  alleen de startdag zodra `date_end` afwijkt (nieuwe `fmt_date_range()`).
- [x] DB opgeschoond (precies gescoped: alleen rijen die nu een `date_end`
  moeten krijgen en dat nog niet hadden) en alle drie scrapers live gedraaid +
  export + generate. Geverifieerd: Zomerfeest Eext toont nu het volledige
  bereik. Zie decisions.md 2026-08-17 voor de volledige technische uitwerking.

## Claude Design-integratie + eerste design-review — DEELS VERWERKT 2026-08-17
Michiel koppelde de `claude-design` MCP-server en vroeg om de live site te
laten beoordelen. Werkverdeling: Claude Design adviseert, ik bouw (site wordt
gegenereerd door `gen_uitjes.py`, niet bewerkbaar als los HTML-bestand in een
design-project). Design-system-project "Uitjesagenda" aangemaakt, site erin
gepusht als preview.
- [x] Contrast-bug actieve bron-chips (wit-op-geel/oranje bij cambuur/lycurgus/effenaar/goahead) — nieuwe generieke `_contrast_text()`-helper
- [x] `rel="noopener"` op externe links
- [x] `content-visibility:auto` op event-kaarten (perf, ~8202 events in de DOM)
- [x] `#addr-input` font-size naar 16px (voorkwam iOS-zoom-bug)
- [x] Nederlandse maandnaam in "Bijgewerkt: ..." (was Engels door locale-afhankelijke `strftime`)
- [x] Titel/datum-hiërarchie versterkt (titel nu de sterkste tekst op de kaart)
- [x] `:focus-visible`-stijlen toegevoegd (ontbrak volledig)
- [x] Lege-staat-bericht bij 0 resultaten (met waarschijnlijke oorzaak)
- [ ] **Grotere/subjectieve suggesties nog te prioriteren met Michiel**: zoekveld, datumfilter, filterbalk→toolbar+popover-herbouw, kleurstrategie, mobiele touch-targets, URL/localStorage-filterstate, sorteren voor Uitjes, aria-pressed/role=group — zie overleg.md punt 17 voor de volledige lijst.
- Zie decisions.md 2026-08-17 voor de volledige technische uitwerking, incl. een procesles over een gecrashte batch-script-run die stilzwijgend 2 van de 3 eerdere fixes ongedaan maakte.

## SPOT Groningen toonde weer generiek "Spot Groningen" i.p.v. Oosterpoort/Stadsschouwburg — OPGELOST 2026-08-17
4e keer hetzelfde `insert_event()`-patroon (na forum.nl, Geke Hoogstins,
TivoliVredenburg): 611/662 rijen stonden vast op de generieke fallback-venue
terwijl de scraper allang het juiste gebouw (Oosterpoort/Stadsschouwburg/etc.)
uit `data-location` haalt — gewoon nooit ge-update sinds die logica gebouwd
is. 559 stale rijen gescoped verwijderd, live herscraped: 329 Oosterpoort,
202 Stadsschouwburg, nog maar 67 legitiem generiek.

## insert_event() structureel gefixt — OPGELOST 2026-08-17
Michiel vroeg door op het "4e keer hetzelfde patroon"-restpunt hierboven.
`insert_event()` doet nu een veld-voor-veld merge bij een same-source-
botsing (nieuwe waarde wint alleen als niet leeg) i.p.v. de rij altijd
ongewijzigd te laten — voorkomt dat dit patroon (forum.nl/Geke Hoogstins/
TivoliVredenburg/SPOT Groningen) zich nog een 5e keer herhaalt. Getest met
6 scenario's tegen een losstaande test-DB. Zie decisions.md/overleg.md
punt 18/ARCHITECTURE.md §Cross-source dedup.

## Claude Design-review clusters 1-5 — GEBOUWD op branch 2026-08-17/18
Michiel liet de volledige punt-17-lijst clusteren en besloot per cluster wat
te bouwen: uiteindelijk alle 5 clusters, BEHALVE lazy-loading (bewust "nog
niet, later apart bekijken") — zie overleg.md punt 17 voor de volledige,
bijgewerkte status per item.
- [x] Op verzoek van Michiel op een feature-branch gebouwd
  (`design-review-clusters-1-4`) i.p.v. direct op `main` — wacht op review
  voor te mergen.
- [x] Clusters 1-4 + de modus-wissel-filterbehoud-taak (2026-08-17) —
  **echt in de browser getest** (lokale `http.server`-preview +
  `javascript_exec`, niet alleen grep).
- [x] **2 echte bugs gevonden en gefixt tijdens clusters 1-4, alleen te
  vinden via een live browsertest**: (1) `requestAnimationFrame`-batching van
  `apply()` bleek stil te vallen in een niet-actief-zichtbaar tabblad
  (`document.visibilityState==='hidden'`) — teruggedraaid; (2) de nieuwe
  datumfilter-logica gaf door `.toISOString()`'s UTC-conversie de verkeerde
  datum terug in de Nederlandse zomertijd (UTC+2) — zou ELKE Nederlandse
  gebruiker geraakt hebben, gefixt met lokale datumcomponenten. Zie
  decisions.md 2026-08-17 voor de volledige analyse van beide.
- [x] **Cluster 5 (2026-08-18)**: filterbalk herbouwd naar compacte toolbar +
  popovers (bronnen gegroepeerd per provincie, filterteller per knop, 1
  sticky wrapper — lost meteen ook de sticky-volgorde en mobiele
  touch-targets op), kleurstrategie omgegooid (bronchips neutraal, kleur
  alleen nog via de kaart-linkerrand). Lazy-loading bewust overgeslagen.
- [x] Bij het verifiëren van cluster 5 een methodologische ontdekking
  gedaan: `getComputedStyle()` op net-zichtbaar-gemaakte popover-elementen
  geeft in deze test-omgeving bevroren verf-eigenschappen terug (kleur/
  achtergrond), zelfde onderliggende oorzaak als de rAF-bug. CSS grondig
  via cascade-analyse geverifieerd i.p.v. computed-style; Michiel wordt
  gevraagd de kleuren zelf op de preview te bevestigen. Zie decisions.md
  2026-08-18.
- [x] **Derde Claude Design-ronde (2026-08-18)**: een blokkerende bug
  (Wanneer-filter deed niets, `#uitjes-datum`→`#popover-when` gemist bij de
  cluster-5-rename) + 2 regressies + kleine bugs gevonden en gefixt. Michiel
  koos daarna "ja, graag" op alle 4 resterende clusters (A: kaart-layout +
  dag-groepering, B: 44px-chips/typografie/lege-staat-knoppen, C: URL-state
  compleet + localStorage + zoek-normalisatie, D: mobiele toolbar) — allemaal
  gebouwd en geverifieerd. overleg.md punt 19 nu volledig afgesloten.
- [x] Michiel gaf akkoord ("mag nu mergen") — branch gemerged naar `main`
  (commit a211104, `git merge --no-ff`) en gepusht. Live deploy geverifieerd
  via de Browser pane én via Chrome (extensie, na inloggen) op
  https://uitjesagenda.pages.dev: 1000px-layout, dag-groepering, toolbar,
  geen console-errors.
- [x] **"De puntjes"**: de 2 bewust-niet-gebouwde punten uit overleg.md
  punt 19 alsnog gebouwd — lege venue-regel (`venue_display()`-fallback op
  het bron-label) en de "alleen bronnen binnen mijn afstand"-toggle in de
  Bron-popover. Geverifieerd via lokale preview (JS-niveau: display:none-
  gedrag bij 50km, combinatie met tekstzoek, actieve-knop-kleur,
  aria-pressed). Zie decisions.md 2026-08-18. Gecommit (9f1996d) en gepusht
  naar `main`.

## Zummerbühne toonde verkeerde afstand — OPGELOST 2026-08-17
Michiel meldde dat de afstand bij Zummerbühne (~20km) niet klopte met Google
Maps (35,7km rijdend vanaf huis). Bleek een plaatsnaam-verwarring: er bestaan
twee "Oostwold"-plaatsen in Noord-Nederland (Oldambt, waar Zummerbühne echt
zit, en Westerkwartier) — `city_coords.json` wees naar de verkeerde. Gefixt
op drie plekken: `city_coords.json`, de 25 handmatige DB-rijen kregen
expliciete lat/lon/city, en `VENUE_LOC['zummerbuhne']`'s fallback in
`gen_uitjes.py` (bleek ook de verkeerde provincie te hebben: Drenthe i.p.v.
Groningen). Resterend verschil (~27km hemelsbreed vs 35,7km rijdend) is
inherent aan de haversine-methode, geen bug. Zie decisions.md 2026-08-17.

## Sessie 2026-08-18/19/20/21 — design-review-clusters-1-4 gemerged, 3 nieuwe bronnen, 2 nieuwe topniveau-modi, Supabase-backend
Lange, meerdaagse sessie. Volledige technische uitwerking per item staat in
decisions.md (elk met eigen datum-kop) en overleg.md (punt 9/15/17/19/20) —
hier alleen de samenvatting van wat er gebeurd is.

- [x] **Branch gemerged naar `main`** (commit a211104) na Michiels
  "mag nu mergen" — live deploy geverifieerd via Browser pane + Chrome.
- [x] **"De puntjes"**: lege-venue-rij-fix (`venue_display()`) + Bron-
  popover afstandstoggle, beide live (commit a98b462).
- [x] **Lazy-loading-vraag beantwoord met een echte meting** i.p.v.
  aanname: `transferSize` ~444KB/1 request/~600ms — ruim onder de HTTP
  Archive-mediaan. Besluit: geen lazy-loading bouwen, blijft een
  toekomstoptie. Vastgelegd in decisions.md/ARCHITECTURE.md §Deployment.
- [x] **overleg.md volledig herstructureerd**: alle afgeronde punten naar
  een archief-sectie, punt-nummers bewust ongewijzigd (talloze code-
  comments/decisions.md-verwijzingen zijn nummer-gebaseerd).
- [x] **Punt 15 (drenthe.nl "t/m N maand") heronderzocht**: personapaneel-
  gesprek over "hoort dit bij Uitjes of Exposities", daarna een echte crawl
  i.p.v. de oude schatting — bleek van "~150 gevallen" naar 9 unieke events
  te gaan, waarvan 6 al gefilterd door bestaande `SKIP_TITLE_WORDS`.
  Optie (d) (detailpagina voor een echte startdatum) bleek niet haalbaar:
  drenthe.nl's JSON-LD `startDate`-veld is kapot (CMS-"laatst bewerkt"-
  timestamp, geen echt event-moment).
- [x] **3 nieuwe bronnen gebouwd**:
  - `scrape_staatsbosbeheer.py` — 71 natuuractiviteiten (schone JSON-API,
    genre `actief` expliciet via `cats`).
  - `scrape_intonature.py` — 11 events (Playwright, op-volgorde-lopende
    parser over een platte H3/H5/P-structuur, geen per-activiteit element).
  - `scrape_akerk.py` — 11 events (schone JSON-API, `eventTypes`-array als
    genre-signaal, expositie routeert vanzelf naar Exposities-modus).
- [x] **Externe review (niet Claude Design) nagelopen**: 8 punten, elk apart
  geverifieerd i.p.v. overgenomen. 1 echte fix (`aria-controls` ontbrak),
  1 cijfer-klopt-conclusie-niet (593.000px paginahoogte reëel, maar geen
  laadtijd-probleem dankzij `content-visibility`), 4 niet gereproduceerd
  (mobiele toolbar-overflow, Genre-paneel-bug, actieve-filter-chips
  bestonden al, lege linktekst). 4e-tab-suggestie voor wandelroutes als
  input doorgezet naar Michiels eigen open vraag (punt 15).
- [x] **"Wandelingen/tochten" — 4e topniveau-modus** (2026-08-19): 220
  Staatsbosbeheer-routes, eigen filters (type/lengte/kenmerken), eigen
  `routes.json` buiten de events-DB om (routes hebben nooit een datum).
  Mobiele regressie (4e mode-knop liet `.mode-toggle` overflowen) gevonden
  en gefixt vóór het live ging.
- [x] **"Favorieten" — 5e topniveau-modus, Supabase-backend** (2026-08-20):
  bewaarde zoektermen (geen identiteitsmatch, gewoon vrije tekst/
  onderwerp), cross-device via Supabase (Auth + `favorites`-tabel met RLS)
  i.p.v. localStorage — Michiels expliciete eis "alles zoveel mogelijk
  statisch, alleen wat nodig via Supabase". Library lazy geladen (pas bij
  klik op Favorieten). Onderweg: redirect-bug (Site URL nog op
  `localhost:3000`), e-mail-rate-limit uitgelegd, 2 security-advisor-
  waarschuwingen (`rls_auto_enable`-functie te breed aanroepbaar) opgelost
  via de nieuw gekoppelde Supabase MCP. **Volledig bevestigd door Michiel**
  zelf (eigen account, favoriet toegevoegd/uitgeklapt, lege-staat getest).
- [x] **"Nu lopend"-sectie** (2026-08-21): meerdaagse events die al
  begonnen zijn bleven onder hun gepasseerde startdag-groep hangen — nieuw
  kopje bovenaan (Michiels voorstel) verplaatst ze client-side naar een
  eigen, altijd-actuele sectie. Hergebruikt de bestaande
  `.day-group`-leeg-verbergen-logica, geen aparte zichtbaarheidscode nodig.
- [x] **Bijvangst: TODAY liep een dag achter op Cloudflare's build-server**
  (2026-08-21) — `date.today()` gebruikte de tijdzone van de build-machine;
  Cloudflare draait kennelijk in UTC, dus tussen 22:00-00:00 Nederlandse
  tijd liep de site een dag achter. Gefixt met een handgeschreven
  EU-zomertijdregel (bewust geen `zoneinfo`, geen garantie op systeem-
  tzdata op de build-image) — stdlib-only, geen nieuwe dependency.
- [x] **Supabase MCP-server + `supabase/agent-skills` toegevoegd**
  (project-scoped, `.mcp.json`/`.agents`/`.claude/skills`) — gebruikt voor
  het database-permissiewerk hierboven.
- [ ] **Nog open, geen van alle urgent** (zie overleg.md): punt 5
  (nationale sportteams — suggesties al gegeven: volleybal bevestigd
  regionaal, korfbal/handbal kansrijk), punt 6 (landelijke uitbreiding),
  punt 9's kleinere restvraag (waar precies de "+"-toevoegknop t.o.v. het
  hoofd-zoekveld, nu al opgelost door 'm in de Favorieten-modus zelf te
  zetten — dit puntje is dus feitelijk ook afgerond), punt 11 (Admin-
  scherm, richting bepaald, niet gebouwd), punt 13's laatste restje
  (Universiteitsmuseum Groningen — laag-prioriteit, vereist Playwright,
  nog niet gebouwd), Staatsbosbeheer's 220 `route`-items (Wandelingen/tochten
  dekt inmiddels wel de content, maar Michiel had oorspronkelijk ook nog
  over een bredere "instellingen"-uitbreiding van het account-systeem
  nagedacht, zie overleg.md punt 20 in het archief).

## Sessie 2026-08-21 (vervolg) — Punt 13: 2 nieuwe expositievenues

- [x] **Punt 13 verder onderzocht** ("kleine venues zoeken", Michiels
  verzoek): GRID Grafisch Museum (gesloten, skip), Kunstkrant.nl (te veel
  overlap, skip), Kunstherberg Zweeloo (al gedekt, skip), Universiteits-
  museum Groningen (echt maar Playwright-nodig, laag-prioriteit, nog niet
  gebouwd — enige nog openstaande deel van punt 13).
- [x] **`scrape_debuitenplaats.py` gebouwd** — Drents Museum De
  Buitenplaats (Eelde), server-rendered, geen Playwright nodig. 1
  event/run. "Geen datum verzinnen"-principe toegepast (permanente
  attracties + einddatum-zonder-start overgeslagen).
- [x] **`scrape_princessehof.py` gebouwd** — Keramiekmuseum Princessehof
  (Leeuwarden), Nuxt.js/Vue-app, wél Playwright nodig. Client-side
  tab-klik ("Verwacht") nodig om alle exposities te vinden; datumtekst
  verspreid over meerdere `<article>`-elementen; 2 verschillende
  datum-formuleringen in 1 regex gevangen. 3 events/run.
- [x] Beide toegevoegd aan `SRC` in gen_uitjes.py, geverifieerd lokaal
  (8180 events, geen console-errors), SCRAPERS.md/decisions.md/
  overleg.md bijgewerkt.
- [x] Gecommit, gepusht (`ce33691`), live geverifieerd op
  uitjesagenda.pages.dev — alle 4 events klopten.
- [x] **Michiel "ja, graag" op Universiteitsmuseum Groningen** (het
  laatste restje van punt 13) — `scrape_universiteitsmuseum.py`
  gebouwd. Eerdere inschatting "Playwright nodig" bleek een
  domeinverwarring (universiteitsmuseum.nl → UMU Utrecht i.p.v. het
  Groningse museum op rug.nl) — bleek server-rendered, geen Playwright
  nodig. 2 events/run ("De verloren diamant", "Van Proef tot Publiek").
  "Masterminds" (geen datum) en "Puin Hoop: herdruk van de jaren '80"
  (alleen einddatum, geen start — gepresenteerd door GRID Grafisch
  Museum) bewust overgeslagen. Toegevoegd aan `SRC`, geverifieerd
  lokaal. Punt 13 is nu volledig afgerond op de scope-vraag na.
- [x] Gecommit, gepusht (`fd8e601`), live geverifieerd — beide events
  klopten.

## Sessie 2026-08-22 — Punt 5: nationale sportteams, venue-aanpak

- [x] **Punt 5 opgepakt**: bond-gerichte route (volleybal.nl/Nevobo)
  bleek doodlopend — handmatige HTML-tabel, geen API, alleen
  buitenlandse toernooien, de concrete aanleiding (Martiniplaza-
  oefenwedstrijd) stond er niet eens op.
- [x] **Michiel stelde een venue-aanpak voor**: "afgelopen jaren maar
  een handjevol sporthallen... rotterdam, apeldoorn, doetinchem,
  groningen.. kom jij nog meer tegen?" — websearch leverde 2 extra op
  (Sportcentrum Arcus/Wijchen, Landstede Sportcentrum/Zwolle).
  Feasibility per hal gecheckt: Ahoy (al gedekt), Apeldoorn/Zwolle
  (bouwbaar), Doetinchem/Wijchen (geen bruikbare agenda-bron, skip),
  Martiniplaza (al gedekt maar miste het eigen volleybalweekend).
- [x] **3 scrapers gebouwd**: `scrape_omnisport.py` (12 events/run),
  `scrape_landstedesportcentrum.py` (1 event/run — "Landstede Hammers"
  bewust gefilterd, duplicaat van `scrape_landstede.py`),
  `scrape_martiniplaza_sport.py` (aanvulling op de bestaande
  theater.nl-scraper, dekt nu ook de "Sport"-categorie op
  martiniplaza.nl's eigen site, 2 events/run).
- [x] **Architectuurwijziging**: nieuwe genre-bucket `'sport'`
  toegevoegd aan Uitjes-modus (`cat_map`, `GENRE_ICONS`/`GENRE_LABELS`,
  filterknop, CSS) — los van de bestaande topniveau-"Sport"-modus
  (`SPORT_SRCS`, blijft voor club-thuiswedstrijden). Bijvangst: een los
  `'genre'`-veld in het event-dict bleek al die tijd genegeerd te
  worden door `classify()` — alleen `cats` werkt.
- [x] Gecommit, gepusht, live geverifieerd. Docs bijgewerkt: SCRAPERS.md
  (69 bronnen), decisions.md, overleg.md (punt 5 naar archief), plan.md,
  ARCHITECTURE.md.
- [ ] **Nog open, geen van alle urgent** (zie overleg.md): punt 6
  (landelijke uitbreiding), punt 11 (Admin-scherm, richting bepaald,
  niet gebouwd), punt 13's scope-vraag (alleen Groningen stad vs.
  gerichter Drenthe/Friesland-musea apart zoeken), punt 21
  (scrape_groningermuseum.py geeft 0 resultaten, site herbouwd —
  fixbaar, nog niet opgepakt).

## Sessie 2026-08-22 (vervolg) — Volledige run_weekly_refresh.py-run

- [x] **Michiel: "moeten we niet even een run doen?"** — eerste keer
  de VOLLEDIGE pipeline (69 scrapers) in één keer gedraaid sinds alle
  dit-sessie-toegevoegde scrapers erbij kwamen. 68/69 OK.
- [x] **Bug gevonden en gefixt**: `scrape_staatsbosbeheer.py` printte
  in live-modus nooit een `✓ Klaar:`-regel, waardoor `run_weekly_
  refresh.py`'s succes-detectie het bij ELKE toekomstige run onterecht
  als harde fout zou zien en quarantainen (incl. de geplande ma/wo/za
  04:00-taak) — zowel natuuractiviteiten als alle 220 Wandelingen/
  tochten-routes waren dan stilletjes gestopt met bijwerken. Fix: 1
  samenvattende regel toegevoegd. Zie decisions.md 2026-08-22.
- [x] **Nieuw gevonden, niet urgent**: `scrape_groningermuseum.py`
  geeft 0 resultaten — site herbouwd (Next.js), oude API-endpoints
  404. Wel fixbaar (nieuwe `/programma`-pagina, server-rendered), niet
  in deze sessie opgepakt — genoteerd als overleg.md punt 21.
  Gedeeltelijk cushioned door Kunstpunt Groningen-aggregator.
- [x] Fix + verse data van de volledige run gecommit + gepusht.
