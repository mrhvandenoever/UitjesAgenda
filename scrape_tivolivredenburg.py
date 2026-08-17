"""
scrape_tivolivredenburg.py — TivoliVredenburg (Utrecht), directe agenda

Gebruik:
    python scrape_tivolivredenburg.py              # scrape, sla op in DB
    python scrape_tivolivredenburg.py --dry-run    # toon events zonder op te slaan

**Herzien 2026-08-17** — was tot dan toe een Songkick-omweg (alleen live-
muziek, ~9 shows), omdat tivolivredenburg.nl zelf een "bevestigde Cloudflare
bot-challenge" zou tonen (2026-08-15, "herbevestigd"). Bij het uitzoeken van
2 kapotte links (Filth/Alcest, gemeld door Michiel) bleek dat niet meer te
kloppen: een plain `urllib`-fetch van `/agenda/` en van losse event-URL's
werkt gewoon, geen "Just a moment..."-interstitial ergens in de pagina. De
eerder gevonden term "challenge-platform" bleek Cloudflare's passieve
JS-bot-analytics-script te zijn (`/cdn-cgi/challenge-platform/scripts/
jsd/main.js`), geen daadwerkelijke blokkade. Zie decisions.md 2026-08-17
voor de volledige analyse. Dit is dus GEEN bot-detectie-omzeiling (de
principiële grens in ARCHITECTURE.md §Playwright-scrapers blijft
overeind) — de blokkade bestond kennelijk niet (meer).

Dekt nu de VOLLEDIGE agenda (theater, cabaret, klassiek, alles — niet
alleen live-muziek zoals Songkick), via `/agenda/page/N/`. Elke pagina
toont 20 events; paginering loopt door tot een 404 (dynamisch bepaald,
2026-08-17 was dat pagina 43 — hardcoderen zou dit na verloop van tijd
laten achterlopen).

De datum staat gewoon in de event-URL zelf (`.../agenda/22763649/
filth-17-08-2026` eindigt op `-DD-MM-YYYY`) — geen aparte datumtekst-
parsing nodig, 100% betrouwbaar gebleken over een steekproef van bijna
100 events verspreid over de hele paginareeks.
"""

import urllib.request
import urllib.error
import re
import html as html_lib
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context
from parallel_fetch import fetch_batches

SSL_CTX = create_context()

SOURCE   = 'tivolivredenburg'
BASE_URL = 'https://www.tivolivredenburg.nl/agenda/'
VENUE    = 'TivoliVredenburg, Utrecht'

ITEM_PATTERN = re.compile(
    r'agenda-list-item__figure-link" href="([^"]+)" aria-label="([^"]*)"')
DATE_SUFFIX_PATTERN = re.compile(r'-(\d{2})-(\d{2})-(\d{4})$')


def fetch(url: str) -> str:
    """404 (voorbij de laatste pagina) geeft hier een lege string terug
    i.p.v. een exception — zo kan should_stop_fn() dat herkennen als een
    normaal eind-signaal, zie parallel_fetch.py's docstring over waarom dat
    beter is dan een generieke exception-skip."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
            return r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ''
        raise


def page_url(page: int) -> str:
    return BASE_URL if page == 1 else f'{BASE_URL}page/{page}/'


def should_stop(page: int, html_text: str) -> bool:
    return not html_text or 'js-load-more-button' not in html_text


def parse_page(html_text: str) -> list[dict]:
    events = []
    for url, title in ITEM_PATTERN.findall(html_text):
        title = html_lib.unescape(title).strip()
        m = DATE_SUFFIX_PATTERN.search(url)
        if not title or not m:
            continue
        day, month, year = m.groups()
        try:
            iso_date = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            continue
        events.append({
            'title':  title,
            'date':   iso_date,
            'venue':  VENUE,
            'url':    url,
            'source': SOURCE,
        })
    return events


def scrape(dry_run: bool = False, max_pages: int = 0) -> tuple[int, int]:
    init_db()

    # Onbekend aantal pagina's vooraf (2026-08-17: 43, kan groeien) —
    # batches van 5, stop bij de eerste pagina zonder "load more"-knop.
    # Ruime veiligheidsgrens: 15 batches * 5 = 75 pagina's headroom.
    batch_cap = max_pages if max_pages else 75
    fetched = fetch_batches(
        1, lambda p: fetch(page_url(p)), should_stop, batch_size=5,
        max_batches=(batch_cap // 5) + 1, stop_after_consecutive=1)

    all_events = []
    seen = set()
    for page, html_text, exc in fetched:
        if max_pages and page > max_pages:
            break
        if exc is not None:
            print(f"  Pagina {page}: FOUT: {exc}")
            continue
        if not html_text:
            continue
        for ev in parse_page(html_text):
            key = (ev['title'], ev['date'])
            if key in seen:
                continue
            seen.add(key)
            all_events.append(ev)
        if 'js-load-more-button' not in html_text:
            break

    found = len(all_events)

    if dry_run:
        for ev in all_events:
            print(f"    [{ev['date']}] {ev['title']}")
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")
        return found, 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        return found, 0

    added = 0
    for ev in all_events:
        if insert_event(ev):
            added += 1
    log_scrape(SOURCE, found, added)
    print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, default=0, metavar='N', help='max N pagina\'s (test)')
    args = parser.parse_args()

    print(f"Scraping TivoliVredenburg (directe agenda) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run, max_pages=args.max)
