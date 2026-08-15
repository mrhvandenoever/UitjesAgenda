"""
scrape_donar.py — Donar Groningen (basketbal, BNXT League) thuiswedstrijden

Gebruik:
    python scrape_donar.py              # scrape, sla op in DB
    python scrape_donar.py --dry-run    # toon events zonder op te slaan

Bron: niet donar.nl zelf (Next.js, geen bruikbare API gevonden — zie
SCRAPERS.md voor de 3 eerder onderzochte doodlopende paden), maar de
OFFICIËLE BNXT LEAGUE-SITE (bnxtleague.com). Die draait op een bespoke CMS
"Sportpress" van bureau Webpont (webpont.com/sportpress, specifiek voor deze
competitie gebouwd) met een publieke JSON-API op bnxt.sportpress.info.

Gevonden 2026-08-15 door de JS-bundle van bnxtleague.com te doorzoeken op
"sportpress.info/api" — de site's eigen frontend gebruikt exact deze calls,
inclusief een statische "X-Authorization"-token die gewoon in de publiek
uitgeleverde JS staat (geen login, geen secret — een publieke frontend-key
zoals vaker bij dit soort sites, zelfde categorie als de Sportlink-API die
scrape_handbal.py gebruikt).

API-mechaniek (uitgezocht via trial-and-error, geen officiële documentatie):
  - GET /api/v1/phase/season/{jaar}  -> competition_id + lijst met phases
    (Regular season, Supercup, Playoffs...) voor dat seizoen. Seizoen wordt
    genoemd naar het EINDJAAR, bv. 2026-2027 heet "2027".
  - GET /api/v1/competition-team/all?competition_id={id}  -> alle teams
    (en hun eigen, per-competitie team-id) in die competitie.
  - GET /api/v1/schedule/club/{seizoen}?phase_id=..&competition_team_id=..&
    clubs[0]=1&clubs[1]=2&monthCount=12[&month=1..12]
    -> wedstrijden. LET OP: het "club" in het pad is verwarrend genoemd —
    dat is het SEIZOEN (bv. "2027"), niet een team-id; de team-filter zit in
    de query-param competition_team_id. Zonder `month`-param komen alleen de
    eerste ~3 maanden mee; met expliciete month=1..12 (schijnbaar 1=januari)
    komt de rest. We halen daarom zowel de default-call als month=1..12 op
    en dedupliceren op wedstrijd-id — zo blijft het hele seizoen (getest:
    30 wedstrijden voor Donar in 2026-2027, okt t/m mei) gegarandeerd mee,
    ook al is de exacte paginering-logica niet volledig doorgrond.
  - "arena" in de response is altijd het veld van de THUISspelende club
    (competitors[side=1]) — vandaar het filter op side==1 voor "alleen
    thuiswedstrijden".

Kwetsbaar punt: de X-Authorization-token staat in een webpack-JS-bestand
met een content-hash in de bestandsnaam (bv. app.0a71633a.js) — bij een
nieuwe deploy van bnxtleague.com kan die hash (en in theorie de token)
wijzigen. Als deze scraper op een dag met 401-fouten faalt: open
bnxtleague.com, zoek de huidige /js/app.*.js, en grep daarin op
"X-Authorization" voor de nieuwe token.

scrape_landstede.py is de bijna-identieke tweelingbroer (zelfde API, andere
club) — bewust twee losse bestanden i.p.v. een gedeelde helper, zie
ARCHITECTURE.md §Scrapers-conventie / decisions.md.
"""

import urllib.request
import urllib.parse
import json
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE       = 'donar'
CLUB_NAME    = 'Donar'
DEFAULT_VENUE = 'MartiniPlaza, Groningen'
TICKET_URL   = 'https://www.donar.nl/tickets'

API_BASE = 'https://bnxt.sportpress.info/api/v1'
# Publieke frontend-token uit bnxtleague.com's eigen JS-bundle, zie docstring.
TOKEN    = 'BWSyE7sgg9QAurh2JX9cpjzjGc652BWLuNUS'


def fetch_json(path: str, params: dict) -> dict:
    url = f'{API_BASE}/{path}?{urllib.parse.urlencode(params, doseq=True)}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept': 'application/json',
        'X-Authorization': TOKEN,
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def current_season() -> str:
    """BNXT-seizoen genoemd naar het eindjaar (2026-2027 = '2027').
    Vanaf juli tellen we het nieuwe seizoen als 'aankomend'."""
    today = date.today()
    year = today.year + 1 if today.month >= 7 else today.year
    return str(year)


def find_regular_phase(season: str) -> tuple[int, int] | None:
    """-> (competition_id, phase_id) van de 'Regular season'-phase, of None."""
    data = fetch_json(f'phase/season/{season}', {})
    for entry in data.get('data', []):
        comp = entry.get('competition') or {}
        for phase in entry.get('phases', []):
            if 'regular season' in (phase.get('name') or '').lower():
                return comp.get('id'), phase.get('id')
    return None


def find_team_id(competition_id: int, name_fragment: str) -> int | None:
    data = fetch_json('competition-team/all', {'competition_id': competition_id})
    for t in data.get('data', []):
        if name_fragment.lower() in (t.get('name') or '').lower():
            return t.get('id')
    return None


def fetch_schedule(season: str, phase_id: int, team_id: int) -> list[dict]:
    games = {}
    for month in [None] + list(range(1, 13)):
        params = {
            'phase_id': phase_id,
            'monthCount': 12,
            'clubs[0]': 1,
            'clubs[1]': 2,
            'competition_team_id': team_id,
        }
        if month is not None:
            params['month'] = month
        data = fetch_json(f'schedule/club/{season}', params)
        for g in data.get('data', []):
            games[g['id']] = g
    return list(games.values())


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    season = current_season()
    try:
        phase = find_regular_phase(season)
        if not phase:
            print(f"  FOUT: geen 'Regular season'-phase gevonden voor seizoen {season}")
            return 0, 0
        competition_id, phase_id = phase
        team_id = find_team_id(competition_id, CLUB_NAME)
        if not team_id:
            print(f"  FOUT: team '{CLUB_NAME}' niet gevonden in competition_id {competition_id}")
            return 0, 0
        games = fetch_schedule(season, phase_id, team_id)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    found = added = 0
    all_events = []
    for g in sorted(games, key=lambda g: g['game_time']):
        competitors = g.get('competitors') or []
        home = next((c for c in competitors if c.get('side') == 1), None)
        away = next((c for c in competitors if c.get('side') == 2), None)
        if not home or not away:
            continue
        if home['competition_team'].get('id') != team_id:
            continue  # alleen thuiswedstrijden

        game_time = g.get('game_time') or ''
        game_date, _, game_clock = game_time.partition(' ')
        if not game_date:
            continue
        arena = ((g.get('arena') or {}).get('name') or '').strip()

        found += 1
        ev = {
            'title':  f"{home['competition_team']['name']} - {away['competition_team']['name']}",
            'date':   game_date,
            'time':   game_clock[:5] or None,
            'venue':  arena or DEFAULT_VENUE,
            'genre':  'sport',
            'sport':  'basketbal',
            'gender': 'heren',
            'source': SOURCE,
            'url':    TICKET_URL,
        }
        if dry_run:
            print(f"    [{ev['date']} {ev['time'] or '?'}] {ev['title']} @ {ev['venue']}")
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
        print(f"\nDry-run: {found} thuiswedstrijden gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping {CLUB_NAME} (BNXT League, via bnxtleague.com/Sportpress) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
