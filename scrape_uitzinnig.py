"""
scrape_uitzinnig.py — Uitzinnig.nl tentoonstellingsagenda (aggregator,
Drenthe/Groningen/Friesland)

Gebruik:
    python scrape_uitzinnig.py              # scrape, sla op in DB
    python scrape_uitzinnig.py --dry-run    # toon events zonder op te slaan

Ontstaan uit overleg.md punt 13: een tweede expositie-aggregator naast
scrape_kunstpuntgroningen.py, dit keer met bereik over alle 3 provincies
i.p.v. vooral Groningen-stad.

De "provincie"-pagina's (`/<provincie>/tentoonstellingsagenda.aspx`) blijken
in de praktijk NIET strikt gefilterd — dezelfde expositie duikt op meerdere
provinciepagina's op (bv. een Roden-expositie op zowel de Drenthe- als de
Groningen-pagina). Daarom worden alle 3 pagina's opgehaald en gededupliceerd
op URL (die is wél uniek per expositie) i.p.v. als 3 losstaande feeds
behandeld.

Elke pagina is al specifiek een "tentoonstellingsagenda" — geen categorie-
filter nodig zoals bij Kunstpunt (dat is een algemene 40+-categorieën-
kalender). Genre-signaal via cats=['expositie'], zelfde reden als bij
Kunstpunt (titels zijn niet gegarandeerd Nederlands-keyword-matchbaar).

Datums staan niet compleet op de listing-pagina (alleen "Vandaag t/m X" of
een kale einddatum), maar wel als schone ISO-meta-tags op de detailpagina
van elke expositie (`<meta name="startdatum" content="2026-08-01">`). De
detailpagina geeft ook de echte venue-naam (listing toont alleen de
plaatsnaam) via een `.subinfo`-regel: "1 t/m 23 augustus 2026 |
Kunstencentrum K38 | Roden (Noordenveld)".

Bekende overlap met scrape_kunstpuntgroningen.py: "Mimesis" (Kunstencentrum
K38, Roden) en "Overzichtsexpositie Aldrik Salverda en Lucas Klein"
(Kunstruimte De Smederij, Sappemeer) staan al vollediger via Kunstpunt.
Zelfde soort aggregator-vs-aggregator-dedup-gat als bij DSG eerder
(decisions.md 2026-08-17): `find_cross_source_duplicates()` in events_db.py
slaat een paar over zodra BEIDE kanten een aggregator zijn (`agg_a == agg_b:
continue`), dus de generieke dedup vangt dit niet. Hier ook opgelost met een
gerichte SKIP-lijst i.p.v. een generieke cross-aggregator-matcher.
"""

import urllib.request
import re
import html as html_lib
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context
from parallel_fetch import fetch_many

SSL_CTX = create_context()

SOURCE = 'uitzinnig'
BASE_URL = 'https://www.uitzinnig.nl'
PROVINCE_PAGES = ['drenthe', 'groningen', 'friesland']

CITY_PROVINCE = {
    'Roden': 'Drenthe', 'Dwingeloo': 'Drenthe', 'Emmer-Compascuum': 'Drenthe',
    'Zweeloo': 'Drenthe', 'Emmen': 'Drenthe', 'Borger': 'Drenthe',
    'Delfzijl': 'Groningen', 'Onstwedde': 'Groningen', 'Sappemeer': 'Groningen',
    'Kantens': 'Groningen', 'Leeuwarden': 'Friesland',
}

# Bekende duplicaten met scrape_kunstpuntgroningen.py — zie docstring hierboven.
SKIP_TITLES = {'Mimesis', 'Overzichtsexpositie Aldrik Salverda en Lucas Klein'}

ITEM_PATTERN = re.compile(
    r'<div class="item" onclick="location.href=\'([^\']+)\';">.*?'
    r'<h3><a[^>]*>([^<]*)</a></h3>',
    re.S
)
DATE_PATTERN = re.compile(
    r'name="startdatum" content="([^"]+)".*?name="einddatum" content="([^"]+)"', re.S)
SUBINFO_PATTERN = re.compile(
    r'<div class="subinfo">[^|]+\|\s*([^|<]+?)\s*\|\s*<a[^>]*>([^<]*)</a>')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8')


def clean_city(raw: str) -> str:
    """'Borger (Borger-Odoorn)' -> 'Borger' (municipality-suffix eraf, past
    dan weer op city_coords.json)."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', raw).strip()


def parse_listing(html_text: str) -> dict:
    """url -> titel. Dict i.p.v. lijst — dezelfde expositie komt op meerdere
    provinciepagina's terug (zie moduledocstring)."""
    out = {}
    for path, title in ITEM_PATTERN.findall(html_text):
        title = html_lib.unescape(title).strip()
        if not title or title in SKIP_TITLES:
            continue
        out[BASE_URL + path] = title
    return out


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    by_url = {}
    listing_results = fetch_many(
        [f'{BASE_URL}/{p}/tentoonstellingsagenda.aspx' for p in PROVINCE_PAGES], fetch)
    for html_text, exc in listing_results:
        if exc is not None:
            print(f"  Provinciepagina-fout: {exc}")
            continue
        by_url.update(parse_listing(html_text))

    found = len(by_url)
    print(f"  {found} unieke exposities gevonden, detailpagina's ophalen...")

    urls = list(by_url.keys())
    detail_results = fetch_many(urls, fetch)

    all_events = []
    for url, (detail_html, exc) in zip(urls, detail_results):
        title = by_url[url]
        if exc is not None:
            print(f"  Detailpagina-fout ({title}): {exc}")
            continue
        date_m = DATE_PATTERN.search(detail_html)
        if not date_m:
            continue
        start_iso, end_iso = date_m.groups()

        sub_m = SUBINFO_PATTERN.search(detail_html)
        venue = html_lib.unescape(sub_m.group(1)).strip() if sub_m else ''
        city = clean_city(html_lib.unescape(sub_m.group(2))) if sub_m else ''

        ev = {
            'title':    title,
            'date':     start_iso,
            'venue':    venue,
            'city':     city,
            'province': CITY_PROVINCE.get(city, 'Onbekend'),
            'url':      url,
            'source':   SOURCE,
            'cats':     ['expositie'],
        }
        if end_iso != start_iso:
            ev['date_end'] = end_iso
        all_events.append(ev)

    if dry_run:
        for ev in all_events:
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']} ({ev['venue']}, {ev['city']})")
        print(f"\nDry-run: {len(all_events)} events gevonden (niets opgeslagen)")
        return len(all_events), 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        return found, 0

    added = 0
    for ev in all_events:
        if insert_event(ev):
            added += 1
    log_scrape(SOURCE, found, added)
    print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping Uitzinnig.nl tentoonstellingsagenda [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
