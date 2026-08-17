"""
scrape_visitgroningen.py — scrape festivals en evenementen van visitgroningen.nl

Gebruik:
    python scrape_visitgroningen.py              # scrape alle pagina's, sla op in DB
    python scrape_visitgroningen.py --dry-run    # toon events zonder op te slaan
    python scrape_visitgroningen.py --max 5      # max 5 pagina's (test)

Na afloop:
    python events_db.py export     # exporteer DB naar events_categorized.json
    python gen_uitjes.py           # genereer index.html
"""

import urllib.request
import ssl
import re
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context
from parallel_fetch import fetch_batches

SSL_CTX = create_context()

SOURCE   = 'visitgroningen'
BASE_URL = 'https://www.visitgroningen.nl/nl/doen/uitgaan'
PROVINCE = 'Groningen'
TODAY    = date.today().isoformat()

# Tags die we meenemen (case-insensitive, substring-match)
WANTED_TAGS = {
    'festival', 'muziekfestival', 'muziekfeest', 'cultureel festival',
    'muziek overig', 'muziek', 'concert', 'pop en rock', 'pop', 'rock',
    'jazz', 'klassieke muziek', 'elektronisch', 'folk', 'hip-hop',
    'wereldmuziek', 'r&b en soul', 'r&b',
    'cabaret', 'theater overig', 'toneel', 'jeugdtheater',
    'theatervoorstelling', 'dans', 'dance',
    'sportevenement', 'sport',
    'feest', 'popfeest', 'evenement', 'film',
}

# Tags die we altijd overslaan (exact of substring)
SKIP_TAGS = {
    'rondvaart', 'excursie', 'wandeltocht', 'fietstocht', 'buitensport',
    'watersport', 'wandeling', 'braderie', 'markt', 'rondleiding',
    'open dag', 'culinair', 'varia', 'beurs', 'rommelmarkt',
    'bezinning', 'tentoonstelling', 'expositie',
    'tekenen en schilderen', 'beeldende kunst', 'mode, textiel',
    'smartlab', 'werkplaats', 'workshop', 'pubquiz',
}

