"""
scrape_fcemmen.py — FC Emmen thuiswedstrijden

Gebruik:
    python scrape_fcemmen.py              # scrape, sla op in DB
    python scrape_fcemmen.py --dry-run    # toon events zonder op te slaan

Eigen site: een gewone WordPress-block-table (RONDE|DAG|DATUM|TIJD|THUIS|UIT).
Thuiswedstrijden = rijen waar de THUIS-kolom exact "FC Emmen" is. Datum staat
als D-M-YYYY, tijd als "20.00 uur".
"""

import urllib.request
import re
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SOURCE = 'fcemmen'
CLUB   = 'FC Emmen'
VENUE  = 'De Oude Meerdijk, Emmen'
URL    = 'https://fcemmen.nl/wedstrijdschema/'


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def clean(cell: str) -> str:
    return re.sub(r'<[^>]+>', '', cell).strip()


def parse_date(datum: str) -> str | None:
    m = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', datum.strip())
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def parse_time(tijd: str) -> str | None:
    m = re.match(r'(\d{1,2})[.:](\d{2})', tijd.strip())
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        html = fetch(URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    i = html.rfind('<figure class="wp-block-table">')
    if i == -1:
        print("  FOUT: tabel niet gevonden op de pagina")
        return 0, 0
    end = html.find('</table>', i)
    table_html = html[i:end + 9]
    rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.S)

    found = added = 0
    for row in rows[1:]:  # eerste rij is de header
        cells = re.findall(r'<td>(.*?)</td>', row, re.S)
        if len(cells) < 6:
            continue
        _ronde, _dag, datum, tijd, thuis, uit = [clean(c) for c in cells[:6]]
        if thuis != CLUB:
            continue
        iso_date = parse_date(datum)
        if not iso_date:
            continue
        found += 1
        ev = {
            'title':  f'{CLUB} - {uit}',
            'date':   iso_date,
            'time':   parse_time(tijd),
            'venue':  VENUE,
            'url':    URL,
            'source': SOURCE,
            'genre':  'sport',
            'sport':  'voetbal',
            'gender': 'heren',
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']}")
        else:
            if insert_event(ev):
                added += 1

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB} [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
