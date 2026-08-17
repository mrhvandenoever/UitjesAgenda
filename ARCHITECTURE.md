# Uitjes Agenda — Architecture

**Live site:** https://uitjesagenda.pages.dev  
**Repo:** https://github.com/mrhvandenoever/UitjesAgenda  
*(Let op: GitHub heeft de repo hernoemd van `uitjesagenda` naar `UitjesAgenda` — remote in lokale clone is bijgewerkt)*

---

## Hoe het werkt (in één zin)

`gen_uitjes.py` leest `events_categorized.json` en schrijft alles — HTML, CSS en JavaScript — inline naar één bestand `index.html`. Cloudflare Pages voert dat script uit bij elke push naar `main`.

---

## Bestanden

| Bestand | Rol |
|---|---|
| `gen_uitjes.py` | Python generator. Leest JSON, schrijft index.html. |
| `events_db.py` | SQLite-laag: import/export/dedup. Zie ook §Cross-source dedup. |
| `events_categorized.json` | Brondata — alle events. Single source of truth. |
| `scraping_recipes.json` | Per-bron scrape-instructies (render_type, code, agenda_url). |
| `index.html` | Gegenereerde output. **Nooit handmatig aanpassen.** |
| `requirements.txt` | `playwright` (sinds 2026-08-15, alleen voor lokale headless-browser-scrapers) — verder leeg, de rest is pure Python stdlib. Cloudflare-build gebruikt dit bestand niet (roept alleen `gen_uitjes.py` aan, stdlib-only). |
| `secrets_local.py` + `secrets.local.json` | API-keys (bv. Ticketmaster) — `secrets.local.json` staat in `.gitignore`, nooit committen. Zie §API-keys hieronder. |
| `scrape_<bron>.py` | Eén los scraper-script per bron/venue (zie §Scrapers-conventie). 56 scripts op dit moment — zie `SCRAPERS.md` voor de volledige, actuele lijst per bron (dit bestand houdt bewust geen kopie van die lijst bij, om drift te voorkomen). |
| `run_weekly_refresh.py` | Draait alle `scrape_*.py`-bestanden parallel in twee pools (plain-HTTP/Playwright), daarna export + generate. Zie §Wekelijkse refresh en §Parallelle scrapers. |
| `page_cache.py` | Change-detection: hash-cache in `events.db` om parse/insert-werk over te slaan als een bron ongewijzigd is. Zie §Change-detection. |
| `ssl_fix.py` | Workaround voor `ssl.VERIFY_X509_STRICT` (Python 3.13+), side-effect-import via `page_cache.py` — dus geen aparte import per scraper nodig. Zie decisions.md 2026-08-15. |
| `parallel_fetch.py` | Concurrent pagina's ophalen binnen één scraper (`fetch_many()`/`fetch_batches()`), voor de 7 scrapers met een multi-request paginaloop. Zie §Parallelle scrapers. |
| `scrape_<bron>_pw.py`-stijl (Playwright) | Scrapers voor JS-gerenderde bronnen die geen verborgen API hebben — headless Chromium rendert de pagina, script leest daarna de DOM. Geen AI/LLM nodig per run. Zie §Playwright-scrapers, decisions.md 2026-08-15. Bewust nooit ingezet tegen bot-detectie/CAPTCHA's (TivoliVredenburg, OntdekPoort, Hunebedcentrum blijven daarom buiten schot). |
| `SCRAPERS.md` | Status per bron: geautomatiseerd / kan zonder AI (recipe klaar) / AI-Chrome nodig / nog niet geprobeerd. |
| `CLAUDE.md` | Werkwijze voor Claude in deze repo (wanneer welk .md-bestand lezen/bijwerken). |
| `onboarding.md` / `overleg.md` / `plan.md` / `decisions.md` | Voor beheerders: resp. hoe-neem-ik-dit-over, open discussiepunten, to-do, genomen beslissingen. |

---

## gen_uitjes.py — structuur

### Bovenaan: data-definities

#### `SRC` dict — bronregistratie
```python
SRC = {
    'sleutelwoord': ('Weergavenaam', 'emoji', '#kleurcode'),
    ...
}
```
Elke bron heeft een unieke sleutel (lowercase, geen spaties). De kleur bepaalt de kleur van het filter-knopje en de linkerrand van events.

#### `VENUE_LOC` dict — locatie voor afstandsfilter
```python
VENUE_LOC = {
    'sleutelwoord': (lat, lon, 'Provincie'),
    ...
}
```
Lat/lon wordt gebruikt voor de Haversine-afstandsberekening in de browser. Provincie bepaalt de provinciefilterbadge van elk event.

#### `MUSIC_VENUES`, `THEATER_VENUES`, `EXPO_VENUES` — sets
Gebruikt als fallback in `classify()` als er geen keyword-match is in de titel.

#### `SPORT_CLUBS` dict — sport-indeling
```python
SPORT_CLUBS = {
    'voetbal':    ['fcgroningen', 'fcemmen', 'heerenveen', 'cambuur', 'fctwente', 'goahead', 'peczwolle'],
    'basketbal':  ['donar', 'landstede'],
    'volleybal':  ['lycurgus', 'sudosa', 'friso'],
    'ijshockey':  ['grizzlys', 'flyers', 'ogcapitals'],
    'handbal':    ['hurryup', 'eoemmen'],
    'korfbal':    ['ldodk', 'dos46'],
}
```
`SPORT_SRCS` is de afgeleide set van alle sport-sleutelwoorden. Sport-events worden gefilterd uit de uitjes-modus; alleen zichtbaar in sport-modus. Zie `SCRAPERS.md`/`plan.md` voor welke clubs daadwerkelijk data hebben — sommige staan al in deze dict maar hebben (nog) 0 events omdat het seizoensschema nog niet gepubliceerd is.

