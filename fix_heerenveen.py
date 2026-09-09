"""
scrape_heerenveen.py — SC Heerenveen thuiswedstrijden (Eredivisie)

Gebruik:
    python scrape_heerenveen.py              # scrape, sla op in DB
    python scrape_heerenveen.py --dry-run    # toon events zonder op te slaan

Eigen site (niet ESPN). Statische HTML met per-team/competitie een
<script data-program-json type="application/json"> blok — direct als JSON
te parsen, geen regex-geknoei nodig. Filtert op competitie
"VriendenLoterij Eredivisie" (de pagina bevat ook jeugd/vrouwen/beker-
programma's die we hier niet willen).
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE      = 'heerenveen'
CLUB        = 'sc Heerenveen'
VENUE       = 'Abe Lenstra Stadion, Heerenveen'
URL         = 'https://www.sc-heerenveen.nl/wedstrijden'
COMPETITIE  = 'VriendenLoterij Eredivisie'


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

    blocks = re.findall(
        r'<script data-program-json type="application/json">\s*(\[.*?\])\s*</script>', html, re.S
    )

    found = added = 0
    all_events = []
    for b in blocks:
        try:
            data = json.loads(b)
        except json.JSONDecodeError:
            continue
        for comp in data:
            if comp.get('name') != COMPETITIE:
                continue
            for g in comp.get('games', []):
                if CLUB.lower() not in (g.get('homeTeam') or '').lower():
                    continue
                found += 1
                ev = {
                    'title':  f"{CLUB} - {g.get('awayTeam', 'Onbekend')}",
                    'date':   (g.get('datePlayed') or '')[:10],
                    'venue':  VENUE,
                    'url':    URL,
                    'source': SOURCE,
                    'genre':  'sport',
                    'sport':  'voetbal',
                    'gender': 'heren',
                }
                if not ev['date']:
                    continue
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB} [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
