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
| `gen_uitjes.py` | Python generator (~661 regels). Leest JSON, schrijft index.html. |
| `events_categorized.json` | Brondata — alle events. Single source of truth. |
| `scraping_recipes.json` | Per-bron scrape-instructies (render_type, code, agenda_url). |
| `index.html` | Gegenereerde output. **Nooit handmatig aanpassen.** |
| `requirements.txt` | Intentioneel leeg — alleen Python stdlib nodig. |

---

## gen_uitjes.py — structuur

### Bovenaan: data-definities (regels 17–153)

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
    'voetbal':   ['fcgroningen', 'fcemmen'],
    'basketbal': ['donar'],
    'volleybal': ['lycurgus'],
    'ijshockey': ['grizzlys'],
    'handbal':   ['hurryup'],
}
```
`SPORT_SRCS` is de afgeleide set van alle sport-sleutelwoorden. Sport-events worden gefilterd uit de uitjes-modus; alleen zichtbaar in sport-modus.

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

Bepaalt het genre van een event. Volgorde van prioriteit:

1. **Kinderen-check** (regex) — altijd eerst, overschrijft alles
2. **`cats`-veld** uit JSON (als aanwezig en herkenbaar)
3. **Expo-venues** (groningermuseum, drentsmuseum, hunebedcentrum) → `expo`
4. **Titelkeywords** — musical, cabaret, dans, klassiek, jazz, expo, theater, pop, actief
5. **Venue-fallback** — music_venues → `pop`, theater_venues → `theater`, anders → `overig`

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
- `client_js` → Chrome MCP vereist (JavaScript wordt uitgevoerd in de browser)
- `manual` → geen automatische scraping (eenmalig handmatig)
- `unresolved` → bekend probleem, nog geen werkende methode
- `unverified` → niet getest

Het `_meta`-veld bevat de genre-classifier-definitie en `dead_ends` (bronnen die zijn opgegeven).

---

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

### Wekelijkse refresh (Cowork scheduled task)

Elke maandag om 08:04 draait de Cowork scheduled task "uitjes-agenda-refresh".  
Die opent PowerShell op de PC en voert uit:

```powershell
cd C:\dev\uitjesagenda
python scrape_drenthe.py
python scrape_visitgroningen.py
python scrape_friesland.py
python scrape_handmatig.py
python scrape_naarzuidlaren.py
python events_db.py export
python gen_uitjes.py
git add -A
git commit -m "auto refresh"
git push
```

SQLite werkt alleen lokaal — niet vanuit de Cowork sandbox (FUSE-mount beperking).

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

**Gebruik NOOIT de Cowork Edit-tool op `gen_uitjes.py`.** Die kapt bestanden af bij ~500 regels. Het bestand is ~661 regels.

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

## Huidige bronnen-status (juli 2026)

**Noord-Nederland (actief):** Spot, De Lawei, Atlas Emmen, Drenthe.nl, Kielzog, Forum, Nieuwe Kolk, Van Beresteyn, Vera, Simplon, Martiniplaza, Grand Theatre, Winsinghhof, EM2, Zummerbühne, USVA, Geert Teis, Nienoord, GC Zuidlaren, Geke Hoogstins, Machinefabriek, Be-Wonder, Dorpshuis Annen, Noorderbron, De Tamboer, Posthuis, OntdekPoort, Bostheater, Neushoorn, Groninger Museum, Drents Museum, Zuidhaege Assen, Hunebedcentrum, Koornbeurs

**Landelijk (actief):** TivoliVredenburg, Melkweg, Paradiso, 013 Tilburg, Ziggo Dome, Effenaar, Doornroosje, Rotterdam Ahoy, Het Paard, Hedon Zwolle, AFAS Live, Rotown, De Doelen, GelreDome, Concertgebouw

**Sport (actief):** FC Groningen (18 thuiswedstrijden), FC Emmen (19), Donar (14)

**Sport (inactief / pending):** Lycurgus (seizoen niet gestart), GIJS Groningen (URL onbekend), Hurry-Up (website 404)

**Dead ends:** Theater de Molenberg Delfzijl (DNS), VanSlag Borger (geen site), Seynderslo (DNS), De Harmonie Leeuwarden (JS-only, niet geprobeerd)

---

## Open items

- [ ] Ticketmaster Discovery API (gratis tier, 5.000 req/dag) — key aanvragen op developer.ticketmaster.com
- [ ] Lycurgus — seizoen starten afwachten
- [ ] GIJS Groningen — website URL achterhalen
- [ ] Hurry-Up — werkende URL vinden
- [ ] Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- [ ] 14/57 scraping-recipes nog zonder werkende methode
