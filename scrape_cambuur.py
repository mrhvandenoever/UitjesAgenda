"""
scrape_cambuur.py — SC Cambuur thuiswedstrijden via ESPN.nl

Gebruik:
    python scrape_cambuur.py              # scrape, sla op in DB
    python scrape_cambuur.py --dry-run    # toon events zonder op te slaan

Zelfde aanpak als scrape_fctwente.py (zie die docstring) — bewust een losse
kopie per club i.p.v. een gedeelde helper, zie ARCHITECTURE.md §Scrapers-conventie.
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE = 'cambuur'
CLUB   = 'SC Cambuur Leeuwarden'
VENUE  = 'Cambuurstadion, Leeuwarden'
URL    = 'https://www.espn.nl/voetbal/team/speelkalender/_/id/3736/ned.cambuur_leeuwarden'

PATTERN = re.compile(
    r'"id":"(\d+)","competitors":\[\{"id":"\d+",[^}]*"displayName":"([^"]+)"[^}]{0,300}"isHome":true\}'
    r'.{0,600}'
    r'"displayName":"([^"]+)"[^}]{0,300}"isHome":false\}'
    r'.{0,200}"date":"(202[67]-\d{2}-\d{2})',
    re.S
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    found = added = 0
    for m in PATTERN.finditer(html):
        game_id, home, away, date_iso = m.groups()
        if CLUB.lower() not in home.lower():
            continue
        found += 1
        ev = {
            'title':  f'{CLUB} - {away}',
            'date':   date_iso,
            'venue':  VENUE,
            'url':    f'https://www.espn.nl/voetbal/wedstrijd/_/gameId/{game_id}',
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'voetbal',
            'gender': 'heren',
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB} via ESPN.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
