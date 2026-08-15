"""
scrape_vera.py — Vera (Groningen) via headless browser (Playwright)

Gebruik:
    python scrape_vera.py              # scrape, sla op in DB
    python scrape_vera.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" — eerder onderzocht en bewust NIET gebouwd
(zie decisions.md 2026-08-15): de programma-pagina toont maar ~20 van de
~70 events server-side, de rest zit achter een infinite-scroll die via
`admin-ajax.php` (`action=renderProgramme`) loopt. Een curl-POST naar dat
endpoint gaf steeds een lege 200-respons — leek op een Cloudflare-blokkade.

Bleek geen blokkade te zijn: het probleem was dat curl geen scroll-events
kan simuleren. Playwright (een échte browser) die gewoon omlaag scrollt op
de programma-pagina laadt de infinite-scroll netjes — 70/70 events, geen
enkele AJAX-call handmatig nagebouwd. Elfde Playwright-scraper.

Datum in het Engels ("Saturday 15 August", soms twee spaties bij
eencijferige dagen) — jaartal afgeleid zoals bij scrape_dorpshuisannen.py.
Sommige events hebben een `pretitle` (bv. "SOLD OUT", "MINORIE PRESENTS")
vóór de datum — genegeerd, telt niet mee voor titel/datum.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE = 'vera'
URL    = 'https://www.vera-groningen.nl/programma/'
VENUE  = 'Vera, Groningen'

EN_MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}
ITEM_PATTERN = re.compile(
    r'href="(https://www\.vera-groningen\.nl/\?post_type=events[^"]+)"(?:.*?</h4>)?'
    r'.*?class="date">(?:.*?</h4>)?\s*\w+\s+(\d{1,2})\s+(\w+)\s*</div>'
    r'.*?<h3 class="artist[^"]*">([^<]+)',
    re.S,
)


def fetch_rendered_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page.goto(URL, timeout=30000, wait_until='load')
        page.wait_for_timeout(2000)

        stall = 0
        last_count = 0
        for _ in range(20):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1000)
            n = len(page.locator('a.event-link').all())
            if n == last_count:
                stall += 1
                if stall >= 3:
                    break
            else:
                stall = 0
            last_count = n

        html = page.content()
        browser.close()
        return html


def parse_date(day: int, month_str: str) -> str | None:
    month = EN_MONTHS.get(month_str.lower())
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

    found = added = 0
    all_events = []
    for block in html_text.split('event-wrapper')[1:]:
        m = ITEM_PATTERN.search(block)
        if not m:
            continue
        url, day, month_str, title = m.groups()
        iso_date = parse_date(int(day), month_str)
        title = html_lib.unescape(title).strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'venue':  VENUE,
            'url':    html_lib.unescape(url),
            'source': SOURCE,
        }
        if dry_run:
            print(f"    [{ev['date']}] {ev['title']}")
        else:
            all_events.append(ev)

    print(f"  {found} events na scrollen door de infinite-scroll-lijst")

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

    print(f"Scraping Vera (Playwright, headless, scroll-simulatie) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
