"""
scrape_forum.py — Forum Groningen agenda

Gebruik:
    python scrape_forum.py              # scrape, sla op in DB
    python scrape_forum.py --dry-run    # toon events zonder op te slaan

forum.nl mixt bibliotheek-/sociale activiteiten door de echte agenda heen
(leesclub, digihuis, spreekuur, etc.) — SKIP-lijst filtert die eruit.
Titel wordt afgeleid van de URL-slug (geen aparte titeltekst dicht bij de
link beschikbaar zonder complexere parsing).

Doorlopende items (bv. exposities als "Marilyn Expositie"/"Storyworld")
staan in forum.nl's eigen agenda als een LOSSE rij per dag i.p.v. één rij
met een datumbereik (ontdekt 2026-08-16, zie overleg.md punt 12/decisions.md
2026-08-16). merge_consecutive_days() groepeert per slug opeenvolgende
kalenderdagen tot één event met `date`/`date_end` — een run van 1 dag blijft
gewoon een normaal event zonder date_end. Bewust op OPEENVOLGENDE dagen
gebaseerd (niet "alle dagen van dezelfde slug samen"): een wekelijks
terugkerend programma (bv. "informatieplein-lewenborg", elke week op
dinsdag) heeft dan vanzelf meerdere losse runs van 1 dag i.p.v. onterecht
één lange datumrange, en een exhibitie die een dag dicht is (gat in de
reeks) valt vanzelf uiteen in twee losse, correcte runs i.p.v. dat gat te
overbruggen.
"""

import urllib.request
import re
import argparse
from datetime import date, timedelta
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from parallel_fetch import fetch_many

SOURCE   = 'forum.nl'
BASE_URL = 'https://forum.nl/nl/agenda'
VENUE    = 'Forum Groningen'

SKIP = ['leesclub', 'taalcafe', 'digihuis', 'spreekuur', 'breinbieb',
        'spelochtend', 'inloop', '3d-print', '/film/', 'klik-tik',
        'informatiepunt', 'schrijfhulp', 'computerhulp']


def fetch(page: int) -> str:
    req = urllib.request.Request(
        f'{BASE_URL}?p={page}',
        headers={'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)'}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def merge_consecutive_days(dates: list[str]) -> list[tuple[str, str]]:
    """Groepeer een lijst ISO-datums in runs van opeenvolgende kalenderdagen.
    Retourneert (start, eind) per run — eind==start bij een losse dag."""
    dates = sorted(set(dates))
    if not dates:
        return []
    runs = []
    run_start = run_end = dates[0]
    for d in dates[1:]:
        if date.fromisoformat(d) == date.fromisoformat(run_end) + timedelta(days=1):
            run_end = d
        else:
            runs.append((run_start, run_end))
            run_start = run_end = d
    runs.append((run_start, run_end))
    return runs


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0

    # De 7 pagina's zijn een vast, klein maximum — gewoon allemaal gelijktijdig
    # ophalen (Niveau B, overleg.md punt 2 / decisions.md 2026-08-16), maar
    # nog steeds in paginavolgorde VERWERKEN en stoppen bij de eerste lege
    # pagina, exact zoals de oude sequentiële versie.
    by_slug = {}  # slug -> (base_url, set van ISO-datums)
    pages = list(range(1, 8))
    for page, (html, exc) in zip(pages, fetch_many(pages, fetch)):
        if exc is not None:
            print(f"  Pagina {page} fout: {exc}")
            continue

        matches = list(re.finditer(
            r'data-href="(https://forum\.nl/nl/agenda/([^?]+)\?date=(\d{2})-(\d{2})-(\d{4}))"', html
        ))
        if not matches:
            break

        for m in matches:
            url, slug, d, mo, y = m.groups()
            if any(s in url for s in SKIP):
                continue
            base_url, dates = by_slug.setdefault(slug, (url.split('?')[0], set()))
            dates.add(f'{y}-{mo}-{d}')

    # Per slug de opeenvolgende-dagen-runs omzetten naar events (zie
    # merge_consecutive_days()-docstring hierboven voor de motivatie).
    all_events = []
    for slug, (base_url, dates) in by_slug.items():
        title = slug.replace('-', ' ').title()
        for start, end in merge_consecutive_days(list(dates)):
            found += 1
            ev = {
                'title':  title,
                'date':   start,
                'venue':  VENUE,
                'source': SOURCE,
            }
            if start == end:
                # losse dag: zelfde per-dag-URL als voorheen
                ev['url'] = f'{base_url}?date={start[8:10]}-{start[5:7]}-{start[0:4]}'
            else:
                ev['date_end'] = end
                ev['url'] = base_url
            if dry_run:
                end_txt = f' t/m {ev["date_end"]}' if 'date_end' in ev else ''
                print(f"    [{ev['date']}{end_txt}] {ev['title']}")
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

    print(f"Scraping Forum Groningen [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