`SPORT_ICONS`/`SPORT_LABELS` (bij `SPORT_COLORS`, zie hieronder) geven per sporttype het icoon/label voor de genre-badge — `event_html()` gebruikt deze rechtstreeks voor sport-events, in plaats van via `classify()` te gokken op de titel (zie §classify()).

#### `LANDELIJK` set
```python
LANDELIJK = {'tivolivredenburg','melkweg','paradiso','013','ziggodome','effenaar','doornroosje','ahoy'}
```
Landelijke podia krijgen een eigen "🗺️ Landelijk" groepknop in de bron-filter. Ze zijn opgeslagen onder hun eigen provincie (Utrecht, Noord-Holland, etc.) zodat het provinciefiter correct werkt.

#### `prov_colors` dict
Kleur per provincie voor de knopstatus in de UI.

#### `SPORT_COLORS` dict
Kleur per sporttype (voetbal, basketbal, etc.) voor de knopstatus.

---

### `classify(title, cats, source)` — genre-classifier

**Sport-events slaan `classify()` volledig over** — `event_html()` checkt eerst `src in SPORT_SRCS` en gebruikt dan direct het `sport`-veld uit de JSON (via `SPORT_ICONS`/`SPORT_LABELS`). Reden: titels als "FC Twente - PEC Zwolle" matchen geen enkel keyword en vielen voorheen terug op `overig`.

Voor niet-sport-events, volgorde van prioriteit:

1. **Kinderen-check** (regex) — altijd eerst, overschrijft alles
2. **`cats`-veld** uit JSON (als aanwezig en herkenbaar — `cat_map` bevat o.a. `theater`, `cabaret`, `musical`, `klassiek`, `opera`, `dans`, `kinderen`, `jazz`, `pop`)
3. **Expo-venues** (groningermuseum, drentsmuseum, hunebedcentrum) → `expo`
4. **Titelkeywords** — **jazz/blues eerst**, dán klassiek, musical, cabaret, dans, expo, theater, festival, pop, actief
5. **Venue-fallback** — music_venues → `pop`, theater_venues → `theater`, anders → `overig`

**Let op — genre-ambiguïteit**: woorden als "quartet"/"kwartet"/"trio"/"ensemble"/"kamer" duiden **niet** betrouwbaar op klassieke muziek — jazz-combo's heten net zo vaak "Quartet". Deze woorden staan daarom bewust *niet* in de klassiek-keywordlijst (stonden er eerder wel in, gaf verkeerde classificatie bij bv. "Peter Bernstein Quartet"). Bronnen die zelf een genre-signaal geven (zoals SPOT's `data-subgenres`, zie `scrape_spotgroningen.py`) zijn betrouwbaarder dan titel-keywords — geef die door via het `cats`-veld.

**Bug gevonden en gefixt 2026-08-15**: het losse keyword `'strip'` in de expo-titelkeywords matchte als *substring* ook `"Striptease"` — 3 theater/cabaretshows ("Striptease Van De Dood") werden daardoor onterecht als `expo` geclassificeerd. Vervangen door specifiekere `'stripverhaal'`/`'stripmuseum'`/`'stripkunst'`. Dit kwam pas echt aan het licht toen Exposities een eigen zichtbare sectie kreeg (zie hieronder) — voorheen ging zo'n fout genre-label onopgemerkt schuil tussen honderden Uitjes-events.

`icon_map`/`glabel_map` (icoon + label per genre) zijn gehoist naar module-niveau als `GENRE_ICONS`/`GENRE_LABELS`, zodat zowel `event_html()` als `expo_card_html()` (zie hieronder) dezelfde bron gebruiken i.p.v. gedupliceerde lokale dicts.

Genre wordt sinds 2026-08-15 **één keer per event vooraf berekend** (`event_genre(e)`, opgeslagen als `e['_genre']`) in plaats van opnieuw aangeroepen in `event_html()` — nodig omdat de filterstap (`event_is_valid()`, zie §Exposities) het genre ook al moet weten vóórdat er gerenderd wordt.

---

### HTML-generatie

`event_html(e)` genereert per event een `<div>` met data-attributen:
- `data-src` — bronsleutel
- `data-genre` — genre (uitkomst van classify)
- `data-prov` — provincie (uit VENUE_LOC)
- `data-latlon` — lat,lon voor afstandsberekening

De JavaScript in de browser filtert puur op deze data-attributen — geen server-side filtering.

---

## Exposities (derde topniveau-modus)

Gebouwd 2026-08-15/16, richting bepaald in overleg.md punt 10. Events met
`_genre=='expo'` worden **volledig uit `events_valid`/`main_html` gehaald** en
apart gehouden in `expo_valid`/`expo_html` — ze zitten dus niet tussen de
maand-secties van Uitjes/Sport, maar in een eigen platte lijst.

**Zichtbaarheidsregel (route A, overleg.md punt 10)**: een expositie blijft
zichtbaar totdat een bekende `date_end` al voorbij is. Geen `date_end`
ingevuld → altijd zichtbaar, ongeacht hoe ver de startdatum (`date`) al in het
verleden ligt. Dit is bewust anders dan de normale `TODAY<=date<=2027-12-31`-
regel voor Uitjes/Sport (`event_is_valid(e)` in `gen_uitjes.py` splitst dit
per event op basis van `e['_genre']`). Vrijwel geen scraper vult `date_end` op
dit moment in (2026-08-15: 1 van ~6669 events) — dat is een bewuste,
geaccepteerde consequentie van route A, geen bug: exposities blijven simpelweg
zichtbaar tot een scraper ooit een echte einddatum aanlevert.

