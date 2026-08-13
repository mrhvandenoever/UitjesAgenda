"""
scrape_posthuistheater.py — Posthuis Theater (Heerenveen)

Gebruik:
    python scrape_posthuistheater.py              # scrape, sla op in DB
    python scrape_posthuistheater.py --dry-run    # toon events zonder op te slaan

Statische HTML met data-attributen per event (data-production-title,
data-event-start) — geen JS nodig. Paginering via ?page=N, stopt zodra een
pagina niets oplevert. Vereist een volledige browser-UA (simpele bot-UA
geeft 403).
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'posthuistheater'
BASE_URL = 'https://www.posthuistheater.nl/agenda/'
VENUE    = 'Posthuis Theater, Heerenveen'
UA       = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def fetch(page: int) -> str:
    url = BASE_URL if page == 1 else f'{BASE_URL}?page={page}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    seen = set()

    for page in range(1, 10):
        try:
            html = fetch(page)
        except Exception as e:
            print(f"  Pagina {page} fout: {e}")
            break

        pairs = re.findall(r'data-production-title="([^"]+)"[^>]*data-event-start="([^"]+)"', html)
        pairs += [(t, d) for d, t in re.findall(r'data-event-start="([^"]+)"[^>]*data-production-title="([^"]+)"', html)]
        if not pairs:
            break

        for title, dt_str in pairs:
            key = (title, dt_str)
            if key in seen:
                continue
            seen.add(key)

            m = re.match(r'(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})', dt_str)
            if not m:
                continue
            found += 1
            ev = {
                'title':  title.strip(),
                'date':   m.group(1),
                'time':   m.group(2),
                'venue':  VENUE,
                'url':    BASE_URL,
                'source': SOURCE,
            }
            if dry_run:
                print(f"    [{ev['date']} {ev['time']}] {ev['title']}")
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

    print(f"Scraping Posthuis Theater [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
