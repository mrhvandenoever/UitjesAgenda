"""
scrape_intonature.py — Into Nature: "extra activiteiten"-agenda (intonature.net)

Gebruik:
    python scrape_intonature.py              # scrape, sla op in DB
    python scrape_intonature.py --dry-run    # toon events zonder op te slaan

Michiel wees op deze bron (overleg.md punt 15): naast de hoofdtentoonstelling
"Into Nature: Haunted by Waters" zelf (langlopend, geen vaste dag — precies
het soort event waar punt 15 over ging) heeft Into Nature een eigen pagina
met losse, WEL-gedateerde "extra activiteiten" (rondleidingen, performances,
kennisavonden) — dat past gewoon in ons bestaande Uitjes-model.

De pagina (`/agenda/extra-activiteiten-tijdens-<titel>`) is een React-app;
plain `urllib` ziet alleen een lege shell. Via de Browser pane (2026-08-18)
bleek de content wél een nette, consistente DOM-structuur te hebben binnen
één `div.block__content`: een platte opeenvolging van
  H3 (dag, "Zaterdag 15 augustus", geen jaartal)
  H5 (activiteit-titel) -- niet bij elke activiteit aanwezig, zie hieronder
  P  (vrije tekst, vaak met "Tijd:"/"Locatie:"/"Datum:"-regels)
i.p.v. een herkenbaar per-activiteit HTML-element (geen class/id per
activiteit) -- vandaar de op-volgorde-lopende parser hieronder i.p.v. een
CSS-selector-aanpak.

**Twee content-typen op dezelfde pagina, bewust verschillend behandeld:**
- Losse, concrete activiteiten (rondleiding/performance/kennisavond) — deze
  scrapen we. Meestal (niet altijd) met een eigen H5-kop.
- "Boswachters met bakfiets" — een terugkerend, laagdrempelig inloopmoment
  zonder vaste tijd ("Tijd: volgt", elke week op dezelfde vaste plek). Dit
  is inhoudelijk hetzelfde soort "geen concreet moment"-geval als de
  wandelroutes uit overleg.md punt 15 zelf (2. Wandelroutes-vraag) — bewust
  overgeslagen, ook al kreeg één exemplaar per ongeluk toch een H5 (data-
  inconsistentie op de bron zelf, opgevangen met een titel-check i.p.v. puur
  op structuur te vertrouwen).

Er is geen aparte URL per activiteit op deze pagina (geen id/anker per
H5/blok gevonden) — alle events krijgen dezelfde agenda-pagina-URL.

Kleine, bewust beperkte bron: 1 tentoonstelling, 1 seizoen. Volgend jaar
heet de tentoonstelling anders en verandert de URL — dit script is dus
NIET generiek herbruikbaar voor toekomstige Into Nature-edities zonder de
`AGENDA_URL` bij te werken.
"""

import re
import argparse
from datetime import date
from playwright.sync_api import sync_playwright
from events_db import insert_event, log_scrape, init_db
from page_cache import unchanged

SOURCE     = 'intonature'
AGENDA_URL = 'https://www.intonature.net/agenda/extra-activiteiten-tijdens-into-nature-haunted-by-waters'
PROVINCE   = 'Drenthe'
TODAY      = date.today().isoformat()

MONTHS_NL = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
}

SKIP_TITLE_PAT = re.compile(r'boswachters met bakfiets', re.I)


