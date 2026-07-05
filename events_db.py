"""
events_db.py — centrale SQLite-laag voor uitjesagenda

Gebruik:
    python events_db.py init          # maak/reset schema
    python events_db.py import        # importeer events_categorized.json → DB
    python events_db.py export        # exporteer DB → events_categorized.json
    python events_db.py stats         # toon statistieken per source
    python events_db.py dupes         # toon potentiële duplicaten
"""

import sqlite3
import re
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, 'events.db')
JSON_PATH  = os.path.join(SCRIPT_DIR, 'events_categorized.json')

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    title_norm  TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    date_end    TEXT,
    time        TEXT,
    location    TEXT,
    venue       TEXT,
    city        TEXT,
    province    TEXT,
    lat         REAL,
    lon         REAL,
    genre       TEXT,
    genres      TEXT,
    category    TEXT,
    cats        TEXT,
    source      TEXT    NOT NULL,
    url         TEXT,
    image       TEXT,
    price       TEXT,
    subtitle    TEXT,
    gender      TEXT,
    sport       TEXT,
    type        TEXT,
    created_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(title_norm, date)
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT    NOT NULL,
    scraped_at   TEXT    DEFAULT (datetime('now')),
    events_found INTEGER DEFAULT 0,
    events_new   INTEGER DEFAULT 0,
    status       TEXT    DEFAULT 'ok',
    notes        TEXT
);
"""


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """Strip alles behalve letters/cijfers voor dedup-vergelijking."""
    return re.sub(r'[^a-z0-9]', '', title.lower().strip())


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✓ DB klaar: {DB_PATH}")


# ---------------------------------------------------------------------------
# Invoegen
# ---------------------------------------------------------------------------

def insert_event(event: dict) -> bool:
    """
    Voeg event in. Retourneert True als nieuw, False als duplicaat.
    Accepteert alle bekende velden; onbekende velden worden genegeerd.
    """
    title = (event.get('title') or '').strip()
    date  = (event.get('date')  or '').strip()
    if not title or not date:
        return False

    title_norm = normalize_title(title)

    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO events
                (title, title_norm, date, date_end, time, location, venue, city, province,
                 lat, lon, genre, genres, category, cats, source, url, image,
                 price, subtitle, gender, sport, type)
            VALUES
                (:title, :title_norm, :date, :date_end, :time, :location, :venue, :city, :province,
                 :lat, :lon, :genre, :genres, :category, :cats, :source, :url, :image,
                 :price, :subtitle, :gender, :sport, :type)
        """, {
            'title':      title,
            'title_norm': title_norm,
            'date':       date,
            'date_end':   event.get('date_end'),
            'time':       event.get('time'),
            'location':   event.get('location'),
            'venue':      event.get('venue'),
            'city':       event.get('city'),
            'province':   event.get('province'),
            'lat':        event.get('lat'),
            'lon':        event.get('lon'),
            'genre':      event.get('genre', 'overig'),
            'genres':     json.dumps(event['genres'], ensure_ascii=False)
                          if isinstance(event.get('genres'), list) else event.get('genres'),
            'category':   event.get('category'),
            'cats':       json.dumps(event['cats'], ensure_ascii=False)
                          if isinstance(event.get('cats'), list) else event.get('cats'),
            'source':     event.get('source', 'onbekend'),
            'url':        event.get('url'),
            'image':      event.get('image'),
            'price':      event.get('price'),
            'subtitle':   event.get('subtitle'),
            'gender':     event.get('gender'),
            'sport':      event.get('sport'),
            'type':       event.get('type'),
        })
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicaat
    finally:
        conn.close()


