"""
scrape_effenaar.py — Effenaar (Eindhoven) via headless browser (Playwright)

Gebruik:
    python scrape_effenaar.py              # scrape, sla op in DB
    python scrape_effenaar.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md. Eerdere pogingen gebruikten de
verkeerde URL (`/programma`, geeft een 404 die zelf weer CMS-content-block-
metadata bevat — vandaar de eerdere conclusie "150 datum-strings maar bleek
CMS-metadata, geen events"). De juiste URL is `/agenda`; daar rendert
Playwright een gewoon `agenda-card`-grid met titel, subtitel, datum (mét
jaartal, dus geen jaartal-inferentie nodig) en zaal. Vierde Playwright-
scraper.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'effenaar'
BASE_URL = 'https://www.effenaar.nl'
URL      = f'{BASE_URL}/agenda'
VENUE    = 'Effenaar, Eindhoven'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'agenda-card" href="(/agenda/[^"]+)">.*?'
    r'card-title">([^<]+)</h3>.*?'
    r'card-info-date">\w+ (\d{1,2}) (\w+) (\d{4})</div>'
    r'(?:<div class="card-info-location">.*?>([^<]+)</div>)?',
    re.S,
)


def fetch_rendered_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page.goto(URL, timeout=45000, wait_until='networkidle')
        page.wait_for_timeout(2500)
        html = page.content()
        browser.close()
        return html


def parse_date(day: int, month_str: str, year: int) -> str | None:
    month = NL_MONTHS.get(month_str.lower())
    if not month:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch_rendered_html()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html)
    print(f"  {len(matches)} events op de gerenderde agenda-pagina")

    found = added = 0
    all_events = []
    for rel_url, title, day, month_str, year, location in matches:
        iso_date = parse_date(int(day), month_str, int(year))
        title = title.strip()
        if not iso_date or not title:
            continue
        found += 1
        venue = f'{location.strip()}, Eindhoven (Effenaar)' if location and location.strip() else VENUE
        ev = {
            'title':  title,
            'date':   iso_date,
            'venue':  venue,
            'url':    f'{BASE_URL}{rel_url}',
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']}] {ev['title']} @ {ev['venue']}")
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

    print(f"Scraping Effenaar (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
