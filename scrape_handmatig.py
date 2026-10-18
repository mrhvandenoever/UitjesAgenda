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

    # Bommen Berend — 28 augustus, kermis in Groningen (herdenking ontzet stad 1672)
    bommen = date(year, 8, 28)
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

    # Zuidlaardermarkt-feestweek — meerdaags: kermis opent de vrijdag voor de
    # paardenmarkt (3e dinsdag van oktober) en loopt t/m de woensdag erna
    # (bevestigd 2026-10-18 via evenementenzuidlaardermarkt.nl: opening vr 16 okt,
    # koopzondag/straattheater, ouderenmiddag, paardenmarkt + warenmarkt di 20 okt,
    # kindermiddag wo 21 okt). Eén event met date_end i.p.v. losse eendagsrijen,
    # zodat het onder "Nu lopend" valt zolang de feestweek loopt.
    pm_date = nth_weekday(year, 10, 3, 1)   # 3e dinsdag (weekday=1)
    events.append({
        'title':    'Zuidlaardermarkt – feestweek met kermis, paardenmarkt & warenmarkt',
        'date':     (pm_date - timedelta(days=4)).isoformat(),   # vrijdag ervoor
        'date_end': (pm_date + timedelta(days=1)).isoformat(),   # woensdag erna
        'city':     'Zuidlaren',
        'province': 'Drenthe',
        'location': 'Brink / centrum Zuidlaren',
        'genre':    'festival',
        'source':   'drenthe.nl',
        'url':      'https://www.evenementenzuidlaardermarkt.nl',
        'note':     "3e dinsdag oktober = paardenmarkt (Europa's grootste); kermis vr t/m wo",
    })

    # Losse onderdelen van het feestweek-programma (tynaarlo.nl/zuidlaardermarkt/programma,
    # 2026-10-18). Alleen de nog-niet-voorbije dagen komen door het filter in scrape().
    # Het feestweek-event hierboven dekt kermis/livemuziek/paardenmarkt; dit zijn de
    # aparte, los vindbare activiteiten. (Loop, kinderrommelmarkt en vuurwerk vallen op
    # za 17 okt, dus voor 2026 al voorbij.)
    for dag_offset, titel, tijd, plek in [
        (-2, 'Koopzondag met straattheater Zuidlaren', '13:00', 'Stationsweg / De Millystraat, Zuidlaren'),
        (-1, 'Prikkelarme middag op de kermis Zuidlaren', '13:00', 'Kermis Zuidlaren'),
        (-1, 'Ouderenmiddag Zuidlaardermarkt', '13:00', 'Brinkhotel Zuidlaren'),
        (+1, 'Kindermiddag Zuidlaardermarkt-kermis', '13:00', 'Op en rond de kermis, Zuidlaren'),
    ]:
        events.append({
            'title':    titel,
            'date':     (pm_date + timedelta(days=dag_offset)).isoformat(),
            'time':     tijd,
            'city':     'Zuidlaren',
            'province': 'Drenthe',
            'location': plek,
            'genre':    'festival',
            'source':   'drenthe.nl',
            'url':      'https://www.tynaarlo.nl/zuidlaardermarkt/programma',
            'note':     'Onderdeel Zuidlaardermarkt-feestweek',
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

    # Hurry-Up en E&O (handbal) → verplaatst naar scrape_handbal.py: echte
    # data via de handbal.nl/Sportlink-API (zie scraping_recipes.json). De
    # eerdere handmatige Hurry-Up-entries hier (uit een nieuwsartikel, met
    # geraden venue "Emmen") waren onnauwkeurig — echte venue is
    # "De Eendracht, Zwartemeer" — en zijn vervangen door de scraper.

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
        if (e.get('date_end') or e['date']) < today:
            continue  # verleden (einddatum voorbij); sla over
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
