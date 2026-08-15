"""
scrape_dedoelen.py — De Doelen (Rotterdam) via headless browser (Playwright)

Gebruik:
    python scrape_dedoelen.py              # scrape, sla op in DB
    python scrape_dedoelen.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md. Eerdere check gebruikte de
verkeerde URL (`/programma`, geeft een 404) — de echte agenda-URL is
`/nl/agenda`, zelfde soort fout als bij Effenaar/Winsinghhof. Achtste
Playwright-scraper. `eventCard`-grid met titel, subtitel, datum (mét
2-cijferig jaartal, geen inferentie nodig), tijd en zaal.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'dedoelen'
BASE_URL = 'https://www.dedoelen.nl'
URL      = f'{BASE_URL}/nl/agenda'
VENUE    = 'De Doelen, Rotterdam'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'class="desc" href="(/nl/agenda/[^"]+)">\s*'
    r'<h3 class="title">([^<]+)</h3>\s*'
    r'(?:<div class="subtitle">([^<]*)</div>)?.*?'
    r'<span class="start">\s*\w+ (\d{1,2}) (\w+) (\d{2})\s*</span>\s*'
    r'(?:<span class="time">\s*([\d:]*)\s*</span>)?.*?'
    r'<div class="venue">\s*([^<]*?)\s*</div>',
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
        page.wait_for_timeout(2500)
        html = page.content()
        browser.close()
        return html


def parse_date(day: int, month_str: str, year_2digit: str) -> str | None:
    month = NL_MONTHS.get(month_str.lower())
    if not month:
        return None
    try:
        return date(2000 + int(year_2digit), month, day).isoformat()
    except ValueError:
        return None


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html_text = fetch_rendered_html()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    matches = ITEM_PATTERN.findall(html_text)
    print(f"  {len(matches)} events op de gerenderde agenda-pagina")

    found = added = 0
    all_events = []
    for rel_url, title, subtitle, day, month_str, year, time_str, venue_name in matches:
        iso_date = parse_date(int(day), month_str, year)
        title = html_lib.unescape(title).strip()
        subtitle = html_lib.unescape(subtitle).strip() if subtitle else ''
        full_title = f'{title} - {subtitle}' if subtitle else title
        if not iso_date or not full_title:
            continue
        venue_name = venue_name.strip()
        found += 1
        ev = {
            'title':  full_title,
            'date':   iso_date,
            'time':   time_str.strip() or None,
            'venue':  f'{venue_name}, Rotterdam' if venue_name else VENUE,
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

    print(f"Scraping De Doelen (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
