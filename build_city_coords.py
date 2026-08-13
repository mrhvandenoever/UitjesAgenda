"""
build_city_coords.py — eenmalige geocode-actie voor city_coords.json

De 3 regionale aggregators (drenthe.nl, visitgroningen, friesland.nl) hebben
in VENUE_LOC maar één vast coördinaat per bron, niet per stad — waardoor de
afstandsberekening voor al hun events (~2500, verspreid over ~255 plaatsen)
onjuist is (zie plan.md, bug gevonden 2026-08-11 door Michiel).

Dit script geocodeert elke unieke plaatsnaam bij deze 3 bronnen via Nominatim
(OpenStreetMap) en cachet het resultaat in city_coords.json. Coördinaten van
dorpen/steden veranderen niet — dit hoeft dus maar één keer te draaien, en
daarna alleen opnieuw voor eventuele nieuwe plaatsnamen.

Respecteert Nominatim's usage policy: max 1 request/seconde, eigen
User-Agent, geen parallelle requests.

Gebruik:
    python build_city_coords.py              # geocode ontbrekende plaatsen, sla op
    python build_city_coords.py --dry-run     # toon welke plaatsen ontbreken, geocode niet
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
import ssl
import argparse

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, 'city_coords.json')
EVENTS_PATH = os.path.join(SCRIPT_DIR, 'events_categorized.json')

AGGREGATOR_SOURCES = {'drenthe.nl', 'visitgroningen', 'friesland.nl'}
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
USER_AGENT = 'uitjesagenda-bot/1.0 (https://uitjesagenda.pages.dev; eenmalige geocode-actie voor plaatsnamen)'


def valid_city_name(city: str) -> bool:
    city = city.strip()
    if len(city) < 2:
        return False
    if not re.search(r'[A-Za-zÀ-ÿ]', city):
        return False
    return True


def collect_cities() -> set[str]:
    data = json.load(open(EVENTS_PATH, encoding='utf-8'))
    cities = set()
    for e in data:
        if e.get('source') in AGGREGATOR_SOURCES:
            city = (e.get('city') or '').strip()
            if valid_city_name(city):
                cities.add(city)
    return cities


# Ruwe bounding box Noord-Nederland (Groningen/Drenthe/Friesland) om te voorkomen
# dat een plaatsnaam die ook elders in NL bestaat (bv. Sloten, Steenbergen,
# Zorgvlied, Moddergat) het verkeerde resultaat oplevert. links,boven,rechts,onder.
VIEWBOX = '4.7,53.6,7.4,52.5'


def geocode(city: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode({
        'q': f'{city}, Nederland',
        'format': 'json',
        'countrycodes': 'nl',
        'viewbox': VIEWBOX,
        'bounded': 1,
        'limit': 1,
    })
    req = urllib.request.Request(f'{NOMINATIM_URL}?{params}', headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
            results = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f"    FOUT bij {city}: {e}")
        return None
    if not results:
        return None
    return float(results[0]['lat']), float(results[0]['lon'])


def main(dry_run: bool = False):
    cache = {}
    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH, encoding='utf-8'))

    cities = collect_cities()
    missing = sorted(c for c in cities if c not in cache)

    print(f"{len(cities)} unieke plaatsen bij de 3 aggregators, {len(cache)} al gecached, {len(missing)} nog te geocoden")

    if dry_run:
        for c in missing:
            print(f"  {c}")
        return

    failed = []
    for i, city in enumerate(missing, 1):
        result = geocode(city)
        if result:
            cache[city] = result
            print(f"  [{i}/{len(missing)}] {city} -> {result}")
        else:
            failed.append(city)
            print(f"  [{i}/{len(missing)}] {city} -> NIET GEVONDEN")
        time.sleep(1.1)  # Nominatim usage policy: max 1 req/sec

    json.dump(cache, open(CACHE_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\n✓ Klaar: {len(cache)} plaatsen in {CACHE_PATH}")
    if failed:
        print(f"  Niet gevonden ({len(failed)}): {', '.join(failed)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
