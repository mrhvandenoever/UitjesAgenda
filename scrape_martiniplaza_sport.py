"""
scrape_martiniplaza_sport.py — Martiniplaza (Groningen), categorie "Sport"

Gebruik:
    python scrape_martiniplaza_sport.py              # scrape, sla op in DB
    python scrape_martiniplaza_sport.py --dry-run    # toon events zonder op te slaan

Aanvulling op scrape_martiniplaza.py (die draait via theater.nl en alleen
theater/musical/concert-achtige content dekt). Gevonden via overleg.md
punt 5 ("nationale sportteams"): het TeamNL Volleybal XL Weekend (aug 2026)
stond WEL op martiniplaza.nl's eigen agenda (categorie "Sport"), maar NIET
op theater.nl — een pure theater-aggregator die sportevents categorisch
mist. Bewust een aparte, kleine scraper i.p.v. de bestaande
scrape_martiniplaza.py omgooien: theater.nl geeft nette ISO-datums+tijden
via JSON-LD (regressierisico bij vervangen), terwijl de eigen site geen
jaartal en geen tijd in de datumtekst heeft. Twee scrapers naast elkaar,
zelfde VENUE, aparte SOURCE-sleutel — cross-source-dedup vangt eventuele
overlap vanzelf (zie events_db.py).

martiniplaza.nl/nl/agenda ondersteunt een server-side `category`-filter
(`?category=sport` — gevonden via het <select name="category">-element).
Paginering via een AJAX-endpoint (`/nl/mvc/event/partial?...&guid=...`,
gevonden via de pagina's eigen `loadData()`-JS) die ook zonder sessie/
cookies werkt en het `category`-filter respecteert.

Datumtekst heeft NOOIT een jaartal (bv. "23 september - 27 september",
"08 september") — huidig jaar aannemen, doorrollen naar volgend jaar als
dat al voorbij zou zijn (zelfde patroon als scrape_drenthe.py).
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE       = 'martiniplaza_sport'
BASE_URL     = 'https://www.martiniplaza.nl'
LISTING_URL  = f'{BASE_URL}/nl/agenda?category=sport'
# guid identificeert het agenda-contentblok zelf (niet sessiegebonden) —
# eenmalig gevonden in de pagina-JS, zie decisions.md 2026-08-22.
PARTIAL_URL  = f'{BASE_URL}/nl/mvc/event/partial'
PARTIAL_GUID = 'a3f1210f-d9ce-4e03-9087-df299b13e05f'
VENUE        = 'Martiniplaza, Groningen'
CITY         = 'Groningen'
PROVINCE     = 'Groningen'
TODAY        = date.today().isoformat()
TODAY_DATE   = date.today()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)

RANGE_PAT = re.compile(rf'(\d{{1,2}})\s+({MONTH_PAT})\s*-\s*(\d{{1,2}})\s+({MONTH_PAT})', re.I)
SINGLE_PAT = re.compile(rf'(\d{{1,2}})\s+({MONTH_PAT})', re.I)

ITEM_PAT = re.compile(
    r'<div class="event list col-1-1 no-p">.*?'
    r'<h2 class="title">\s*<a[^>]*href="([^"]+)">([^<]+)</a>\s*</h2>\s*'
    r'<h6 class="date">([^<]+)</h6>',
    re.S,
)


def make_date(day: int, month_n: int) -> str | None:
    year = TODAY_DATE.year
    try:
        d = date(year, month_n, day)
    except ValueError:
        return None
    if d.isoformat() < TODAY:
        try:
            d = date(year + 1, month_n, day)
        except ValueError:
            return None
    return d.isoformat()


def parse_date_text(text: str) -> tuple[str, str | None] | None:
    s = text.strip().lower()
    m = RANGE_PAT.search(s)
    if m:
        d1, mo1, d2, mo2 = m.groups()
        start = make_date(int(d1), MONTHS_NL[mo1])
        end = make_date(int(d2), MONTHS_NL[mo2])
        if not start or not end:
            return None
        return start, end
    m = SINGLE_PAT.search(s)
    if not m:
        return None
    d1, mo1 = m.groups()
    start = make_date(int(d1), MONTHS_NL[mo1])
    return (start, None) if start else None


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def fetch_all_pages() -> list[tuple[str, str, str]]:
    """Geeft alle (url, title, date_text)-tuples terug over alle pagina's."""
    items = []
    html = fetch(LISTING_URL)
    page = 1
    while True:
        batch = ITEM_PAT.findall(html)
        if not batch:
            break
        items.extend(batch)
        page += 1
        partial_url = (
            f'{PARTIAL_URL}?view=list&p={page}&q=&genre=&StartDate=&EndDate='
            f'&label=&guid={PARTIAL_GUID}&category=sport'
        )
        html = fetch(partial_url)
    return items


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        items = fetch_all_pages()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    all_events = []
    seen_urls = set()
    for url, title, date_text in items:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        parsed = parse_date_text(date_text)
        if not parsed:
            continue
        start_iso, end_iso = parsed
        if (end_iso or start_iso) < TODAY:
            continue

        ev = {
            'title':    title.strip(),
            'date':     start_iso,
            'venue':    VENUE,
            'city':     CITY,
            'province': PROVINCE,
            'source':   SOURCE,
            'url':      url if url.startswith('http') else BASE_URL + url,
            'cats':     ['sport'],
        }
        if end_iso:
            ev['date_end'] = end_iso
        all_events.append(ev)

    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']}")
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
    args = parser.parse_args()

    print(f"Scraping martiniplaza.nl (categorie Sport) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
