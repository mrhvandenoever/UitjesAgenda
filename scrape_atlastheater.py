"""
scrape_atlastheater.py — Atlas Theater Emmen via de eigen Umbraco-API

Gebruik:
    python scrape_atlastheater.py              # scrape, sla op in DB
    python scrape_atlastheater.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md (scraping_recipes.json ging uit
van een Chrome-klik-loop op de "Laad meer"-knop). Bleek niet nodig: de site
draait op Umbraco (.NET CMS) met een ticketingplatform (herkenbaar aan
agenda.ticketunie.com-afbeeldings-URL's) dat zijn eigen frontend voedt via
een simpele JSON-API, gevonden door /dist/js/dist-performanceoverview/main.js
te doorzoeken op "/Umbraco/Api/". Geen auth nodig, één call geeft het hele
seizoen (207 voorstellingen, sep 2026 t/m jun 2027) — geen paginering nodig.

Endpoint: GET /Umbraco/Api/PerformanceApi/GetPerformances

Title/Artist-velden zijn niet consistent ingevuld door de venue (soms is
Title de voorstellingsnaam en Artist de act, soms andersom, soms is Title
leeg) — we combineren beide met een simpele fallback i.p.v. te gokken welke
van de twee "de titel" is.
"""

import urllib.request
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'atlastheater'
BASE_URL = 'https://www.atlastheater.nl'
API_URL  = f'{BASE_URL}/Umbraco/Api/PerformanceApi/GetPerformances'


def fetch() -> list[dict]:
    req = urllib.request.Request(API_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def build_title(p: dict) -> str:
    title  = (p.get('Title') or '').strip()
    artist = (p.get('Artist') or '').strip()
    if title and artist and title != artist:
        return f'{title} - {artist}'
    return title or artist


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        items = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    print(f"  {len(items)} voorstellingen opgehaald")

    found = added = 0
    all_events = []
    for item in items:
        p = item.get('Performance') or {}
        title = build_title(p)
        start_time = p.get('StartTime') or ''
        if not title or not start_time:
            continue
        iso_date, _, rest = start_time.partition('T')
        time_str = rest[:5] if rest else None
        room = (p.get('Room') or '').strip()
        rel_url = item.get('Url') or ''

        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  f'{room}, Emmen' if room else 'ATLAS Theater, Emmen',
            'url':    f'{BASE_URL}{rel_url}' if rel_url else BASE_URL,
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

    print(f"Scraping Atlas Theater Emmen (Umbraco-API) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
