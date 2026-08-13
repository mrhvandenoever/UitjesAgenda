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
- [ ] Waar draait de wekelijkse refresh voortaan: deze laptop, andere pc (na reparatie), of iets anders?
- [ ] Scraper-efficiëntie: per-pagina hash-caching + parallelle requests i.p.v. elke run alles opnieuw ophalen
- [ ] Documentatiestructuur compleet: readme / onboarding / architecture / overleg / plan / decisions — bijhouden wie wat update

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

## Bug: afstandsberekening klopt niet voor aggregator-bronnen (gevonden 2026-08-11)
- **Symptoom** (gemeld door Michiel): filter op 15km vanaf een locatie tussen Annen en Zuidlaren toont Ruinen, Diever, Nieuw-Dordrecht, Vledder, Alteveer, Meppel etc. — allemaal met exact "~13km", terwijl deze plaatsen in werkelijkheid zeer verschillende, deels veel grotere afstanden hebben.
- **Oorzaak bevestigd**: `VENUE_LOC` in `gen_uitjes.py` heeft voor de 3 grote regionale aggregators (`drenthe.nl`, `visitgroningen`, `friesland.nl`) maar **één vast coördinaat per bron**, niet per stad — ongeacht of het event in Ruinen, Meppel of Nieuw-Dordrecht is. Alle events van zo'n bron krijgen dus dezelfde (onjuiste) afstand tot de gebruiker.
- **Impact**: 2777 van de ~6800 events (bijna 40%) bij deze 3 bronnen, verspreid over 254 verschillende plaatsen.
- **Voorstel fix**: bouw een city→lat/lon-lookuptabel voor deze 254 plaatsen (eenmalig geocoden via Nominatim, net als de bestaande adres-zoekfunctie al gebruikt; daarna cachen — coördinaten van dorpen/steden veranderen niet). Gebruik in `event_html()`/de afstandsberekening per event de eigen stad-coördinaten i.p.v. de vaste bron-coördinaten, met de huidige `VENUE_LOC`-waarde alleen nog als fallback voor events zonder herkenbare `city`.
- [ ] Lookuptabel bouwen (254 plaatsen, eenmalige geocode-actie)
- [ ] `gen_uitjes.py` aanpassen: per-event coördinaten i.p.v. per-bron
- [ ] Verifiëren met het Annen/Zuidlaren-voorbeeld van Michiel

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
- [ ] Donar (basketbal) — 3 platforms onderzocht, nog niet opgelost. Zie SCRAPERS.md voor de volledige stand (Foys-API, NBB-API met lege 2026-2027-data, livescore.com-tip van Michiel nog te proberen).
- [ ] Zummerbühne, OntdekPoort, Hunebedcentrum — bleken bij nader inzien AI/Chrome nodig (ticketwidget resp. bot-bescherming), verplaatst in SCRAPERS.md.

### Sessie 2026-08-13 vervolg — nog 6 scrapers erbij
- [x] Nieuwe Kolk (denieuwekolk.nl) — eindelijk de per-event-URL opgelost, plus /bieb/-bibliotheekactiviteiten bewust uitgesloten (37 events)
- [x] Lycurgus, Sudosa, Friso (Nevobo RSS, zelfde patroon als eerder)
- [x] Dorpshuis Annen (Jimdo-site, tekst-pattern-matching)
- [x] Nienoord (oude regex was stuk door site-wijziging, herbouwd — kleiner dan verwacht: 3 i.p.v. ~9)
- 6986 → 7031 events na deze batch

### Resterende sporen (zie SCRAPERS.md voor details)
- [ ] **4 bronnen "kan zonder AI"**: Geke Hoogstins (rommelige tekststructuur), Machinefabriek (via podiuminfo.nl), Noorderbron, AFAS Live.
- [ ] **16 bronnen "AI/Chrome nodig"**: Vera, Atlas Emmen, Simplon, Grand Theatre, Winsinghhof, EM2, Neushoorn, Groninger Museum, Drents Museum, Zuidhaege Assen, Koornbeurs, Zummerbühne, OntdekPoort, Hunebedcentrum, FC Groningen, GIJS Groningen.
- [ ] **15 bronnen nog nooit geprobeerd**: TivoliVredenburg, Melkweg, Paradiso, 013, Ziggo Dome, Effenaar, Doornroosje, Ahoy, Het Paard, Hedon Zwolle, Rotown, De Doelen, GelreDome, Concertgebouw, Landstede.
- [ ] Weekelijkse-refresh-commandolijst in `ARCHITECTURE.md` mee laten groeien (of omzetten naar `for f in scrape_*.py`, zie overleg.md) — inmiddels 21 losse scripts, lijst wordt onhandig lang.

## Later / open items (uit ARCHITECTURE.md)
- [ ] Ticketmaster Discovery API (gratis tier, 5.000 req/dag) — key aanvragen op developer.ticketmaster.com
- [ ] Lycurgus/Sudosa/Friso — 2e seizoenshelft volleybal nog niet gepubliceerd door de bond, later herscrapen
- [ ] GIJS Groningen — URL is nu wel bekend (gijsgroningen.nl/gijs-eredivisie/), maar toont nog seizoen 2025-2026; herchecken zodra 2026-2027 live is
- [ ] Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- [ ] Overige scraping-recipes zonder werkende methode — zie `SCRAPERS.md` voor de actuele, volledige stand
