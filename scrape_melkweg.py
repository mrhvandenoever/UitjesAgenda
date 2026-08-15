"""
scrape_melkweg.py — Melkweg (Amsterdam) via server-rendered HTML

Gebruik:
    python scrape_melkweg.py              # scrape, sla op in DB
    python scrape_melkweg.py --dry-run    # toon events zonder op te slaan

Stond als "AI/Chrome nodig" in SCRAPERS.md (eerdere check vond geen
__NEXT_DATA__ met events en concludeerde client-side rendering). Bleek niet
waar: melkweg.nl (Next.js) rendert de agenda WEL server-side — de HTML bevat
gewoon een `<h2>`-datumkop per dag (met `dateTime="ISO"`) gevolgd door een
`<ol>` met `<a href="/nl/agenda/...">`-items per event, geen JS/browser
nodig. `__NEXT_DATA__` bevatte inderdaad geen bruikbare events-array (die
zit specifiek voor deze pagina blijkbaar leeg/elders), maar de gerenderde
HTML zelf wel — dus regex op de HTML i.p.v. op de JSON-praps, zelfde aanpak
als de ESPN.nl-scrapers (scrape_cambuur.py e.d.).

Elk event heeft precies één datum in de agenda-listing (geen duplicaten
over meerdere dagen voor meerdaagse exposities) — één simpele lijst is dus
genoeg, geen dedup-logica nodig.
"""

import urllib.request
import re
import html as html_lib
import argparse
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE   = 'melkweg'
BASE_URL = 'https://www.melkweg.nl'
AGENDA_URL = f'{BASE_URL}/nl/agenda/'
VENUE    = 'Melkweg, Amsterdam'

HEADER_PATTERN = re.compile(r'dateTime="([^"]+)"')
ITEM_PATTERN = re.compile(
    r'href="(/nl/agenda/[^"]+)"[^>]*>.*?<h3 class="[^"]*event-compact__title[^"]*">([^<]+)</h3>',
    re.S,
)


def fetch() -> str:
    req = urllib.request.Request(AGENDA_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def extract_events(html_text: str) -> list[tuple[str, str, str]]:
    """-> lijst van (iso_date, titel, relatieve_url)."""
    headers = [(m.start(), m.group(1)) for m in HEADER_PATTERN.finditer(html_text)]
    events = []
    for i, (pos, iso) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(html_text)
        chunk = html_text[pos:end]
        for url, title in ITEM_PATTERN.findall(chunk):
            events.append((iso[:10], html_lib.unescape(title).strip(), url))
    return events


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html_text = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    items = extract_events(html_text)
    print(f"  {len(items)} events op de agenda-pagina")

    found = added = 0
    all_events = []
    for iso_date, title, rel_url in items:
        if not title or not iso_date:
            continue
        found += 1
        ev = {
            'title':  title,
            'date':   iso_date,
            'venue':  VENUE,
            'url':    f'{BASE_URL}{rel_url}',
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

    print(f"Scraping Melkweg (server-rendered HTML) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