**Rendering**: `expo_card_html(e)` (geen maand-groepering, i.t.t. `event_html`)
toont "vanaf `<startdatum>` · t/m `<einddatum>`" of "vanaf `<startdatum>` ·
einddatum onbekend". Kaart-layout is 2 kolommen (`.event.expo-item{{grid-
template-columns:1fr auto;}}`, hogere specificiteit dan de standaard
3-koloms-`.event`-regel zodat het ook onder de mobile media-query wint) i.p.v.
de standaard 3-koloms-kaart met een smalle datumkolom — een datumbereik past
niet in 70px.

**Sortering**: default op startdatum (server-side, `expo_valid` is al zo
gesorteerd), met knoppen "Startdatum"/"Einddatum"/"Alfabetisch" die **client-
side** de DOM-nodes in `#expo-wrap` herordenen (`Array.sort()` +
`appendChild()` in volgorde — geen page-reload, geen server-round-trip).
Events zonder `date_end` krijgen `data-dateend="9999-99-99"` (sentinel) zodat
ze bij sorteren-op-einddatum altijd onderaan komen i.p.v. bovenaan.

**Filters**: Provincie + afstand werken automatisch mee (zelfde gedeelde
`.filters`-blok en `apply()`-logica als Uitjes/Sport, geen aparte code nodig).
Bewust **geen** eigen Bron-filter gebouwd — bij de huidige kleine omvang (4
events, 3 bronnen) niet nodig, kan later alsnog als het aantal groeit.

**Mode-toggle**: derde knop "🖼️ Exposities" naast Uitjes/Sport. `setMode()`
verbergt/toont `<main>` (maand-secties) vs `#expo-wrap` (platte lijst) en de
bijbehorende filter-balken (`#expo-filters` i.p.v. `#uitjes-genre`/
`#uitjes-src`/`#sport-filters`).

**Bijvangst-bug gevonden en gefixt tijdens deze bouw**: `apply()` (de client-
side filterfunctie) werd nergens aangeroepen bij het laden van de pagina —
alleen vanuit knop-click-handlers. Gevolg: op een verse paginalaad stonden
sportwedstrijden gewoon zichtbaar tussen de Uitjes-events totdat een gebruiker
voor het eerst een filter aanklikte (bevestigd op de live site vóór de fix:
172 sportevents zichtbaar in Uitjes-modus bij het laden). Fix: `setMode
('uitjes')` (roept zelf `apply()` aan) toegevoegd aan het JS-init-blok. Dit
was al zo vóór de Exposities-bouw — puur toevallig ontdekt omdat dezelfde
init-code voor de nieuwe derde modus aangepast moest worden.

---

### JavaScript (inline, f-string)

**Let op:** de JS zit in een Python f-string. Alle letterlijke accolades in JS moeten worden verdubbeld: `{{` en `}}`. Vergeet dit → `KeyError` of `ValueError` bij het runnen van `gen_uitjes.py`.

Kernvariabelen:
- `selSrc`, `selGenre`, `selProv` — Sets met actieve filters
- `selSport`, `selClub` — Sets voor sport-modus
- `currentMode` — `'uitjes'` of `'sport'`
- `centerLat`, `centerLon` — Middelpunt voor afstandsfilter (standaard: Annen)
- `maxDist` — Max afstand in km (5 stappen: 25/50/75/100/9999)

Knop-activatie gebruikt **JavaScript inline styles**, niet CSS-klassen, om CSS-transition-timing problemen te vermijden:
```javascript
function actBtn(el, c) { el.style.background=c; el.style.color=...; el.style.borderColor=c; }
function deactBtn(el)  { el.style.background=''; el.style.color=''; el.style.borderColor=''; }
```

Afstandsberekening via Haversine in de browser. Geocoding via Nominatim (OpenStreetMap) — geen API-key nodig.

---

## events_categorized.json — schema

Elke entry is een object:

```json
{
  "title":  "Voorstellingsnaam",
  "date":   "2026-09-15",
  "venue":  "Locatienaam, Stad",
  "url":    "https://...",
  "source": "bronsleutel",
  "genre":  "theater",
  "cats":   ["toneel"]
}
```

Sport-events hebben extra veld:
```json
{
  "source": "fcgroningen",
  "genre":  "sport",
  "sport":  "voetbal"
}
```

**Regels:**
- `source` moet overeenkomen met een sleutel in `SRC`
- `date` is ISO 8601 (`YYYY-MM-DD`)
- `genre` wordt door `gen_uitjes.py` opnieuw berekend via `classify()` — het veld in JSON is informatief, niet bindend
- Events vóór vandaag of na 2027-12-31 worden gefilterd

---

## scraping_recipes.json — schema

Per bron:
```json
{
  "display_name":    "Naam in UI",
  "agenda_url":      "https://...",
  "render_type":     "static | client_js | manual | unresolved | unverified",
  "scrape_code":     "kant-en-klare Python of JS code",
  "notes":           "bijzonderheden",
  "sample_event_url":"voorbeeld event-URL",
  "last_verified":   "2026-07-05"
}
```

