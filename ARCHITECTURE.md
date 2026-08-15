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
| `requirements.txt` | Intentioneel leeg — alleen Python stdlib nodig. |
| `scrape_<bron>.py` | Eén los scraper-script per bron/venue (zie §Scrapers-conventie). Huidige scripts: `scrape_drenthe.py`, `scrape_friesland.py`, `scrape_visitgroningen.py`, `scrape_spotgroningen.py`, `scrape_handbal.py` (E&O + Hurry-Up), `scrape_naarzuidlaren.py`, `scrape_handmatig.py` (vaste jaarevents). |
| `run_weekly_refresh.py` | Draait alle `scrape_*.py`-bestanden (auto-discovery via glob), daarna export + generate. Zie §Wekelijkse refresh. |
| `page_cache.py` | Change-detection: hash-cache in `events.db` om parse/insert-werk over te slaan als een bron ongewijzigd is. Zie §Change-detection. |
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

---

### HTML-generatie

`event_html(e)` genereert per event een `<div>` met data-attributen:
- `data-src` — bronsleutel
- `data-genre` — genre (uitkomst van classify)
- `data-prov` — provincie (uit VENUE_LOC)
- `data-latlon` — lat,lon voor afstandsberekening

De JavaScript in de browser filtert puur op deze data-attributen — geen server-side filtering.

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
