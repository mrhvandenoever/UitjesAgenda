"""
scrape_usva.py — USVA (Groningen) programma

Gebruik:
    python scrape_usva.py              # scrape, sla op in DB
    python scrape_usva.py --dry-run    # toon events zonder op te slaan

Elementor-WordPress-pagina zonder machine-leesbare datums (geen <time>/
itemprop) — titels en datums staan als losse tekstblokken in dezelfde
volgorde. Positionele koppeling (titel N hoort bij datum N); jaar niet in de
tekst, wordt afgeleid (rollen naar volgend jaar als de datum al voorbij is).
Klein (~10 events), niet elk event heeft een herkenbaar "dag D maand"-datum
(bv. events met een lopende periode) — die worden overgeslagen.
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'usva'
BASE_URL = 'https://www.usva.nl/programma/'
VENUE    = 'USVA, Groningen'

NL_MONTHS = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}


def unescape(s: str) -> str:
    return (s.replace('&#8211;', '–').replace('&amp;', '&').replace('&#039;', "'")
             .replace('&quot;', '"')).strip()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def parse_date(dag_tekst: str) -> str | None:
    m = re.search(r'(\d{1,2})\s+(\w+)', dag_tekst)
    if not m:
        return None
    month = NL_MONTHS.get(m.group(2).lower())
    if not month:
        return None
    day = int(m.group(1))
    today = date.today()
    year = today.year
    try:
        d = date(year, month, day)
    except ValueError:
        return None
    if d < today:
        try:
            d = date(year + 1, month, day)
        except ValueError:
            return None
    return d.isoformat()


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    titles = re.findall(
        r'<h2 class="elementor-heading-title[^"]*"><a href="([^"]+)">([^<]+)</a></h2>', html
    )
    dates = re.findall(
        r'elementor-post-info__item--type-custom">\s*(\w+dag \d{1,2} \w+)\s*</span>', html
    )

    found = added = 0
    all_events = []
    for (url, raw_title), dag_tekst in zip(titles, dates):
        iso_date = parse_date(dag_tekst)
        if not iso_date:
            continue
        found += 1
        ev = {
            'title':  unescape(raw_title),
            'date':   iso_date,
            'venue':  VENUE,
            'url':    url,
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']}] {ev['title']}")
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

    print(f"Scraping USVA [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
