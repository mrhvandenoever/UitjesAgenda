"""
scrape_neushoorn.py — Neushoorn (Leeuwarden) via headless browser (Playwright)

Gebruik:
    python scrape_neushoorn.py              # scrape, sla op in DB
    python scrape_neushoorn.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — bevestigde Webflow-SPA, de
programma-lijst wordt volledig client-side gevuld (Finsweet CMS-filter),
geen verborgen JSON-API gevonden. Dit is de eerste Playwright-scraper van
het project (zie ARCHITECTURE.md §Playwright-scrapers, decisions.md
2026-08-15): een headless Chromium rendert de pagina, daarna regex op de
resulterende DOM-HTML — zelfde parsing-stijl als de andere scrapers, alleen
het ophalen gaat via een browser i.p.v. urllib.

Datumtekst heeft geen jaartal ("15 Aug") — jaartal afgeleid zoals bij
scrape_dorpshuisannen.py (rollen naar volgend jaar als de datum al voorbij
is). Onderliggend ticketingplatform is "Stager" (neushoorn.stager.co) —
zelfde platform als Vera, maar de programma-pagina zelf (niet Stager's
eigen shop-domein) bleek de simpelste bron.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'neushoorn'
URL      = 'https://neushoorn.nl/programma'
VENUE    = 'Neushoorn, Leeuwarden'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'program_row w-dyn-item".*?'
    r'program_date-wrapper">'
    r'<div class="program_day">[^<]*</div>'
    r'<div class="program_date">(\d{1,2}) (\w+)</div>'
    r'<div class="program_time">([^<]*)</div>'
    r'</div><h3 class="program_title">([^<]+)</h3>',
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


def parse_date(day: int, month_str: str) -> str | None:
    month = NL_MONTHS.get(month_str.lower()[:3])
    if not month:
        return None
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
    for day, month_str, time_str, title in matches:
        iso_date = parse_date(int(day), month_str)
        title = title.strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str.strip() or None,
            'venue':  VENUE,
            'url':    URL,
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

    print(f"Scraping Neushoorn (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
