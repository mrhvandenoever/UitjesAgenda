"""
scrape_paard.py — Het Paard (Den Haag) via denhaag.com

Gebruik:
    python scrape_paard.py              # scrape, sla op in DB
    python scrape_paard.py --dry-run    # toon events zonder op te slaan

Het Paard's eigen site (paard.nl, niet hetpaard.nl — dat domein bestaat
niet) bleek zelfs met Playwright leeg te blijven. Michiel wees op
denhaag.com/nl/paard (stads-agenda van The Hague & Partners) als omweg —
die toont "Evenementen op deze locatie", 8 per pagina, met een normale
`?page=N`-paginering (géén browser nodig, gewoon volgende pagina's
ophalen tot een pagina leeg is).

Twee datumformaten in de kaarten:
  - "zat 22 aug" — losse dag, geen jaartal, wordt afgeleid (rollen naar
    volgend jaar als de datum al voorbij is), zelfde patroon als
    scrape_dorpshuisannen.py.
  - "28 augustus 2026 t/m 29 augustus 2026" — meerdaagse events (vooral
    Paardcafé-nachten), wél een jaartal; we nemen de eerste (start)datum.
"""

import urllib.request
import re
import html as html_lib
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from parallel_fetch import fetch_batches

SOURCE   = 'paard'
BASE_URL = 'https://denhaag.com'
VENUE    = 'Het Paard, Den Haag'

NL_MONTHS_ABBR = {
    'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12,
}
NL_MONTHS_FULL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}

CARD_PATTERN = re.compile(
    r'href="(/nl/agenda/[^"]+)" class="card card--full[^"]*">.*?'
    r'card__label[^>]*>\s*([^<]+?)\s*</div>.*?'
    r'card__title[^>]*>([^<]+)</h3>\s*'
    r'<div class="card__meta[^"]*">\s*<div class="card__meta-item">([^<]*)</div>',
    re.S,
)

SHORT_DATE = re.compile(r'^\w+ (\d{1,2}) (\w{3})$')
LONG_DATE  = re.compile(r'(\d{1,2}) (\w+) (\d{4})')


def fetch(page: int) -> str:
    url = f'{BASE_URL}/nl/paard' + (f'?page={page}' if page else '')
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def parse_date(date_text: str) -> str | None:
    m = SHORT_DATE.match(date_text)
    if m:
        day, month_str = int(m.group(1)), m.group(2).lower()
        month = NL_MONTHS_ABBR.get(month_str)
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

    m = LONG_DATE.search(date_text)
    if m:
        day, month_str, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = NL_MONTHS_FULL.get(month_str)
        if not month:
            return None
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def extract_matches(html_text: str) -> list[tuple]:
    blocks = html_text.split('paragraph--type--playlist-item')[1:]
    matches = [CARD_PATTERN.search(b) for b in blocks]
    return [m.groups() for m in matches if m]


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    # Pagina's in batches van 5 gelijktijdig ophalen i.p.v. één voor één
    # (Niveau B, overleg.md punt 2 / decisions.md 2026-08-16). Geverifieerd
    # (2026-08-16): denhaag.com geeft voorbij het echte einde gewoon 0
    # matches terug (geen fallback-content-quirk zoals bij drenthe.nl), dus
    # "0 matches" is hier een betrouwbaar, direct eind-signaal.
    def should_stop(page: int, html_text: str) -> bool:
        return not extract_matches(html_text)

    fetched = fetch_batches(0, fetch, should_stop, max_batches=7, stop_after_consecutive=1)

    all_matches = []
    last_page = 0
    for page, html_text, exc in fetched:
        if exc is not None:
            print(f"  FOUT op pagina {page}: {exc}")
            continue
        matches = extract_matches(html_text)
        if not matches:
            break
        all_matches.extend(matches)
        last_page = page

    print(f"  {len(all_matches)} events over {last_page + 1} pagina's")

    found = added = 0
    all_events = []
    for rel_url, date_text, title, time_str in all_matches:
        iso_date = parse_date(date_text.strip())
        title = html_lib.unescape(title).strip()
        if not iso_date or not title:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'time':   (time_str.strip().split('-')[0].strip() or None) if time_str else None,
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

    print(f"Scraping Het Paard (via denhaag.com) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
