"""
scrape_geertteis.py — Theater Geert Teis (Stadskanaal)

Gebruik:
    python scrape_geertteis.py              # scrape, sla op in DB
    python scrape_geertteis.py --dry-run    # toon events zonder op te slaan

Gebruikt schema.org itemprop-attributen (startDate) i.p.v. een <time>-tag.
Splitst de pagina per event-kaart (op elke "href=/voorstellingen/..."
voorkomen) i.p.v. één grote regex over de hele pagina — voorkomt dat de
titel/datum van het ene event aan de URL van een ander event gekoppeld raakt.
"""

import urllib.request
import re
import argparse
from events_db import insert_event, log_scrape, init_db

SOURCE   = 'geertteis'
BASE_URL = 'https://www.theatergeertteis.nl/voorstellingen'
VENUE    = 'Geert Teis, Stadskanaal'


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    blocks = re.split(r'(?=<a[^>]+href="/voorstellingen/)', html)

    found = added = 0
    for b in blocks:
        href_m = re.search(r'href="(/voorstellingen/[^"]+)"', b)
        date_m = re.search(r'itemprop="startDate"\s+content="([\d\-T:]+)"', b)
        h3_m = re.search(r'<h3>([^<]+)</h3>', b)
        if not (href_m and date_m and h3_m):
            continue

        found += 1
        ev = {
            'title':  h3_m.group(1).strip(),
            'date':   date_m.group(1)[:10],
            'time':   date_m.group(1)[11:16] or None,
            'venue':  VENUE,
            'url':    'https://www.theatergeertteis.nl' + href_m.group(1),
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
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

    print(f"Scraping Geert Teis [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
