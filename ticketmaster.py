"""
ticketmaster.py — kleine, herbruikbare helper rond de Ticketmaster Discovery
API (gratis tier). Zie ARCHITECTURE.md §Ticketmaster-scrapers en
decisions.md 2026-08-15.

Vereist een API-key in secrets.local.json (nooit in dit bestand hardcoden,
nooit committen) — zie secrets.local.json.example.

Gebruik in een scraper:

    from ticketmaster import fetch_venue_events
    events = fetch_venue_events(VENUE_ID)  # VENUE_ID eenmalig opgezocht,
                                            # zie find_venue_id() hieronder

Rate limits (gratis tier): 5.000 calls/dag, 5 requests/seconde, deep paging
beperkt tot size*page<1000. Deze module wacht daarom altijd minstens 0.25s
tussen calls en gebruikt size=200 (max) om het aantal requests te
minimaliseren.

Waarom het venue-id hardcoded hoort te worden in een scraper i.p.v. elke
run opnieuw op naam te zoeken: `find_venue_id()` matcht op een zoekterm, en
Ticketmaster kan meerdere venues met vergelijkbare naam teruggeven (bv.
"Ziggo Dome", "Ziggo Dome Club", "Vinyl Room - Ziggo Dome") — een
naam-zoekopdracht die bij elke run opnieuw draait kan dus per ongeluk een
ander/verkeerd venue matchen. Een venue-id verandert niet.
"""

import json
import time
import urllib.parse
import urllib.request

from secrets_local import get_secret

API_BASE = 'https://app.ticketmaster.com/discovery/v2'
_MIN_INTERVAL = 0.25  # ruim onder de 5 requests/seconde-limiet
_last_call = 0.0


def _get(path: str, params: dict) -> dict:
    global _last_call
    wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    full_params = {**params, 'apikey': get_secret('ticketmaster_api_key')}
    url = f'{API_BASE}/{path}?{urllib.parse.urlencode(full_params)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'uitjesagenda-bot/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode('utf-8'))
    _last_call = time.monotonic()
    return data


def find_venue_id(keyword: str, country_code: str = 'NL') -> list[dict]:
    """Zoek venues op naam — bedoeld om eenmalig te draaien (bv. in een
    python -c-eenregelaar) om het juiste venue-id te vinden, niet om in een
    scraper zelf bij elke run aan te roepen."""
    data = _get('venues.json', {'keyword': keyword, 'countryCode': country_code})
    return data.get('_embedded', {}).get('venues', [])


def fetch_venue_events(venue_id: str) -> list[dict]:
    """Alle events voor een venue-id, alle pagina's automatisch opgehaald."""
    events = []
    page = 0
    while True:
        data = _get('events.json', {'venueId': venue_id, 'size': 200, 'page': page})
        events.extend(data.get('_embedded', {}).get('events', []))
        total_pages = data.get('page', {}).get('totalPages', 1)
        page += 1
        if page >= total_pages:
            break
    return events
