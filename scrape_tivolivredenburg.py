"""
scrape_tivolivredenburg.py — TivoliVredenburg (Utrecht) via Songkick

Gebruik:
    python scrape_tivolivredenburg.py              # scrape, sla op in DB
    python scrape_tivolivredenburg.py --dry-run    # toon events zonder op te slaan

tivolivredenburg.nl zelf toont een echte Cloudflare bot-challenge
("Just a moment...") — bewust niet omzeild, zie decisions.md. In plaats
daarvan: songkick.com/venues/2360344-tivolivredenburg heeft gewoon
JSON-LD (schema.org MusicEvent) in de ruwe HTML, geen browser nodig.

BEPERKING: Songkick is alleen live-muziek/concerten (geen theater, comedy,
klassiek-op-de-eigen-zalen e.d.) en toont maar de eerstvolgende ~9 shows
(paginering-parameter `?page=N` wordt genegeerd door Songkick zelf) — dus
dit is bewust een gedeeltelijke dekking, geen volledige TivoliVredenburg-
agenda. Beter een deel dan niets; te vergelijken met USVA's ~6/10-dekking.
"""

import urllib.request
import re
import json
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'tivolivredenburg'
URL      = 'https://www.songkick.com/venues/2360344-tivolivredenburg'
VENUE    = 'TivoliVredenburg, Utrecht'

LDJSON_PATTERN = re.compile(r'<script type="application/ld\+json">(\[.*?\])</script>', re.S)


def fetch() -> str:
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    items = []
    for block in LDJSON_PATTERN.findall(html):
        try:
            items.extend(json.loads(block))
        except json.JSONDecodeError:
            continue

    print(f"  {len(items)} MusicEvent-items gevonden op Songkick")

    found = added = 0
    all_events = []
    for item in items:
        if item.get('@type') != 'MusicEvent':
            continue
        title = (item.get('name') or '').replace(' @ TivoliVredenburg', '').strip()
        start = item.get('startDate') or ''
        if not title or not start:
            continue
        iso_date, _, rest = start.partition('T')
        time_str = rest[:5] if rest else None

        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
            'venue':  VENUE,
            'url':    item.get('url'),
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
        else:
            all_events.append(ev)

    if not dry_run:
        if unchanged(SOURCE, all_events):
            log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
            print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
            return found, 0
        for ev in all_events:
            if insert_event(ev):
                added += 1
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping TivoliVredenburg (via Songkick, alleen muziek) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
