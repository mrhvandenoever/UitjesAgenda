"""
scrape_handmatig.py — bekende jaarlijkse evenementen die niet op aggregator-sites staan

Deze events worden berekend op basis van het huidige jaar en zijn hardcoded.
Voeg nieuwe events toe in JAARLIJKSE_EVENTS hieronder.

Gebruik:
    python scrape_handmatig.py              # sla op in DB
    python scrape_handmatig.py --dry-run    # toon events zonder op te slaan
"""

import calendar
import argparse
from datetime import date, timedelta
from events_db import insert_event, log_scrape, init_db


def nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
    """
    Geef de n-de (1-based) weekday in een maand.
    weekday: 0=ma, 1=di, 2=wo, 3=do, 4=vr, 5=za, 6=zo
    """
    weeks = calendar.monthcalendar(year, month)
    days = [w[weekday] for w in weeks if w[weekday] != 0]
    return date(year, month, days[n - 1])


def build_events(year: int) -> list[dict]:
    """
    Bereken alle handmatige events voor het gegeven jaar.
    Geef een lijst van event-dicts terug.
    """
    events = []

    # ── GRONINGEN STAD ────────────────────────────────────────────────────────

    # Bommen Berend — 10 augustus, kermis in Groningen (herdenking slag om Groningen 1672)
    bommen = date(year, 8, 10)
    events.append({
        'title':    'Bommen Berend – Kermis Groningen',
        'date':     bommen.isoformat(),
        'city':     'Groningen',
        'province': 'Groningen',
        'genre':    'festival',
        'source':   'visitgroningen',
        'url':      'https://www.visitgroningen.nl',
        'note':     'Jaarlijks 10 augustus; slag om Groningen 1672 + kermis',
    })

    # ── ZUIDLAREN (gemeente Tynaarlo, Drenthe) ────────────────────────────────

    # Zuidlaarder Paardenmarkt — 3e dinsdag van oktober
    pm_date = nth_weekday(year, 10, 3, 1)   # 3e dinsdag (weekday=1)
    events.append({
        'title':    'Zuidlaarder Paardenmarkt',
        'date':     pm_date.isoformat(),
        'city':     'Zuidlaren',
        'province': 'Drenthe',
        'genre':    'festival',
        'source':   'drenthe.nl',
        'url':      'https://www.drenthe.nl',
        'note':     '3e dinsdag oktober; een van grootste paardenmarkten van Europa',
    })

    # Kermis Zuidlaren opening — vrijdag voor de paardenmarkt
    # pm_date is dinsdag (weekday=1), vrijdag ervoor is -4 dagen
    kermis_zuidlaren = pm_date - timedelta(days=4)
    events.append({
        'title':    'Kermis Zuidlaren (opening)',
        'date':     kermis_zuidlaren.isoformat(),
        'city':     'Zuidlaren',
        'province': 'Drenthe',
        'genre':    'festival',
        'source':   'drenthe.nl',
        'url':      'https://www.drenthe.nl',
        'note':     'Kermis opent de vrijdag voor de Paardenmarkt',
    })

    # Muzieknacht Zuidlaren — los evenement in juli (bevestigd via naarzuidlaren.nl + Facebook)
    # Datum: elk jaar in juli, exacte dag via naarzuidlaren.nl te scrapen
    # 2026: zaterdag 11 juli (bevestigd Grand Café Zuidlaren, 21:00)
    muzieknacht_day = 11  # update dit jaarlijks of vervang door naarzuidlaren scraper
    events.append({
        'title':    'Muzieknacht Zuidlaren',
        'date':     date(year, 7, muzieknacht_day).isoformat(),
        'city':     'Zuidlaren',
        'province': 'Drenthe',
        'genre':    'pop',
        'source':   'drenthe.nl',
        'url':      'https://naarzuidlaren.nl/evenementen/',
        'note':     'Jaarlijks in juli; meerdere venues in Zuidlaren',
    })

    # Berend Botje Festival → wordt gescraped via scrape_naarzuidlaren.py (dynamische datum)

# ── VOEG HIER NIEUWE EVENTS TOE ──────────────────────────────────────────
    # Patroon:
    # events.append({
    #     'title':    'Naam van het event',
    #     'date':     date(year, maand, dag).isoformat(),
    #     'city':     'Stad',
    #     'province': 'Groningen' / 'Drenthe' / 'Friesland',
    #     'genre':    'festival' / 'pop' / 'theater' / 'overig',
    #     'source':   'visitgroningen' / 'drenthe.nl' / 'friesland.nl',
    #     'url':      'https://...',
    # })

    return events


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    year   = date.today().year
    events = build_events(year)
    today  = date.today().isoformat()

    found = added = 0
    for e in events:
        if e['date'] < today:
            continue  # verleden; sla over
        found += 1
        if dry_run:
            print(f"  [{e['date']}] {e['genre']:10s} {e['title']} ({e['city']}, {e['province']})")
            if 'note' in e:
                print(f"              → {e['note']}")
        else:
            row = {k: v for k, v in e.items() if k != 'note'}
            if insert_event(row):
                added += 1

    if not dry_run:
        log_scrape('handmatig', found, added)
        print(f"✓ Klaar: {found} events, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} toekomstige events")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    year = date.today().year
    print(f"Handmatige events voor {year} ({'dry-run' if args.dry_run else 'live'})...")
    scrape(dry_run=args.dry_run)
