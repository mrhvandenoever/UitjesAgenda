"""
scrape_princessehof.py — Keramiekmuseum Princessehof (Leeuwarden)

Gebruik:
    python scrape_princessehof.py              # scrape, sla op in DB
    python scrape_princessehof.py --dry-run    # toon events zonder op te slaan

Gevonden via overleg.md punt 13 ("kleine venues zoeken" — Michiel,
2026-08-21). Nuxt.js (Vue) app: de titel-tag wordt per route server-side
gezet, maar de daadwerkelijke expositie-inhoud (titel, datumbereik) wordt
client-side gehydrateerd — geen bruikbare inhoud in de ruwe HTML, geen
onderliggende JSON-API gevonden bij een netwerkcheck (Browser pane). Dus
wél Playwright nodig, anders dan bij de meeste andere musea dit seizoen.
Extra complicatie: de listingpagina heeft 3 tabs ("Nu in het museum" /
"Verwacht" / "Geweest") die client-side wisselen welke links zichtbaar
zijn -- de scraper klikt daarom ook expliciet op "Verwacht" om die
exposities niet te missen (bv. "Koffie?", "Josiah Wedgwood").

Twee categorieën NIET meegenomen, bewust, geen aanname:
  - Permanente presentaties zonder tijdelijke einddatum ("Van Oost en
    West" -- expliciet "vaste presentatie" in de eigen tekst) en pagina's
    zonder enig datumpatroon (bv. "Gouden Vrienden", een jubileum-pagina
    zonder concrete loopperiode).
  - Alles waar de regex geen volledig "D maand JJJJ t/m D maand JJJJ"-
    patroon vindt -- deze bron toont in de geziene gevallen altijd het
    volledige jaartal aan beide kanten (schoner dan drenthe.nl/
    dmdebuitenplaats.nl), dus geen jaartal-aanname nodig zoals daar.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE       = 'princessehof'
BASE_URL     = 'https://princessehof.nl'
LISTING_URL  = f'{BASE_URL}/te-zien-en-te-doen/tentoonstellingen'
VENUE        = 'Keramiekmuseum Princessehof, Leeuwarden'
CITY         = 'Leeuwarden'
PROVINCE     = 'Friesland'
TODAY        = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}
MONTH_PAT = '|'.join(MONTHS_NL)
# Deze bron gebruikt per pagina een andere formulering voor hetzelfde
# datumbereik -- gezien zowel "D maand JJJJ t/m D maand JJJJ" (Van
# Achterberghprijs) als "van D maand JJJJ tot en met D maand JJJJ"
# (Sustainable Ceramics #2) -- vandaar beide varianten in één patroon.
RANGE_PAT = re.compile(
    rf'(?:van\s+)?(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})\s+(?:t/m|tot en met)\s+(\d{{1,2}})\s+({MONTH_PAT})\s+(\d{{4}})',
    re.I,
)


def parse_range(text: str) -> tuple[str, str] | None:
    m = RANGE_PAT.search(text)
    if not m:
        return None
    d1, mo1, y1, d2, mo2, y2 = m.groups()
    try:
        start = date(int(y1), MONTHS_NL[mo1.lower()], int(d1))
        end = date(int(y2), MONTHS_NL[mo2.lower()], int(d2))
    except ValueError:
        return None
    if end < start:
        return None
    return start.isoformat(), end.isoformat()


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()

    all_events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
            ))
            page.goto(LISTING_URL, timeout=30000, wait_until='networkidle')
            page.wait_for_timeout(1000)

            def collect_hrefs():
                return page.eval_on_selector_all(
                    'a[href*="/tentoonstellingen/"]',
                    'els => els.map(e => e.getAttribute("href"))'
                )

            # De listing heeft 3 tabs ("Nu in het museum" / "Verwacht" /
            # "Geweest") die client-side wisselen welke links zichtbaar zijn
            # -- alleen het eerste tabblad staat er bij page-load al. "Geweest"
            # bewust overgeslagen (per definitie al voorbij, dus toch
            # gefilterd door de end_iso < TODAY-check verderop).
            hrefs = set(collect_hrefs())
            try:
                page.get_by_role('button', name='Verwacht').click(timeout=5000)
                page.wait_for_timeout(800)
                hrefs |= set(collect_hrefs())
            except Exception as e:
                print(f"  waarschuwing: 'Verwacht'-tab niet gevonden/geklikt: {e}")
            hrefs = sorted(hrefs)
            print(f"  {len(hrefs)} expositie-pagina's gevonden")

            for href in hrefs:
                url = href if href.startswith('http') else BASE_URL + href
                try:
                    # 'domcontentloaded' i.p.v. 'networkidle': sommige pagina's
                    # (bv. "thuis-bij-m-c-escher") houden een achtergrond-
                    # verbinding open (chatwidget/tracker) waardoor networkidle
                    # nooit gehaald wordt en de hele run anders vastloopt.
                    page.goto(url, timeout=30000, wait_until='domcontentloaded')
                    page.wait_for_timeout(1200)
                    title = (page.locator('article h1').first.text_content() or '').strip()
                    # De pagina heeft meerdere <article>-elementen naast elkaar
                    # (intro, titletext, item-cards) -- de datumtekst kan in elk
                    # daarvan zitten (gezien: bij Sustainable Ceramics #2 zit hij
                    # in "titletext", niet in "intro"), dus alles samenvoegen.
                    body_text = page.eval_on_selector_all(
                        'article', 'els => els.map(e => e.textContent).join("\\n")'
                    )
                except Exception as e:
                    print(f"  FOUT bij {url}: {e}")
                    continue
                if not title:
                    continue
                rng = parse_range(body_text)
                if not rng:
                    continue
                start_iso, end_iso = rng
                if end_iso < TODAY:
                    continue
                ev = {
                    'title':    title,
                    'date':     start_iso,
                    'venue':    VENUE,
                    'city':     CITY,
                    'province': PROVINCE,
                    'source':   SOURCE,
                    'url':      url,
                    'cats':     ['expositie'],
                }
                if end_iso != start_iso:
                    ev['date_end'] = end_iso
                all_events.append(ev)
            browser.close()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            end_txt = f" t/m {ev['date_end']}" if ev.get('date_end') else ''
            print(f"    [{ev['date']}{end_txt}] {ev['title']}")
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

    print(f"Scraping princessehof.nl (Playwright) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
