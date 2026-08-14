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
"""

import argparse
import glob
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
SUCCESS_MARKERS = ('✓ Klaar:', 'Dry-run:')


def find_scrapers() -> list[str]:
    files = sorted(glob.glob(os.path.join(SCRIPT_DIR, 'scrape_*.py')))
    return [os.path.basename(f) for f in files]


def run_one(script: str, dry_run: bool) -> tuple[bool, str]:
    """Retourneert (ok, output). ok=False betekent harde fout."""
    args = [PYTHON, script] + (['--dry-run'] if dry_run else [])
    try:
        result = subprocess.run(
            args, cwd=SCRIPT_DIR, capture_output=True, text=True,
            timeout=600, encoding='utf-8', errors='replace'
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
    args = parser.parse_args()

    scrapers = find_scrapers()
    print(f"{len(scrapers)} scrapers gevonden (scrape_*.py)\n")

    if args.dry_run:
        for s in scrapers:
            print(f"  zou draaien: {s}")
        return

    ok_count = 0
    renamed = []
    zero_results = []

    for script in scrapers:
        print(f"=== {script} ===")
        ok, output = run_one(script, dry_run=False)
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
        print(f"\n=== events_db.py export ===")
        subprocess.run([PYTHON, 'events_db.py', 'export'], cwd=SCRIPT_DIR)
        print(f"\n=== gen_uitjes.py ===")
        subprocess.run([PYTHON, 'gen_uitjes.py'], cwd=SCRIPT_DIR)


if __name__ == '__main__':
    main()
