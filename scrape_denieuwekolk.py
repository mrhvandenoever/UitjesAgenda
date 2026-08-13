"""
scrape_denieuwekolk.py — De Nieuwe Kolk (Assen)

Gebruik:
    python scrape_denieuwekolk.py              # scrape, sla op in DB
    python scrape_denieuwekolk.py --dry-run    # toon events zonder op te slaan

De Nieuwe Kolk combineert bibliotheek (/bieb/), bioscoop (/bios/) en theater
(/theater/) op één agenda — we nemen alleen /theater/ en /bios/ mee, de
/bieb/-activiteiten (taalcafé, adviesplein, cursussen) zijn geen "uitjes".

Domein is denieuwekolk.nl, NIET nieuwekolk.nl. Vereist header HX-Request:
true en een volledige browser-UA. Per maand een aparte fetch
(?load_from=YYYY-MM-01), elke dag-groep bevat de link dubbel (mobiel+desktop
layout) — dedupliceren op (href, dag).
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'denieuwekolk.nl'
BASE_URL = 'https://denieuwekolk.nl/agenda'
DOMAIN   = 'https://denieuwekolk.nl'
VENUE    = 'De Nieuwe Kolk, Assen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
KEEP_PREFIXES = ('/theater/agenda/', '/bios/agenda/')


def unescape(s: str) -> str:
    return (s.replace('&#39;', "'").replace('&amp;', '&').replace('&quot;', '"')
             .replace('&lt;', '<').replace('&gt;', '>')).strip()


def fetch(load_from: str) -> str:
    url = f'{BASE_URL}?_dnk_fragment=agenda&d=asc&load_from={load_from}&sort=starts_at'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'HX-Request': 'true'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def month_starts(n: int = 14):
    today = date.today()
    y, m = today.year, today.month
    for _ in range(n):
        yield f'{y:04d}-{m:02d}-01'
        m += 1
        if m > 12:
            m = 1
            y += 1


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    seen = set()

    for load_from in month_starts():
        try:
            html = fetch(load_from)
        except Exception as e:
            print(f"  {load_from} fout: {e}")
            continue

        blocks = re.split(r'(?=id="day-\d{4}-\d{2}-\d{2}")', html)
        for b in blocks:
            dm = re.match(r'id="day-(\d{4}-\d{2}-\d{2})"', b)
            if not dm:
                continue
            dag = dm.group(1)
            for href, title in re.findall(
                r'href="([^"]+)"[^>]*aria-label="Meer info over ([^"]+)"', b, re.S
            ):
                if not href.startswith(KEEP_PREFIXES):
                    continue
                key = (href, dag)
                if key in seen:
                    continue
                seen.add(key)

                found += 1
                ev = {
                    'title':  unescape(title),
                    'date':   dag,
                    'venue':  VENUE,
                    'url':    DOMAIN + href,
                    'source': SOURCE,
                }
                if dry_run:
                    print(f"    [{ev['date']}] {ev['title']}")
                else:
                    if insert_event(ev):
                        added += 1

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping De Nieuwe Kolk [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
