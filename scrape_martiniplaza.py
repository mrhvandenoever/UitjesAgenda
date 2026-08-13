"""
scrape_martiniplaza.py — Martiniplaza (Groningen) via de theater.nl-aggregator

Gebruik:
    python scrape_martiniplaza.py              # scrape, sla op in DB
    python scrape_martiniplaza.py --dry-run    # toon events zonder op te slaan

Martiniplaza heeft geen bruikbare eigen agenda-scrape; theater.nl vermeldt
hun programma wel, met nette JSON-LD Event-schema's (geen regex-geknoei
nodig). Paginering via ?start=N in stappen van 6 — stopt zodra een pagina
dezelfde events als de vorige teruggeeft (of leeg is).

Let op: theater.nl blokkeert een simpele User-Agent (403) — een volledige
browser-UA is nodig.
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'martiniplaza'
BASE_URL = 'https://www.theater.nl/groningen/martini-plaza-groningen'
VENUE    = 'Martiniplaza, Groningen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def fetch(start: int) -> str:
    req = urllib.request.Request(f'{BASE_URL}/?start={start}', headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    seen_keys = set()
    prev_batch = None

    for start in range(0, 60, 6):  # ruime marge, stopt vanzelf eerder
        try:
            html = fetch(start)
        except Exception as e:
            print(f"  start={start} fout: {e}")
            break

        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        batch = []
        for b in blocks:
            try:
                data = json.loads(b)
            except json.JSONDecodeError:
                continue
            for item in data.get('@graph', [data]):
                if 'Event' in str(item.get('@type', '')):
                    batch.append((item.get('name', '').strip(), item.get('startDate', ''), item.get('url')))

        if not batch or batch == prev_batch:
            break
        prev_batch = batch

        for title, start_date, url in batch:
            key = (title, start_date)
            if key in seen_keys or not start_date:
                continue
            seen_keys.add(key)

            found += 1
            ev = {
                'title':  title,
                'date':   start_date[:10],
                'time':   start_date[11:16] if len(start_date) >= 16 else None,
                'venue':  VENUE,
                'url':    url or BASE_URL,
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

    print(f"Scraping Martiniplaza (via theater.nl) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
