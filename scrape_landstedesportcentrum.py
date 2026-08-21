"""
scrape_landstedesportcentrum.py — Landstede Sportcentrum (Zwolle)

Gebruik:
    python scrape_landstedesportcentrum.py              # scrape, sla op in DB
    python scrape_landstedesportcentrum.py --dry-run    # toon events zonder op te slaan

Gevonden via overleg.md punt 5 ("nationale sportteams" — zie
scrape_omnisport.py voor de volledige achtergrond). Landstede Sportcentrum
is net als Omnisport een vaste locatie voor Oranje-oefeninterlands
(volleybal, basketbal e.d.) — de hele agenda wordt gevolgd i.p.v. een
scraper voor de bonden zelf.

`landstedesportcentrum.nl/agenda/` is server-rendered maar zit in een
"glide"-carouselwidget die de events 3x herhaalt in de DOM (loop-effect) —
dedupliceren op URL. Het is een kleine "highlights"-widget, geen volledig
gepagineerd archief — er zijn geen extra pagina's op te halen.

Datumtekst heeft NOOIT een jaartal (bv. "vrijdag 20 maart t/m zondag 22
maart", "zondag 29 maart van 14:00 tot 18:00") — huidig jaar aannemen, en
naar volgend jaar doorrollen als dat al voorbij zou zijn (zelfde patroon
als scrape_drenthe.py).

"Landstede Hammers"-thuiswedstrijden worden bewust overgeslagen: die komen
al preciezer binnen via scrape_landstede.py (officiële BNXT League-API).
Structurele overlap (elke thuiswedstrijd van dezelfde club raakt deze
generieke venue-agenda ook), dus expliciet gefilterd i.p.v. op de
cross-source-dedup vertrouwen.
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE      = 'landstedesportcentrum'
BASE_URL    = 'https://landstedesportcentrum.nl'
LISTING_URL = f'{BASE_URL}/agenda/'
VENUE       = 'Landstede Sportcentrum, Zwolle'
CITY        = 'Zwolle'
PROVINCE    = 'Overijssel'
TODAY       = date.today().isoformat()
TODAY_DATE  = date.today()

WEEKDAYS = ('maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag')
MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)

RANGE_PAT = re.compile(rf'(\d{{1,2}})\s+({MONTH_PAT})\s+t/m\s+(\d{{1,2}})\s+({MONTH_PAT})', re.I)
SINGLE_PAT = re.compile(rf'(\d{{1,2}})\s+({MONTH_PAT})', re.I)
TIME_PAT = re.compile(r'van\s+(\d{1,2}:\d{2})\s+tot', re.I)

# "Landstede Hammers"-thuiswedstrijden komen al preciezer binnen via
# scrape_landstede.py (officiële BNXT League-API, echte tijd+seizoen) --
# dit is een structurele, gegarandeerde overlap (elke thuiswedstrijd van
# dezelfde club), geen incidentele titel-botsing, dus expliciet uitfilteren
# i.p.v. op de generieke cross-source-dedup vertrouwen.
SKIP_TITLE_WORDS = ('landstede hammers',)

ITEM_PAT = re.compile(
    r'<h3 class="eventoverview-component__item-introtitle">([^<]+)</h3>\s*'
    r'<h2 class="eventoverview-component__item-title">([^<]+)</h2>'
    r'.*?<a class="eventoverview-component__item-link"[^>]*href="([^"]+)"',
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


def parse_date_text(text: str) -> tuple[str, str | None, str | None] | None:
    """Geef (start_iso, end_iso, time) terug, of None als er geen datum in zit."""
    s = text.lower()
    for wd in WEEKDAYS:
        s = s.replace(wd, '')

    m = RANGE_PAT.search(s)
    if m:
        d1, mo1, d2, mo2 = m.groups()
        start = make_date(int(d1), MONTHS_NL[mo1])
        end = make_date(int(d2), MONTHS_NL[mo2])
        if not start or not end:
            return None
        return start, end, None

    m = SINGLE_PAT.search(s)
    if not m:
        return None
    d1, mo1 = m.groups()
    start = make_date(int(d1), MONTHS_NL[mo1])
    if not start:
        return None
    tm = TIME_PAT.search(s)
    return start, None, (tm.group(1) if tm else None)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        html = fetch(LISTING_URL)
    except Exception as e:
        print(f"  FOUT bij listingpagina: {e}")
        return 0, 0

    all_events = []
    seen_urls = set()
    for m in ITEM_PAT.finditer(html):
        date_text, title, url = m.groups()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if any(w in title.lower() for w in SKIP_TITLE_WORDS):
            continue

        parsed = parse_date_text(date_text)
        if not parsed:
            continue
        start_iso, end_iso, time_ = parsed
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
            # Alles wat hier overblijft (na de Hammers-filter hierboven) is
            # per definitie sport -- vandaar altijd 'sport', in
            # tegenstelling tot scrape_omnisport.py waar niet-sportcontent
            # (Qmusic-feest, Gelderse Dag) ook op de agenda staat.
            'cats':     ['sport'],
        }
        if end_iso:
            ev['date_end'] = end_iso
        if time_:
            ev['time'] = time_
        all_events.append(ev)

    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            time_txt = f" {ev['time']}" if ev.get('time') else ''
            print(f"    [{ev['date']}{end_txt}{time_txt}] {ev['title']}")
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

    print(f"Scraping landstedesportcentrum.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
