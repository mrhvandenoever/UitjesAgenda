"""
scrape_theaterroden.py — Winsinghhof (Roden) via de eigen website

Gebruik:
    python scrape_theaterroden.py              # scrape, sla op in DB
    python scrape_theaterroden.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — de oude URL (winsinghhof.nl)
gaf een connectiefout, het domein bleek verhuisd naar theaterroden.nl
(bron: `SRC`-sleutel is al `theaterroden`, zie gen_uitjes.py). De site zelf
is gewoon server-rendered HTML met een schoon `event-title`/`event-dates`-
patroon — geen browser nodig. podiuminfo.nl (tip Michiel) gaf hier maar 12
van de ~70 events (dekt alleen concerten, niet het theater/cabaret-
programma dat dit podium vooral doet) — de eigen site is hier dus de
betere bron, in tegenstelling tot Ziggo Dome.
"""

import urllib.request
import re
import html as html_lib
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'theaterroden'
BASE_URL = 'https://theaterroden.nl'
URL      = f'{BASE_URL}/voorstellingen'
VENUE    = 'Winsinghhof, Roden'

ITEM_PATTERN = re.compile(
    r'href="(https://theaterroden\.nl/[^"]+)" class="event-hgroup">'
    r'<h3 class="event-title">([^<]+)</h3>'
    r'(?:<h4 class="event-subtitle">([^<]*)</h4>)?</a>'
    r'<ol class="event-dates"><li><time datetime="([^"]+)"',
    re.S,
)


def fetch() -> str:
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html_text = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html_text)
    print(f"  {len(matches)} events op de voorstellingen-pagina")

    found = added = 0
    all_events = []
    for url, title, subtitle, dt in matches:
        title = html_lib.unescape(title).strip()
        subtitle = html_lib.unescape(subtitle).strip() if subtitle else ''
        full_title = f'{title} - {subtitle}' if subtitle and subtitle != title else title
        iso_date, _, rest = dt.partition(' ')
        if not full_title or not iso_date:
            continue
        found += 1
        ev = {
            'title':  full_title,
            'date':   iso_date,
            'time':   rest[:5] if rest else None,
            'venue':  VENUE,
            'url':    url,
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

    print(f"Scraping Winsinghhof (theaterroden.nl) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
