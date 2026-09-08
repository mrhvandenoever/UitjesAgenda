"""
run_weekly_refresh.py — draai alle scrapers, export, genereer de site

Gebruik:
    python run_weekly_refresh.py              # scrapers + export + gen_uitjes.py
    python run_weekly_refresh.py --no-generate # alleen scrapers + export, niet genereren
    python run_weekly_refresh.py --dry-run     # toon welke scripts zouden draaien, doe niks

Vervangt de handmatige scraper-lijst in ARCHITECTURE.md: elk bestand dat
voldoet aan `scrape_*.py` wordt automatisch meegenomen — geen aparte lijst
meer om bij te houden zodra er een nieuwe scraper bijkomt.

Zelf-herstellend gedrag:
  - Een scraper die een HARDE fout geeft (crash, timeout, of geen
    "✓ Klaar"/"Dry-run:" regel in de output — dat gebeurt alleen als de
    fetch/parse-stap zelf faalt, zie de except-blokken in elk
    scrape_*.py-bestand) wordt automatisch hernoemd naar fix_<naam>.py. Dat
    bestand matcht niet meer met scrape_*.py, dus wordt bij de volgende run
    vanzelf overgeslagen — "tijdelijk uit de roulatie" totdat iemand het
    repareert en terugzet naar scrape_<naam>.py.
  - Timeout staat op 600s (10 min), niet 300s: bij de eerste echte run
    (2026-08-14) werd scrape_friesland.py onterecht gequarantained — die
    haalt ~69 pagina's op à ~3s, wat bij netwerkdrukte over de toenmalige
    300s-grens kan gaan. Geen kapotte scraper, gewoon een te strakke
    timeout voor de grote aggregators (drenthe.nl/friesland.nl/
    visitgroningen, allemaal tientallen pagina's). Zie decisions.md.
  - Een scraper die succesvol draait maar 0 events vindt, wordt NIET
    hernoemd (kan legitiem zijn — bv. buiten-seizoen, of een venue zonder
    events deze week) — komt wel in het rapport te staan als "0 resultaten,
    controleer handmatig" zodat het niet stilletjes onopgemerkt blijft.

Uitzonderen van de wekelijkse run: geef een script geen scrape_-prefix (of
zet het in een subfolder) — dan matcht de glob het niet.

Parallel draaien (Niveau A, overleg.md punt 2 / decisions.md 2026-08-16):
  - Scrapers draaien niet meer één voor één, maar in twee pools met een
    eigen concurrency-limiet: "plain"-scrapers (gewone HTTP-requests, licht)
    en "playwright"-scrapers (eigen Chromium-proces per run, geheugen-zwaar)
    — zie is_playwright_scraper(). Beide pools draaien tegelijk met elkaar.
  - Concurrency instelbaar via --max-plain/--max-playwright (default 8/3).
    Op 1 zetten geeft het oude sequentiële gedrag terug zonder code-wijziging
    — handige noodrem als er in productie iets misgaat.
  - Output per script wordt als één blok geprint zodra dat script klaar is
    (niet regel-voor-regel interleaved) — de VOLGORDE waarin scripts
    afgerond worden is nu voltooiingsvolgorde, niet meer bestandsvolgorde.
  - SQLite-schrijven is veilig gemaakt voor gelijktijdige processen via
    WAL-mode + busy_timeout in events_db.py's get_conn() — zonder die fix
    zou dit "database is locked"-fouten kunnen geven.

Lock-bestand tegen gelijktijdige runs (gevonden 2026-09-08, decisions.md):
  - Twee runs van dit script tegelijk (bv. een handmatige poging naast een
    nog lopende/orphaned eerdere run) concurreren om dezelfde
    os.rename()-doelen bij een "harde fout" -- de tweede rename-poging op
    een al hernoemd bestand crasht met een onafgevangen FileNotFoundError.
    Bovendien verdubbelt de netwerk/CPU-belasting, wat scrapers die alleen
    prima zouden lopen alsnog laat timeouten. Gevolg: tientallen scrapers
    onterecht gequarantained in één klap.
  - `.refresh.lock` (dit bestand, niet in git) voorkomt dit: een tweede
    run stopt meteen met een duidelijke melding i.p.v. te botsen. Een lock
    ouder dan `LOCK_STALE_SECONDS` wordt als vastgelopen beschouwd en
    genegeerd (zelf-herstellend, geen PID-checks nodig die per OS
    verschillen).
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Zelfde reden als events_db.py: dit script draait zelf ook vaak via een
# pipe (weekly_refresh.ps1's "2>&1 | Tee-Object"), en print de al-
# gedecodeerde "✓"-tekens van scrapers door -- zonder dit crasht ook DIT
# proces met een UnicodeEncodeError zodra het onder een niet-UTF-8-
# console draait. Zie decisions.md 2026-09-08.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
SUCCESS_MARKERS = ('✓ Klaar:', 'Dry-run:')
DEFAULT_MAX_PLAIN = 8
DEFAULT_MAX_PLAYWRIGHT = 3
LOCK_FILE = os.path.join(SCRIPT_DIR, '.refresh.lock')
LOCK_STALE_SECONDS = 30 * 60  # een volledige run duurt normaal enkele minuten, nooit 30


def acquire_lock() -> bool:
    """True = lock verkregen, verder gaan. False = een andere run is al
    bezig, dit proces moet meteen stoppen."""
    if os.path.exists(LOCK_FILE):
        age = time.time() - os.path.getmtime(LOCK_FILE)
        if age < LOCK_STALE_SECONDS:
            print(f"Al een run bezig (lock is {int(age)}s oud) -- gestopt om races te voorkomen.")
            print(f"Vastgelopen oude run? Verwijder dan handmatig: {LOCK_FILE}")
            return False
        print(f"Verouderde lock gevonden ({int(age)}s oud, > {LOCK_STALE_SECONDS}s) -- overschreven.")
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


def find_scrapers() -> list[str]:
    files = sorted(glob.glob(os.path.join(SCRIPT_DIR, 'scrape_*.py')))
    return [os.path.basename(f) for f in files]


def is_playwright_scraper(script: str) -> bool:
    """Geen aparte config per script nodig: gewoon checken of het bestand
    zelf 'playwright' importeert. Eén losse Chromium-run per script, dus
    deze pool moet een lagere concurrency-limiet krijgen dan de lichte
    plain-HTTP-scrapers."""
    try:
        with open(os.path.join(SCRIPT_DIR, script), encoding='utf-8') as f:
            return 'playwright' in f.read()
    except OSError:
        return False


def run_one(script: str, dry_run: bool) -> tuple[bool, str]:
    """Retourneert (ok, output). ok=False betekent harde fout."""
    args = [PYTHON, script] + (['--dry-run'] if dry_run else [])
    # PYTHONIOENCODING expliciet meegeven: capture_output=True maakt van
    # de subprocess' stdout een pipe i.p.v. een echte console, waardoor
    # Python's eigen stdout-encoding op Windows terugvalt op de
    # systeem-ANSI-codepage (cp1252) i.p.v. UTF-8 -- gaf een
    # UnicodeEncodeError bij elke scraper die "✓" print. De
    # encoding='utf-8'-parameter hieronder regelt alleen hoe DIT proces
    # de teruggekregen bytes decodeert, niet hoe het kind-proces zelf
    # zijn eigen output encodeert. Zie ook events_db.py's eigen
    # stdout.reconfigure() -- dit is de tweede laag verdediging voor
    # scrapers die niet via deze functie draaien. Zie decisions.md
    # 2026-09-08.
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    try:
        result = subprocess.run(
            args, cwd=SCRIPT_DIR, capture_output=True, text=True,
            timeout=600, encoding='utf-8', errors='replace', env=env
        )
    except subprocess.TimeoutExpired:
        return False, '  FOUT: timeout na 600s'

    output = (result.stdout or '') + (result.stderr or '')
    ok = result.returncode == 0 and any(m in output for m in SUCCESS_MARKERS)
    return ok, output


def found_count(output: str) -> int | None:
    m = re.search(r'(?:✓ Klaar|Dry-run):\s*(\d+)\s*(?:gevonden|thuiswedstrijden|events)', output)
    return int(m.group(1)) if m else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='toon alleen welke scripts zouden draaien')
    parser.add_argument('--no-generate', action='store_true', help='sla events_db.py export + gen_uitjes.py over')
    parser.add_argument('--max-plain', type=int, default=DEFAULT_MAX_PLAIN, metavar='N',
                        help=f'max. gelijktijdige plain-HTTP-scrapers (default {DEFAULT_MAX_PLAIN}, 1 = sequentieel)')
    parser.add_argument('--max-playwright', type=int, default=DEFAULT_MAX_PLAYWRIGHT, metavar='N',
                        help=f'max. gelijktijdige Playwright-scrapers (default {DEFAULT_MAX_PLAYWRIGHT}, 1 = sequentieel)')
    args = parser.parse_args()

    scrapers = find_scrapers()
    print(f"{len(scrapers)} scrapers gevonden (scrape_*.py)\n")

    if args.dry_run:
        for s in scrapers:
            print(f"  zou draaien: {s}")
        return

    plain_scripts = [s for s in scrapers if not is_playwright_scraper(s)]
    playwright_scripts = [s for s in scrapers if is_playwright_scraper(s)]
    print(f"  {len(plain_scripts)} plain-HTTP (max {args.max_plain} tegelijk), "
          f"{len(playwright_scripts)} Playwright (max {args.max_playwright} tegelijk)\n")

    ok_count = 0
    renamed = []
    zero_results = []

    with ThreadPoolExecutor(max_workers=max(1, args.max_plain)) as plain_pool, \
         ThreadPoolExecutor(max_workers=max(1, args.max_playwright)) as pw_pool:
        future_to_script = {}
        for s in plain_scripts:
            future_to_script[plain_pool.submit(run_one, s, False)] = s
        for s in playwright_scripts:
            future_to_script[pw_pool.submit(run_one, s, False)] = s

        for fut in as_completed(future_to_script):
            script = future_to_script[fut]
            ok, output = fut.result()
            print(f"=== {script} ===")
            print(output.rstrip())

            if not ok:
                new_name = 'fix_' + script[len('scrape_'):]
                os.rename(os.path.join(SCRIPT_DIR, script), os.path.join(SCRIPT_DIR, new_name))
                renamed.append((script, new_name))
                print(f"  >> HARDE FOUT — hernoemd naar {new_name} (wordt overgeslagen tot reparatie)")
            else:
                ok_count += 1
                n = found_count(output)
                if n == 0:
                    zero_results.append(script)

    print(f"\n{'=' * 60}")
    print(f"Klaar: {ok_count}/{len(scrapers)} scrapers OK")
    if renamed:
        print(f"\n{len(renamed)} hernoemd naar fix_*.py (harde fout, handmatig repareren):")
        for old, new in renamed:
            print(f"  {old} -> {new}")
    if zero_results:
        print(f"\n{len(zero_results)} gaven 0 resultaten (kan legitiem zijn, wel even checken):")
        for s in zero_results:
            print(f"  {s}")

    if not args.no_generate:
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        print(f"\n=== events_db.py export ===")
        subprocess.run([PYTHON, 'events_db.py', 'export'], cwd=SCRIPT_DIR, env=env)
        print(f"\n=== gen_uitjes.py ===")
        subprocess.run([PYTHON, 'gen_uitjes.py'], cwd=SCRIPT_DIR, env=env)


if __name__ == '__main__':
    # --dry-run wijzigt niets op schijf (geen rename/DB-writes), dus geen
    # lock nodig -- alleen de echte run beschermen.
    if '--dry-run' in sys.argv:
        main()
    elif acquire_lock():
        try:
            main()
        finally:
            release_lock()
    else:
        sys.exit(1)
