"""
scrape_staatsbosbeheer.py — staatsbosbeheer.nl/uit-in-de-natuur/activiteiten

Gebruik:
    python scrape_staatsbosbeheer.py              # scrape activiteiten (DB) + routes (routes.json)
    python scrape_staatsbosbeheer.py --dry-run    # toon beide, sla niets op

Michiel wees op deze bron n.a.v. de punt-15-discussie (drenthe.nl "t/m N
maand"-events). De pagina zelf is een client-rendered app (React), maar
heeft een publieke, schone JSON-API: `/api/activities?perPage[]=N&page[]=N`
— gevonden via een netwerkcheck (Browser pane), geen Playwright nodig. Drie
content-typen op deze ene endpoint:
  - `activity` — geboekte excursies/rondleidingen met een echte datum
    (`Date`) en precieze coördinaten (`GeoCoordinate`). Via `insert_event()`
    naar de gewone events-DB, net als elke andere bron.
  - `route`    — permanent beschikbare wandel-/fiets-/mountainbikeroutes,
    `Date` is altijd null. Past niet in het datum-gebaseerde events-schema
    (UNIQUE(title_norm,date), insert_event() eist een datum) — daarom NIET
    via events_db.py, maar rechtstreeks naar een eigen `routes.json`
    (volledige overschrijving per run, geen incrementele merge nodig: dit
    is een vrijwel statische catalogus, geen "nieuwe occurrences over
    tijd"-stroom zoals events). Michiel koos 2026-08-18 voor een eigen
    4e topniveau-knop "Wandelingen/tochten" i.p.v. deze routes te negeren
    of tussen de Uitjes te proppen, zie overleg.md punt 15 en
    ARCHITECTURE.md §Wandelingen/tochten.
  - `accomodation` — kampeerterreinen, geen event, altijd overgeslagen.

Landelijke bron (1213 resultaten NL-breed) — net als bij drenthe.nl/
friesland.nl/visitgroningen filteren we op `InfoDetails.Location.Provinces`
i.p.v. alles op te halen: alleen Groningen/Drenthe/Friesland/Overijssel
(dezelfde regionale scope als de rest van de site). Resultaat 2026-08-18:
153 `activity`-events, 220 `route`-routes in deze 4 provincies.

Genre voor activity-events: `cats=['actief']` — een expliciet genre-signaal
(zelfde patroon als `cats=['expositie']` bij andere aggregators), i.p.v.
classify()'s titel-keyword-gok. `gen_uitjes.py`'s `cat_map` kreeg een
`'actief':'actief'`-entry om dit signaal te laten werken (decisions.md
2026-08-18).

`HasMoreDates=True` bij activity-events betekent dat een activiteit vaker
terugkomt dan de ene datum die de API hier toont (waarschijnlijk
"eerstvolgende keer") — we nemen alleen die ene datum mee, geen poging tot
een volledige kalender per activiteit. Bij elke scraperun toont de API
opnieuw de eerstvolgende datum, en de structureel gefixte
`insert_event()`-merge (2026-08-17) zorgt ervoor dat die datum netjes
bijwerkt i.p.v. te blijven hangen op de eerst geziene datum.

Route-eigenschappen (`Properties`) geobserveerd in de brondata: "Honden
toegestaan"/"Honden niet toegestaan"/"Honden los toegestaan" (elkaar
uitsluitend), "Voor kinderen", "Fysieke beperking" (rolstoel-/
scootmobielvriendelijk) — vertaald naar aparte, herbruikbare velden i.p.v.
de ruwe tekst 1-op-1 door te geven, zodat de site-filters er chips van
kunnen maken.
"""

import urllib.request
import json
import os
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE      = 'staatsbosbeheer'
BASE_URL    = 'https://www.staatsbosbeheer.nl'
API_URL     = f'{BASE_URL}/api/activities'
TODAY       = date.today().isoformat()
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROUTES_JSON = os.path.join(SCRIPT_DIR, 'routes.json')

# Zelfde regionale scope als de rest van de site (zie ARCHITECTURE.md).
TARGET_PROVINCES = {'Groningen', 'Drenthe', 'Friesland', 'Overijssel'}

DOG_PROPS = {
    'Honden toegestaan':      'toegestaan',
    'Honden los toegestaan':  'los',
    'Honden niet toegestaan': 'niet-toegestaan',
}


def fetch_page(page: int, per_page: int = 200) -> dict:
    url = f'{API_URL}?perPage[]={per_page}&page[]={page}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_all() -> list[dict]:
    """Haalt alle resultaten NL-breed op (perPage=200 -> ~7 requests voor
    1213 resultaten) -- dekt zowel activity- als route-items in 1 keer,
    filtering op type/provincie gebeurt in de aanroepende functies."""
    results = []
    page = 1
    while True:
        data = fetch_page(page)
        results.extend(data.get('Results', []))
        total = data.get('TotalResults', 0)
        if len(results) >= total or not data.get('Results'):
            break
        page += 1
    return results