MONTHS_NL = {
    'januari': '01', 'februari': '02', 'maart': '03', 'april': '04',
    'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08',
    'september': '09', 'oktober': '10', 'november': '11', 'december': '12',
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
        'Accept-Language': 'nl-NL,nl;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return r.read().decode('utf-8')


def unescape(s: str) -> str:
    return (s.replace('&amp;', '&').replace('&#039;', "'")
             .replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').strip())


def parse_date(date_str: str) -> tuple[str, str | None] | None:
    """Zet datumstring om naar (start_iso, end_iso).

    Zelfde fix als scrape_drenthe.py (2026-08-17, zie decisions.md): een
    volledig bereik ("21 t/m 23 augustus" — start- én einddag) levert nu ook
    een date_end op. "t/m N maand" zonder zichtbare startdag blijft bewust
    ongewijzigd (ambigu, zie overleg.md)."""
    s = date_str.strip().lower()
    for dag in ('maandag', 'dinsdag', 'woensdag', 'donderdag',
                'vrijdag', 'zaterdag', 'zondag'):
        s = s.replace(dag, '').strip()

    year_m = re.search(r'\b(202\d)\b', s)
    year   = int(year_m.group(1)) if year_m else datetime.now().year

    def make_date(day: int, month_n: str, roll_year: bool) -> date | None:
        try:
            d = date(year, int(month_n), day)
        except ValueError:
            return None
        if roll_year and not year_m and d.isoformat() < TODAY:
            try:
                d = date(year + 1, int(month_n), day)
            except ValueError:
                return None
        return d

    m_range = re.search(
        r'(\d{1,2})\s*t/m\s*(\d{1,2})\s*'
        r'(januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)',
        s
    )
    if m_range:
        start_day, end_day, month_name = m_range.groups()
        month_n = MONTHS_NL.get(month_name)
        if not month_n:
            return None
        start = make_date(int(start_day), month_n, roll_year=True)
        if not start:
            return None
        end = make_date(int(end_day), month_n, roll_year=False)
        if not end or end < start:
            end = start
        return start.isoformat(), end.isoformat()

    m = re.search(
        r'(\d{1,2})\s*(?:t/m\s*\d{1,2}\s*)?'
        r'(januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)',
        s
    )
    if not m:
        return None

    month_n = MONTHS_NL.get(m.group(2))
    if not month_n:
        return None

    d = make_date(int(m.group(1)), month_n, roll_year=True)
    if not d:
        return None

    return d.isoformat(), None


def parse_page(html: str) -> list[dict]:
    """
    Parse evenementkaarten van visitgroningen.nl (plaece.nl platform).
    HTML-structuur per kaart:
        <span class="description__headtext tiles__title-txt ">Titel</span>
        <a href="/nl/doen/uitgaan/ID/slug" class="link-overlay">...</a>
        <p class="description__date ...">datum\\n                , stad</p>
        <p class="tile__tag">Categorie</p>
    """
    events = []

    titles   = [unescape(t) for t in
                re.findall(r'<span class="description__headtext[^"]*">([^<]+)</span>', html)]
    date_raw = re.findall(r'<p class="description__date[^"]*">(.*?)</p>', html, re.DOTALL)
    tags     = [unescape(t).strip() for t in
                re.findall(r'<p class="tile__tag">([^<]+)</p>', html)]
    links    = re.findall(r'href="(/nl/doen/uitgaan/\d[^"]+)"', html)

    n = min(len(titles), len(date_raw), len(tags))

    for i in range(n):
        tag       = tags[i]
        tag_lower = tag.lower()

        # Filter: skip unwanted
        if any(skip in tag_lower for skip in SKIP_TAGS):
            continue
        # Filter: alleen wanted (maar lege tag = meenemen)
        if tag_lower and not any(w in tag_lower for w in WANTED_TAGS):
            continue

        # Datum: eerste regel is datumtekst, tweede (na \n + ,) is stad
        raw   = date_raw[i]
        parts = [p.strip().lstrip(',').strip() for p in raw.split('\n') if p.strip()]
        date_part = parts[0] if parts else ''
        city_part = parts[-1] if len(parts) > 1 else None

        parsed = parse_date(date_part)
        if not parsed:
            continue
        start_iso, end_iso = parsed

        title = titles[i]
        url   = ('https://www.visitgroningen.nl' + links[i]) if i < len(links) else None
        city  = city_part.title() if city_part else None

        genre = (
            'Festival' if any(w in tag_lower for w in ('festival', 'feest')) else
            'Sport'    if 'sport' in tag_lower else
            'Muziek'   if any(w in tag_lower for w in (
                'muziek', 'concert', 'jazz', 'klassiek', 'elektronisch', 'folk',
                'hip-hop', 'wereldmuziek', 'r&b', 'pop', 'rock', 'dance')) else
            'Theater'  if any(w in tag_lower for w in (
                'theater', 'cabaret', 'comedy', 'dans', 'toneel', 'jeugd')) else
            'overig'
        )

        ev = {
            'title':    title,
            'date':     start_iso,
            'city':     city,
            'province': PROVINCE,
            'genre':    genre,
            'category': tag,
            'source':   SOURCE,
            'url':      url,
        }
        if end_iso and end_iso != start_iso:
            ev['date_end'] = end_iso
        events.append(ev)

    return events


def scrape(max_pages: int = 0, dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    all_events = []

    # Pagina's in batches van 5 gelijktijdig ophalen i.p.v. één voor één
    # (Niveau B, overleg.md punt 2 / decisions.md 2026-08-16). Stop-signaal
    # is het ontbreken van een "volgende pagina"-link (zelfde platform als
    # drenthe.nl — zie de les in scrape_drenthe.py/parallel_fetch.py: "0
    # events" bleek daar géén betrouwbaar eind-signaal, dit wél).
    def url_for(page: int) -> str:
        return f"{BASE_URL}?order=desc&sort=calendar&page={page}"

    def no_next_page(page: int, html: str) -> bool:
        return f'page={page + 1}' not in html

    # batch_cap: visitgroningen.nl bleek bij het bouwen (2026-08-16) ~70-79
    # echte pagina's te hebben (meer dan drenthe.nl's ~41, ondanks hetzelfde
    # platform) — ruime marge aangehouden, geen bevestigde bovengrens gemeten.
    batch_cap = max_pages if max_pages else 120
    fetched = fetch_batches(
        1, lambda p: fetch(url_for(p)), no_next_page,
        max_batches=(batch_cap // 5) + 1, stop_after_consecutive=1)

    for page, html, exc in fetched:
        if max_pages and page > max_pages:
            break
        if exc is not None:
            print(f"  Pagina {page}: FOUT: {exc}")
            continue

        events = parse_page(html)
        print(f"  Pagina {page}... {len(events)} events")

        for e in events:
            found += 1
            if not dry_run:
                all_events.append(e)
            else:
                print(f"    [{e['date']}] {e['genre']:10s} {e['title'][:50]} ({e.get('city','')})")

        if f'page={page + 1}' not in html:
            break

    if not dry_run:
        if unchanged(SOURCE, all_events):
            log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
            print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
            return found, 0
        for e in all_events:
            if insert_event(e):
                added += 1
        log_scrape(SOURCE, found, added)
        print(f"\n✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, default=0, metavar='N',
                        help='maximaal N paginas (0 = alles)')
    args = parser.parse_args()

    print(f"Scraping visitgroningen.nl ({'dry-run' if args.dry_run else 'live'})...")
    scrape(max_pages=args.max, dry_run=args.dry_run)