`render_type` bepaalt de scraping-aanpak:
- `static` → urllib/requests volstaat
- `client_js` → Chrome MCP vereist (JavaScript wordt uitgevoerd in de browser) — tenzij alsnog een verborgen API gevonden wordt (gebeurde bij SPOT en handbal.nl, die zagen er eerst uit als `client_js` maar bleken toch `static`)
- `manual` → geen automatische scraping (eenmalig handmatig, of vast jaarlijks event zoals in `scrape_handmatig.py`)
- `resolved_locally` → data staat er, ooit eenmalig lokaal/via Chrome opgelost, maar geen herhaalbaar script
- `duplicate_skip` → bewust niet los toegevoegd, events komen al via een andere bron binnen
- `unresolved` → bekend probleem, nog geen werkende methode
- `unverified` → niet getest

Het `_meta`-veld bevat de genre-classifier-definitie en `dead_ends` (bronnen die zijn opgegeven). Zie `SCRAPERS.md` voor de actuele status per bron in tabelvorm.

---

## Scrapers-conventie: één bestand per bron

Elke bron krijgt een eigen, klein `scrape_<naam>.py`-bestand (zie `SCRAPERS.md` voor
de volledige lijst) — bewust geen gedeeld/groot scraper-bestand, ook niet als dat
duplicatie tussen scripts oplevert (bv. meerdere venues op hetzelfde
ticketing-platform). Redenen: kleinere bestanden zijn veiliger te editen (zelfde
risico als de KRITIEKE REGEL hieronder voor `gen_uitjes.py`, alleen dan preventief),
en een foutmelding uit één scraper wijst meteen naar precies het juiste bestand.

Elk scraper-script volgt hetzelfde patroon (zie `scrape_spotgroningen.py` of
`scrape_handbal.py` als recent voorbeeld):
- CLI met `--dry-run` (toont events zonder op te slaan)
- `insert_event()` uit `events_db.py` voor het opslaan
- `log_scrape()` aan het eind voor de scrape-historie
- Docstring bovenaan met de gebruikte methode/URL/eventuele bijzonderheden

Einddoel: de wekelijkse refresh volledig automatisch zonder AI. AI (Chrome MCP)
wordt alleen eenmalig ingezet om de scrape-methode van een bron te *ontdekken*
(netwerkverkeer/DOM uitlezen) — niet structureel bij elke run. Voortgang staat in
`SCRAPERS.md`.

---

## Change-detection (page_cache.py)

Elke scraper haalt bij elke run alle pagina's opnieuw op — dat blijft zo
(zie §Wekelijkse refresh, netwerktijd is niet het doel hiervan). Wat wél
overgeslagen kan worden: de parse/insert-stap, als de opgehaalde data
identiek is aan de vorige run. Daarvoor is `page_cache.py` gebouwd:

```python
from page_cache import unchanged

# ...verzamel events zoals normaal in een lijst...

if unchanged(SOURCE, all_events):
    log_scrape(SOURCE, len(all_events), 0, notes='ongewijzigd, geskipt')
    print(f"✓ Klaar: {len(all_events)} gevonden, geen wijzigingen (geskipt)")
    return len(all_events), 0

# ...anders: normale insert_event()-loop...
```

`unchanged(key, data)` hasht `data` (SHA256, via `repr()`) en vergelijkt met
de hash die bij `key` is opgeslagen in de `page_hash`-tabel in `events.db`
(zelfde database, aparte tabel — geen los bestand). Werkt de hash altijd bij,
ook bij de eerste keer of bij een wijziging.

**Ontwerpkeuzes:**
- **Vergelijk de geëxtraheerde data, niet de ruwe HTML.** HTML bevat vaak
  ruis (advertenties, CSRF-tokens, timestamps) die een "wijziging" lijkt
  terwijl de events zelf niet veranderd zijn — dat zou de cache waardeloos
  maken (elke run "gewijzigd").
- **Geen early-stop tijdens het ophalen.** Bewust niet gekozen (zie
  `overleg.md` punt 2): bij bronnen die niet gegarandeerd append-only zijn
  kan een nieuw event ook op een oudere pagina verschijnen. Elke pagina
  wordt dus nog steeds opgehaald; alleen het parsen/opslaan wordt
  overgeslagen als de inhoud (of de hele resulterende eventlijst)
  ongewijzigd is.
- **Eén key per bron is meestal genoeg** (`SOURCE`, bv. `'martiniplaza'`).
  Voor bronnen met losse sub-onderdelen (meerdere teams/pagina's die
  onafhankelijk kunnen wijzigen) kan een specifiekere key gebruikt worden,
  bv. `f"{SOURCE}:cambuur"` — dan wordt per sub-onderdeel bepaald of parsen
  nodig is in plaats van alles-of-niets voor de hele bron.
- **`--dry-run` negeert de cache** — een dry-run toont altijd alle gevonden
  events, en werkt de hash niet bij (geen state-wijziging bij een preview).
- **Valkuil bij handmatige DB-opruiming** (zie decisions.md 2026-08-15,
  Ziggo Dome): als je na een scrape handmatig rijen in `events` verwijdert
  (bv. stale/dubbele data opruimen) en de bron daarna opnieuw scraped, kan
  `unchanged()` denken dat er "niks veranderd" is — de opgehaalde data zelf
  is immers identiek aan de vorige run — en slaat dan de hele insert-stap
  over, ook al mist de DB nu een rij die er wel hoort te staan. Fix: wis
  eerst de `page_hash`-rij voor die bron (`DELETE FROM page_hash WHERE
  key='<source>'`) vóór de eerstvolgende run na een handmatige opruiming.

