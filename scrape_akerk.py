"""
scrape_akerk.py — Akerk (Groningen), via de eigen JSON-API

Gebruik:
    python scrape_akerk.py              # scrape, sla op in DB
    python scrape_akerk.py --dry-run    # toon events zonder op te slaan

Michiel wees op deze bron (2026-08-19) met een concreet voorbeeld
(https://akerk.nl/event/all-cops-are-expositie). De agenda-pagina zelf is
een client-rendered app ("Javascript moet ingeschakeld zijn"), maar een
netwerkcheck (Browser pane) legde meteen een publieke, schone JSON-API
bloot: `https://akerk.nl/events.json` (gepagineerd via `meta.pagination.
links.next`) — geen Playwright nodig, net als bij Groninger Museum/
Staatsbosbeheer. Kleine bron: 11 events over 2 pagina's.

Elk event heeft een `eventTypes`-array (bv. `["Orgelconcert",
"Arp Schnitgerorgel"]`, `["Expositie"]`, `["Festival","Diner"]`) — een
betrouwbaar genre-signaal van de bron zelf, vertaald naar onze `cats`-
vocabulaire via EVENTTYPE_CAT_MAP i.p.v. classify()'s titel-keyword-gok
("Orgelzomer Groningen | Michael Bennett" bevat bv. geen van de bestaande
klassiek-keywords en zou anders op 'overig' uitkomen). Types zonder mapping
(Gratis/Rondleidingen/Diner/Event/Koor) leveren gewoon geen extra cats-hint
— classify() valt dan terug op titel-keywords, prima als fallback.

`beginDate`/`endDate` zijn allebei altijd aanwezig en ISO-achtig
(`"2026-08-18 00:00:00.000000"`) — geen datum-parsing-onzekerheid zoals bij
drenthe.nl. Meerdaagse dingen (de expositie, Wijnfestival, Whiskey
Festival) krijgen gewoon een echte `date_end`.

Vaste locatie (1 gebouw, geen per-event venue-variatie nodig): Akerkhof 2,
Groningen.
"""

import urllib.request
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE   = 'akerk'
API_URL  = 'https://akerk.nl/events.json'
VENUE    = 'Akerk, Groningen'
CITY     = 'Groningen'
PROVINCE = 'Groningen'
TODAY    = date.today().isoformat()

EVENTTYPE_CAT_MAP = {
    'Expositie':    'expositie',
    'Orgelconcert': 'klassiek',
    'Koor':         'klassiek',
    'Festival':     'festival',
}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_all() -> list[dict]:
    items = []
    url = API_URL
    while url:
        data = fetch(url)
        items.extend(data.get('data', []))
        url = (data.get('meta', {}).get('pagination', {}).get('links', {}) or {}).get('next')
    return items


def cats_for(event_types: list[str]) -> list[str]:
    seen = set()
    cats = []
    for t in event_types or []:
        c = EVENTTYPE_CAT_MAP.get(t)
        if c and c not in seen:
            seen.add(c)
            cats.append(c)
    return cats


def parse_item(item: dict) -> dict | None:
    title = (item.get('title') or '').strip()
    begin = ((item.get('beginDate') or {}).get('date') or '')[:10]
    if not title or not begin:
        return None

    end = ((item.get('endDate') or {}).get('date') or '')[:10]
    date_end = end if end and end != begin else None
    # Al helemaal voorbij (meerdaags of eendaags) -> niet meenemen.
    if (date_end or begin) < TODAY:
        return None

    ev = {
        'title':    title,
        'date':     begin,
        'venue':    VENUE,
        'city':     CITY,
        'province': PROVINCE,
        'source':   SOURCE,
        'url':      item.get('url'),
        'time':     item.get('time') or None,
        'subtitle': (item.get('description') or '').strip() or None,
        'cats':     cats_for(item.get('eventTypes')),
    }
    if date_end:
        ev['date_end'] = date_end
    return ev


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        raw_items = fetch_all()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0
    print(f"  {len(raw_items)} events opgehaald")

    all_events = []
    for item in raw_items:
        ev = parse_item(item)
        if ev:
            all_events.append(ev)
    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['cats']} {ev['title']}")
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

    print(f"Scraping akerk.nl [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
