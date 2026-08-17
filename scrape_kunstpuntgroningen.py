"""
scrape_kunstpuntgroningen.py — Kunstpunt Groningen kunstagenda (aggregator)

Gebruik:
    python scrape_kunstpuntgroningen.py              # scrape, sla op in DB
    python scrape_kunstpuntgroningen.py --dry-run    # toon events zonder op te slaan

Ontstaan uit overleg.md punt 13 (Exposities uitbreiden): i.p.v. tientallen
losse kunstgalerieën elk een eigen scraper te geven, bleek kunstpuntgroningen.nl
zelf al een AGGREGATOR te zijn — een kunstagenda die exposities van tientallen
Groningse (en soms verder weg gelegen) instellingen bundelt: musea, galerieën,
kunstcentra. Precies hetzelfde principe als drenthe.nl/friesland.nl/
visitgroningen voor Uitjes. Toegevoegd aan AGGREGATOR_SOURCES in events_db.py
zodat een directe-venue-scraper (bv. scrape_gekehoogstins.py voor Galerie DSG)
altijd voorrang krijgt bij een botsing — zelfde regel als bij Uitjes.

Alleen categorie "Exhibition" wordt meegenomen — de kalender bevat ook
workshops/lezingen/concerten/wandelroutes (40+ categorieën in totaal).
Genre-signaal wordt doorgegeven via cats=['expositie'] i.p.v. te vertrouwen
op classify()'s (Nederlandse) titel-keywords — de titels hier zijn vaak
Engels.

Voor elke expositie wordt naast de listing-pagina ook de eigen detailpagina
opgehaald (gelijktijdig, via parallel_fetch):
  - de link (`url`) op de detailpagina is Kunstpunt's EIGEN artikel-URL, niet
    de homepage van de galerie zelf — geverifieerd (2026-08-17): de meeste
    kleine galerieën linken op hun beurt alleen naar hun eigen algemene
    homepage (geen eigen expositie-pagina per stuk), dus Kunstpunt's eigen
    pagina IS de specifiekste beschikbare link voor deze ene expositie.
  - de detailpagina bevat ook de exacte lat/lon van de venue, ingebed als
    kaart-marker-data (HTML-entity-encoded: `&quot;lat&quot;:53.14,
    &quot;lng&quot;:6.43`). Preciezer dan de bestaande city_coords.json-
    lookup, en dekt ook plaatsen die daar niet in staan (bv. Zuidhorn,
    Sappemeer, Slochteren). gen_uitjes.py's event_html()/expo_card_html()
    zijn hiervoor uitgebreid met een lat/lon-eerst-prioriteit (was tot nu
    toe ongebruikte infrastructuur, zie decisions.md 2026-08-17).
"""

import urllib.request
import re
import html as html_lib
import argparse
from datetime import date
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged
from ssl_fix import create_context
from parallel_fetch import fetch_many

SSL_CTX = create_context()

SOURCE   = 'kunstpuntgroningen'
BASE_URL = 'https://www.kunstpuntgroningen.nl/en/art-calendar/'

MONTHS_EN = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

# Klein, handmatig — dekt de plaatsen die op 2026-08-17 daadwerkelijk
# voorkwamen. Onbekende plaatsen vallen terug op 'Onbekend', zelfde patroon
# als de "Winsum-Obergum"/"Zuidwest-Drenthe"-restgevallen elders (decisions.md).
CITY_PROVINCE = {
    'Groningen': 'Groningen', 'Zuidhorn': 'Groningen', 'Leek': 'Groningen',
    'Sappemeer': 'Groningen', 'Slochteren': 'Groningen',
    'Roden': 'Drenthe', 'Assen': 'Drenthe',
}

# 'Venue wint van aggregator' (AGGREGATOR_SOURCES in events_db.py) werkt via
# fuzzy TITEL-matching op EXACT dezelfde datum — en faalt dus zowel bij een
# vertaalde titel als bij een datum die 1 dag verschilt tussen bron en
# aggregator (find_cross_source_duplicates() groepeert strikt per datum, dus
# vergelijkt zulke paren nooit). Twee bevestigde gevallen (2026-08-17):
# - "The experience of Drenthe" (Galerie DSG) = scrape_gekehoogstins.py's
#   "groepsexpositie DSG 'De beleving van Drenthe'" (Geke Hoogstins is
#   DSG-lid, haar site volgt DSG's groepstentoonstellingen al) — geen woord
#   gemeenschappelijk.
# - "Bakstain" (Groninger Museum) = scrape_groningermuseum.py's eigen
#   "Bakstain" maar dan 1 dag eerder (05-08 vs 05-09) — zelfde titel, maar
#   de datum-groepering in find_cross_source_duplicates() vergelijkt ze
#   daardoor nooit.
# Geen generieke cross-taal/datum-tolerante matcher gebouwd voor deze 2
# gevallen — gewoon deze venues overslaan, ze komen al binnen via hun eigen,
# preciezere directe scraper.
SKIP_VENUES = {'Galerie DSG', 'Groninger Museum'}

