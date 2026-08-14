"""
scrape_forum.py — Forum Groningen agenda

Gebruik:
    python scrape_forum.py              # scrape, sla op in DB
    python scrape_forum.py --dry-run    # toon events zonder op te slaan

forum.nl mixt bibliotheek-/sociale activiteiten door de echte agenda heen
(leesclub, digihuis, spreekuur, etc.) — SKIP-lijst filtert die eruit.
Titel wordt afgeleid van de URL-slug (geen aparte titeltekst dicht bij de
link beschikbaar zonder complexere parsing).
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'forum.nl'
BASE_URL = 'https://forum.nl/nl/agenda'
VENUE    = 'Forum Groningen'

SKIP = ['leesclub', 'taalcafe', 'digihuis', 'spreekuur', 'breinbieb',
        'spelochtend', 'inloop', '3d-print', '/film/', 'klik-tik',
        'informatiepunt', 'schrijfhulp', 'computerhulp']


def fetch(page: int) -> str:
    req = urllib.request.Request(
        f'{BASE_URL}?p={page}',
        headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    all_events = []
    seen = set()

    for page in range(1, 8):
        try:
            html = fetch(page)
        except Exception as e:
            print(f"  Pagina {page} fout: {e}")
            continue

        matches = list(re.finditer(
            r'data-href="(https://forum\.nl/nl/agenda/([^?]+)\?date=(\d{2})-(\d{2})-(\d{4}))"', html
        ))
        if not matches:
            break

        for m in matches:
            url, slug, d, mo, y = m.groups()
            if any(s in url for s in SKIP):
                continue
            key = (slug, d, mo, y)
            if key in seen:
                continue
            seen.add(key)

            found += 1
            title = slug.replace('-', ' ').title()
            ev = {
                'title':  title,
                'date':   f'{y}-{mo}-{d}',
                'venue':  VENUE,
                'url':    url,
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

    print(f"Scraping Forum Groningen [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
