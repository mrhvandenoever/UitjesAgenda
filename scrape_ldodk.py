"""
scrape_ldodk.py — LDODK (korfbal, Korfbal League) thuiswedstrijden

Gebruik:
    python scrape_ldodk.py              # scrape, sla op in DB
    python scrape_ldodk.py --dry-run    # toon events zonder op te slaan

Stond geparkeerd: "Competitie zelf zegt: seizoen start pas 6-8 nov 2026"
(overleg.md/scraping_recipes.json, 2026-08-10). Herchecked 2026-09-02: het
programma blijkt inmiddels wél gepubliceerd op ldodk.nl/teams/ldodk-1/
(Nuxt.js/Storyblok-site).

Geen aparte API-call zichtbaar in het netwerkverkeer — de wedstrijddata zit
server-side al ingebakken in de Nuxt-payload (`<script id="__NUXT_DATA__">`),
een platte JSON-array in het "devalue"-formaat: elk element is óf een
letterlijke waarde, óf een object/lijst waarvan de waarden weer INDEXES
zijn naar andere elementen in diezelfde array (een graaf-serialisatie,
i.p.v. geneste JSON). `_resolve_devalue()` hieronder lost dat recursief op.
Geen Playwright nodig — plain `urllib` volstaat, de payload staat al in de
ruwe server-rendered HTML.

Alleen ~6 wedstrijden per keer zichtbaar (geen duidelijke manier gevonden
om een breder venster op te vragen zoals bij handbal.nl's `aantaldagen`-
param) — geen probleem gezien de dagelijkse refresh: het venster schuift
vanzelf mee.
"""

import urllib.request
import re
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE   = 'ldodk'
CLUB     = 'LDODK/Rinsma Modeplein 1'
PAGE_URL = 'https://www.ldodk.nl/teams/ldodk-1/?tab=programma'
TODAY    = date.today().isoformat()

SPECIAL_WRAPPERS = {'ShallowReactive', 'Reactive', 'Ref', 'ShallowRef'}


def _resolve_devalue(arr: list, i: int, cache: dict, depth: int = 0):
    """Lost 1 element van een Nuxt __NUXT_DATA__-devalue-array recursief op.
    Zie de moduledocstring voor de uitleg van het formaat."""
    if i in cache:
        return cache[i]
    if depth > 40:
        return None
    cache[i] = None  # cyclus-bescherming
    v = arr[i]
    if isinstance(v, list):
        if v and isinstance(v[0], str) and v[0] in SPECIAL_WRAPPERS and len(v) == 2:
            r = _resolve_devalue(arr, v[1], cache, depth + 1)
        elif v and isinstance(v[0], str) and v[0] == 'Set':
            r = [_resolve_devalue(arr, x, cache, depth + 1) for x in v[1:]]
        elif v and isinstance(v[0], str) and v[0] in ('Map', 'Date', 'NuxtError', 'EmptyRef', 'EmptyShallowRef'):
            r = v  # niet nodig voor deze scraper, ruw teruggeven
        elif v and all(isinstance(x, int) for x in v):
            r = [_resolve_devalue(arr, x, cache, depth + 1) for x in v]
        else:
            r = v
    elif isinstance(v, dict):
        if v and all(isinstance(x, int) for x in v.values()):
            r = {k: _resolve_devalue(arr, x, cache, depth + 1) for k, x in v.items()}
        else:
            r = v
    else:
        r = v
    cache[i] = r
    return r


def find_match_list(data: dict) -> list[dict]:
    """Zoekt in de opgeloste 'data'-tak van de Nuxt-payload naar de eerste
    lijst met wedstrijd-records (herkenbaar aan een 'thuisteam'-veld) --
    de sleutel zelf (bv. 'WukI77niGN') is een auto-gegenereerde Nuxt-
    fetch-cache-key, niet stabiel/voorspelbaar, dus structureel zoeken."""
    for val in data.values():
        if isinstance(val, dict):
            rows = val.get('data')
            if isinstance(rows, list) and rows and isinstance(rows[0], dict) and 'thuisteam' in rows[0]:
                return rows
    return []


def fetch_matches() -> list[dict]:
    req = urllib.request.Request(PAGE_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        html = r.read().decode('utf-8', errors='replace')

    idx = html.find('id="__NUXT_DATA__"')
    if idx == -1:
        raise RuntimeError("__NUXT_DATA__ niet gevonden -- site-structuur gewijzigd?")
    start = html.find('>', idx) + 1
    end = html.find('</script>', start)
    arr = json.loads(html[start:end])

    cache: dict = {}
    root = _resolve_devalue(arr, 0, cache)
    data = root.get('data', {}) if isinstance(root, dict) else {}
    return find_match_list(data)


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        matches = fetch_matches()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    found = added = 0
    all_events = []
    for m in matches:
        if m.get('thuisteam') != CLUB:
            continue
        start = m.get('wedstrijddatum', '') or ''
        if not start or start[:10] < TODAY:
            continue
        venue = m.get('accommodatie') or ''
        plaats = (m.get('plaats') or '').title()

        found += 1
        ev = {
            'title':  f"{CLUB} - {m.get('uitteam', '')}",
            'date':   start[:10],
            'time':   start[11:16] if len(start) >= 16 else None,
            'venue':  f"{venue}, {plaats}" if plaats and plaats not in venue else venue,
            'url':    PAGE_URL,
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'korfbal',
            'gender': 'gemengd',
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB} (ldodk.nl, Nuxt-payload) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
