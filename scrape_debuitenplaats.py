"""
scrape_debuitenplaats.py — Drents Museum De Buitenplaats (Eelde)

Gebruik:
    python scrape_debuitenplaats.py              # scrape, sla op in DB
    python scrape_debuitenplaats.py --dry-run    # toon events zonder op te slaan

Gevonden via overleg.md punt 13 ("kleine venues zoeken" — Michiel,
2026-08-21). Server-rendered, geen Playwright nodig: de `/tentoonstellingen`-
listingpagina linkt naar per-expositie-pagina's, elk met een
`<meta name="description">` die het datumbereik in vrije tekst noemt
(geen JSON-LD/gestructureerde datums beschikbaar — zelfde soort CMS-
beperking als eerder bij drenthe.nl gezien).

Twee categorieën NIET meegenomen, bewust, geen aanname:
  - Permanente attracties zonder tijdelijke einddatum ("Museumtuin",
    "Nijsinghhuis") — geen enkel datumpatroon in de tekst, dus simpelweg
    overgeslagen (regex matcht niets).
  - Exposities met alleen een "tot en met"-einddatum en GEEN zichtbare
    startdatum (bv. "Beauty of the Beast", verlengd zonder vermelding van
    de oorspronkelijke startdatum) — zelfde principe als bij drenthe.nl's
    "t/m N maand"-gevallen (overleg.md punt 15): geen startdatum
    verzinnen, dus overgeslagen i.p.v. met een foutieve datum getoond.

Alleen het volledige "Van X t/m Y"-patroon (beide datums bekend, bv. "Into
Nature: Haunted by Waters") wordt meegenomen.
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE      = 'debuitenplaats'
BASE_URL    = 'https://dmdebuitenplaats.nl'
LISTING_URL = f'{BASE_URL}/tentoonstellingen'
VENUE       = 'Drents Museum De Buitenplaats, Eelde'
CITY        = 'Eelde'
PROVINCE    = 'Drenthe'
TODAY       = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)

# "Van 1 augustus t/m 25 oktober" -- jaartal staat er in de praktijk niet
# altijd bij (deze bron noemt het seizoen, niet expliciet het jaartal) --
# huidig jaar aannemen, net als bij andere "geen jaartal genoemd"-bronnen.
RANGE_PAT = re.compile(
    rf'[Vv]an\s+(\d{{1,2}})\s+({MONTH_PAT})\s+t/m\s+(\d{{1,2}})\s+({MONTH_PAT})(?:\s+(\d{{4}}))?',
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def unescape(s: str) -> str:
    return (s.replace('&amp;', '&').replace('&#039;', "'")
             .replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')).strip()


def parse_range(text: str) -> tuple[str, str] | None:
    m = RANGE_PAT.search(text)
    if not m:
        return None
    d1, mo1, d2, mo2, year_str = m.groups()
    year = int(year_str) if year_str else date.today().year
    try:
        start = date(year, MONTHS_NL[mo1], int(d1))
        end = date(year, MONTHS_NL[mo2], int(d2))
    except ValueError:
        return None
    if end < start:
        return None
    return start.isoformat(), end.isoformat()


def find_exhibition_urls() -> list[str]:
    html = fetch(LISTING_URL)
    paths = set(re.findall(r'href="(https://dmdebuitenplaats\.nl/tentoonstellingen/[a-z0-9\-]+)"', html))
    return sorted(paths)


def parse_exhibition(url: str) -> dict | None:
    html = fetch(url)
    title_m = re.search(r'<title>Buitenplaats - ([^<]+)</title>', html)
    if not title_m:
        return None
    title = unescape(title_m.group(1))

    desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if not desc_m:
        return None
    rng = parse_range(unescape(desc_m.group(1)))
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
        urls = find_exhibition_urls()
    except Exception as e:
        print(f"  FOUT bij listingpagina: {e}")
        return 0, 0
    print(f"  {len(urls)} expositie-pagina's gevonden")

    all_events = []
    for url in urls:
        try:
            ev = parse_exhibition(url)
        except Exception as e:
            print(f"  FOUT bij {url}: {e}")
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

    print(f"Scraping dmdebuitenplaats.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
