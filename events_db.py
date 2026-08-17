"""
events_db.py — centrale SQLite-laag voor uitjesagenda

Gebruik:
    python events_db.py init          # maak/reset schema
    python events_db.py import        # importeer events_categorized.json → DB
    python events_db.py export        # exporteer DB → events_categorized.json
    python events_db.py stats         # toon statistieken per source
    python events_db.py dupes         # toon potentiële duplicaten (exacte titel+datum)
    python events_db.py cross-dupes   # toon aggregator-vs-venue duplicaten (fuzzy titel)
"""

import sqlite3
import re
import json
import os
import sys
import collections
import itertools
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, 'events.db')
JSON_PATH  = os.path.join(SCRIPT_DIR, 'events_categorized.json')

# Regionale agenda's die events herlisten die al rechtstreeks van de venue-site
# gescraped zijn (vaak met net iets andere titel: support-act, subtitel, landcode).
AGGREGATOR_SOURCES = {'visitgroningen', 'drenthe.nl', 'friesland.nl', 'kunstpuntgroningen', 'uitzinnig'}
CROSS_DUPE_MIN_CORE_LEN = 10  # kortere titels zijn te generiek om veilig te matchen

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
    # timeout=30 + PRAGMA busy_timeout: bij gelijktijdige scrapers (Niveau A,
    # zie overleg.md punt 2 / decisions.md 2026-08-16) kunnen meerdere
    # processen tegelijk willen schrijven. WAL-mode laat lezers en één
    # schrijver gelijktijdig toe; busy_timeout laat SQLite tot 30s wachten
    # op een korte schrijf-lock i.p.v. meteen "database is locked" te geven.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
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

_UPDATE_SQL = """
    UPDATE events SET
        title=:title, date_end=:date_end, time=:time, location=:location,
        venue=:venue, city=:city, province=:province, lat=:lat, lon=:lon,
        genre=:genre, genres=:genres, category=:category, cats=:cats,
        source=:source, url=:url, image=:image, price=:price,
        subtitle=:subtitle, gender=:gender, sport=:sport, type=:type
    WHERE title_norm=:title_norm AND date=:date
"""


def _event_values(event: dict, title: str, title_norm: str, date: str) -> dict:
    """Bouwt de kolom-waarden-dict voor een event -- gedeeld door INSERT en
    beide UPDATE-paden in insert_event(), was voorheen 2x losstaand herhaald."""
    return {
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
    }


def _is_empty(v) -> bool:
    return v is None or v == '' or v == '[]'


def _merge_values(existing_row, new_values: dict) -> tuple[dict, bool]:
    """Merge nieuwe veldwaarden over een bestaande rij heen: een nieuwe
    waarde wint alleen als die niet leeg is, anders blijft de bestaande
    waarde staan. Voorkomt dat een scraper-run met een incompleet veld (bv.
    een parse-fout bij een event) een eerder wel gevulde waarde overschrijft
    -- maar laat een same-source herscrape met BETERE data (het scenario dat
    al 4x dit project misging omdat insert_event() same-source-botsingen
    voorheen altijd negeerde: forum.nl, Geke Hoogstins, TivoliVredenburg,
    SPOT Groningen -- zie decisions.md 2026-08-17) nu wel doorkomen."""
    merged, changed = {}, False
    for field, new_val in new_values.items():
        if field in ('title_norm', 'date'):
            merged[field] = new_val
            continue
        old_val = existing_row[field] if field in existing_row.keys() else None
        merged[field] = new_val if not _is_empty(new_val) else old_val
        if merged[field] != old_val:
            changed = True
    return merged, changed


