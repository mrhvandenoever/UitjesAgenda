"""
scrape_handbal.py — thuiswedstrijden E&O en Hurry-Up via handbal.nl (Sportlink)

Gebruik:
    python scrape_handbal.py              # scrape, sla op in DB
    python scrape_handbal.py --dry-run    # toon events zonder op te slaan

Bron: https://handbal.nl/competitie-vereniging/?club=<code> (Sportlink-gedreven
NHV-clubpagina). Onder de motorkap haalt die pagina data op bij
api.handbal.nl/general/api/competition/clubs/<code>/program — een DataTables
server-side endpoint met een breed datumfilter (filters[date]=VAN><TOT) en
een instelbare pagegrootte (length). Gevonden via Chrome MCP (netwerkverkeer
+ DataTables JS-object uitgelezen), 2026-08-10.

Let op: de standaard datumfilter op de site zelf toont maar 2 weken vooruit —
dat gaf eerder ten onrechte de indruk dat er nog niks gepubliceerd was. Met
een ruimere filters[date]-range staat het hele seizoen er wel degelijk in.
"""

import urllib.request
import ssl
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

CLUBS = [
    # (club-code op handbal.nl, source-sleutel, provincie)
    ('ZQ052WS', 'hurryup', 'Drenthe'),
    ('ZQ052JF', 'eoemmen', 'Drenthe'),
]

# Alleen de 1e senioren-teams meenemen (HS1/DS1) — niet de jeugdteams
# (F1, DB1, HB1 e.d.) die ook onder dezelfde club-code meelopen.
SENIOR_SUFFIXES = ('HS1', 'DS1')


def fetch_program(club_code: str, date_from: str, date_to: str) -> list[dict]:
    url = (
        f'https://api.handbal.nl/general/api/competition/clubs/{club_code}/program'
        f'?dt=1&teamDetails=true&facility=true&officials=true&pool=&team='
        f'&start=0&length=300'
        f'&filters%5Bdate%5D={date_from}%3E%3C{date_to}'
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        data = json.loads(r.read().decode('utf-8'))
    return data.get('data', [])


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    today = date.today()
    date_from = today.isoformat()
    date_to = date(today.year + 1, today.month, today.day).isoformat()

    found = added = 0
    for club_code, source_key, province in CLUBS:
        try:
            matches = fetch_program(club_code, date_from, date_to)
        except Exception as e:
            print(f"  {source_key}: FOUT: {e}")
            continue

        home = [
            m for m in matches
            if m['homeTeam']['clubRefId'] == club_code
            and m['homeTeam']['teamName'].split()[-1] in SENIOR_SUFFIXES
        ]
        print(f"  {source_key}: {len(matches)} wedstrijden opgehaald, {len(home)} thuis (senioren HS1/DS1)")

        for m in home:
            team_suffix = m['homeTeam']['teamName'].split()[-1]
            gender = 'heren' if team_suffix == 'HS1' else 'dames'
            facility = m.get('facility') or {}
            addr = facility.get('address') or {}
            city = (addr.get('city') or '').title()
            venue = f"{facility.get('name', '')}" + (f", {city}" if city else '')

            found += 1
            ev = {
                'title':    f"{m['homeTeam']['teamName']} - {m['awayTeam']['teamName']}",
                'date':     m['matchDate'],
                'time':     (m.get('startTime') or '')[:5] or None,
                'venue':    venue or None,
                'city':     city or None,
                'province': province,
                'genre':    'sport',
                'sport':    'handbal',
                'gender':   gender,
                'source':   source_key,
                'url':      f'https://handbal.nl/competitie-vereniging/?club={club_code}',
            }
            if dry_run:
                print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']} @ {ev['venue']}")
            else:
                if insert_event(ev):
                    added += 1

    if not dry_run:
        log_scrape('handbal.nl', found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping handbal.nl (E&O + Hurry-Up) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
