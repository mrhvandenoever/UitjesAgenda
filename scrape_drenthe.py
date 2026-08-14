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
import time
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

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


def parse_date(date_str: str) -> str | None:
    """Pakt de eerste concrete datum uit de datumstring."""
    s = date_str.strip().lower()

    # Skip terugkerende events
    if any(w in s for w in ('wekelijks', 'maandelijks', 'dagelijks')):
        return None

    for dag in ('maandag', 'dinsdag', 'woensdag', 'donderdag',
                'vrijdag', 'zaterdag', 'zondag'):
        s = s.replace(dag, '').strip()

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

    year_m = re.search(r'\b(202\d)\b', s)
    year   = int(year_m.group(1)) if year_m else datetime.now().year

    try:
        d = date(year, int(month_n), int(m.group(1)))
    except ValueError:
        return None

    if not year_m and d.isoformat() < TODAY:
        try:
            d = date(year + 1, int(month_n), int(m.group(1)))
        except ValueError:
            return None

    return d.isoformat()


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

        city  = unescape(cities[i]).title() if i < len(cities) else None
        url   = ('https://www.drenthe.nl' + links[i]) if i < len(links) else None
        genre = genre_from_title(title)

        events.append({
            'title':    title,
            'date':     parsed,
            'city':     city,
            'province': PROVINCE,
            'genre':    genre,
            'source':   SOURCE,
            'url':      url,
        })

    return events


def scrape(max_pages: int = 0, dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    all_events = []
    page  = 1
    consecutive_empty = 0

    while True:
        url = f"{BASE_URL}?order=desc&sort=calendar&page={page}"
        print(f"  Pagina {page}...", end=' ', flush=True)

        try:
            html = fetch(url)
        except Exception as e:
            print(f"FOUT: {e}")
            break

        events = parse_page(html)
        print(f"{len(events)} events")

        if not events:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
        else:
            consecutive_empty = 0

        for e in events:
            found += 1
            if not dry_run:
                all_events.append(e)
            else:
                print(f"    [{e['date']}] {e['genre']:10s} {e['title'][:50]} ({e.get('city','')})")

        if f'page={page + 1}' not in html:
            break
        page += 1
        if max_pages and page > max_pages:
            break
        time.sleep(0.5)

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
