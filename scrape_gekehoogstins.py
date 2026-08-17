"""
scrape_gekehoogstins.py — Geke Hoogstins (kunstenares, Eext) exposities

Gebruik:
    python scrape_gekehoogstins.py              # scrape, sla op in DB
    python scrape_gekehoogstins.py --dry-run    # toon events zonder op te slaan

Was eerder bewust NIET gebouwd (zie SCRAPERS.md/decisions.md): "maandenlange
doorlopende exposities, geen losse datums, past niet in ons single-date-
event-model". Sinds de Exposities-modus (2026-08-16, zie ARCHITECTURE.md
§Exposities) is dat opgelost — `date_end` wordt nu echt gebruikt, dus een
doorlopende expositie past prima.

De site zelf is verder gewoon vrije tekst/proza (geen gestructureerde
event-listing), MAAR de "EXPOSITIES <jaar>"-sectie op de exposities-pagina
is wél consistent HTML: een `<h2>`-heading met het jaartal, gevolgd door een
`<p><strong>datumbereik</strong> titel</p>` per expositie. Alleen dát blok
wordt geparsed — de rest van de pagina (vrije tekst met meer details per
expositie) wordt bewust genegeerd, dat zou wél een AI-achtige lees-taak zijn.

Datumbereik-formaten die voorkomen (en de reden voor parse_range()'s vorm):
  - "22 mei t/m eind oktober" — geen einddag, "eind <maand>" → laatste dag
    van die maand (via calendar.monthrange()).
  - "3 juli t/m 5 september" — beide kanten dag+maand, jaartal impliciet
    (het jaar uit de "EXPOSITIES <jaar>"-heading, tenzij de eindmaand vóór
    de beginmaand ligt — dan +1 jaar, voor de jaarwisseling hieronder).
  - "13 november t/m 9 januari 2027" — eindkant heeft een EXPLICIET jaartal
    (jaarwisseling). Dat jaartal wint altijd als het aanwezig is.
"""

import urllib.request
import re
import html as html_lib
import calendar
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context

SSL_CTX = create_context()

SOURCE   = 'gekehoogstins.nl'
BASE_URL = 'https://gekehoogstins.nl/exposities-evenementen/exposities/'
VENUE    = 'Geke Hoogstins (Eext)'

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}


def fetch() -> str:
    req = urllib.request.Request(BASE_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return r.read().decode('utf-8')


def parse_range(text: str, default_year: int) -> tuple[str, str] | None:
    """'22 mei t/m eind oktober' of '13 november t/m 9 januari 2027'
    -> (start_iso, end_iso), of None als het niet te parsen is."""
    text = text.strip().rstrip(':').strip()
    if 't/m' not in text:
        return None
    start_part, end_part = [p.strip() for p in text.split('t/m', 1)]

    m_start = re.match(r'(\d{1,2})\s+(\w+)', start_part)
    if not m_start:
        return None
    start_day, start_month_word = int(m_start.group(1)), m_start.group(2).lower()
    start_month = MONTHS_NL.get(start_month_word)
    if not start_month:
        return None
    try:
        start = date(default_year, start_month, start_day)
    except ValueError:
        return None

    m_eind = re.match(r'eind\s+(\w+)', end_part)
    if m_eind:
        end_month = MONTHS_NL.get(m_eind.group(1).lower())
        if not end_month:
            return None
        end_year = default_year if end_month >= start_month else default_year + 1
        end_day = calendar.monthrange(end_year, end_month)[1]
    else:
        m_end = re.match(r'(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', end_part)
        if not m_end:
            return None
        end_day = int(m_end.group(1))
        end_month = MONTHS_NL.get(m_end.group(2).lower())
        if not end_month:
            return None
        end_year = int(m_end.group(3)) if m_end.group(3) else (
            default_year if end_month >= start_month else default_year + 1)
    try:
        end = date(end_year, end_month, end_day)
    except ValueError:
        return None

    return start.isoformat(), end.isoformat()


def parse_exposities(html_text: str) -> list[dict]:
    m_heading = re.search(r'EXPOSITIES\s+(\d{4})', html_text)
    if not m_heading:
        return []
    year = int(m_heading.group(1))

    # Alleen het blok tussen deze heading en de volgende h2/h3/section
    # doorzoeken — de rest van de pagina is vrije-tekst-detail, geen losse
    # events.
    block_start = m_heading.end()
    m_block_end = re.search(r'<h[23]|<section', html_text[block_start:])
    block = html_text[block_start:block_start + m_block_end.start()] if m_block_end else html_text[block_start:]

    events = []
    for m in re.finditer(r'<p[^>]*><strong>([^<]+)</strong>\s*([^<]*)</p>', block):
        date_text, title_text = m.groups()
        title = ' '.join(html_lib.unescape(title_text).split())
        if not title:
            continue
        rng = parse_range(date_text, year)
        if not rng:
            continue
        start_iso, end_iso = rng
        ev = {
            'title':  title,
            'date':   start_iso,
            'venue':  VENUE,
            'url':    BASE_URL,
            'source': SOURCE,
        }
        if end_iso != start_iso:
            ev['date_end'] = end_iso
        events.append(ev)
    return events


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0

    try:
        html_text = fetch()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    all_events = parse_exposities(html_text)
    found = len(all_events)

    if dry_run:
        for ev in all_events:
            end_txt = f" t/m {ev['date_end']}" if 'date_end' in ev else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']}")
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")
        return found, 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        return found, 0
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

    print(f"Scraping Geke Hoogstins [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
