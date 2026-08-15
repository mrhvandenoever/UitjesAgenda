"""
scrape_concertgebouw.py — Het Concertgebouw (Amsterdam) via headless
browser (Playwright)

Gebruik:
    python scrape_concertgebouw.py              # scrape, sla op in DB
    python scrape_concertgebouw.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" — eerdere check keek op de homepage (geen
agenda-link zichtbaar, nav is client-side). De juiste URL is
/concerten-en-tickets (tip Michiel). Vue.js-app, events gegroepeerd per
dag (`c-event-overview-list-item-day`-blokken, elk met een `<h3>`-datumkop
zonder jaartal + één of meer event-`<article>`s). Tiende Playwright-
scraper. Paginering via `?page=N` — Michiel wees erop dat er ~39 pagina's
zijn (~700 concerten/jaar), dus we lopen door tot een lege pagina.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'concertgebouw'
BASE_URL = 'https://www.concertgebouw.nl'
LIST_URL = f'{BASE_URL}/concerten-en-tickets'
VENUE    = 'Concertgebouw, Amsterdam'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
DAY_TITLE_PATTERN = re.compile(r'c-event-overview-list-item-day__title"[^>]*>([^<]+)</h3>')
ITEM_PATTERN = re.compile(
    r'href="(/concerten/[^"]+)"[^>]*>.*?c-content__title[^"]*"[^>]*>\s*([^<]+?)\s*</h3>',
    re.S,
)
MAX_PAGES = 60  # veiligheidslimiet, ruim boven de ~39 die Michiel zag


def fetch_all_pages() -> list[str]:
    """Eén browser-instance voor alle pagina's (i.p.v. per pagina een nieuwe
    Chromium starten — dat zou bij ~39 pagina's onnodig traag zijn)."""
    pages_html = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page_num = 0
        while page_num < MAX_PAGES:
            url = LIST_URL + (f'?page={page_num}' if page_num else '')
            page.goto(url, timeout=30000, wait_until='load')
            page.wait_for_timeout(1500)
            html = page.content()
            if not extract_events(html):
                break
            pages_html.append(html)
            page_num += 1
        browser.close()
    return pages_html


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


def extract_events(html_text: str) -> list[tuple[str, str, str]]:
    """-> lijst van (rel_url, titel, datumtekst-zonder-jaartal)."""
    results = []
    for block in html_text.split('class="c-event-overview-list-item-day"')[1:]:
        day_m = DAY_TITLE_PATTERN.search(block)
        if not day_m:
            continue
        date_text = day_m.group(1).strip()
        for rel_url, title in ITEM_PATTERN.findall(block):
            results.append((rel_url, title, date_text))
    return results


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        pages_html = fetch_all_pages()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    all_items = []
    for html_text in pages_html:
        all_items.extend(extract_events(html_text))

    print(f"  {len(all_items)} events over {len(pages_html)} pagina's")

    found = added = 0
    all_events = []
    for rel_url, title, date_text in all_items:
        m = re.match(r'\w+ (\d{1,2}) (\w+)', date_text)
        if not m:
            continue
        iso_date = parse_date(int(m.group(1)), m.group(2))
        title = html_lib.unescape(title).strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'venue':  VENUE,
            'url':    f'{BASE_URL}{rel_url}',
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

    print(f"Scraping Concertgebouw (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
