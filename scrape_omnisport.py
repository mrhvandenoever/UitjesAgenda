"""
scrape_omnisport.py — Omnisport Apeldoorn (evenementenagenda)

Gebruik:
    python scrape_omnisport.py              # scrape, sla op in DB
    python scrape_omnisport.py --dry-run    # toon events zonder op te slaan

Gevonden via overleg.md punt 5 ("nationale sportteams" — Michiel wees op de
oefeninterlands van de volleybal-Oranje-teams; Omnisport Apeldoorn is een
vaste VNL-speelstad). In plaats van een scraper voor de nationale bonden zelf
(bleek geen bruikbare/scrapebare bron te hebben, zie overleg.md) wordt de
VENUE gevolgd: gewoon de hele agenda van Omnisport meenemen, ongeacht sport.

`omnisport.nl/agenda-omnisport/` is volledig server-rendered met
`data-events-per-page="-1"` — alle events staan al in de eerste page-load,
geen paginering nodig.

Datumformaat bevat altijd een jaartal, maar in 3 varianten:
  "5 september 2026"                  (1 dag)
  "13 - 14 oktober 2026"               (bereik, zelfde maand)
  "29 oktober - 1 november 2026"       (bereik, andere maand)
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE      = 'omnisport'
BASE_URL    = 'https://omnisport.nl'
LISTING_URL = f'{BASE_URL}/agenda-omnisport/'
VENUE       = 'Omnisport Apeldoorn'
CITY        = 'Apeldoorn'
PROVINCE    = 'Gelderland'
TODAY       = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)

# Meest specifieke patroon eerst: bereik over 2 maanden, dan bereik binnen 1
# maand, dan losse dag. Jaartal staat er bij deze bron altijd bij.
RANGE_2MONTH_PAT = re.compile(
    rf'(\d{{1,2}})\s+({MONTH_PAT})\s*-\s*(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})', re.I)
RANGE_1MONTH_PAT = re.compile(
    rf'(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})', re.I)
SINGLE_PAT = re.compile(
    rf'(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})', re.I)

ITEM_PAT = re.compile(
    r'<a\s+href="([^"]+)"\s+class="c-card"[^>]*>.*?'
    r'<h5 class="c-card__date">([^<]+)</h5>\s*'
    r'<p class="c-card__tax">([^<]*)</p>.*?'
    r'<h3 class="c-card__title">([^<]+)</h3>',
    re.S,
)


def unescape(s: str) -> str:
    return (s.replace('&amp;', '&').replace('&#8217;', "'").replace('&#8216;', "'")
             .replace('&#8220;', '"').replace('&#8221;', '"')
             .replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')).strip()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def parse_range(text: str) -> tuple[str, str] | None:
    m = RANGE_2MONTH_PAT.search(text)
    if m:
        d1, mo1, d2, mo2, y = m.groups()
        try:
            start = date(int(y), MONTHS_NL[mo1.lower()], int(d1))
            end = date(int(y), MONTHS_NL[mo2.lower()], int(d2))
        except ValueError:
            return None
        return start.isoformat(), end.isoformat()

    m = RANGE_1MONTH_PAT.search(text)
    if m:
        d1, d2, mo, y = m.groups()
        try:
            start = date(int(y), MONTHS_NL[mo.lower()], int(d1))
            end = date(int(y), MONTHS_NL[mo.lower()], int(d2))
        except ValueError:
            return None
        return start.isoformat(), end.isoformat()

    m = SINGLE_PAT.search(text)
    if m:
        d1, mo, y = m.groups()
        try:
            start = date(int(y), MONTHS_NL[mo.lower()], int(d1))
        except ValueError:
            return None
        return start.isoformat(), start.isoformat()

    return None


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        html = fetch(LISTING_URL)
    except Exception as e:
        print(f"  FOUT bij listingpagina: {e}")
        return 0, 0

    all_events = []
    seen_urls = set()
    for m in ITEM_PAT.finditer(html):
        url, date_text, category, title = m.groups()
        if url in seen_urls:
            continue
        seen_urls.add(url)

        rng = parse_range(date_text.strip())
        if not rng:
            continue
        start_iso, end_iso = rng
        if end_iso < TODAY:
            continue

        ev = {
            'title':    unescape(title),
            'date':     start_iso,
            'venue':    VENUE,
            'city':     CITY,
            'province': PROVINCE,
            'source':   SOURCE,
            'url':      url if url.startswith('http') else BASE_URL + url,
        }
        if category.lower().strip() in ('sport evenement', 'training'):
            ev['cats'] = ['sport']
        if end_iso != start_iso:
            ev['date_end'] = end_iso
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

    print(f"Scraping omnisport.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
