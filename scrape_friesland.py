"""
scrape_friesland.py — scrape festivals en evenementen van friesland.nl

Gebruik:
    python scrape_friesland.py              # scrape, sla op in DB
    python scrape_friesland.py --dry-run    # toon events zonder op te slaan

Na afloop:
    python events_db.py export     # exporteer DB naar events_categorized.json
    python gen_uitjes.py           # genereer index.html

Noot: friesland.nl heeft ~64 events op één pagina (geen paginering).
Event-links: /nl/plannen/evenementen/agenda/ID/slug
"""

import urllib.request
import ssl
import re
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SOURCE   = 'friesland.nl'
BASE_URL = 'https://www.friesland.nl/agenda'
PROVINCE = 'Friesland'
TODAY    = date.today().isoformat()

# Titelwoorden → skip
SKIP_TITLE_WORDS = {
    'rondvaart', 'dagtocht', 'kanotocht', 'zeehondentocht', 'etmaal op de waddenzee',
    'wandeling', 'wandeltocht', 'excursie', 'rondleiding',
    'expositie', 'tentoonstelling', 'fotoexpositie', 'kunstexpositie',
    'workshop', 'cursus', 'lezing', 'meditatie', 'yoga',
    'openluchtdienst', 'kerkdienst',
    'wellness', 'sauna',
    'zeilen voor volwassenen', 'zeilmaatjes', 'zeilweekend', 'zeilreis',
    'zwaardbootles', 'zeilweek',
    'openstelling bruggen',
    'zwembad', 'zwemmen',
    'fietsweek', 'fietstocht', 'fietslan',
    'ouder-kind-dag',
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
    s = date_str.strip().lower()
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
    t = title.lower()
    return not any(w in t for w in SKIP_TITLE_WORDS)


def genre_from_title(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ('festival', 'feest', 'ballonfeesten', 'sneekweek',
                             'lemsterwike', 'volksvermaak', 'monumentendag')):
        return 'Festival'
    if any(w in t for w in ('skûtsjesilen', 'skutsjesilen', 'kaatswedstrijd',
                             'fierljep', 'profronde', 'sup ', 'zeilen', 'race',
                             'kampioenschap', 'wedstrijd', 'toernooi', 'WK ', 'PC ')):
        return 'Sport'
    if any(w in t for w in ('concert', 'muziek', 'optreden', 'live', 'session',
                             'zomerconcert', 'zangavond', 'band', 'tribute')):
        return 'Muziek'
    if any(w in t for w in ('theater', 'voorstelling', 'cabaret', 'musical',
                             'opera', 'toneel', 'straattheater')):
        return 'Theater'
    return 'overig'


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0

    # friesland.nl heeft geen paginering — alles op één pagina
    url = f"{BASE_URL}?order=desc&sort=calendar&page=1"
    print(f"  Ophalen {url}...", end=' ', flush=True)

    try:
        html = fetch(url)
    except Exception as e:
        print(f"FOUT: {e}")
        return 0, 0

    titles = [unescape(t) for t in
              re.findall(r'<span class="description__headtext[^"]*">([^<]+)</span>', html)]
    date_raw = re.findall(r'<p class="description__date[^"]*">(.*?)</p>', html, re.DOTALL)
    cities   = re.findall(
        r'city-description__wrapper[^>]*>.*?<span class="description__text">([^<]+)</span>',
        html, re.DOTALL)
    links    = re.findall(r'href="(/nl/plannen/evenementen/agenda/\d[^"]+)"', html)

    print(f"{len(titles)} kandidaten")

    for i in range(min(len(titles), len(date_raw))):
        title = titles[i]

        if not should_include(title):
            continue

        parsed = parse_date(date_raw[i].strip())
        if not parsed:
            continue

        city  = unescape(cities[i]).title() if i < len(cities) else None
        url_e = ('https://www.friesland.nl' + links[i]) if i < len(links) else None
        genre = genre_from_title(title)

        found += 1
        if not dry_run:
            if insert_event({
                'title':    title,
                'date':     parsed,
                'city':     city,
                'province': PROVINCE,
                'genre':    genre,
                'source':   SOURCE,
                'url':      url_e,
            }):
                added += 1
        else:
            print(f"    [{parsed}] {genre:10s} {title[:50]} ({city or ''})")

    if not dry_run:
        log_scrape(SOURCE, found, added)
        print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    else:
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")

    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping friesland.nl ({'dry-run' if args.dry_run else 'live'})...")
    scrape(dry_run=args.dry_run)
