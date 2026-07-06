"""
scrape_naarzuidlaren.py — scrape naarzuidlaren.nl/evenementen/

WordPress/GeoDirectory site met lokale Zuidlaren evenementen.
Klein (~5 events), maar de enige scrapbare bron voor events als
Muzieknacht Zuidlaren, Berend Botje Festival, Vossenjacht.

Gebruik:
    python scrape_naarzuidlaren.py              # scrape, sla op in DB
    python scrape_naarzuidlaren.py --dry-run    # toon zonder op te slaan
"""

import urllib.request
import ssl
import re
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SOURCE   = 'drenthe.nl'   # valt onder Drenthe provincie-filter
PROVINCE = 'Drenthe'
BASE_URL = 'https://naarzuidlaren.nl/evenementen/'
TODAY    = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4,
    'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}

# Events die we overslaan (trainingen, niet-publieksevents)
SKIP_WORDS = {'beginnerscursus', 'training', 'cursus', 'workshop', 'vergadering'}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def parse_date(date_str: str) -> str | None:
    """Parse '22 augustus 2026' → '2026-08-22'."""
    s = date_str.strip().lower()
    m = re.search(
        r'(\d{1,2})\s+'
        r'(januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)\s+(\d{4})',
        s
    )
    if not m:
        return None
    try:
        d = date(int(m.group(3)), MONTHS_NL[m.group(2)], int(m.group(1)))
        return d.isoformat() if d.isoformat() >= TODAY else None
    except ValueError:
        return None


def genre_from_title(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ('festival', 'feest', 'markt', 'kermis')): return 'festival'
    if any(w in t for w in ('concert', 'muziek', 'dance', 'muzieknacht')): return 'pop'
    if any(w in t for w in ('theater', 'voorstelling', 'toneel')): return 'theater'
    return 'overig'


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0

    print(f'  Ophalen {BASE_URL}...', end=' ', flush=True)
    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f'FOUT: {e}')
        return 0, 0

    # Haal event-links + titels op
    # Patroon: entry-title anchor
    entries = re.findall(
        r'class="[^"]*entry-title[^"]*"[^>]*>.*?'
        r'<a[^>]*href="(https://naarzuidlaren\.nl/evenementen/[^"]+)"[^>]*>([^<]+)</a>',
        html, re.DOTALL
    )

    # Haal alle datums op uit de pagina voor koppeling
    all_dates = re.findall(
        r'(\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)\s+\d{4})',
        html, re.IGNORECASE
    )

    print(f'{len(entries)} events gevonden (listing pagina)')

    # Voor elke event: bezoek detailpagina voor betrouwbare datum
    for idx, (url, title) in enumerate(entries):
        title = title.strip()

        if any(w in title.lower() for w in SKIP_WORDS):
            continue

        # Zoek datum in de context rond deze titel op de listingpagina
        title_idx = html.find(title[:20])
        chunk = html[max(0, title_idx):title_idx + 600] if title_idx >= 0 else ''
        chunk_dates = re.findall(
            r'(\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|'
            r'september|oktober|november|december)\s+\d{4})',
            chunk, re.IGNORECASE
        )

        date_str = chunk_dates[0] if chunk_dates else ''
        parsed = parse_date(date_str) if date_str else None

        # Als geen datum gevonden, bezoek detailpagina
        if not parsed:
            try:
                detail_html = fetch(url)
                detail_dates = re.findall(
                    r'(\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|'
                    r'september|oktober|november|december)\s+\d{4})',
                    detail_html, re.IGNORECASE
                )
                parsed = parse_date(detail_dates[0]) if detail_dates else None
            except Exception:
                pass

        if not parsed:
            if dry_run:
                print(f'    [geen datum] {title}')
            continue

        found += 1
        genre = genre_from_title(title)

        if dry_run:
            print(f'    [{parsed}] {genre:10s} {title} ({PROVINCE})')
        else:
            if insert_event({
                'title':    title,
                'date':     parsed,
                'city':     'Zuidlaren',
                'province': PROVINCE,
                'genre':    genre,
                'source':   SOURCE,
                'url':      url,
            }):
                added += 1

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f'✓ Klaar: {found} gevonden, {added} nieuw in DB')
    else:
        print(f'\nDry-run: {found} events')

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(f'Scraping naarzuidlaren.nl [{"dry-run" if args.dry_run else "live"}]...')
    scrape(dry_run=args.dry_run)
