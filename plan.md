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
- [ ] Scraper-efficiëntie: per-pagina hash-caching (gebouwd, zie sessie 2026-08-14) + parallelle requests (nog niet gebouwd) i.p.v. elke run alles opnieuw ophalen
- [ ] Documentatiestructuur compleet: readme / onboarding / architecture / overleg / plan / decisions — bijhouden wie wat update

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
- [ ] Resterende bronnen zonder duidelijk vervolgpad (zie SCRAPERS.md voor details per bron): Grand Theatre, Winsinghhof (domein onbereikbaar), Koornbeurs, Groninger Museum, Drents Museum, Zummerbühne, OntdekPoort (403), Hunebedcentrum (403), GIJS Groningen (oud seizoen), Doornroosje, De Doelen, Ahoy, GelreDome, Paradiso, Concertgebouw, Rotown, Het Paard, Hedon Zwolle

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
- [ ] Ticketmaster Discovery API (gratis tier, 5.000 req/dag) — key aanvragen op developer.ticketmaster.com
- [ ] Lycurgus/Sudosa/Friso — 2e seizoenshelft volleybal nog niet gepubliceerd door de bond, later herscrapen
- [ ] GIJS Groningen — URL is nu wel bekend (gijsgroningen.nl/gijs-eredivisie/), maar toont nog seizoen 2025-2026; herchecken zodra 2026-2027 live is
- [ ] Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- [ ] Overige scraping-recipes zonder werkende methode — zie `SCRAPERS.md` voor de actuele, volledige stand
