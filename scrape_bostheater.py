"""
scrape_bostheater.py — Bostheater (Diever)

Gebruik:
    python scrape_bostheater.py              # scrape, sla op in DB
    python scrape_bostheater.py --dry-run    # toon events zonder op te slaan

Kleine zomerseizoen-programmering (~6 events). URL is /programma, niet
/events. Vereist een volledige browser-UA.
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'bostheater'
BASE_URL = 'https://bostheater.nl/programma'
VENUE    = 'Bostheater, Diever'
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

    found = added = 0
    all_events = []
    for art in re.findall(r'<article[^>]*>(.*?)</article>', html, re.S):
        h = re.search(r'<h[234][^>]*>(.*?)</h[234]>', art, re.S)
        dt = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', art)
        href = re.search(r'href="([^"]+)"', art)
        if not (h and dt):
            continue
        found += 1
        ev = {
            'title':  re.sub(r'<[^>]+>', '', h.group(1)).strip(),
            'date':   dt.group(1),
            'venue':  VENUE,
            'url':    href.group(1) if href else BASE_URL,
            'source': SOURCE,
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
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping Bostheater [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
