"""
scrape_friesland.py — scrape friesland.nl/nl/plannen/evenementen/agenda

Gebruik:
    python scrape_friesland.py              # scrape, sla op in DB
    python scrape_friesland.py --dry-run    # toon events zonder op te slaan

Na afloop:
    python events_db.py export     # exporteer DB naar events_categorized.json
    python gen_uitjes.py           # genereer index.html

Noot: friesland.nl heeft ~1236 events op ~69 pagina's (?page=N).
Event-links: /nl/plannen/evenementen/agenda/ID/slug
"""

import urllib.request
import ssl
import re
import time
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SOURCE   = 'friesland.nl'
BASE_URL = 'https://www.friesland.nl/nl/plannen/evenementen/agenda'
PROVINCE = 'Friesland'
TODAY    = date.today().isoformat()
PER_PAGE = 18

# Titelwoorden → skip (activiteiten, geen evenementen)
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
    'wadlopen', 'vogelexcursie', 'vlinderexcursie',
    'seizoenswandeling', 'veenexcursie', 'wilde bloemen',
    'kayak', 'kajakken', 'sloeptocht',
    'open tuin',
    'beurtveer',
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
                             'lemsterwike', 'volksvermaak', 'monumentendag',
                             'marktfeest', 'havenfeest', 'straatfestival')):
        return 'Festival'
    if any(w in t for w in ('skûtsjesilen', 'skutsjesilen', 'kaatswedstrijd',
                             'fierljep', 'profronde', 'race', 'autocross',
                             'kampioenschap', 'wedstrijd', 'toernooi')):
        return 'Sport'
    if any(w in t for w in ('concert', 'muziek', 'optreden', 'livemuziek',
                             'zomerconcert', 'zangavond', 'band', 'tribute',
                             'session', 'lazy sunday')):
        return 'Muziek'
    if any(w in t for w in ('theater', 'voorstelling', 'cabaret', 'musical',
                             'opera', 'toneel', 'straattheater', 'imaginarium')):
        return 'Theater'
    if any(w in t for w in ('markt', 'braderie', 'beurs', 'vlooienmarkt')):
        return 'overig'
    return 'overig'


def parse_page(html: str) -> list[dict]:
    """Parse één pagina resultaten, geef lijst van ruwe event-dicts terug."""
    titles   = [unescape(t) for t in
                re.findall(r'<span class="description__headtext[^"]*">([^<]+)</span>', html)]
    date_raw = re.findall(r'<p class="description__date[^"]*">(.*?)</p>', html, re.DOTALL)
    cities   = re.findall(
        r'city-description__wrapper[^>]*>.*?<span class="description__text">([^<]+)</span>',
        html, re.DOTALL)
    links    = re.findall(r'href="(/nl/plannen/evenementen/agenda/\d[^"]+)"', html)
    return [
        {
            'title':    titles[i],
            'date_str': date_raw[i].strip() if i < len(date_raw) else '',
            'city':     unescape(cities[i]).title() if i < len(cities) else '',
            'url':      'https://www.friesland.nl' + links[i] if i < len(links) else '',
        }
        for i in range(len(titles))
    ]


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0

    # Pagina 1: ook totaal aantal detecteren
    url1 = f"{BASE_URL}?page=1"
    print(f"  Ophalen {url1}...", end=' ', flush=True)
    try:
        html1 = fetch(url1)
    except Exception as e:
        print(f"FOUT: {e}")
        return 0, 0

    total_m = re.search(r'van\s+([\d.]+)\s+resultaten', html1)
    total   = int(total_m.group(1).replace('.', '')) if total_m else 1236
    n_pages = (total + PER_PAGE - 1) // PER_PAGE
    print(f"{total} events op {n_pages} pagina's")

    all_raw = parse_page(html1)

    for p in range(2, n_pages + 1):
        try:
            html = fetch(f"{BASE_URL}?page={p}")
            all_raw.extend(parse_page(html))
            if p % 10 == 0:
                print(f"    pagina {p}/{n_pages} ({len(all_raw)} verzameld)")
            time.sleep(0.25)
        except Exception as e:
            print(f"  Pagina {p} fout: {e}")

    print(f"  Totaal opgehaald: {len(all_raw)} kandidaten")

    for raw in all_raw:
        title = raw['title']
        if not should_include(title):
            continue

        parsed = parse_date(raw['date_str'])
        if not parsed:
            continue

        found += 1
        city  = raw['city']
        url_e = raw['url']
        genre = genre_from_title(title)

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
            print(f"    [{parsed}] {genre:10s} {title[:55]} ({city})")

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

    print(f"Scraping friesland.nl ({BASE_URL}) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
