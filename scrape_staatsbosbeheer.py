"""
scrape_staatsbosbeheer.py — staatsbosbeheer.nl/uit-in-de-natuur/activiteiten

Gebruik:
    python scrape_staatsbosbeheer.py              # scrape, sla op in DB
    python scrape_staatsbosbeheer.py --dry-run    # toon events zonder op te slaan

Michiel wees op deze bron n.a.v. de punt-15-discussie (drenthe.nl "t/m N
maand"-events). De pagina zelf is een client-rendered app (React), maar
heeft een publieke, schone JSON-API: `/api/activities?perPage[]=N&page[]=N`
— gevonden via een netwerkcheck (Browser pane), geen Playwright nodig. Drie
content-typen op deze ene endpoint:
  - `activity` — geboekte excursies/rondleidingen met een echte datum
    (`Date`) en precieze coördinaten (`GeoCoordinate`). Dit scrapen we.
  - `route`    — permanent beschikbare wandelroutes, `Date` is altijd null.
    Bewust NIET meegenomen: past niet in ons datum-gebaseerde model (geen
    start, geen eind, gewoon altijd aanwezig) — apart ontwerpvraagstuk,
    zie overleg.md punt 15 ("2. Wandelroutes" — Michiel twijfelt nog of dit
    de scope van de site moet vergroten).
  - `accomodation` — kampeerterreinen, geen event, altijd overgeslagen.

Landelijke bron (1213 resultaten NL-breed) — net als bij drenthe.nl/
friesland.nl/visitgroningen filteren we op `InfoDetails.Location.Provinces`
i.p.v. alles op te halen: alleen Groningen/Drenthe/Friesland/Overijssel
(dezelfde regionale scope als de rest van de site). Resultaat 2026-08-18:
153 `activity`-events in deze 4 provincies.

Genre: alle events krijgen `cats=['actief']` — een expliciet genre-signaal
(zelfde patroon als `cats=['expositie']` bij andere aggregators), i.p.v.
classify()'s titel-keyword-gok. Titels als "Beleef het Boomkroonpad" of
"Ontdek Radio Kootwijk" bevatten geen van de bestaande 'actief'-keywords
(wandeling/safari/natuur/...) en zouden anders ten onrechte op 'overig'
uitkomen. `gen_uitjes.py`'s `cat_map` kreeg een `'actief':'actief'`-entry
om dit signaal te laten werken (zie decisions.md 2026-08-18).

`HasMoreDates=True` betekent dat een activiteit vaker terugkomt dan de ene
datum die de API hier toont (waarschijnlijk "eerstvolgende keer") — we
nemen alleen die ene datum mee, geen poging tot een volledige kalender per
activiteit (zou een extra request per item vereisen, buiten scope voor nu).
Bij elke scraperun toont de API opnieuw de eerstvolgende datum, en de
inmiddels structureel gefixte `insert_event()`-merge (2026-08-17) zorgt
ervoor dat die datum netjes bijwerkt i.p.v. te blijven hangen op de eerst
geziene datum.
"""

import urllib.request
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE     = 'staatsbosbeheer'
BASE_URL   = 'https://www.staatsbosbeheer.nl'
API_URL    = f'{BASE_URL}/api/activities'
TODAY      = date.today().isoformat()

# Zelfde regionale scope als de rest van de site (zie ARCHITECTURE.md).
TARGET_PROVINCES = {'Groningen', 'Drenthe', 'Friesland', 'Overijssel'}


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
    1213 resultaten), filtering op provincie gebeurt in scrape()."""
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


def parse_item(item: dict) -> dict | None:
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

    url_path = item.get('URL') or ''
    url = BASE_URL + url_path if url_path.startswith('/') else (url_path or None)

    geo = item.get('GeoCoordinate') or {}
    lat, lon = geo.get('Latitude'), geo.get('Longitude')

    ev = {
        'title':    title,
        'date':     iso_date,
        'venue':    loc.get('Text') or None,
        'province': next(iter(provinces & TARGET_PROVINCES)),
        'source':   SOURCE,
        'url':      url,
        'subtitle': (item.get('Introduction') or '').strip() or None,
        'cats':     ['actief'],
    }
    if lat and lon:
        ev['lat'], ev['lon'] = lat, lon
    return ev


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        raw_items = fetch_all()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0
    print(f"  {len(raw_items)} resultaten NL-breed opgehaald")

    seen_urls = set()
    all_events = []
    for item in raw_items:
        ev = parse_item(item)
        if not ev:
            continue
        key = ev.get('url') or (ev['title'], ev['date'])
        if key in seen_urls:
            continue
        seen_urls.add(key)
        all_events.append(ev)

    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            print(f"    [{ev['date']}] {ev['title'][:55]:55s} @ {ev['venue']} ({ev['province']})")
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")
        return found, 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        return found, 0

    added = 0
    for ev in all_events:
        if insert_event(ev):
            added += 1
    log_scrape(SOURCE, found, added)
    print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping staatsbosbeheer.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
