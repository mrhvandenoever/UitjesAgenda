"""
scrape_hedon.py — Hedon (Zwolle) via de eigen JSON-API

Gebruik:
    python scrape_hedon.py              # scrape, sla op in DB
    python scrape_hedon.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md (pagina laadt maar is een lege
Angular-SPA-shell, 7KB). Michiel wees op een LinkedIn-post van Hedon zelf
over hun koppeling met Yesplan (venue-planningsoftware) — dat bleek de
sleutel: de site heeft een simpele eigen JSON-endpoint `/api/events` die
zijn data uit Yesplan haalt (herkenbaar aan het `yesplanId`-veld per event).
Geen auth nodig, geen paginering — één call geeft alles.

`/api/events` bevat ook events die Hedon promoot maar die ELDERS
plaatsvinden (bv. "Zwolse Theaters - De Spiegel", "Calluna, Ommen") — we
filteren op `venue` die met "Hedon" begint, zodat alleen echte
Hedon-locatie-events meekomen (Grote Zaal / Kleine Zaal).
"""

import urllib.request
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE  = 'hedon'
API_URL = 'https://www.hedon-zwolle.nl/api/events'


def fetch() -> list[dict]:
    req = urllib.request.Request(API_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        items = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    hedon_items = [e for e in items if (e.get('venue') or '').startswith('Hedon')]
    print(f"  {len(items)} events opgehaald, {len(hedon_items)} op Hedon-locatie zelf")

    found = added = 0
    all_events = []
    for e in hedon_items:
        title = (e.get('title') or '').strip()
        event_date = e.get('eventDate') or ''
        if not title or not event_date:
            continue
        iso_date, _, rest = event_date.partition('T')
        time_str = rest[:5] if rest else None
        venue = e.get('venue') or 'Hedon'

        found += 1
        ev = {
            'title':  title.title() if title.isupper() else title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  f'{venue}, Zwolle',
            'url':    e.get('externalTicketsUrl') or 'https://www.hedon-zwolle.nl/programma',
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']} @ {ev['venue']}")
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

    print(f"Scraping Hedon Zwolle (eigen API, Yesplan-backed) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
