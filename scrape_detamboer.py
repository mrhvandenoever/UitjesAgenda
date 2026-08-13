"""
scrape_detamboer.py — De Tamboer (Hoogeveen)

Gebruik:
    python scrape_detamboer.py              # scrape, sla op in DB
    python scrape_detamboer.py --dry-run    # toon events zonder op te slaan

JSON-LD Event-schema's op de programma-pagina, geen HTML-parsing nodig.
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'detamboer'
BASE_URL = 'https://www.detamboer.nl/programma'
VENUE    = 'De Tamboer, Hoogeveen'


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)

    found = added = 0
    for b in blocks:
        try:
            data = json.loads(b)
        except json.JSONDecodeError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if 'Event' not in str(item.get('@type', '')):
                continue
            start_date = item.get('startDate', '')
            if not start_date:
                continue
            found += 1
            ev = {
                'title':  (item.get('name') or '').strip(),
                'date':   start_date[:10],
                'time':   start_date[11:16] if len(start_date) >= 16 else None,
                'venue':  VENUE,
                'url':    item.get('url') or BASE_URL,
                'source': SOURCE,
            }
            if dry_run:
                print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
            else:
                if insert_event(ev):
                    added += 1

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping De Tamboer [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
