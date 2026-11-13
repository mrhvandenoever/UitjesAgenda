"""
scrape_sudosa.py — CRAFT Sudosa (volleybal, dames 1) via Nevobo RSS

Gebruik:
    python scrape_sudosa.py              # scrape, sla op in DB
    python scrape_sudosa.py --dry-run    # toon events zonder op te slaan

Zelfde aanpak als scrape_lycurgus.py (zie die docstring) — bewust een losse
kopie per club, zie ARCHITECTURE.md §Scrapers-conventie. Volledige naam:
Jumbo Virena Autogroep Sudosa. Teamcode cpx7m7h (dames/1).
"""

import urllib.request
import re
import argparse
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import fromstring
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE    = 'sudosa'
CLUB_NAME = 'Sudosa'
VENUE     = 'Sporthal Kardinge, Groningen'
FEED_URL  = 'https://api.nevobo.nl/export/team/cpx7m7h/dames/1/programma.rss'


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
    all_events = []
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        desc = (item.findtext('description') or '').strip()
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

        venue_m = re.search(r'Speellocatie:\s*(.+)', desc)
        venue = venue_m.group(1).strip() if venue_m else VENUE

        found += 1
        ev = {
            'title':  f'{CLUB_NAME} - {away}',
            'date':   dt.date().isoformat(),
            'time':   dt.strftime('%H:%M'),
            'venue':  venue,
            'url':    link or FEED_URL,
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'volleybal',
            'gender': 'dames',
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time']}] {ev['title']}")
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB_NAME} [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
