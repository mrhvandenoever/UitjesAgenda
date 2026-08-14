"""
scrape_kielzog.py — Kielzog (Winschoten) via de eigen JSON-API

Gebruik:
    python scrape_kielzog.py              # scrape, sla op in DB
    python scrape_kielzog.py --dry-run    # toon events zonder op te slaan

Echte JSON-API (kielzog.nl/api/v1/agenda?page=N), geen HTML-parsing nodig.
Let op: 'date'-veld is Nederlandse tekst en soms een bereik ("Do 23 jul t/m
wo 9 sep") — we pakken alleen de eerste dag+maand uit die tekst, met het
aparte 'year'-veld erbij (dat staat niet in de datumtekst zelf).
"""

import urllib.request
import json
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'kielzog'
BASE_URL = 'https://www.kielzog.nl/api/v1/agenda'
VENUE    = 'Kielzog, Winschoten'

NL_MON = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}


def fetch(page: int) -> dict:
    req = urllib.request.Request(
        f'{BASE_URL}?page={page}',
        headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def parse_date(date_str: str, year_str: str) -> str | None:
    m = re.search(r'(\d{1,2})\s+(\w{3})', date_str.lower())
    if not m:
        return None
    month = NL_MON.get(m.group(2))
    if not month:
        return None
    try:
        return date(int(year_str), month, int(m.group(1))).isoformat()
    except ValueError:
        return None


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        first = fetch(1)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    total_pages = first.get('meta', {}).get('pagination', {}).get('totalPages', 1)
    print(f"  {total_pages} pagina's op de agenda")

    all_items = list(first.get('data', []))
    for page in range(2, total_pages + 1):
        try:
            all_items.extend(fetch(page).get('data', []))
        except Exception as e:
            print(f"  Pagina {page} fout: {e}")

    found = added = 0
    all_events = []
    for item in all_items:
        iso_date = parse_date(item.get('date', ''), item.get('year', ''))
        if not iso_date:
            continue
        found += 1
        ev = {
            'title':    item.get('title', '').strip(),
            'date':     iso_date,
            'venue':    VENUE,
            'url':      item.get('url'),
            'subtitle': item.get('subtitle') or item.get('introText'),
            'source':   SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']}] {ev['title']}")
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
        print(f"\nDry-run: {found} toekomstige/geldige events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping Kielzog [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
