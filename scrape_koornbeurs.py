"""
scrape_koornbeurs.py — Koornbeurs (Franeker) via headless browser (Playwright)

Gebruik:
    python scrape_koornbeurs.py              # scrape, sla op in DB
    python scrape_koornbeurs.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md — eerdere check vond geen
Umbraco/API-sporen in de JS-bundle (ondanks een vergelijkbare bestands-
structuur als Atlas Emmen). Bleek gewoon client-side gerenderd zonder
verborgen API — vijfde Playwright-scraper. Programma-pagina heeft een
`performance-preview`-grid met dag/maand (geen jaartal, afgeleid zoals bij
scrape_dorpshuisannen.py), tijd, artiest en titel.

`performance-artist`/`performance-title` zijn niet consistent gevuld (soms
zit de naam in artist, soms in title, soms is er maar één van de twee) —
combineren met een simpele fallback i.p.v. aannemen welke "de titel" is,
zelfde aanpak als bij scrape_atlastheater.py.
"""

import re
import html as html_lib
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'koornbeurs'
BASE_URL = 'https://www.theaterdekoornbeurs.nl'
URL      = f'{BASE_URL}/programma'
VENUE    = 'Koornbeurs, Franeker'

NL_MONTHS = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
ITEM_PATTERN = re.compile(
    r'performance-day">(\d+)</p>\s*<p class="performance-month">(\w+)</p>.*?'
    r'href="(/voorstelling/[^"]+)">\s*<p class="performance-time">([^<]*)</p>\s*'
    r'<p class="performance-artist">([^<]*)</p>\s*<p class="performance-title">([^<]*)</p>',
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


def build_title(artist: str, title: str) -> str:
    artist, title = html_lib.unescape(artist).strip(), html_lib.unescape(title).strip()
    if artist and title and artist != title:
        return f'{artist} - {title}'
    return title or artist


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
    for day, month_str, rel_url, time_str, artist, title in matches:
        iso_date = parse_date(int(day), month_str)
        full_title = build_title(artist, title)
        if not iso_date or not full_title:
            continue
        found += 1
        ev = {
            'title':  full_title,
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

    print(f"Scraping Koornbeurs (Playwright, headless) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
