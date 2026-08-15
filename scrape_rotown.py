"""
scrape_rotown.py — Rotown (Rotterdam) via de eigen homepage

Gebruik:
    python scrape_rotown.py              # scrape, sla op in DB
    python scrape_rotown.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — `/agenda/` (zonder slug) gaf
een 404, dus leek er geen listing-pagina te bestaan. Bleek onnodig: de
HOMEPAGE zelf bevat gewoon 139 losse `<script type="application/ld+json">
{"@type":"Event",...}</script>`-blokken (schema.org), geen browser nodig.

Rotown promoot ook events bij andere Rotterdamse venues (V11, De Doelen,
Maassilo, Annabel, ...) — gefilterd op `location.name == 'Rotown'` zodat
alleen echte Rotown-locatie-events meekomen, net als bij scrape_hedon.py.
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE  = 'rotown'
URL     = 'https://www.rotown.nl/'
VENUE   = 'Rotown, Rotterdam'

LDJSON_PATTERN = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def fetch() -> str:
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    items = []
    for block in LDJSON_PATTERN.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get('@type') == 'Event':
            items.append(data)

    rotown_items = [e for e in items if (e.get('location') or {}).get('name') == 'Rotown']
    print(f"  {len(items)} events gevonden, {len(rotown_items)} op Rotown-locatie zelf")

    found = added = 0
    all_events = []
    for item in rotown_items:
        title = (item.get('name') or '').strip()
        start = item.get('startDate') or ''
        if not title or not start:
            continue
        iso_date, _, rest = start.partition('T')
        time_str = rest[:5] if rest else None

        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  VENUE,
            'url':    item.get('url'),
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
        else:
            all_events.append(ev)

    if not dry_run:
        if unchanged(SOURCE, all_events):
            log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
            print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
            return found, 0
        for ev in all_events:
            if insert_event(ev):
                added += 1
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping Rotown (JSON-LD op homepage) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