def log_scrape(source: str, found: int, new: int, status: str = 'ok', notes: str = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO scrape_log (source, events_found, events_new, status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (source, found, new, status, notes))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Importeren vanuit JSON
# ---------------------------------------------------------------------------

def import_json(json_path: str = None) -> tuple[int, int]:
    """
    Lees events_categorized.json en importeer in DB.
    Retourneert (toegevoegd, overgeslagen).
    """
    json_path = json_path or JSON_PATH
    with open(json_path, encoding='utf-8') as f:
        events = json.load(f)

    added = skipped = 0
    for e in events:
        if insert_event(e):
            added += 1
        else:
            skipped += 1

    print(f"Import klaar: {added} nieuw, {skipped} duplicaten overgeslagen")
    return added, skipped


# ---------------------------------------------------------------------------
# Exporteren naar JSON
# ---------------------------------------------------------------------------

def export_json(json_path: str = None, min_date: str = None) -> int:
    """
    Exporteer events naar events_categorized.json (compatibel met gen_uitjes.py).
    Alleen toekomstige events (>= vandaag) tenzij min_date opgegeven.
    """
    json_path = json_path or JSON_PATH
    min_date  = min_date or datetime.now().strftime('%Y-%m-%d')

    conn  = get_conn()
    rows  = conn.execute("""
        SELECT * FROM events
        WHERE date >= ? AND date <= '2027-12-31'
        ORDER BY date, title
    """, (min_date,)).fetchall()
    conn.close()

    out = []
    for r in rows:
        e = {
            'title':  r['title'],
            'date':   r['date'],
            'source': r['source'],
            'genre':  r['genre'] or 'overig',
        }
        # Optionele velden — alleen toevoegen als gevuld
        for field in ('date_end', 'time', 'location', 'venue', 'city', 'province',
                      'url', 'image', 'price', 'subtitle', 'gender', 'sport', 'type',
                      'category'):
            val = r[field]
            if val:
                e[field] = val
        if r['lat'] and r['lon']:
            e['lat'] = r['lat']
            e['lon'] = r['lon']
        if r['genres']:
            try:
                e['genres'] = json.loads(r['genres'])
            except Exception:
                e['genres'] = r['genres']
        if r['cats']:
            try:
                e['cats'] = json.loads(r['cats'])
            except Exception:
                e['cats'] = r['cats']
        out.append(e)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✓ Geëxporteerd: {len(out)} events → {json_path}")
    return len(out)


# ---------------------------------------------------------------------------
# Statistieken
# ---------------------------------------------------------------------------

def stats():
    conn  = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"\nTotaal events in DB: {total}")

    print("\nPer source:")
    for r in conn.execute(
        "SELECT source, COUNT(*) n FROM events GROUP BY source ORDER BY n DESC"
    ).fetchall():
        print(f"  {r['source']:30s} {r['n']:5d}")

    print("\nPer provincie:")
    for r in conn.execute("""
        SELECT COALESCE(province,'(onbekend)') p, COUNT(*) n
        FROM events GROUP BY p ORDER BY n DESC LIMIT 15
    """).fetchall():
        print(f"  {r['p']:30s} {r['n']:5d}")

    print("\nLaatste scrapes:")
    for r in conn.execute(
        "SELECT source, scraped_at, events_new, status FROM scrape_log ORDER BY id DESC LIMIT 10"
    ).fetchall():
        print(f"  {r['scraped_at']} | {r['source']:25s} | +{r['events_new']:4d} | {r['status']}")
    conn.close()


def dupes():
    """Toon title_norm waarden die meer dan één keer voorkomen (zouden niet mogen)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT title_norm, date, COUNT(*) n, GROUP_CONCAT(source, ', ') srcs
        FROM events
        GROUP BY title_norm, date
        HAVING n > 1
        ORDER BY n DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    if not rows:
        print("Geen duplicaten gevonden.")
    else:
        print(f"{len(rows)} dubbelen:")
        for r in rows:
            print(f"  [{r['date']}] {r['title_norm'][:50]} ({r['srcs']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'

    if cmd == 'init':
        init_db()
    elif cmd == 'import':
        init_db()
        import_json()
    elif cmd == 'export':
        export_json()
    elif cmd == 'stats':
        stats()
    elif cmd == 'dupes':
        dupes()
    else:
        print(__doc__)
                                            