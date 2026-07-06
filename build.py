"""
build.py — Cloudflare Pages build script

Stap 1: Seed events.db vanuit committed events_categorized.json (baseline)
Stap 2: Run alle actieve scrapers (voegt nieuwe/verse events toe)
Stap 3: Export DB → events_categorized.json
Stap 4: gen_uitjes.py genereert index.html  ← apart aangeroepen door Cloudflare

Cloudflare build command:
    python build.py && python gen_uitjes.py
"""

import sys
import os

# Zorg dat scrapers de events_db module kunnen vinden
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from events_db import init_db, import_json, export_json

# ── Stap 1: Seed DB vanuit committed baseline ─────────────────────────────────
print("=" * 60)
print("BUILD STAP 1: Seed events.db vanuit events_categorized.json")
print("=" * 60)
init_db()
seeded, skipped = import_json()
print(f"  Geseedde events: {seeded} nieuw, {skipped} al aanwezig")

# ── Stap 2: Run alle actieve scrapers ─────────────────────────────────────────
print("\n" + "=" * 60)
print("BUILD STAP 2: Scrapers draaien")
print("=" * 60)

SCRAPERS = [
    ('scrape_drenthe',       'Drenthe.nl'),
    ('scrape_visitgroningen','VisitGroningen'),
    ('scrape_friesland',     'Friesland.nl'),
    ('scrape_handmatig',     'Handmatige events'),
    ('scrape_naarzuidlaren', 'NaarZuidlaren.nl'),
]

for module_name, label in SCRAPERS:
    print(f"\n→ {label}...")
    try:
        mod = __import__(module_name)
        mod.scrape()
    except Exception as e:
        print(f"  ⚠ FOUT bij {label}: {e} (doorgaan)")

# ── Stap 3: Export DB → JSON ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("BUILD STAP 3: Export naar events_categorized.json")
print("=" * 60)
n = export_json()
print(f"  {n} events geëxporteerd")

print("\n✓ Build klaar — gen_uitjes.py draait hierna")
