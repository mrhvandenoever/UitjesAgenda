# Overleg — UitjesAgenda

Werkdocument voor het plan-overleg. Vul aan tijdens het gesprek.

## Aanleiding
- Andere pc (met de wekelijkse Cowork scheduled task "uitjes-agenda-refresh") moet gerepareerd worden.
- Deze laptop is tijdelijk (of structureel?) ingericht om dezelfde refresh te kunnen draaien: Python geïnstalleerd, repo gecloned naar `C:\dev\uitjesagenda`.
- Laatste live update: commit van 6 juli 2026 — ruim 5 weken oud.

## Open vragen / te bespreken

### 1. Waar draait de wekelijkse refresh voortaan?
- Tijdelijk op deze laptop tot de andere pc terug is?
- Structureel verhuizen?
- Scheduled task ("uitjes-agenda-refresh", maandag 08:04) moet dan ook verhuisd/opnieuw ingesteld worden.

### 2. Slimmer scrapen (efficiëntie)
- Huidige situatie: elke scraper haalt bij elke run alle pagina's opnieuw op (bv. drenthe.nl: 34+ pagina's, duurde >3 min).
- Idee (rsync/delta-achtig) afgewogen:
  - **Early-stop bij eerste "alles al bekend"-pagina** — simpel, maar riskant: nieuwe events kunnen ook op oudere pagina's worden ingevoegd (niet gegarandeerd chronologisch/append-only).
  - **Per-pagina hash-caching** — blijft elke pagina ophalen (dus niets gemist), slaat alleen parse/DB-stap over bij ongewijzigde pagina-inhoud. Bespaart CPU/DB-tijd, niet netwerktijd.
  - **Parallelle requests** — waarschijnlijk de grootste tijdswinst als de bottleneck vooral het aantal sequentiële HTTP-requests is (lijkt hier het geval).
  - Voorstel: hash-caching + parallelisatie combineren, geen early-stop.

### 3. SPOT Groningen — Oosterpoort vs Stadsschouwburg
- Nu: alle SPOT-events tonen alleen "Spot Groningen", zonder te specificeren welk gebouw (Oosterpoort of Stadsschouwburg).
- Het specifieke gebouw staat wel op elke individuele event-pagina, maar de huidige scraper haalt alleen titel+datum van de programma-lijst — geen locatie.
- Fix vereist een extra HTTP-request per event (~325+ stuks) om de detailpagina te lezen. Afweging: is de extra scrape-tijd/load het waard?
- Keuze nodig: wel/niet doen, en zo ja hoe vaak (elke run, of eenmalig + alleen nieuwe events)?

### 4. Generieke/kapotte event-links (26 van ~50 bronnen)
- Audit: 26 bronnen linken alle events naar dezelfde generieke agenda-URL i.p.v. een specifieke event-pagina. O.a. TivoliVredenburg (406 events → 1 link), Melkweg (175), Atlastheater (165), Doornroosje, 013, Effenaar, Ahoy, Koornbeurs, Vera (35), Posthuistheater, Martiniplaza, Neushoorn, Ziggo Dome, Paradiso, denieuwekolk.nl (86), en alle 8 sportclubs.
- denieuwekolk.nl heeft de juiste regex al klaarstaan in scraping_recipes.json maar nooit afgemaakt (was een `pass`-placeholder) — waarschijnlijk de snelste eerste fix.
- Sportclubs linken vaak bewust naar een algemene wedstrijdkalender — mogelijk acceptabel, geen per-wedstrijd pagina nodig?
- Keuze nodig: prioritering — alle 26 is een grote klus. Welke eerst (denieuwekolk.nl / Vera / de grote landelijke podia)? Sportclubs meenemen of bewust laten staan?

### 5. Landelijke uitbreiding
- Ambitie: de tool op termijn landelijk maken (nu vooral Noord-Nederland + een aantal landelijke podia).
- Nader te bepalen: schaal (hoeveel bronnen/pagina's erbij), of de huidige scraper-architectuur dat aankan, prioritering t.o.v. de andere open items.

### 4. Overig (uit ARCHITECTURE.md — openstaand)
- Ticketmaster Discovery API (gratis tier) — key aanvragen?
- Lycurgus — seizoen nog niet gestart
- GIJS Groningen — URL onbekend
- Hurry-Up — website 404
- Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- 14/57 scraping-recipes nog zonder werkende methode

## Status huidige sessie (dry run)
- [x] Toegang GitHub gecheckt (repo: mrhvandenoever/UitjesAgenda)
- [x] Toegang Cloudflare gecheckt (account Chielemans@hotma…, project `uitjesagenda`)
- [x] Python geïnstalleerd op deze laptop
- [x] Repo gecloned naar `C:\dev\uitjesagenda`
- [ ] Scrapers gedraaid (drenthe, visitgroningen, friesland, handmatig, naarzuidlaren) — loopt op de achtergrond
- [ ] `events_db.py export` + `gen_uitjes.py`
- [ ] `git diff` bekijken
- [ ] Akkoord voor commit + push