**Status (2026-08-14):** uitgerold naar alle 30 scrapers die live data ophalen
(31e, `scrape_handmatig.py`, bewust overgeslagen — vaste jaarlijkse events,
niets om te cachen). Grotendeels mechanisch toegepast (het insert-patroon was
opvallend consistent over alle bestanden) met een migratiescript, twee
afwijkende bestanden (`scrape_friesland.py`, `scrape_naarzuidlaren.py` —
inline dict-literal i.p.v. losse `ev`-variabele) met de hand. Getest op
`scrape_bostheater.py` en `scrape_handbal.py`: tweede live run meldt
"geen wijzigingen sinds vorige run (geskipt)", `--dry-run` negeert de cache
zoals bedoeld. Let op `scrape_naarzuidlaren.py`: gebruikt bewust dezelfde
`SOURCE = 'drenthe.nl'` als `scrape_drenthe.py` (provincie-filter), maar een
eigen cache-key (`SOURCE + ':naarzuidlaren'`) — anders zou een wijziging bij
de één de cache van de ander onterecht laten denken dat er niks veranderd is.

## Parallelle scrapers (Niveau A + B, gebouwd 2026-08-16)

Twee onafhankelijke niveaus van parallellisatie, zie overleg.md punt 2 en
decisions.md 2026-08-16 voor de volledige geschiedenis.

### Niveau A — tussen scrapers (`run_weekly_refresh.py`)

De hoofdlus draait alle `scrape_*.py`-bestanden niet meer na elkaar, maar in
twee `ThreadPoolExecutor`-pools die tegelijk lopen:
- **plain-HTTP-pool** (max 8 gelijktijdig, default): lichte scrapers, gewoon
  `urllib`-requests.
- **Playwright-pool** (max 3 gelijktijdig, default): elk een eigen headless
  Chromium-proces, geheugen-zwaarder — vandaar een lagere limiet.

Scraper-type wordt herkend door het bestand te grep'en op de string
`"playwright"` (`is_playwright_scraper()`) — geen aparte config per script
nodig. Concurrency instelbaar via `--max-plain`/`--max-playwright`; op 1
zetten geeft het oude sequentiële gedrag terug zonder code-wijziging (handige
noodrem als er in productie iets misgaat). Output van elk script wordt als
één blok geprint zodra dat script klaar is — de volgorde is nu
voltooiingsvolgorde, niet meer bestandsvolgorde.

**Randvoorwaarde**: alle scrapers schrijven naar dezelfde SQLite-file via
`insert_event()`. `events_db.py`'s `get_conn()` gebruikt daarom `PRAGMA
journal_mode=WAL` + `busy_timeout=30000` — zonder deze fix zou gelijktijdig
schrijven een "database is locked"-fout kunnen geven.

### Niveau B — binnen één scraper (`parallel_fetch.py`)

Voor de 7 scrapers met een echte multi-request paginaloop (`scrape_drenthe.py`,
`scrape_friesland.py`, `scrape_visitgroningen.py`, `scrape_forum.py`,
`scrape_kielzog.py`, `scrape_posthuistheater.py`, `scrape_paard.py`) — de
overige ~49 doen 1 request of een handjevol en zijn onaangeraakt.
Concertgebouw/GelreDome hebben ook paginering maar via Playwright met al één
hergebruikte browser-instance — bewust buiten scope (ander soort wijziging).

`parallel_fetch.py` biedt twee functies, geen scraping-logica erin (zelfde
soort klein infra-bestand als `ssl_fix.py`/`page_cache.py`/`ticketmaster.py`):

```python
from parallel_fetch import fetch_many, fetch_batches

# 1. Bekend aantal pagina's vooraf (bv. friesland.nl: totaal uit "van X
#    resultaten" op pagina 1, dan de rest in één keer):
for p, (html, exc) in zip(pages, fetch_many(pages, lambda p: fetch(url(p)))):
    if exc is not None: ...  # zelfde try/except-per-pagina-gevoel als voorheen
    ...

# 2. Aantal pagina's pas bekend terwijl je gaat (bv. drenthe.nl):
fetched = fetch_batches(1, lambda p: fetch(url(p)), should_stop_fn,
                         batch_size=5, max_batches=..., stop_after_consecutive=1)
for page, html, exc in fetched:
    ...  # nog steeds sequentieel VERWERKEN or breken op het eigen stopsignaal
