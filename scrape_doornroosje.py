"""
scrape_doornroosje.py — Doornroosje (Nijmegen) via headless browser (Playwright)

Gebruik:
    python scrape_doornroosje.py              # scrape, sla op in DB
    python scrape_doornroosje.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md ("WordPress bevestigd, geen
bruikbaar events-type via REST"). De programma-pagina zelf rendert een
`c-program__item`-lijst zodra Playwright de JS uitvoert — geen browser-
onafhankelijke API gevonden, dus toch een Playwright-scraper (zevende).

Meerdere shows op dezelfde dag delen één datum-blok: het eerste item van
die dag heeft de datum, de volgende (`c-program__item--samedate`) hebben
een leeg datum-blok — de laatst geziene datum wordt dan hergebruikt.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE = 'doornroosje'
URL    = 'https://www.doornroosje.nl/programma'
VENUE  = 'Doornroosje, Nijmegen'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'href="(https://www\.doornroosje\.nl/event/[^"]+)" class="c-program__item[^"]*">'
    r'<div class="c-program__date">(.*?)</div>'
    r'<div class="c-program__content"><h3 class="c-program__title[^"]*"><span class="c-program__title--main">([^<]+)</span>'
    r'(?:<span class="c-program__title--small">([^<]*)</span>)?',
    re.S,
)
DATE_SPAN_PATTERN = re.compile(r'<span>([^<]+)</span>')


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
    month = NL_MONTHS.get(month_str.lower())
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
        html_text = fetch_rendered_html()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html_text)
    print(f"  {len(matches)} events op de gerenderde programma-pagina")

    found = added = 0
    all_events = []
    last_date = None
    for url, date_html, main, small in matches:
        spans = DATE_SPAN_PATTERN.findall(date_html)
        if len(spans) >= 3:
            iso_date = parse_date(int(spans[1]), spans[2])
            last_date = iso_date
        else:
            iso_date = last_date  # "samedate"-item, deelt de vorige datum

        main = html_lib.unescape(main).strip()
        small = html_lib.unescape(small).strip() if small else ''
        title = f'{main} - {small}' if small else main
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

    print(f"Scraping Doornroosje (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
