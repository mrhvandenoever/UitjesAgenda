"""
scrape_gelredome.py — GelreDome (Arnhem) via headless browser (Playwright)

Gebruik:
    python scrape_gelredome.py              # scrape, sla op in DB
    python scrape_gelredome.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — Webflow-site (net als
scrape_neushoorn.py) met een client-side gevulde CMS-collectie. Tweede
Playwright-scraper, zie ARCHITECTURE.md §Playwright-scrapers.

Agenda is een mix van Vitesse-thuiswedstrijden en concerten/evenementen
(Hard Bass, Snuffelmarkt, Mega Piraten Festijn, ...) — allemaal via
dezelfde kaarten-grid, geen aparte behandeling nodig. Paginering via
Webflow's eigen `?<hash>_page=N`-query-param (client-side, Playwright
voert de JS uit dus dit werkt gewoon door de URL te bezoeken) — we volgen
de "Volgende"-link net zo lang als die bestaat.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'gelredome'
BASE_URL = 'https://www.gelredome.nl'
START_URL = f'{BASE_URL}/agenda'
VENUE    = 'GelreDome, Arnhem'

NL_MONTHS = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
ITEM_PATTERN = re.compile(
    r'cards-overview-heading text-style-3lines">([^<]+)</div></div>'
    r'<div class="label-group"><div class="label"><div>(\d+)</div>'
    r'<div class="date-transl">([a-zA-Z]+)</div><div>(\d{4})</div></div>'
    r'<div class="label"><div>([^<]*)</div></div></div>'
    r'.{0,300}?href="(/evenement/[^"]+)"',
    re.S,
)
NEXT_PAGE_PATTERN = re.compile(r'href="(\?[a-z0-9]+_page=\d+)" aria-label="Next Page"')


def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        pages_html = []
        current_url = url
        for _ in range(10):  # veiligheidslimiet
            page.goto(current_url, timeout=30000, wait_until='networkidle')
            page.wait_for_timeout(1500)
            html = page.content()
            pages_html.append(html)
            m = NEXT_PAGE_PATTERN.search(html)
            if not m:
                break
            current_url = f'{START_URL}{m.group(1)}'
        browser.close()
        return '\n'.join(pages_html)


def parse_date(day: int, month_name: str, year: int) -> str | None:
    month = NL_MONTHS.get(month_name.lower())
    if not month:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch_rendered_html(START_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html)
    print(f"  {len(matches)} events op de gerenderde agenda (alle pagina's)")

    found = added = 0
    all_events = []
    for title, day, month_name, year, time_str, rel_url in matches:
        iso_date = parse_date(int(day), month_name, int(year))
        title = title.strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str.strip() or None,
            'venue':  VENUE,
            'url':    f'{BASE_URL}{rel_url}',
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

    print(f"Scraping GelreDome (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