```

Beide draaien op `concurrent.futures.ThreadPoolExecutor` + de bestaande
`urllib`-fetch-functie van elke scraper — geen nieuwe dependency (alle 7
kandidaten gebruikten al `urllib`, niet `requests`). Default concurrency is
laag (5 gelijktijdig per bron) — bewuste keuze, deze sites zijn nu gewend aan
één sequentiële request tegelijk en te veel gelijktijdige connecties kan
alsnog rate-limiting/bot-detectie triggeren die er nu niet is.

**Belangrijke les, ontdekt tijdens het bouwen (2026-08-16) — kies het
stopsignaal zorgvuldig.** Het eerste ontwerp van `fetch_batches()` gebruikte
"0 events op de pagina" als signaal om te stoppen met verder ophalen. Voor
drenthe.nl bleek dit **onbetrouwbaar**: de site geeft voorbij het echte einde
gewoon een fallback-pagina terug (bevestigd: pagina 42/50/60 gaven allemaal 8
events, nooit 0) — dus "0 events" kwam letterlijk nooit voor, en het ophalen
liep door tot de veiligheidsgrens (105 pagina's i.p.v. de echte ~41), wat de
hele snelheidswinst tenietdeed (3m34s, nauwelijks sneller dan de oude
sequentiële versie). Het WEL betrouwbare signaal was het al langer bestaande
`f'page={page+1}' not in html`-check (ontbrekende "volgende pagina"-link) —
`fetch_batches()`'s callback is daarom `should_stop_fn(page, resultaat)`
(met het paginanummer erbij, nodig voor zo'n check) i.p.v. simpelweg
"is dit resultaat leeg". Na de fix: 13.1s voor drenthe.nl, identiek
eventaantal (1221) — de bug kostte alleen tijd, geen foute data.
`scrape_visitgroningen.py` bleek een vergelijkbare, wél-vertrouwde
"0 events + geen next-link"-combinatie te hebben (geen fallback-content-kwirk
zoals drenthe.nl) — maar had een te lage voorlopige veiligheidsgrens (60,
terwijl het echte einde pas rond pagina 70-80 ligt), waardoor een eerste test
er stil maar 489 van de uiteindelijke 1030 events uithaalde. Beide lessen:
**meet het echte eindpunt van een bron voor je een aanname over paginacount
of stopsignaal in code vastlegt.**

## Playwright-scrapers

Sinds 2026-08-15 (zie decisions.md) is `playwright` toegevoegd als eerste
externe dependency (`requirements.txt`), specifiek voor bronnen die
JS-rendering nodig hebben en waarvoor geen verborgen API te vinden was
(anders dan bv. Atlas Emmen/Melkweg/013, die uiteindelijk zónder browser
opgelost bleken — zie SCRAPERS.md). Installatie: `pip install -r
requirements.txt && playwright install chromium` (eenmalig, ~300MB
browser-download).

Patroon (zie `scrape_neushoorn.py` als eerste voorbeeld): een functie die
Chromium headless start, naar de URL navigeert, wacht op `networkidle` (+
een korte extra `wait_for_timeout` voor late JS-updates), en de gerenderde
`page.content()` teruggeeft als HTML-string — daarna gewoon dezelfde
regex-extractie als bij de niet-Playwright-scrapers. Geen AI/LLM betrokken;
dit is pure browser-automatisering, dus prima geschikt voor de wekelijkse
refresh (`run_weekly_refresh.py` pikt deze scripts automatisch op, net als
alle andere `scrape_*.py`-bestanden — geen aparte behandeling nodig).

**Principiële grens**: Playwright wordt bewust NOOIT ingezet om
bot-detectie of CAPTCHA's te omzeilen. Bronnen met een bevestigde
Cloudflare-uitdaging (TivoliVredenburg) of 403-bot-bescherming (OntdekPoort,
Hunebedcentrum) blijven daarom buiten deze aanpak, ongeacht of een headless
browser die blokkade toevallig zou kunnen passeren.

Overweeg voor toekomstige Playwright-scrapers: opstarttijd is merkbaar
trager dan een plain `urllib`-request (~7s voor Neushoorn, vs <1s voor de
meeste andere scrapers) — bij veel Playwright-scrapers kan dit de totale
duur van `run_weekly_refresh.py` merkbaar verlengen. Nog niet geoptimaliseerd
(bv. één gedeelde browser-instance voor meerdere scrapers) — apart punt,
zie plan.md. Voor bronnen met véél pagina's (bv. Concertgebouw, ~40) wél al
één browser-instance hergebruikt binnen die ene scraper (zie
`fetch_all_pages()` in `scrape_concertgebouw.py`) — dat scheelt fors t.o.v.
per pagina een nieuwe Chromium starten.

**Infinite-scroll i.p.v. paginering** (zie `scrape_vera.py`, decisions.md
2026-08-15): sommige bronnen laden extra content pas na scrollen
(IntersectionObserver), niet via een klikbare knop of `?page=N`-URL. Een
`page.mouse.wheel(0, N)` in een lus, net zo lang tot het aantal gevonden
items niet meer groeit (2-3x stabiel = klaar), simuleert dit. **Let op**:
een falende curl-POST naar een AJAX-endpoint is geen bewijs van bot-
detectie — check eerst of de site misschien gewoon scroll- of klik-
interactie verwacht die curl niet kan nabootsen, vóór je concludeert dat
een bron "geblokkeerd" is. Een échte Cloudflare-challenge-pagina (zoals bij
TivoliVredenburg, "Just a moment...") is wél een harde grens.

## API-keys

Sommige bronnen (bv. de Ticketmaster Discovery API, zie plan.md) vereisen
een eigen API-key. Nooit hardcoded in een `scrape_*.py`-bestand en nooit in
de chat plakken (zie decisions.md 2026-08-15 — zelfde risico als het
GitHub-PAT-incident: een key die eenmaal in een transcript staat, moet als
gecompromitteerd behandeld worden).

Patroon: `secrets.local.json` (staat in `.gitignore`, nooit gecommit) met
per key een entry, uitgelezen via `secrets_local.get_secret(naam)`:

```python
from secrets_local import get_secret
API_KEY = get_secret('ticketmaster_api_key')
```

Eenmalig opzetten (per machine, niet via chat): kopieer
`secrets.local.json.example` naar `secrets.local.json` en vul de echte
waarde(s) zelf in een lokale editor in.

## Ticketmaster-scrapers

Sinds 2026-08-15: voor grote arena's/podia die via Ticketmaster verkopen is
`ticketmaster.py` een herbruikbare helper rond de gratis Discovery API
(zie §API-keys hierboven voor de key-opslag). Patroon (zie
`scrape_ziggodome.py`/`scrape_ahoy.py`):

```python
from ticketmaster import fetch_venue_events
VENUE_ID = 'Z598xZbpZdFeF'  # eenmalig opgezocht met find_venue_id('...')
items = fetch_venue_events(VENUE_ID)
```

`find_venue_id(keyword)` is bedoeld om **eenmalig** te draaien (bv. via een
losse `python -c`-eenregelaar) om het juiste venue-id te vinden — niet om
in de scraper zelf bij elke run aan te roepen, want een naam-zoekopdracht
kan per ongeluk een ander venue matchen (Ticketmaster geeft vaak meerdere
resultaten terug voor dezelfde naam, bv. "Ziggo Dome", "Ziggo Dome Club",
"Vinyl Room - Ziggo Dome"). Het venue-id zelf is stabiel.

**Niet elk podium verkoopt via Ticketmaster** — geprobeerd voor Paradiso en
Concertgebouw (venue gevonden, 0 events) en Rotown/Het Paard (geen
venue-match). Alleen bruikbaar gebleken voor de grotere commerciële
arena's/stadions (Ziggo Dome, Ahoy).

Rate limits (gratis tier): 5.000 calls/dag, 5 requests/seconde, deep paging
tot `size*page<1000` — `ticketmaster.py` wacht zelf minimaal 0.25s tussen
calls en gebruikt `size=200` om het aantal requests te minimaliseren.

## Cross-source dedup & insert-prioriteit

Regionale aggregators (`drenthe.nl`, `visitgroningen`, `friesland.nl`, samen
`AGGREGATOR_SOURCES` in `events_db.py`) herlisten vaak events die al rechtstreeks
van de venue-site gescraped zijn, met een net iets andere titel (support-act,
subtitel, landcode). Twee mechanismen in `events_db.py` werken samen om dit op te
lossen:

1. **Bij het invoegen** (`insert_event()`): de database heeft `UNIQUE(title_norm, date)`.
   Bij een botsing wint niet zomaar de eerst-ingevoegde rij — als de **bestaande**
   rij van een aggregator komt en de **nieuwe** rij van een directe venue-bron, wordt
   de bestaande rij overschreven. Zonder deze regel zou de scrape-volgorde bepalen
   welke bron wint, in plaats van welke bron beter is (dat gebeurde ook echt —
   zie `decisions.md`, 2026-08-11).
2. **Bij het exporteren** (`export_json()` → `find_cross_source_duplicates()`): een
   fuzzy titel-match op dezelfde datum tussen een aggregator- en een directe-bron-rij
   (die dus ALLEBEI de invoeg-stap overleefd hebben, bv. omdat ze in dezelfde run
   zijn binnengekomen) — de aggregator-rij wordt dan bij export overgeslagen.
   Titels die te generiek zijn om betrouwbaar te matchen (bv. "Theaterweekend",
   "Kerstconcert" — matchen dan met meerdere, inhoudelijk verschillende events)
   worden bewust *niet* gededupliceerd. Preview: `python events_db.py cross-dupes`.

Praktisch gevolg: fix #1 werkt alleen met terugwerkende kracht zodra een bron
**opnieuw** gescraped wordt — bestaande data van een bron die nooit opnieuw
gedraaid is, kan nog steeds een niet-opgemerkte aggregator-dubbel bevatten.

## Deployment

### Volledige flow (data + site)

```
1. Scrapers draaien lokaal op de PC (zie §Wekelijkse refresh)
       ↓