def fetch_blocks() -> list[tuple[str, str]]:
    """Rendert de agenda-pagina en geeft (tag, tekst) terug voor elk kind-
    element van `.block__content`, in document-volgorde."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        ))
        page.goto(AGENDA_URL, timeout=30000, wait_until='load')
        page.wait_for_timeout(1500)
        blocks = page.eval_on_selector(
            'h3', """
            h3 => {
                const container = h3.closest('div.block__content');
                if (!container) return [];
                return [...container.children].map(el => [el.tagName, el.textContent.trim()]);
            }
            """
        )
        browser.close()
        return [(tag, text) for tag, text in blocks]


def parse_day(day_text: str) -> str | None:
    """'Zaterdag 15 augustus' -> ISO-datum (jaartal afgeleid als huidig jaar).

    Bewust GEEN "rol naar volgend jaar als al voorbij"-logica (zoals bv.
    scrape_drenthe.py/scrape_vera.py wel hebben): dit is een terugkerende
    maandelijkse activiteit ("Wandeling langs kunstwerken...") binnen 1
    tentoonstellingsseizoen (t/m okt 2026) -- een editie die al bij het
    scrapen in het verleden ligt (bv. "15 augustus" terwijl vandaag al 18
    augustus is) is gewoon al geweest, geen toekomstige editie in 2027. De
    aanroepende `parse_blocks()` filtert zulke verleden-datums er sowieso
    uit (`e['date'] >= TODAY`), dus hier simpelweg niet naar volgend jaar
    projecteren -- dat zou een allang-gepasseerde activiteit ten onrechte
    een jaar vooruit laten opduiken (gevonden en gefixt 2026-08-18)."""
    m = re.search(
        r'(\d{1,2})\s+(januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)',
        day_text.lower())
    if not m:
        return None
    day, month_name = m.groups()
    month = MONTHS_NL[month_name]
    try:
        d = date(date.today().year, month, int(day))
    except ValueError:
        return None
    return d.isoformat()


def extract_field(text: str, label: str) -> str | None:
    m = re.search(rf'{label}:\s*([^\n]+)', text, re.I)
    if not m:
        return None
    val = m.group(1).strip()
    return None if val.lower() in ('volgt', '') else val


def parse_time(text: str) -> str | None:
    raw = extract_field(text, 'Tijd')
    if not raw:
        return None
    m = re.match(r'(\d{1,2})[.:](\d{2})', raw)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def parse_blocks(blocks: list[tuple[str, str]]) -> list[dict]:
    events = []
    current_day_iso = None
    title = None
    buffer_texts: list[str] = []

    def flush():
        if not title or title == '__SKIP__' or not current_day_iso:
            return
        if SKIP_TITLE_PAT.search(title):
            return
        joined = '\n'.join(buffer_texts)
        ev = {
            'title':    title.strip(),
            'date':     current_day_iso,
            'time':     parse_time(joined),
            'venue':    extract_field(joined, 'Locatie'),
            # Alle geziene locaties (Roderwolderweg/IJsbaan/Dorpshuis
            # Roderwolde, De Onlanderij Eelderwolde, Wooncentrum Peize)
            # liggen op een paar km van elkaar rond Roderwolde -- 'city' zet
            # de afstandsberekening op CITY_COORDS['Roderwolde'] (al
            # aanwezig in city_coords.json), een redelijke benadering zonder
            # zelf per-locatie coördinaten te hoeven opzoeken.
            'city':     'Roderwolde',
            'province': PROVINCE,
            'source':   SOURCE,
            'url':      AGENDA_URL,
            'cats':     ['actief'],
        }
        events.append(ev)

    for tag, text in blocks:
        if tag == 'H3':
            flush()
            current_day_iso = parse_day(text)
            title, buffer_texts = None, []
        elif tag == 'H5':
            flush()
            title, buffer_texts = text, []
        elif tag == 'P':
            if title is None and not buffer_texts:
                # Geen H5 gezien sinds de laatste dag-kop -- eerste regel
                # van deze alinea bepaalt of dit een losse activiteit is
                # (titel = eerste regel) of de terugkerende "Boswachters
                # met bakfiets"-vulling (overslaan).
                first_line = text.split('\n')[0].split('|')[0].strip()
                title = '__SKIP__' if SKIP_TITLE_PAT.search(first_line) else first_line
            buffer_texts.append(text)
    flush()

    return [e for e in events if e['date'] and e['date'] >= TODAY]


def scrape(dry_run: bool = False) -> tuple[int, int]:
    init_db()
    try:
        blocks = fetch_blocks()
    except Exception as e:
        print(f"  FOUT: {e}")
        return 0, 0

    all_events = parse_blocks(blocks)
    found = len(all_events)

    if dry_run:
        for ev in sorted(all_events, key=lambda e: e['date']):
            t = f" {ev['time']}" if ev.get('time') else ''
            v = f" @ {ev['venue']}" if ev.get('venue') else ''
            print(f"    [{ev['date']}{t}] {ev['title'][:60]:60s}{v}")
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

    print(f"Scraping intonature.net (Playwright) [{'dry-run' if args.dry_run else 'live'}]...")
    scrape(dry_run=args.dry_run)
