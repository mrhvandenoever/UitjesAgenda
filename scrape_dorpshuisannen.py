"""
scrape_dorpshuisannen.py — Dorpshuis Annen

Gebruik:
    python scrape_dorpshuisannen.py              # scrape, sla op in DB
    python scrape_dorpshuisannen.py --dry-run    # toon events zonder op te slaan

Jimdo-website zonder machine-leesbare datums — strip de HTML naar platte
tekst en match op het terugkerende patroon "Weekdag D maand\ntijd\ntitel".
Jaartal niet in de tekst, wordt afgeleid (rollen naar volgend jaar als de
datum al voorbij is).
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'dorpshuisannen'
BASE_URL = 'https://www.dorpshuisannen.nl/voorstellingen'
VENUE    = 'Dorpshuis Annen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

NL_MONTHS = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
PATTERN = re.compile(
    r'(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+(\d{1,2})\s+(\w+)\n'
    r'(\d{1,2})\.(\d{2})\n([^\n]+)', re.I
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def to_text(html: str) -> str:
    text = re.sub(r'<script.*?</script>', ' ', html, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    return re.sub(r'\n{2,}', '\n', text)


def parse_date(day: int, month_str: str) -> str | None:
    month = NL_MONTHS.get(month_str.lower())
    if not month:
        return None
    today = date.today()
    try:
        d = date(today.year, month, day)
    except ValueError:
        return None
    if d < today:
        try:
            d = date(today.year + 1, month, day)
        except ValueError:
            return None
    return d.isoformat()


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    text = to_text(html)

    found = added = 0
    for _dag, day, month_str, hh, mm, title in PATTERN.findall(text):
        iso_date = parse_date(int(day), month_str)
        if not iso_date:
            continue
        found += 1
        ev = {
            'title':  title.strip(),
            'date':   iso_date,
            'time':   f'{int(hh):02d}:{mm}',
            'venue':  VENUE,
            'url':    BASE_URL,
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time']}] {ev['title']}")
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

    print(f"Scraping Dorpshuis Annen [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
