"""
scrape_grandtheatregroningen.py — Grand Theatre (Groningen) via headless
browser (Playwright)

Gebruik:
    python scrape_grandtheatregroningen.py              # scrape, sla op in DB
    python scrape_grandtheatregroningen.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md ("innerText-parsing nodig, geen
bruikbare CSS-classes"). Klopt gedeeltelijk: data-attributen ontbreken
inderdaad, maar de DOM-structuur zelf is wel consistent genoeg voor regex —
elk event zit in een `<li class="event-container">`-blok met een
`overlay-link` (echte, soms externe URL — een deel van het programma is
"op locatie" bij het Noorderzon-festival) en één of meer `<h1>wd DD mmm</h1>`
speelmomenten (kan meerdere dagen per show zijn, elk wordt een los event).
Zesde Playwright-scraper. Datum zonder jaartal — afgeleid zoals bij
scrape_dorpshuisannen.py.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE = 'grandtheatregroningen'
URL    = 'https://www.grandtheatregroningen.nl/nl/programma'
VENUE  = 'Grand Theatre, Groningen'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
URL_PATTERN   = re.compile(r'<a href="([^"]*)" class="overlay-link"')
TITLE_PATTERN = re.compile(r'<h1>(.*?)</h1>', re.S)
DATE_PATTERN  = re.compile(r'<h1>\w\w (\d{1,2}) (\w{3})</h1>')


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


def clean_title(raw_html: str) -> str:
    text = re.sub(r'<br\s*/?>', ' - ', raw_html)
    text = re.sub(r'<[^>]+>', '', text)
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


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

    blocks = html_text.split('<li class="event-container')[1:]
    print(f"  {len(blocks)} voorstellingen op de gerenderde programma-pagina")

    found = added = 0
    all_events = []
    for block in blocks:
        url_m = URL_PATTERN.search(block)
        title_m = TITLE_PATTERN.search(block)
        if not url_m or not title_m:
            continue
        title = clean_title(title_m.group(1))
        event_url = url_m.group(1)
        for day, month_str in DATE_PATTERN.findall(block):
            iso_date = parse_date(int(day), month_str)
            if not iso_date or not title:
                continue
            found += 1
            ev = {
                'title':  title,
                'date':   iso_date,
                'venue':  VENUE,
                'url':    event_url or URL,
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

    print(f"Scraping Grand Theatre Groningen (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
