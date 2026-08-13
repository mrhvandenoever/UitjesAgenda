"""
scrape_lycurgus.py — Lycurgus (volleybal, heren 1) via Nevobo RSS

Gebruik:
    python scrape_lycurgus.py              # scrape, sla op in DB
    python scrape_lycurgus.py --dry-run    # toon events zonder op te slaan

Nevobo biedt een officiële RSS-programma-feed per team:
https://api.nevobo.nl/export/team/{teamcode}/{heren|dames}/{volgnummer}/programma.rss
Alleen thuiswedstrijden (waar Lycurgus in de titel als eerste/thuisteam
staat) worden opgeslagen.
"""

import urllib.request
import re
import argparse
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import fromstring
from events_db import insert_event, log_scrape, init_db

SOURCE    = 'lycurgus'
CLUB_NAME = 'Lycurgus'
VENUE     = 'Topsportcentrum Alfacollege, Groningen'
FEED_URL  = 'https://api.nevobo.nl/export/team/cmj3g4f/heren/1/programma.rss'


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        data = fetch(FEED_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    data = data.replace('<![CDATA[', '').replace(']]>', '')
    root = fromstring(data)

    found = added = 0
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        m = re.match(r'.+?:\s+(.+?)\s+-\s+(.+)', title)
        if not m:
            continue
        home, away = m.group(1).strip(), m.group(2).strip()
        if CLUB_NAME not in home:
            continue
        try:
            dt = parsedate_to_datetime(pub)
        except (TypeError, ValueError):
            continue

        found += 1
        ev = {
            'title':  f'{CLUB_NAME} - {away}',
            'date':   dt.date().isoformat(),
            'time':   dt.strftime('%H:%M'),
            'venue':  VENUE,
            'url':    link or FEED_URL,
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'volleybal',
            'gender': 'heren',
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB_NAME} [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
