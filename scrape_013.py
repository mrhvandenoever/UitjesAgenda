"""
scrape_013.py — 013 Tilburg via server-rendered HTML

Gebruik:
    python scrape_013.py              # scrape, sla op in DB
    python scrape_013.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md (JSON-LD aanwezig maar alleen
metadata, geen Event-items). Bleek niet nodig: de programma-pagina rendert
zelf server-side een reeks `<article>`-blokken (Alpine.js voor interactie,
maar de data staat gewoon in de HTML) met een titel (`<h2>`), link en
`<time datetime="ISO">` — regex-extractie, geen browser nodig.
"""

import urllib.request
import re
import html as html_lib
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = '013'
BASE_URL = 'https://www.013.nl'
AGENDA_URL = f'{BASE_URL}/programma'
VENUE    = '013, Tilburg'

PATTERN = re.compile(
    r'href="(https://www\.013\.nl/programma/\d+/[^"]+)"[^>]*>.*?'
    r'<h2[^>]*>([^<]+)</h2>.*?'
    r'<time datetime="([^"]+)"',
    re.S,
)


def fetch() -> str:
    req = urllib.request.Request(AGENDA_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html_text = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = PATTERN.findall(html_text)
    print(f"  {len(matches)} events op de programma-pagina")

    found = added = 0
    all_events = []
    for url, title, dt in matches:
        title = html_lib.unescape(title).strip()
        iso_date, _, rest = dt.partition('T')
        if not title or not iso_date:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   rest[:5] if rest else None,
            'venue':  VENUE,
            'url':    url,
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
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

    print(f"Scraping 013 Tilburg (server-rendered HTML) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
