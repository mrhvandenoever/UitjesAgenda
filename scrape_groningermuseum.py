"""
scrape_groningermuseum.py — Groninger Museum, via de eigen JSON-API

Gebruik:
    python scrape_groningermuseum.py              # scrape, sla op in DB
    python scrape_groningermuseum.py --dry-run    # toon events zonder op te slaan

Was één van de 7 bronnen "geparkeerd als moeilijk" (zie SCRAPERS.md/
decisions.md 2026-08-15): "Craft CMS (SEOmatic-generator) — voor de hand
liggende GraphQL-endpoints geven 404, geen API gevonden. Met Playwright
gecheckt: pagina blijft leeg, zelfs na volledige render."

**Opgelost 2026-08-17** naar aanleiding van Michiels melding dat "Groninger
Museumnacht" ontbrak als Uitje. Een Playwright-check (via subagent) op
`groningermuseum.nl/?type=soon&page=1&perPage=6` liet zien dat de site zelf
GEEN GraphQL gebruikt voor deze content, maar een simpele, publieke REST/
JSON-endpoint: `/api/activities?type=<now|soon|past>&page=N&perPage=N` en
`/api/exhibitions?type=<now|soon>&page=N&perPage=N` — plain `urllib` volstaat,
geen AI/Playwright nodig. Bevestigd met een directe HTTP-GET (geen sessie/
cookie/referrer nodig).

Twee content-typen, beide op deze bron:
  - **Exhibitions** → Exposities. `prettyDate` is een schoon Nederlands
    datumbereik ("19 september 2026 t/m 9 mei 2027") — day+month+year aan
    beide kanten in alle geziene gevallen (geen "eind <maand>"-vorm zoals bij
    Geke Hoogstins). cats=['expositie'] voor een betrouwbaar genre-signaal.
  - **Activities** → Uitjes, maar het overgrote deel is generiek-terug-
    kerend ("Dinsdag t/m zondag", "Ieder weekend en in de schoolvakanties")
    zonder een concrete losse datum — die passen niet in ons single-date-
    model en worden bewust overgeslagen. Alleen activiteiten met een
    herkenbaar `<weekdag> D <maand>[ JJJJ]`-patroon (zoals "Groninger
    Museumnacht") worden meegenomen.

`type=now` én `type=soon` worden allebei opgehaald (niet alleen `soon`) —
zo blijven al-begonnen-maar-nog-lopende exposities (bv. "Bakstain") ook mee,
consistent met hoe events_db.py's export_json() en gen_uitjes.py's
event_is_valid() dat al ondersteunen (zie decisions.md 2026-08-17).
"""

import urllib.request
import json
import re
import argparse
from datetime import date, datetime
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE   = 'groningermuseum'
BASE_URL = 'https://www.groningermuseum.nl'
VENUE    = 'Groninger Museum'

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}


def fetch_api(path: str, type_: str, page: int = 1, per_page: int = 50) -> dict:
    url = f'{BASE_URL}/api/{path}?type={type_}&page={page}&perPage={per_page}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_all(path: str, type_: str) -> list[dict]:
    first = fetch_api(path, type_, page=1)
    items = list(first.get('data', []))
    last_page = first.get('pagination', {}).get('lastPage', 1)
    for p in range(2, last_page + 1):
        items.extend(fetch_api(path, type_, page=p).get('data', []))
    return items


def parse_exhibition_range(pretty_date: str) -> tuple[str, str] | None:
    """'19 september 2026 t/m 9 mei 2027' -> (start_iso, end_iso)."""
    m = re.match(
        r'(\d{1,2})\s+(\w+)\s+(\d{4})\s+t/m\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
        (pretty_date or '').strip())
    if not m:
        return None
    d1, mo1, y1, d2, mo2, y2 = m.groups()
    m1, m2 = MONTHS_NL.get(mo1.lower()), MONTHS_NL.get(mo2.lower())
    if not m1 or not m2:
        return None
    try:
        start = date(int(y1), m1, int(d1))
        end = date(int(y2), m2, int(d2))
    except ValueError:
        return None
    return start.isoformat(), end.isoformat()


def parse_activity_date(pretty_date: str) -> str | None:
    """'zaterdag 19 september tussen 19:00 - 01:00 uur' -> ISO-datum voor
    een concrete, losse activiteit. Retourneert None voor generieke/
    terugkerende teksten (komma-lijsten, 't/m', "Ieder weekend", etc.) —
    die passen niet in ons single-date-model, bewust overgeslagen."""
    if not pretty_date:
        return None
    text = pretty_date.strip()
    if ',' in text or 't/m' in text.lower():
        return None
    m = re.match(r'^(?:\w+\s+)?(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', text)
    if not m:
        return None
    day, month_word, year_str = m.groups()
    month = MONTHS_NL.get(month_word.lower())
    if not month:
        return None
    today = date.today()
    year = int(year_str) if year_str else today.year
    try:
        d = date(year, month, int(day))
    except ValueError:
        return None
    if not year_str and d < today:
        try:
            d = date(year + 1, month, int(day))
        except ValueError:
            return None
    return d.isoformat()


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    all_events = []
    try:
        exhibitions = fetch_all('exhibitions', 'now') + fetch_all('exhibitions', 'soon')
    except Exception as e:
        print(f"  FOUT bij exhibitions: {e}")
        exhibitions = []
    seen_ids = set()
    for item in exhibitions:
        if item['id'] in seen_ids:  # now+soon kunnen overlappen
            continue
        seen_ids.add(item['id'])
        rng = parse_exhibition_range(item.get('prettyDate'))
        if not rng:
            continue
        start_iso, end_iso = rng
        ev = {
            'title':  item.get('title', '').strip(),
            'date':   start_iso,
            'venue':  VENUE,
            'url':    item.get('url'),
            'source': SOURCE,
            'cats':   ['expositie'],
        }
        if end_iso != start_iso:
            ev['date_end'] = end_iso
        if ev['title']:
            all_events.append(ev)

    try:
        activities = fetch_all('activities', 'now') + fetch_all('activities', 'soon')
    except Exception as e:
        print(f"  FOUT bij activities: {e}")
        activities = []
    seen_act_ids = set()
    for item in activities:
        if item['id'] in seen_act_ids:
            continue
        seen_act_ids.add(item['id'])
        iso_date = parse_activity_date(item.get('prettyDate'))
        if not iso_date:
            continue
        title = item.get('title', '').strip()
        if not title:
            continue
        all_events.append({
            'title':  title,
            'date':   iso_date,
            'venue':  VENUE,
            'url':    item.get('url'),
            'source': SOURCE,
        })

    found = len(all_events)

    if dry_run:
        for ev in all_events:
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

    print(f"Scraping Groninger Museum [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
