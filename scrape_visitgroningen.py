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
import time
import argparse
from datetime import datetime, date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

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


def parse_date(date_str: str) -> str | None:
    """Zet datumstring om naar YYYY-MM-DD. Pakt de eerste datum uit de string."""
    s = date_str.strip().lower()
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

        events.append({
            'title':    title,
            'date':     parsed,
            'city':     city,
            'province': PROVINCE,
            'genre':    genre,
            'category': tag,
            'source':   SOURCE,
            'url':      url,
        })

    return events


def scrape(max_pages: int = 0, dry_run: bool = False) -> tuple[int, int]:
    init_db()
    found = added = 0
    all_events = []
    page  = 1

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
    parser.add_argument('--max', type=int, default=0, metavar='N',
                        help='maximaal N paginas (0 = alles)')
    args = parser.parse_args()

    print(f"Scraping visitgroningen.nl ({'dry-run' if args.dry_run else 'live'})...")
    scrape(max_pages=args.max, dry_run=args.dry_run)
