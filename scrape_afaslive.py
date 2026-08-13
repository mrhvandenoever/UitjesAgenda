"""
scrape_afaslive.py — AFAS Live (Amsterdam)

Gebruik:
    python scrape_afaslive.py              # scrape, sla op in DB
    python scrape_afaslive.py --dry-run    # toon events zonder op te slaan

Statische HTML, per event een <article id="_agenda_ID">-blok met absolute
URL's (niet relatief) en een volledige NL-datumtekst incl. jaar
("vrijdag 04 september 2026") — geen jaar-inferentie nodig.
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'afaslive'
BASE_URL = 'https://www.afaslive.nl/agenda'
VENUE    = 'AFAS Live, Amsterdam'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

NL_MONTHS = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}


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

    blocks = re.split(r'(?=<article id="_agenda_)', html)
    seen = set()

    found = added = 0
    for b in blocks:
        url_m = re.search(r'<a href="([^"]+)" class="rowMain"', b)
        info_m = re.search(
            r'class="rowMain"[^>]*>\s*<h4>([^<]+)</h4>.*?<span class="d">\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
            b, re.S
        )
        if not (url_m and info_m):
            continue
        title, day, month_str, year = info_m.groups()
        month = NL_MONTHS.get(month_str.lower())
        if not month:
            continue
        try:
            iso_date = date(int(year), month, int(day)).isoformat()
        except ValueError:
            continue

        key = (url_m.group(1), iso_date)
        if key in seen:
            continue
        seen.add(key)

        found += 1
        ev = {
            'title':  unescape(title),
            'date':   iso_date,
            'venue':  VENUE,
            'url':    url_m.group(1),
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']}] {ev['title']}")
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

    print(f"Scraping AFAS Live [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
