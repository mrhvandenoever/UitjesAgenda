"""
scrape_ahoy.py — Rotterdam Ahoy via de Ticketmaster Discovery API

Gebruik:
    python scrape_ahoy.py              # scrape, sla op in DB
    python scrape_ahoy.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md (Foundation-framework, geen
API-sporen gevonden). Michiel wees erop dat grote arena's als Ahoy vrijwel
altijd via Ticketmaster verkopen — bevestigd: 41 events. Zie ticketmaster.py
en decisions.md 2026-08-15.

Venue-id (Z598xZbpZdk7k) eenmalig opgezocht met
`ticketmaster.find_venue_id('Ahoy Rotterdam')` — de zoekterm gaf ook
"RTM Stage - Rotterdam Ahoy" (een aparte zaal binnen hetzelfde complex) en
"Ahoy' Rotterdam" (0 events) terug; dit id ("Rotterdam Ahoy") had de meeste
events en is de hoofdzaal.
"""

import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ticketmaster import fetch_venue_events

SOURCE   = 'ahoy'
VENUE    = 'Rotterdam Ahoy, Rotterdam'
VENUE_ID = 'Z598xZbpZdk7k'


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        items = fetch_venue_events(VENUE_ID)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    print(f"  {len(items)} events via Ticketmaster")

    found = added = 0
    all_events = []
    for item in items:
        title = (item.get('name') or '').strip()
        start = item.get('dates', {}).get('start', {})
        iso_date = start.get('localDate')
        time_str = (start.get('localTime') or '')[:5] or None
        if not title or not iso_date:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  VENUE,
            'url':    item.get('url'),
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

    print(f"Scraping Rotterdam Ahoy (Ticketmaster Discovery API) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
