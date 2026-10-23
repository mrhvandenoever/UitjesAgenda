"""
scrape_grizzlys.py — GIJS Marne Groningen (ijshockey) thuiswedstrijden

Gebruik:
    python scrape_grizzlys.py              # scrape, sla op in DB
    python scrape_grizzlys.py --dry-run    # toon events zonder op te slaan

Stond lange tijd geparkeerd (SCRAPERS.md: "site toont nog seizoen 2025-2026")
— het 2026-2027-seizoen bleek inmiddels wél gepubliceerd (herchecked
2026-09-02, overleg.md). gijsgroningen.nl zelf is client-rendered (Shift4Shop-
achtige builder, geen data in de ruwe HTML), maar de pagina blijkt onder de
motorkap een PUBLIEKE JSONP-API van derde partij "hockeydata.net" te
gebruiken (gevonden via Chrome MCP netwerkverkeer): een complete
Eredivisie-schema-feed die ALLE 13 clubs in één call teruggeeft, inclusief
GIJS Marne Groningen, Jumbo Flyers Heerenveen en OG Capitals Leeuwarden
(zie ook scrape_flyers.py/scrape_ogcapitals.py — bewust 3 losse kopieën
i.p.v. een gedeelde helper, zie ARCHITECTURE.md §Scrapers-conventie).

De apiKey staat gewoon in de publiek uitgeleverde frontend-JS (geen login,
geen secret) — zelfde categorie publieke frontend-key als bij
scrape_handbal.py (Sportlink) en scrape_donar.py/scrape_landstede.py
(Sportpress). `callback=`-param weglaten geeft gewoon platte JSON i.p.v.
JSONP.
"""

import urllib.request
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE    = 'grizzlys'
CLUB      = 'GIJS Marne Groningen'
API_URL   = (
    'https://api.hockeydata.net/data/ebel/Schedule'
    '?apiKey=ae650348443c267e3af31d21fe5533fa&lang=en&referer=gijsgroningen.nl'
    '&divisionId=22086&widgetOptions=%7B%22semantic%22%3Atrue%2C%22noScorers%22%3Atrue%7D'
)
TODAY = date.today().isoformat()


def fetch() -> dict:
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return json.loads(r.read().decode('utf-8'))


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        data = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    rows = data.get('data', {}).get('rows', [])
    found = added = 0
    all_events = []
    for r in rows:
        if r.get('homeTeamLongName') != CLUB:
            continue
        start = r.get('scheduledGameStart', '')
        if not start or start[:10] < TODAY:
            continue
        loc = r.get('location') or {}
        try:
            addr = json.loads(loc.get('address') or '{}')
        except json.JSONDecodeError:
            addr = {}
        venue = loc.get('longname') or ''
        city = addr.get('city') or loc.get('shortname') or ''

        found += 1
        ev = {
            'title':  f"{CLUB} - {r.get('awayTeamLongName', '')}",
            'date':   start[:10],
            'time':   r.get('scheduledTime') or start[11:16],
            'venue':  f"{venue}, {city}" if city and city not in venue else venue,
            'url':    'https://gijsgroningen.nl/gijs-eredivisie/',
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'ijshockey',
            'gender': 'heren',
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time']}] {ev['title']} @ {ev['venue']}")
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

    print(f"Scraping {CLUB} (hockeydata.net) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