def insert_event(event: dict) -> bool:
    """
    Voeg event in. Retourneert True als nieuw (of bijgewerkt), False als
    ongewijzigd duplicaat.

    UNIQUE(title_norm, date) betekent dat twee bronnen die hetzelfde event
    melden botsen op de insert. Drie botsings-gevallen:
    1. Zelfde bron herscraped hetzelfde event (title_norm, date) -- merge
       per veld (zie _merge_values): een nieuwe niet-lege waarde wint, een
       lege nieuwe waarde laat de bestaande staan. Dit was voorheen een pure
       no-op (de rij werd nooit bijgewerkt), wat 4x tot stille dataveroudering
       leidde (zie decisions.md 2026-08-17) -- nu wel opgelost, met de
       leeg-wint-nooit-regel als vangnet tegen een incomplete scraper-run.
    2. Aggregator vs. directe venue-bron -- bestaand gedrag ongewijzigd: als
       de AL BESTAANDE rij van een aggregator komt (AGGREGATOR_SOURCES) en de
       NIEUWE rij van een directe venue-bron, overschrijft de nieuwe rij de
       bestaande volledig (preciezere venue/url/cats, geen veld-voor-veld-
       merge nodig want de directe bron is altijd de betere bron).
    3. Overig (bv. aggregator na directe bron, of twee verschillende directe
       bronnen) -- genegeerd zoals voorheen, bestaande rij is al even goed of
       beter.
    """
    title = (event.get('title') or '').strip()
    date  = (event.get('date')  or '').strip()
    if not title or not date:
        return False

    title_norm = normalize_title(title)
    new_source = event.get('source', 'onbekend')
    values = _event_values(event, title, title_norm, date)

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
        """, values)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        existing = conn.execute(
            'SELECT * FROM events WHERE title_norm = ? AND date = ?',
            (title_norm, date)
        ).fetchone()
        if existing is None:
            return False
        existing_source = existing['source']

        if existing_source == new_source:
            merged, changed = _merge_values(existing, values)
            if not changed:
                return False
            conn.execute(_UPDATE_SQL, merged)
            conn.commit()
            return True
        elif existing_source in AGGREGATOR_SOURCES and new_source not in AGGREGATOR_SOURCES:
            conn.execute(_UPDATE_SQL, values)
            conn.commit()
            return True
        return False  # duplicaat, bestaande rij is al even goed of beter
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
# Cross-source dedup (aggregator herlist een event dat al direct gescraped is)
# ---------------------------------------------------------------------------

def _cross_dupe_norm(title: str) -> str:
    t = title.lower()
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def find_cross_source_duplicates(rows) -> set:
    """
    Vind db-ids van aggregator-events (visitgroningen/drenthe.nl/friesland.nl)
    die een event herlisten dat al rechtstreeks van de venue-site komt.
    De directe venue-bron heeft voorrang (preciezere venue/url) — deze functie
    geeft de te verwijderen aggregator-ids terug.

    Veiligheid: als een titel te generiek is om betrouwbaar te matchen (bv.
    'Theaterweekend', 'Kerstconcert' — matcht dan met meerdere, inhoudelijk
    verschillende events), wordt die niet gededupliceerd maar overgeslagen.
    """
    by_date = collections.defaultdict(list)
    for r in rows:
        by_date[r['date']].append(r)

    pairs = []  # (direct_id, agg_id, agg_title)
    for date, evs in by_date.items():
        for a, b in itertools.combinations(evs, 2):
            agg_a = a['source'] in AGGREGATOR_SOURCES
            agg_b = b['source'] in AGGREGATOR_SOURCES
            if agg_a == agg_b:
                continue
            agg_ev, direct_ev = (a, b) if agg_a else (b, a)
            na, nd = _cross_dupe_norm(agg_ev['title']), _cross_dupe_norm(direct_ev['title'])
            core = min(na, nd, key=len)
            if len(core.replace(' ', '')) < CROSS_DUPE_MIN_CORE_LEN:
                continue
            if na == nd or na in nd or nd in na:
                pairs.append((direct_ev['id'], agg_ev['id'], na))

    agg_to_dirs = collections.defaultdict(set)
    for id_dir, id_agg, _ in pairs:
        agg_to_dirs[id_agg].add(id_dir)
    ambiguous_agg = {i for i, dirs in agg_to_dirs.items() if len(dirs) > 1}

    dir_to_agg_cores = collections.defaultdict(set)
    for id_dir, id_agg, na in pairs:
        dir_to_agg_cores[id_dir].add(na)
    ambiguous_dir = {i for i, cores in dir_to_agg_cores.items() if len(cores) > 1}

    return {
        id_agg for id_dir, id_agg, _ in pairs
        if id_agg not in ambiguous_agg and id_dir not in ambiguous_dir
    }


# ---------------------------------------------------------------------------
# Exporteren naar JSON
# ---------------------------------------------------------------------------

def export_json(json_path: str = None, min_date: str = None) -> int:
    """
    Exporteer events naar events_categorized.json (compatibel met gen_uitjes.py).
    Alleen toekomstige events (>= vandaag) tenzij min_date opgegeven.

    Uitzondering (sinds de Exposities-modus, 2026-08-16): een event met een
    date_end die nog niet voorbij is, blijft mee — ook als de startdatum
    zelf al in het verleden ligt (een doorlopende expositie die al begonnen
    is maar nog loopt). Zonder deze OR-clausule zou zo'n event hier al
    wegvallen, vóórdat gen_uitjes.py's eigen expo-aware filtering
    (event_is_valid() in gen_uitjes.py, zie ARCHITECTURE.md §Exposities)
    er ooit aan toekomt. Gevonden 2026-08-17 bij het bouwen van de eerste
    echte "al begonnen, nog lopende" expositie (scrape_gekehoogstins.py).
    """
    json_path = json_path or JSON_PATH
    min_date  = min_date or datetime.now().strftime('%Y-%m-%d')

    conn  = get_conn()
    rows  = conn.execute("""
        SELECT * FROM events
        WHERE (date >= ? OR (date_end IS NOT NULL AND date_end >= ?))
          AND date <= '2027-12-31'
        ORDER BY date, title
    """, (min_date, min_date)).fetchall()
    conn.close()

    dupe_ids = find_cross_source_duplicates(rows)
    if dupe_ids:
        print(f"  Cross-source dedup: {len(dupe_ids)} aggregator-events overgeslagen (al aanwezig via directe venue-bron)")
    rows = [r for r in rows if r['id'] not in dupe_ids]

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


def cross_dupes():
    """Preview van find_cross_source_duplicates() zonder te exporteren."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM events WHERE date >= date('now')").fetchall()
    conn.close()
    dupe_ids = find_cross_source_duplicates(rows)
    by_id = {r['id']: r for r in rows}
    print(f"{len(dupe_ids)} aggregator-events te verwijderen bij export:")
    for i in sorted(dupe_ids, key=lambda i: by_id[i]['date']):
        r = by_id[i]
        print(f"  [{r['date']}] {r['source']:15s} {r['title'][:60]}")


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
    elif cmd == 'cross-dupes':
        cross_dupes()
    else:
        print(__doc__)
