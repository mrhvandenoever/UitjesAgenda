"""
scrape_ziggodome.py — Ziggo Dome (Amsterdam) via podiuminfo.nl

Gebruik:
    python scrape_ziggodome.py              # scrape, sla op in DB
    python scrape_ziggodome.py --dry-run    # toon events zonder op te slaan

Tip van Michiel: podiuminfo.nl (al gebruikt voor Machinefabriek, zie
scrape_machinefabriek.py) heeft ook een podium-pagina voor Ziggo Dome, met
gewoon JSON-LD (schema.org MusicEvent) in de ruwe HTML — geen browser nodig.

ziggodome.nl zelf is wél onderzocht met Playwright: bleek een gevirtualiseerde
lijst (react-window-achtig, ~40 events maar maar een deel tegelijk in de
DOM) die met scroll-simulatie meer/verder-vooruit events oplevert (tot mei
2027) dan podiuminfo (tot ongeveer 2 maanden vooruit, geen paginering
gevonden — `?pagina=2` geeft dezelfde 25 events terug). We kiezen toch voor
podiuminfo: geen Playwright/browser-overhead nodig, én echte per-event-URL's
(ziggodome.nl's eigen kaarten hebben geen zichtbare per-event-link in de
DOM). Bewuste gedeeltelijke dekking, zelfde afweging als bij
scrape_tivolivredenburg.py (Songkick).
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE = 'ziggodome'
URL    = 'https://www.podiuminfo.nl/podium/1968/concerten/Ziggo-Dome/Amsterdam/'
VENUE  = 'Ziggo Dome, Amsterdam'

LDJSON_PATTERN = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def fetch() -> str:
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    items = []
    for block in LDJSON_PATTERN.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get('@type') == 'MusicEvent':
            items.append(data)

    print(f"  {len(items)} MusicEvent-items gevonden op podiuminfo.nl")

    found = added = 0
    all_events = []
    for item in items:
        title = (item.get('name') or '').replace(' @ Ziggo Dome', '').strip()
        start = item.get('startDate') or ''
        if not title or not start:
            continue
        iso_date, _, rest = start.partition('T')
        time_str = rest[:5] if rest else None

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

    print(f"Scraping Ziggo Dome (via podiuminfo.nl) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
