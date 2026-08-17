"""
scrape_drenthe.py — scrape festivals en evenementen van drenthe.nl

Gebruik:
    python scrape_drenthe.py              # scrape alle pagina's, sla op in DB
    python scrape_drenthe.py --dry-run    # toon events zonder op te slaan
    python scrape_drenthe.py --max 5      # max 5 pagina's (test)

Na afloop:
    python events_db.py export     # exporteer DB naar events_categorized.json
    python gen_uitjes.py           # genereer index.html

Noot: drenthe.nl (plaece.nl) heeft geen tags op de listingpagina, dus
we filteren op trefwoorden in de titel.
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

SOURCE   = 'drenthe.nl'
BASE_URL = 'https://www.drenthe.nl/evenementen-activiteiten/evenementen'
PROVINCE = 'Drenthe'
TODAY    = date.today().isoformat()

# Titelwoorden die duidelijk op een interessant event wijzen
WANTED_TITLE_WORDS = {
    'festival', 'concert', 'optreden', 'muziek', 'live', 'feest',
    'show', 'theater', 'voorstelling', 'cabaret', 'musical',
    'sport', 'race', 'rally', 'run', 'triatlon', 'wedstrijd',
    'marathon', 'toernooi', 'kampioenschap', 'fair', 'expo',
    'market', 'podium', 'zomerkermis', 'kermis', 'volksfeest',
}

# Titelwoorden die we overslaan
SKIP_TITLE_WORDS = {
    'wandeling', 'wandeltocht', 'excursie', 'rondleiding', 'rondvaart',
    'workshop', 'cursus', 'lezing', 'meditatie', 'meditatief', 'yoga',
    'orgelconcert', 'orgelbespeling',
    'tentoonstelling', 'expositie',
    'boekenmarkt', 'vlooienmarkt', 'rommelmarkt', 'kofferbakmarkt',
    'fiets4daagse', 'fietstocht',
    'openluchtdienst', 'kerkdienst',
    'proeverij', 'kookworkshop',
    'kabouterspoor', 'puzzelrit',
    'weekmarkt', 'braderie',
    'schapenknipdagen', 'schapenscheren',
    'springwedstrijd',  # paardensport, te niche
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
    """Pakt de datum uit de datumstring. Retourneert (start_iso, end_iso).

    Bij een volledig bereik ("21 t/m 23 augustus" — start- én einddag,
    zelfde maand in alle 102 geziene gevallen, geen cross-month-bereiken
    aangetroffen op drenthe.nl) wordt nu ook echt een `date_end` herkend —
    voorheen ving de regex de "t/m N" wel op maar gooide 'm meteen weg via
    een non-capturing group, dus een 3-daags evenement als Zomerfeest Eext
    kwam alleen op zijn eerste dag in de agenda te staan (gemeld door
    Michiel, zie decisions.md 2026-08-17).

    Let op — bewust NIET aangepakt in deze fix: strings die ALLEEN een
    einddatum tonen zonder startdag ("t/m 23 augustus", ~150 gevallen op
    drenthe.nl, vermoedelijk al eerder begonnen doorlopende dingen). Die
    blijven met de oude (onvolledige, maar niet per se meer fout dan
    voorheen) aanname behandeld: de regex leest het cijfer na "t/m" als
    losse startdag en levert geen einddatum. Een echte fix hiervoor vereist
    een aanname over de onbekende startdatum — bewust niet gegokt, zie
    overleg.md."""
    s = date_str.strip().lower()

    # Skip terugkerende events
    if any(w in s for w in ('wekelijks', 'maandelijks', 'dagelijks')):
        return None

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

    # Volledig bereik: "21 t/m 23 augustus" — start- en einddag samen.
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
        # Defensief: als de startdatum over de jaarwisseling gerold is
        # (roll_year=True) maar de eindberekening niet, kan end < start
        # uitkomen — val dan terug op end=start i.p.v. een omgekeerd
        # bereik op te slaan.
        if not end or end < start:
            end = start
        return start.isoformat(), end.isoformat()

    # Enkele datum (of een "t/m N maand"-tekst zonder startdag — zie de
    # docstring hierboven, bewust ongewijzigd gedrag voor dat geval).
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


def should_include(title: str) -> bool:
    """Filter op basis van titelwoorden. True = meenemen."""
    t = title.lower()

    # Expliciete skip
    if any(w in t for w in SKIP_TITLE_WORDS):
        return False

    # Expliciete match → meenemen
    if any(w in t for w in WANTED_TITLE_WORDS):
        return True

    # Verder niets: meenemen als het een specifieke datum heeft (geen recurring)
    # (recurring events zijn al uitgefilterd via parse_date)
    return True


def genre_from_title(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ('festival', 'feest', 'fair', 'volksfeest', 'kermis')):
        return 'Festival'
    if any(w in t for w in ('sport', 'race', 'rally', 'run', 'marathon',
                             'toernooi', 'wedstrijd', 'kampioenschap', 'triatlon',
                             'truck', 'truckstar', 'pulldag', 'tractorpulling',
                             'waterpolo', 'voetbal', 'wielren')):
        return 'Sport'
    if any(w in t for w in ('concert', 'muziek', 'optreden', 'live', 'podium',
                             'muziekavond', 'session', 'tribute', 'band',
                             'zangavond', 'zangeres', 'zanger')):
        return 'Muziek'
    if any(w in t for w in ('theater', 'voorstelling', 'cabaret', 'musical',
                             'straattheater', 'toneel', 'openluchtspel',
                             'theatervoorstelling', 'buitentheater', 'vr-voorstelling')):
        return 'Theater'
    return 'overig'


def parse_page(html: str) -> list[dict]:
    """
    Parse evenementkaarten van drenthe.nl (plaece.nl platform).
    HTML-structuur per kaart (verschilt van visitgroningen.nl!):
        <span class="description__headtext tiles__title-txt ">Titel</span>
        <a href="/evenementen-activiteiten/ID/slug" class="link-overlay">
        <p class="description__date ...">datum</p>
        <address class="...city-description__wrapper...">
            <span class="description__text">Stad</span>
        </address>
        (geen tile__tag op listing-pagina)
    """
    events = []

    titles   = [unescape(t) for t in
                re.findall(r'<span class="description__headtext[^"]*">([^<]+)</span>', html)]
    date_raw = [d.strip() for d in
                re.findall(r'<p class="description__date[^"]*">([^<]+)</p>', html)]
    cities   = re.findall(
        r'city-description__wrapper[^>]*>.*?<span class="description__text">([^<]+)</span>',
        html, re.DOTALL)
    links    = re.findall(r'href="(/evenementen-activiteiten/\d[^"]+)"', html)

    n = min(len(titles), len(date_raw))

    for i in range(n):
        title = unescape(titles[i])

        if not should_include(title):
            continue

        parsed = parse_date(date_raw[i])
        if not parsed:
            continue
        start_iso, end_iso = parsed

        city  = unescape(cities[i]).title() if i < len(cities) else None
        url   = ('https://www.drenthe.nl' + links[i]) if i < len(links) else None
        genre = genre_from_title(title)

        ev = {
            'title':    title,
            'date':     start_iso,
            'city':     city,
            'province': PROVINCE,
            'genre':    genre,
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
    # (Niveau B, overleg.md punt 2 / decisions.md 2026-08-16). We weten het
    # aantal pagina's niet vooraf, dus fetch_batches() haalt ze in kleine
    # batches op en checkt na elke batch of we kunnen stoppen. Kan een paar
    # pagina's na het echte einde nog meepakken — bewuste, kleine afweging
    # voor de snelheidswinst (zie parallel_fetch.py).
    #
    # Stop-signaal is het ONTBREKEN van een "volgende pagina"-link, niet
    # "0 events" — ontdekt tijdens het bouwen (2026-08-16): drenthe.nl geeft
    # voorbij het echte einde gewoon een fallback-pagina terug met events
    # erop, dus "0 events" triggert hier nooit en het ophalen liep door tot
    # de veiligheidsgrens (105 pagina's i.p.v. de echte ~41). Zie
    # parallel_fetch.py's docstring voor de volledige les.
    def url_for(page: int) -> str:
        return f"{BASE_URL}?order=desc&sort=calendar&page={page}"

    def no_next_page(page: int, html: str) -> bool:
        return f'page={page + 1}' not in html

    batch_cap = max_pages if max_pages else 60
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

        # Geen "volgende pagina"-link meer: stop met verwerken, ook al zijn er
        # door de batch-fetch mogelijk al 1-4 pagina's verder opgehaald — die
        # negeren we dan gewoon (zelfde eind-signaal als de oude sequentiële
        # versie, alleen kan het ophalen zelf al iets verder gelopen zijn).
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
    parser.add_argument('--max', type=int, default=0, metavar='N')
    args = parser.parse_args()

    print(f"Scraping drenthe.nl ({'dry-run' if args.dry_run else 'live'})...")
    scrape(max_pages=args.max, dry_run=args.dry_run)
