"""
page_cache.py — change-detection: sla het parse/insert-werk over als een
bron sinds de vorige run niet gewijzigd is.

Gebruik in een scraper:

    from page_cache import unchanged

    ...verzamel events zoals normaal in een lijst `batch`...

    if unchanged(SOURCE, batch):
        print("Geen wijzigingen sinds vorige run, skip.")
        log_scrape(SOURCE, len(batch), 0, notes='ongewijzigd, geskipt')
        return len(batch), 0

    for title, date, ... in batch:
        insert_event(...)

Ontwerpkeuzes:
  - Vergelijk de GEËXTRAHEERDE data (titels/datums/etc.), niet de ruwe HTML.
    HTML bevat vaak ruis (advertenties, CSRF-tokens, timestamps) die een
    "wijziging" lijkt terwijl de events zelf niet veranderd zijn — dat zou
    de cache waardeloos maken (elke run "gewijzigd").
  - De pagina wordt nog steeds elke run opgehaald (bespaart geen netwerktijd,
    alleen CPU/DB-tijd) — een vroege stop na de eerste pagina is bewust NIET
    gekozen, zie overleg.md punt 2: nieuwe events kunnen ook op een oudere
    pagina verschijnen bij bronnen die niet gegarandeerd append-only zijn.
  - Voor bronnen met losse pagina's/teams (bv. meerdere ESPN-teams, of
    drenthe.nl se paginering) kan `unchanged()` per sub-onderdeel aangeroepen
    worden met een eigen `key` (bv. f"{SOURCE}:cambuur", f"{SOURCE}:p3") in
    plaats van één key voor de hele bron.
  - Hash wordt ALTIJD bijgewerkt (ook bij eerste keer of bij wijziging), dus
    de eerstvolgende run vergelijkt weer tegen de huidige stand.

Losse tabel (`page_hash`) in dezelfde events.db — geen aparte databestand.
"""

import hashlib
from events_db import get_conn

SCHEMA = """
CREATE TABLE IF NOT EXISTS page_hash (
    key        TEXT PRIMARY KEY,
    hash       TEXT NOT NULL,
    checked_at TEXT DEFAULT (datetime('now'))
);
"""


def _fingerprint(data) -> str:
    """Maak een stabiele hash van data (lijst/tuple/str/willekeurig object)."""
    text = repr(data) if not isinstance(data, str) else data
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def unchanged(key: str, data) -> bool:
    """
    True als `data` exact gelijk is aan wat er de vorige keer onder deze
    `key` is opgeslagen. Werkt altijd de opgeslagen hash bij.
    """
    h = _fingerprint(data)
    conn = get_conn()
    conn.execute(SCHEMA)
    row = conn.execute('SELECT hash FROM page_hash WHERE key = ?', (key,)).fetchone()
    same = row is not None and row['hash'] == h
    conn.execute("""
        INSERT INTO page_hash (key, hash, checked_at) VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET hash=excluded.hash, checked_at=excluded.checked_at
    """, (key, h))
    conn.commit()
    conn.close()
    return same
