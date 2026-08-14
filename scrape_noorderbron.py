"""
scrape_noorderbron.py — Noorderbron (Annen)

Gebruik:
    python scrape_noorderbron.py              # scrape, sla op in DB
    python scrape_noorderbron.py --dry-run    # toon events zonder op te slaan

Vergader-/teambuildinglocatie met soms een publieke activiteit (geen
volle agenda). WP Event Manager-plugin (wpem-*-classes), met een volledige
DD-MM-YYYY datum in wpem-event-date-time-text — geen jaar-inferentie nodig.
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'denoorderbron.nl'
BASE_URL = 'https://denoorderbron.nl/agenda/'
VENUE    = 'Noorderbron, Annen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def unescape(s: str) -> str:
    return (s.replace('&amp;', '&').replace('&#039;', "'").replace('&quot;', '"')).strip()


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

    blocks = re.split(r'(?=<div class="event_listing )', html)

    found = added = 0
    all_events = []
    for b in blocks:
        href = re.search(r'<a href="(https://denoorderbron\.nl/evenement/[^"]+)"', b)
        title = re.search(r'<h3 class="wpem-heading-text">([^<]+)</h3>', b)
        dt = re.search(r'wpem-event-date-time-text">\s*(\d{2})-(\d{2})-(\d{4})', b)
        if not (href and title and dt):
            continue

        found += 1
        d, m, y = dt.groups()
        ev = {
            'title':  unescape(title.group(1)),
            'date':   f'{y}-{m}-{d}',
            'venue':  VENUE,
            'url':    href.group(1),
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

    print(f"Scraping Noorderbron [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
