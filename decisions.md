# Decisions — belangrijke beslissingen onderweg

Chronologisch, nieuwste onderaan. Kort: wat is besloten en waarom.

## Architectuur
- **Statische generator, geen framework**: `gen_uitjes.py` (pure Python stdlib) leest `events_categorized.json` en schrijft alles — HTML, CSS, JS — inline naar één `index.html`. Geen build-dependencies (`requirements.txt` bewust leeg).
- **JSON als single source of truth, SQLite als lokale werklaag**: `events_categorized.json` is wat gegenereerd wordt uit; `events_db.py` beheert dedup/opslag lokaal. SQLite werkt niet vanuit een Cowork-sandbox (FUSE-mount-beperking) — dus scrapen/dedupliceren gebeurt altijd op een lokale pc, nooit in de sandbox.
- **Cloudflare draait nooit de scrapers**, alleen `gen_uitjes.py` bij elke push naar `main`. Scraping + dedup blijft strikt lokaal.
- **Landelijke podia** (TivoliVredenburg, Melkweg, Paradiso, 013, Ziggo Dome, Effenaar, Doornroosje, Ahoy, AFAS Live, Rotown, De Doelen, GelreDome, Concertgebouw) worden getoond onder een eigen "Landelijk" groepsfilter, niet onder hun eigen provincie — expliciete keuze van Michiel.
- **De Kuip / Johan Cruijff Arena**: geen scrapbare eigen concertagenda (loopt via Ticketmaster) — bewust overgeslagen, geen scraper gebouwd.

## Workflow / beheer
- **`gen_uitjes.py` en `events_categorized.json` nooit met een Edit-tool bewerken** — editors kappen het bestand (~661 regels) af rond regel 500, wat het corrumpeert. Altijd via `open().read()` → `str.replace()` → `open('w').write()`, met validatie (`ast.parse()` / `json.load()`) vóór commit.
- **Push moet vanaf een machine met eigen git-credentials**, niet vanuit een sandbox zonder credentials.
- **Geen GitHub Personal Access Token ooit in de chat plakken** — een eerdere sessie deed dit per ongeluk, de token stond daarna in plaintext in meerdere transcripten en moet als gecompromitteerd worden behandeld. Sindsdien: nooit een geplakt token accepteren, ook niet als er expliciet om gevraagd wordt met verwijzing naar dit precedent.
- **Wekelijkse refresh** (maandag 08:04) via een scheduled task die de 5 scrapers + export + generate + git push achter elkaar draait.

## 2026-08-10 — deze sessie
- **Andere pc (met de scheduled task) is kapot** en moet gerepareerd worden. Tijdelijke beslissing: refresh handmatig draaien vanaf deze laptop, na expliciete controle van GitHub- en Cloudflare-toegang.
- **Volgorde afgesproken**: eerst dry run (scrapers + generate, `git diff` bekijken), pas na akkoord van Michiel committen en pushen — geen automatische push zonder review.
- **Documentatiestructuur uitgebreid**: readme.md (uitleg tool), onboarding.md (voor beheerders), architecture.md (technisch), overleg.md (nog te bespreken), plan.md (to-do), decisions.md (dit bestand) — om kennis niet alleen in chatgeschiedenis te laten zitten.
- **Cross-source dedup toegevoegd** (`events_db.py: find_cross_source_duplicates`, `AGGREGATOR_SOURCES`): regionale agenda's (visitgroningen, drenthe.nl, friesland.nl) herlisten vaak events die al rechtstreeks van de venue-site gescraped zijn, met een net iets andere titel (support-act, subtitel, landcode). Bij een fuzzy titel-match op dezelfde datum wint de directe venue-bron (preciezere venue/url); het aggregator-duplicaat wordt bij export overgeslagen. Veiligheidsregel: te generieke titels die met meerdere, inhoudelijk verschillende events matchen (bv. "Theaterweekend", "Kerstconcert") worden bewust *niet* gededupliceerd — beter een gemiste dubbel dan een verkeerd verwijderd uniek event. Resultaat eerste run: 249 duplicaten verwijderd, 21 dubbelzinnige gevallen overgeslagen (zie `python events_db.py cross-dupes` voor een preview).