LIST_PATTERN = re.compile(
    r'<article class="m-post[^"]*">\s*<a href="([^"]+)"[^>]*>.*?'
    r'<span class="m-post__meta">([^<]*)</span>\s*'
    r'<h2[^>]*>([^<]*)</h2>\s*'
    r'<div class="m-post__subtitle">([^<]*)</div>\s*'
    r'<div class="m-post__details">([^<]*)</div>',
    re.S
)
LATLNG_PATTERN = re.compile(r'&quot;lat&quot;:(\d+\.\d+),&quot;lng&quot;:(\d+\.\d+)')
LAST_PAGE_PATTERN = re.compile(r'&quot;last_page&quot;:(\d+)')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; uitjesagenda-bot/1.0)',
    })
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read().decode('utf-8')


def parse_date_range(text: str) -> tuple[str, str] | None:
    """'1 August 2026 to 23 August 2026' -> (start_iso, end_iso)."""
    m = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})\s+to\s+(\d{1,2})\s+(\w+)\s+(\d{4})', text.strip())
    if not m:
        return None
    d1, mo1, y1, d2, mo2, y2 = m.groups()
    m1, m2 = MONTHS_EN.get(mo1.lower()), MONTHS_EN.get(mo2.lower())
    if not m1 or not m2:
        return None
    try:
        start = date(int(y1), m1, int(d1))
        end = date(int(y2), m2, int(d2))
    except ValueError:
        return None
    return start.isoformat(), end.isoformat()


def extract_city(address_line2: str) -> str:
    """'9301 LT Roden' of '9801CG Zuidhorn' -> 'Roden'/'Zuidhorn'. Geen
    postcode herkend (bv. 'Groningen' zonder postcode) -> ongewijzigd."""
    m = re.match(r'^\d{4}\s?[A-Za-z]{2}\s+(.+)$', address_line2.strip())
    return (m.group(1) if m else address_line2).strip()


def parse_listing(html_text: str) -> list[dict]:
    events = []
    for url, meta, title, venue, details in LIST_PATTERN.findall(html_text):
        if 'exhibition' not in meta.lower():
            continue
        title = html_lib.unescape(title).strip()
        if not title or title.lower() == 'no title':
            continue
        venue_clean = html_lib.unescape(venue).strip()
        if venue_clean in SKIP_VENUES:
            continue
        rng = parse_date_range(details)
        if not rng:
            continue
        start_iso, end_iso = rng
        ev = {
            'title':  title,
            'date':   start_iso,
            'venue':  venue_clean,
            'url':    url,
            'source': SOURCE,
            'cats':   ['expositie'],
        }
        if end_iso != start_iso:
            ev['date_end'] = end_iso
        events.append(ev)
    return events


def enrich_with_detail(ev: dict, detail_html: str) -> None:
    """Best-effort: lat/lon + city/province uit de detailpagina halen. Geen
    harde eis — als het niet lukt blijft het event gewoon zonder, net als
    elders in het project (bv. events zonder herkende city)."""
    m = LATLNG_PATTERN.search(detail_html)
    if m:
        ev['lat'], ev['lon'] = float(m.group(1)), float(m.group(2))
    addr_m = re.search(
        re.escape(ev['venue']) + r'<br>\s*([^<]*)<br>\s*([^<]*)<br>', detail_html)
    if addr_m:
        city = extract_city(addr_m.group(2))
        # Sommige venues hebben een afwijkend adres-widget-formaat (bv. Forma
        # Aktua toont een telefoonnummer i.p.v. een postcoderegel op de
        # verwachte plek) — een "stad" met cijfers erin is duidelijk fout,
        # dan liever geen city/province dan een misleidende.
        if city and not any(ch.isdigit() for ch in city):
            ev['city'] = city
            ev['province'] = CITY_PROVINCE.get(city, 'Onbekend')


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    try:
        html1 = fetch(BASE_URL)
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    m = LAST_PAGE_PATTERN.search(html1)
    last_page = int(m.group(1)) if m else 1
    print(f"  {last_page} pagina('s) in de kalender")

    all_html = [html1]
    if last_page > 1:
        pages = [f'{BASE_URL}?pag={p}' for p in range(2, last_page + 1)]
        for html_page, exc in fetch_many(pages, fetch):
            if exc is not None:
                print(f"  Pagina-fout: {exc}")
                continue
            all_html.append(html_page)

    all_events = []
    for h in all_html:
        all_events.extend(parse_listing(h))
    found = len(all_events)
    print(f"  {found} exposities gevonden, detailpagina's ophalen voor locatie...")

    # Detailpagina's gelijktijdig ophalen — de listing-pagina zelf bevat geen
    # lat/lon/adres, alleen de detailpagina per expositie.
    detail_results = fetch_many([e['url'] for e in all_events], fetch)
    for ev, (detail_html, exc) in zip(all_events, detail_results):
        if exc is None:
            enrich_with_detail(ev, detail_html)

    if dry_run:
        for ev in all_events:
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']} "
                  f"({ev.get('venue','')}, {ev.get('city','?')})")
        print(f"\nDry-run: {found} events gevonden (niets opgeslagen)")
        return found, 0

    if unchanged(SOURCE, all_events):
        log_scrape(SOURCE, found, 0, notes='ongewijzigd sinds vorige run, geskipt')
        print(f"✓ Klaar: {found} gevonden, geen wijzigingen sinds vorige run (geskipt)")
        return found, 0

    added = 0
    for ev in all_events:
        if insert_event(ev):
            added += 1
    log_scrape(SOURCE, found, added)
    print(f"✓ Klaar: {found} gevonden, {added} nieuw in DB")
    return found, added


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Scraping Kunstpunt Groningen [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
