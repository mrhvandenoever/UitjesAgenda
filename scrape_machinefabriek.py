"""
scrape_machinefabriek.py — Theater de Machinefabriek (Groningen) via podiuminfo.nl

Gebruik:
    python scrape_machinefabriek.py              # scrape, sla op in DB
    python scrape_machinefabriek.py --dry-run    # toon events zonder op te slaan

Geen bruikbare eigen agenda-scrape voor deze kleine zaal; podiuminfo.nl heeft
een aggregator-pagina met nette JSON-LD Event-schema's. Titel bevat een
"@ Theater de Machinefabriek"-suffix die we wegknippen.
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'machinefabriek'
BASE_URL = 'https://www.podiuminfo.nl/podium/5631/concerten/Theater-de-Machinefabriek/Groningen/'
VENUE    = 'Theater de Machinefabriek, Groningen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
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
            title = re.sub(r'\s*@ Theater de Machinefabriek\s*$', '', item.get('name', '')).strip()
            ev = {
                'title':  title,
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

    print(f"Scraping Theater de Machinefabriek (via podiuminfo.nl) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
