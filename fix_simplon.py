"""
scrape_simplon.py — Simplon (Groningen) via headless browser (Playwright)

Gebruik:
    python scrape_simplon.py              # scrape, sla op in DB
    python scrape_simplon.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — WordPress-site zonder
REST-exposed events (zie ook Vera, dezelfde situatie), programma-pagina zelf
is client-rendered. Onderliggend ticketingplatform is "Stager" (net als
Vera), maar Simplon's eigen programma-pagina heeft — anders dan Vera — een
simpel, direct regex-baar DOM-patroon (`block--event`/`block__date`/
`block__title`) zodra Playwright de pagina gerenderd heeft, zonder Vera's
AJAX-paginering-probleem. Derde Playwright-scraper.

Datumtekst zonder jaartal ("vr 16.10" = dag.maand) — jaartal afgeleid zoals
bij scrape_dorpshuisannen.py.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE = 'simplon'
URL    = 'https://simplon.nl/programma/'
VENUE  = 'Simplon, Groningen'

ITEM_PATTERN = re.compile(
    r'block--event.*?href="(https://simplon\.nl/events/[^"]+)" class="block__content">'
    r'<p class="block__date">\w+ (\d{1,2})\.(\d{1,2})</p>.*?'
    r'<h2 class="block__title">([^<]+)</h2>',
    re.S,
)


def fetch_rendered_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page.goto(URL, timeout=30000, wait_until='networkidle')
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html


def parse_date(day: int, month: int) -> str | None:
    today = date.today()
    try:
        d = date(today.year, month, day)
    except ValueError:
        return None
    if d < today:
        try:
            d = date(today.year + 1, month, day)
        except ValueError:
            return None
    return d.isoformat()


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch_rendered_html()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html)
    print(f"  {len(matches)} events op de gerenderde programma-pagina")

    found = added = 0
    all_events = []
    for url, day, month, title in matches:
        iso_date = parse_date(int(day), int(month))
        title = title.strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
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

    print(f"Scraping Simplon (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
