"""
scrape_universiteitsmuseum.py — Universiteitsmuseum Groningen (rug.nl)

Gebruik:
    python scrape_universiteitsmuseum.py              # scrape, sla op in DB
    python scrape_universiteitsmuseum.py --dry-run    # toon events zonder op te slaan

Gevonden via overleg.md punt 13 ("kleine venues zoeken" — Michiel,
2026-08-21). Eerder (2026-08-17) verkeerd ingeschat als "Playwright
nodig" — dat gold voor het verkeerde domein (universiteitsmuseum.nl
redirect't naar het Utrechtse UMU). Het Groningse museum draait gewoon
op rug.nl (de standaard RUG-website-CMS) en is volledig server-rendered,
dus toch géén Playwright nodig.

Twee categorieën NIET meegenomen, bewust, geen aanname:
  - Permanente tentoonstellingen zonder loopperiode ("Masterminds", geen
    enkel datumpatroon in de tekst — ondanks dat de listingpagina 'm
    tussen de wisselende exposities toont) en de 3 losse permanente
    zalen (Aletta Jacobskamer, Anatomisch Theater, Muurschildering
    J.C. Kapteyn — expliciet `/permanent/`-URL's, niet eens bezocht).
  - Exposities met alleen een "T/m"-einddatum en GEEN zichtbare
    startdatum (bv. "Puin Hoop: herdruk van de jaren '80" — "T/m 17
    januari 2027" zonder enige startdag) — zelfde principe als bij
    drenthe.nl (overleg.md punt 15) en dmdebuitenplaats.nl: geen
    startdatum verzinnen, dus overgeslagen i.p.v. met een foutieve
    datum getoond.

Datumformaat op deze bron: "D maand [JJJJ] t/m D maand JJJJ" — het
jaartal bij de startdatum ontbreekt soms (bv. "10 april t/m 8 november
2026"); dan wordt het jaartal van de einddatum aangehouden, zelfde
patroon als dmdebuitenplaats.nl.
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE      = 'universiteitsmuseum'
BASE_URL    = 'https://www.rug.nl'
LISTING_URL = f'{BASE_URL}/museum/exhibitions/'
VENUE       = 'Universiteitsmuseum Groningen'
CITY        = 'Groningen'
PROVINCE    = 'Groningen'
TODAY       = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)
RANGE_PAT = re.compile(
    rf'(\d{{1,2}})\s+({MONTH_PAT})(?:\s+(\d{{4}}))?\s+t/m\s+(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})',
    re.I,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def main_text(html: str) -> str:
    m = re.search(r'<main.*?</main>', html, re.S)
    body = m.group(0) if m else html
    text = re.sub(r'<[^>]+>', ' ', body)
    return re.sub(r'\s+', ' ', text).strip()


def parse_range(text: str) -> tuple[str, str] | None:
    m = RANGE_PAT.search(text)
    if not m:
        return None
    d1, mo1, y1, d2, mo2, y2 = m.groups()
    year1 = int(y1) if y1 else int(y2)
    try:
        start = date(year1, MONTHS_NL[mo1.lower()], int(d1))
        end = date(int(y2), MONTHS_NL[mo2.lower()], int(d2))
    except ValueError:
        return None
    if end < start:
        return None
    return start.isoformat(), end.isoformat()


def find_exhibition_urls() -> list[str]:
    html = fetch(LISTING_URL)
    # /permanent/ en /previous/ bewust uitgesloten: geen loopperiode resp.
    # per definitie al voorbij.
    paths = set(re.findall(r'href="(/museum/exhibitions/\d{4}/[a-z0-9\-]+)"', html))
    return sorted(paths)


def parse_exhibition(path: str) -> dict | None:
    url = BASE_URL + path
    html = fetch(url)
    title_m = re.search(r'<title>([^|<]+)', html)
    if not title_m:
        return None
    title = title_m.group(1).strip()

    text = main_text(html)
    rng = parse_range(text)
    if not rng:
        return None
    start_iso, end_iso = rng
    if end_iso < TODAY:
        return None

    ev = {
        'title':    title,
        'date':     start_iso,
        'venue':    VENUE,
        'city':     CITY,
        'province': PROVINCE,
        'source':   SOURCE,
        'url':      url,
        'cats':     ['expositie'],
    }
    if end_iso != start_iso:
        ev['date_end'] = end_iso
    return ev


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        paths = find_exhibition_urls()
    except Exception as e:
        print(f"  FOUT bij listingpagina: {e}")
        return 0, 0
    print(f"  {len(paths)} expositie-pagina's gevonden")

    all_events = []
    for path in paths:
        try:
            ev = parse_exhibition(path)
        except Exception as e:
            print(f"  FOUT bij {path}: {e}")
            continue
        if ev:
            all_events.append(ev)

    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']}")
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")
        return found, 0

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

    print(f"Scraping rug.nl/museum [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
