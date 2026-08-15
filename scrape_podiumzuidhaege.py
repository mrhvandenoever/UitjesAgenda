"""
scrape_podiumzuidhaege.py — Podium Zuidhaege (Assen) via de WP REST-API

Gebruik:
    python scrape_podiumzuidhaege.py              # scrape, sla op in DB
    python scrape_podiumzuidhaege.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md. WordPress-site met een eigen
`event_listing`-post-type dat WEL via `/wp-json/wp/v2/event_listing`
opvraagbaar is (in tegenstelling tot Vera/Simplon, ook WordPress, die geen
custom event-post-type via REST exposen). Het `date`-veld van de REST-API is
alleen de WP-publicatiedatum, niet de evenementdatum, en `meta` (custom
fields) is leeg — dus de echte datum staat alleen in de vrije tekst van
`content.rendered` ("Op zaterdag 10 oktober van 21.00 tot 23.00 uur...").
Zelfde patroon als scrape_dorpshuisannen.py: tekst-regex + jaartal afleiden
(rollen naar volgend jaar als de datum al voorbij is).
"""

import urllib.request
import json
import re
import html as html_lib
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'podiumzuidhaege'
API_URL  = 'https://podiumzuidhaege.nl/wp-json/wp/v2/event_listing?per_page=100&page=1'
VENUE    = 'Podium Zuidhaege, Assen'

NL_MONTHS = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
DATE_PATTERN = re.compile(
    r'\bOp\s+(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)?\s*'
    r'(\d{1,2})\s+(' + '|'.join(NL_MONTHS) + r')'
    r'(?:\s+(?:van|om)\s+(\d{1,2})[.:](\d{2}))?',
    re.I,
)


def fetch(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def strip_tags(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)
    return html_lib.unescape(text)


def parse_date(day: int, month_name: str) -> str | None:
    month = NL_MONTHS.get(month_name.lower())
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
        items = fetch(API_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    print(f"  {len(items)} event_listing-posts opgehaald")

    found = added = 0
    all_events = []
    for item in items:
        title = strip_tags((item.get('title') or {}).get('rendered', '')).strip()
        content = strip_tags((item.get('content') or {}).get('rendered', ''))
        m = DATE_PATTERN.search(content)
        if not title or not m:
            continue
        iso_date = parse_date(int(m.group(1)), m.group(2))
        if not iso_date:
            continue
        time_str = f'{int(m.group(3)):02d}:{m.group(4)}' if m.group(3) else None

        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  VENUE,
            'url':    item.get('link'),
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

    print(f"Scraping Podium Zuidhaege (WP REST-API) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