def resolve_url(url_path: str | None) -> str | None:
    if not url_path:
        return None
    return BASE_URL + url_path if url_path.startswith('/') else url_path


def parse_activity(item: dict) -> dict | None:
    if item.get('Type') != 'activity':
        return None

    loc = (item.get('InfoDetails') or {}).get('Location') or {}
    provinces = set(loc.get('Provinces') or [])
    if not (provinces & TARGET_PROVINCES):
        return None

    title = (item.get('Title') or '').strip()
    raw_date = item.get('Date')
    if not title or not raw_date:
        return None
    iso_date = raw_date[:10]
    if iso_date < TODAY:
        return None

    geo = item.get('GeoCoordinate') or {}
    lat, lon = geo.get('Latitude'), geo.get('Longitude')

    ev = {
        'title':    title,
        'date':     iso_date,
        'venue':    loc.get('Text') or None,
        'province': next(iter(provinces & TARGET_PROVINCES)),
        'source':   SOURCE,
        'url':      resolve_url(item.get('URL')),
        'subtitle': (item.get('Introduction') or '').strip() or None,
        'cats':     ['actief'],
    }
    if lat and lon:
        ev['lat'], ev['lon'] = lat, lon
    return ev


def parse_route(item: dict) -> dict | None:
    if item.get('Type') != 'route':
        return None

    loc = (item.get('InfoDetails') or {}).get('Location') or {}
    provinces = set(loc.get('Provinces') or [])
    if not (provinces & TARGET_PROVINCES):
        return None

    title = (item.get('Title') or '').strip()
    if not title:
        return None

    geo = item.get('GeoCoordinate') or {}
    lat, lon = geo.get('Latitude'), geo.get('Longitude')
    if not (lat and lon):
        return None  # geen positie -> kan niet op afstand gefilterd worden, nutteloos zonder kaart-context

    props = item.get('Properties') or []
    dogs = next((DOG_PROPS[p] for p in props if p in DOG_PROPS), None)

    return {
        'title':      title,
        'url':        resolve_url(item.get('URL')),
        'venue':      loc.get('Text') or None,
        'province':   next(iter(provinces & TARGET_PROVINCES)),
        'lat':        lat,
        'lon':        lon,
        'route_type': item.get('RouteType') or 'Wandelen',
        'length_km':  item.get('RouteLength') or None,
        'dogs':       dogs,
        'kids':       'Voor kinderen' in props,
        'accessible': 'Fysieke beperking' in props,
        'subtitle':   (item.get('Introduction') or '').strip() or None,
    }


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        raw_items = fetch_all()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0
    print(f"  {len(raw_items)} resultaten NL-breed opgehaald")

    # --- Activiteiten (events-DB, zelfde patroon als elke andere bron) ---
    seen_urls = set()
    all_events = []
    for item in raw_items:
        ev = parse_activity(item)
        if not ev:
            continue
        key = ev.get('url') or (ev['title'], ev['date'])
        if key in seen_urls:
            continue
        seen_urls.add(key)
        all_events.append(ev)

    found = len(all_events)

    # --- Routes (routes.json, buiten de events-DB om, zie docstring) ---
    seen_route_urls = set()
    all_routes = []
    for item in raw_items:
        rt = parse_route(item)
        if not rt:
            continue
        key = rt.get('url') or rt['title']
        if key in seen_route_urls:
            continue
        seen_route_urls.add(key)
        all_routes.append(rt)
    routes_found = len(all_routes)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            print(f"    [{ev['date']}] {ev['title'][:55]:55s} @ {ev['venue']} ({ev['province']})")
        print(f"\nDry-run: {found} activiteiten gevonden (niets opgeslagen)")
        for rt in sorted(all_routes, key=lambda r: r['title'])[:15]:
            print(f"    {rt['route_type']:12s} {rt['length_km'] or '?':>5} km  {rt['title'][:50]:50s} ({rt['province']})")
        print(f"...\nDry-run: {routes_found} routes gevonden (niets opgeslagen)")
        return found, 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Activiteiten: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        added = 0
    else:
        added = 0
        for ev in all_events:
            if insert_event(ev):
                added += 1
        log_scrape(SOURCE, found, added)
        print(f"✓ Activiteiten: {found} gevonden, {added} nieuw in DB")

    with open(ROUTES_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_routes, f, ensure_ascii=False, indent=2)
    print(f"✓ Routes: {routes_found} weggeschreven naar {os.path.basename(ROUTES_JSON)}")

    # Samenvattende regel nodig voor run_weekly_refresh.py's succes-detectie
    # (SUCCESS_MARKERS = ('✓ Klaar:', 'Dry-run:')) -- zonder deze regel
    # matcht de live-modus van dit script NOOIT en wordt het bij elke
    # wekelijkse run onterecht als "harde fout" gequarantained. Zie
    # decisions.md 2026-08-22.
    print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB ({routes_found} routes ook verwerkt)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping staatsbosbeheer.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
