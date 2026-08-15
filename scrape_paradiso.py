"""
scrape_paradiso.py — Paradiso (Amsterdam) via headless browser (Playwright)

Gebruik:
    python scrape_paradiso.py              # scrape, sla op in DB
    python scrape_paradiso.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" — eerdere check vond geen agenda-link op de
homepage (nav is client-side). De juiste URL bleek een specifieke
"landing"-pagina: /landing/concertagenda-paradiso/2069817 (gevonden via
websearch, niet vanzelfsprekend vanaf de homepage te vinden). Negende
Playwright-scraper. Chakra UI (React) — de CSS-classes zijn auto-
gegenereerde hashes die bij een rebuild kunnen wijzigen, dus de regex
matcht op HTML-tagvolgorde i.p.v. specifieke class-namen (iets robuuster,
maar nog steeds kwetsbaar voor structuurwijzigingen).

Paradiso programmeert ook op andere locaties (Tolhuistuin e.d., staat dan
in de subtitel) — we behandelen alles gewoon als Paradiso-events, net als
de rest van het project bij podia die op meerdere zalen programmeren.
"Uitverkocht"/"Wachtlijst" i.p.v. een tijd komt voor — dan wordt time=None.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'paradiso'
BASE_URL = 'https://www.paradiso.nl'
URL      = f'{BASE_URL}/landing/concertagenda-paradiso/2069817'
VENUE    = 'Paradiso, Amsterdam'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'href="(/nl/programma/[^"]+)"><div[^>]*><div[^>]*><p[^>]*>\w+ (\d{1,2}) (\w+)</p>'
    r'<div[^>]*><div[^>]*><h3[^>]*>([^<]+)</h3>.*?'
    r'</div></div></div><p[^>]*>([^<]*)</p>',
    re.S,
)
TIME_PATTERN = re.compile(r'^\d{1,2}:\d{2}$')


def fetch_rendered_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page.goto(URL, timeout=30000, wait_until='load')
        page.wait_for_timeout(2500)
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
    print(f"  {len(matches)} events op de gerenderde concertagenda")

    found = added = 0
    all_events = []
    for rel_url, day, month_str, title, status_or_time in matches:
        iso_date = parse_date(int(day), month_str)
        title = html_lib.unescape(title).strip()
        if not iso_date or not title:
            continue
        time_str = status_or_time.strip()
        time_str = time_str if TIME_PATTERN.match(time_str) else None

        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   time_str,
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

    print(f"Scraping Paradiso (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