2. events_categorized.json bijgewerkt (SQLite → export_json())
       ↓
3. git push origin main
       ↓
4. Cloudflare Pages detecteert push
       → Build: python3 gen_uitjes.py
       → Output dir: /  (index.html)
       → Live: uitjesagenda.pages.dev (~30–60 seconden)
```

**Belangrijk:** Cloudflare draait alleen `gen_uitjes.py` — géén scrapers.  
De scraping en deduplicatie vinden altijd lokaal op de PC plaats.

`requirements.txt` is leeg — Cloudflare gebruikt Python stdlib.

---

### Wekelijkse refresh (Windows Taakplanner-taak)

Elke **ma/wo/za om 04:00** draait Windows Taakplanner-taak "uitjes-agenda-refresh"
op `C:\dev\uitjesagenda` (deze laptop, `mrhva`). De taak roept
`weekly_refresh.ps1` aan, die:

```powershell
cd C:\dev\uitjesagenda
python run_weekly_refresh.py
# alleen als git status --porcelain iets teruggeeft:
git add -A
git commit -m "auto refresh <datum>"
git push
```

en alles logt naar `refresh_log.txt` (lokaal, staat in `.gitignore`).

**Zonder AI**: de taak is puur `schtasks`/Taakplanner + een PowerShell-script,
geen Cowork-sessie of Claude bij betrokken — sluit aan bij het einddoel
"wekelijkse refresh volledig no-ai-needed" (zie `decisions.md`).

Taak-principal staat op **S4U** (`LogonType S4U`, `RunLevel Limited`): draait
ongeacht of `mrhva` is ingelogd, zonder dat er een wachtwoord is opgeslagen.
Dit moest vanuit een **verhoogde** PowerShell ingesteld worden (`Set-ScheduledTask`
met een nieuwe `-Principal`) — de standaard (niet-elevated) registratie geeft
alleen `LogonType Interactive` (draait alleen als er een ingelogde sessie is).

Taak bekijken/aanpassen:
```powershell
Get-ScheduledTask -TaskName "uitjes-agenda-refresh" | Get-ScheduledTaskInfo
```

`run_weekly_refresh.py` globt zelf alle `scrape_*.py`-bestanden en draait ze
één voor één — **geen handmatige lijst meer om bij te houden** (was tot
2026-08-14 wel zo, liep binnen twee sessies drie kwart achter: 31 scrapers
bestonden, ARCHITECTURE.md noemde er nog 7). Daarna `events_db.py export` +
`gen_uitjes.py` automatisch.

Zelf-herstellend: een scraper die een harde fout geeft (crash, of geen
`✓ Klaar`/`Dry-run`-regel in de output — gebeurt alleen als de fetch/parse-
stap zelf faalt) wordt automatisch hernoemd naar `fix_<naam>.py`. Zo'n
bestand matcht `scrape_*.py` niet meer en wordt de volgende run vanzelf
overgeslagen, tot iemand het repareert en terugzet. Een scraper die succesvol
draait maar 0 events vindt wordt **niet** hernoemd (kan legitiem zijn, bv.
buiten seizoen) — komt wel in het eindrapport te staan om handmatig te
checken. Zie de docstring van `run_weekly_refresh.py` voor het volledige
gedrag, en `python run_weekly_refresh.py --dry-run` om te zien welke scripts
zouden draaien zonder iets uit te voeren.

Een script uitzonderen van de wekelijkse run: geen `scrape_`-prefix gebruiken
(of in een subfolder zetten) — dan matcht de glob het niet.

SQLite werkt alleen lokaal — niet vanuit de Cowork sandbox (FUSE-mount beperking).

**Geschiedenis**: tot 2026-08-15 liep dit via een Cowork scheduled task
(maandag 08:04) op een andere pc; die pc was kapot, dus de refresh draaide
tijdelijk handmatig vanaf deze laptop (`C:\dev\uitjesagenda`). Op 2026-08-15
vervangen door de Windows Taakplanner-taak hierboven — deze laptop is nu de
vaste plek, geen Cowork-afhankelijkheid meer. Zie `decisions.md` en
`overleg.md` punt 1.

---

### build.py

`build.py` staat in de repo maar wordt **niet** door Cloudflare aangeroepen.  
Het is een alternatief voor als je de scrapers eenmalig handmatig wil draaien  
zonder lokale Python-omgeving (bijv. in CI). Niet onderdeel van de standaard flow.

---

## Nieuwe bron toevoegen

1. Voeg toe aan `SRC`: `'sleutel': ('Naam', 'emoji', '#kleur')`
2. Voeg toe aan `VENUE_LOC`: `'sleutel': (lat, lon, 'Provincie')`
3. Voeg toe aan de juiste venue-set (`MUSIC_VENUES`, `THEATER_VENUES`, of `EXPO_VENUES`) als fallback voor `classify()`
4. Voeg events toe aan `events_categorized.json` met `"source": "sleutel"`
5. Documenteer scraping-methode in `scraping_recipes.json`
6. Run `python3 gen_uitjes.py` lokaal ter verificatie
7. Push

### Sport club toevoegen

Bovenstaande stappen, plus:
- Voeg sleutel toe aan de juiste sporttype-lijst in `SPORT_CLUBS`
- Events krijgen `"genre": "sport"` en `"sport": "voetbal"` (of ander sporttype)
- Voeg club-knop toe in de HTML-template in `gen_uitjes.py` (sport-filters sectie)
- Voeg kleur toe aan `CLUB_COLOR_MAP` in de JS-sectie

---

## KRITIEKE REGEL: gen_uitjes.py aanpassen

**Gebruik NOOIT de Cowork Edit-tool op `gen_uitjes.py`.** Die kapt bestanden af bij ~500 regels. Het bestand is ~757 regels (groeit mee — check zelf even met een regel-telling voor je begint, dit getal veroudert).

**Altijd via:**
```python
content = open('gen_uitjes.py').read()
content = content.replace('OUD', 'NIEUW')
# Verifieer:
import ast; ast.parse(content)
open('gen_uitjes.py', 'w').write(content)
```

In bash (sandbox): bestand staat op `/sessions/.../mnt/uitjesagenda/gen_uitjes.py`.

---

## Git-quirks (FUSE mount)

De FUSE-mount die `C:\dev\uitjesagenda` koppelt kan eigenaardigheden hebben:

- **`unlink` van bestaande bestanden** werkt niet altijd betrouwbaar → gebruik altijd overwrite-in-place, nooit delete+recreate
- **`.git/index.lock` / `.git/HEAD.lock` stuck** → workaround:
  ```bash
  GIT_INDEX_FILE=/tmp/gitidx git add -A
  GIT_INDEX_FILE=/tmp/gitidx git commit -m "..."
  cp /tmp/gitidx .git/index
  ```
  Als `HEAD.lock` vastzit: gebruik `git write-tree` + `git commit-tree` en overschrijf `.git/refs/heads/main` direct.
- **`unable to unlink .git/objects/xx/tmp_obj_*` warnings** tijdens commit → harmless, negeren

---

## Huidige bronnen-status

Verplaatst naar `SCRAPERS.md` (per-bron tabel: geautomatiseerd / kan zonder AI /
AI-Chrome nodig / geblokkeerd / nog niet geprobeerd) — dat wordt actief
bijgehouden; deze sectie hier raakte snel verouderd doordat het op twee plekken
stond.

**Dead ends (blijven hier, veranderen zelden):** Theater de Molenberg Delfzijl (DNS), VanSlag Borger (geen site), Seynderslo (DNS), De Harmonie Leeuwarden (JS-only, niet geprobeerd)

---

## Open items

Verplaatst naar `plan.md` (levend to-do-document, met datering per gevonden issue).
