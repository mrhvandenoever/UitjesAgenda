"""
scrape_spotgroningen.py — spotgroningen.nl/programma/

Gebruik:
    python scrape_spotgroningen.py              # scrape, sla op in DB
    python scrape_spotgroningen.py --dry-run    # toon events zonder op te slaan

SPOT (Groningen) bestaat uit meerdere gebouwen (Oosterpoort, Stadsschouwburg,
A-Theater, Machinefabriek, USVA, Lutherse Kerk). De programma-pagina rendert
server-side (static HTML, geen JS nodig) en elk event zit in een
<article class="program__item" data-location="..." data-genres="..."
data-subgenres="..."> blok — dat geeft ons zowel het exacte gebouw als een
echt genre-signaal, i.p.v. te moeten gokken op de titeltekst.

Aanpak: split de pagina op elk "<article class=\"program__item" voorkomen en
parseer per blok los (i.p.v. één grote regex over de hele pagina) — een
enkele regex over de volledige pagina matcht onbetrouwbaar zodra events
extra markup bevatten (bv. een "Noorderzon"-statuslabel), waardoor loc/genre
van het ene event aan de titel van een ander event gekoppeld raakt.
Geverifieerd 2026-08-11: 625/625 blokken succesvol geparsed.
"""

import urllib.request
import ssl
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SOURCE   = 'spotgroningen.nl'
BASE_URL = 'https://www.spotgroningen.nl/programma/'
PROVINCE = 'Groningen'

# data-location → weergavenaam
LOCATIONS = {
    'oosterpoort':     'Oosterpoort, Groningen',
    'stadsschouwburg': 'Stadsschouwburg, Groningen',
    'a-theater':       'A-Theater, Groningen',
    'machinefabriek':  'Machinefabriek, Groningen',
    'usva':            'USVA, Groningen',
    'lutherse-kerk':   'Lutherse Kerk, Groningen',
    'elders':          'Spot Groningen',
    '':                'Spot Groningen',
}

# SPOT's eigen genres/subgenres (comma-separated, meerdere mogelijk) →
# onze 'cats'-vocabulaire (zie cat_map in gen_uitjes.py:classify()).
# Subgenres zijn specifieker en krijgen voorrang boven genres.
SUBGENRE_MAP = {
    'jazz':               'jazz',
    'blues':               'jazz',
    # 'cross-over' bewust NIET gemapt: te dubbelzinnig (in de praktijk zowel
    # klassieke talentavonden/kamermuziek als bv. een punkoperette) — laat
    # die gevallen terugvallen op classify()'s titel-keyword-logica.
    'orkesten-ensembles':  'klassiek',
    'kamermuziek':         'klassiek',
    'koren':               'klassiek',
    'opera':               'opera',
    'pop-rock':            'pop',
    'indie':               'pop',
    'roots-americana':     'pop',
    'hiphop':              'pop',
    'stand-up':            'cabaret',
    'kleinkunst':          'cabaret',
    'muziektheater':       'theater',
    'theatercollege':      'theater',
    'jeugd-toneel':        'kinderen',
    'jeugd-muziek':        'kinderen',
    'jeugd-dans':          'kinderen',
    'moderne-dans':        'dans',
}
GENRE_MAP = {
    'klassiek':     'klassiek',
    'cabaret':      'cabaret',
    'theater':      'theater',
    'dans':         'dans',
    'familie':      'kinderen',
}


def unescape(s: str) -> str:
    return (s.replace('&amp;', '&').replace('&#039;', "'")
             .replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')).strip()


def strip_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', ' ', s)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def cats_for(genres_raw: str, subgenres_raw: str) -> list[str]:
    cats = []
    for sg in subgenres_raw.split(','):
        if sg in SUBGENRE_MAP:
            cats.append(SUBGENRE_MAP[sg])
    for g in genres_raw.split(','):
        if g in GENRE_MAP:
            cats.append(GENRE_MAP[g])
    # dedupliceer, behoud volgorde (subgenres het eerst = hoogste prioriteit)
    seen = set()
    return [c for c in cats if not (c in seen or seen.add(c))]


def parse_block(block: str) -> dict | None:
    loc_m = re.search(r'data-location="([^"]*)"', block)
    genres_m = re.search(r'data-genres="([^"]*)"', block)
    subgenres_m = re.search(r'data-subgenres="([^"]*)"', block)
    url_m = re.search(r'href="([^"]+)" class="program__link"', block)
    dt_m = re.search(r'<time datetime="([^"]+)"', block)
    h2_m = re.search(r'<h2>(.*?)</h2>', block, re.S)
    p_m = re.search(r'</h2>\s*<p>(.*?)</p>', block, re.S)

    if not (loc_m and dt_m and h2_m):
        return None

    title = unescape(strip_tags(h2_m.group(1)))
    if not title:
        return None
    subtitle = unescape(strip_tags(p_m.group(1))) if p_m else ''

    return {
        'title':    title,
        'subtitle': subtitle or None,
        'date':     dt_m.group(1)[:10],
        'time':     dt_m.group(1)[11:16],
        'venue':    LOCATIONS.get(loc_m.group(1), 'Spot Groningen'),
        'url':      url_m.group(1) if url_m else BASE_URL,
        'cats':     cats_for(genres_m.group(1) if genres_m else '',
                              subgenres_m.group(1) if subgenres_m else ''),
    }


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    today = date.today().isoformat()

    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    blocks = html.split('<article class="program__item')[1:]
    print(f"  {len(blocks)} events op de programma-pagina")

    for b in blocks:
        parsed = parse_block(b)
        if not parsed or parsed['date'] < today:
            continue
        found += 1
        ev = {
            'title':    parsed['title'],
            'date':     parsed['date'],
            'time':     parsed['time'],
            'venue':    parsed['venue'],
            'subtitle': parsed['subtitle'],
            'province': PROVINCE,
            'source':   SOURCE,
            'url':      parsed['url'],
            'cats':     parsed['cats'],
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time']}] {ev['title'][:50]:50s} cats={ev['cats']} @ {ev['venue']}")
        else:
            if insert_event(ev):
                added += 1

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} toekomstige events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping spotgroningen.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
