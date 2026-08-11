# Plan — to-do

Levend document. Vink af / verplaats naar "Later" zodra iets besproken of gedaan is.

## Nu (deze sessie — dry run refresh)
- [x] GitHub-toegang gecheckt
- [x] Cloudflare-account/project gecheckt (Chielemans@hotma…, project `uitjesagenda`)
- [x] Python geïnstalleerd op deze laptop
- [x] Repo gecloned naar `C:\dev\uitjesagenda`
- [ ] 5 scrapers gedraaid (drenthe, visitgroningen, friesland, handmatig, naarzuidlaren)
- [ ] `events_db.py export` + `gen_uitjes.py`
- [ ] `git diff` bekijken met Michiel
- [ ] Akkoord voor commit + push

## Binnenkort — te overleggen (zie overleg.md)
- [ ] Waar draait de wekelijkse refresh voortaan: deze laptop, andere pc (na reparatie), of iets anders?
- [ ] Scraper-efficiëntie: per-pagina hash-caching + parallelle requests i.p.v. elke run alles opnieuw ophalen
- [ ] Documentatiestructuur compleet: readme / onboarding / architecture / overleg / plan / decisions — bijhouden wie wat update

## Sport-audit (2026-08-10)
Van de 19 geconfigureerde clubs in `gen_uitjes.py` (`SPORT_CLUBS`):
- **Compleet, data klopt**: fcgroningen (16), fcemmen (18), heerenveen (24), cambuur (16), fctwente (17), goahead (16), peczwolle (16), donar (14) — volledig seizoen aug 2026 - mei 2027.
- **Klopt, maar seizoen nog niet compleet gepubliceerd**: lycurgus, sudosa, friso (volleybal) — Nevobo-RSS-feed zelf heeft nu maar 7 thuiswedstrijden (2e seizoenshelft nog niet vrijgegeven door de bond). Geen scraper-fout — later in het seizoen opnieuw scrapen.
- **OPGELOST 2026-08-10**: `hurryup` (14 thuiswedstrijden) + `eoemmen` (26 thuiswedstrijden) — Michiel wees erop dat de standaard datumfilter op handbal.nl maar 2 weken vooruit toont; met een ruimere `filters[date]`-range op de onderliggende Sportlink-API (`api.handbal.nl/.../program`) bleek het hele seizoen al gepubliceerd. Nieuwe scraper: `scrape_handbal.py` (plain requests, geen browser nodig). Lost ook Hurry-Up's oude 404-probleem structureel op (nieuwe bron: officiële NHV-clubpagina i.p.v. eigen site).
- **Nog altijd leeg** (filterknop bestaat, 0 events) — herchecked 2026-08-10, status per bron in `scraping_recipes.json`:
  - [ ] `landstede` (basketbal) — DNS-fout, domein lijkt niet meer te bestaan, juiste URL uitzoeken
  - [ ] `grizzlys` / GIJS Groningen (ijshockey) — site toont nog seizoen 2025-2026, 2026-2027 nog niet live
  - [ ] `flyers` (ijshockey) — schema nog niet gepubliceerd
  - [ ] `ogcapitals` (ijshockey) — redirect-loop, niet bereikbaar zonder browser (Chrome MCP proberen)
  - [ ] `ldodk` (korfbal) — site zegt expliciet "geen programma bekend"
  - [ ] `dos46` (korfbal) — mijn.korfbal.nl laadt leeg (JS-shell)

## Bug: afstandsberekening klopt niet voor aggregator-bronnen (gevonden 2026-08-11)
- **Symptoom** (gemeld door Michiel): filter op 15km vanaf een locatie tussen Annen en Zuidlaren toont Ruinen, Diever, Nieuw-Dordrecht, Vledder, Alteveer, Meppel etc. — allemaal met exact "~13km", terwijl deze plaatsen in werkelijkheid zeer verschillende, deels veel grotere afstanden hebben.
- **Oorzaak bevestigd**: `VENUE_LOC` in `gen_uitjes.py` heeft voor de 3 grote regionale aggregators (`drenthe.nl`, `visitgroningen`, `friesland.nl`) maar **één vast coördinaat per bron**, niet per stad — ongeacht of het event in Ruinen, Meppel of Nieuw-Dordrecht is. Alle events van zo'n bron krijgen dus dezelfde (onjuiste) afstand tot de gebruiker.
- **Impact**: 2777 van de ~6800 events (bijna 40%) bij deze 3 bronnen, verspreid over 254 verschillende plaatsen.
- **Voorstel fix**: bouw een city→lat/lon-lookuptabel voor deze 254 plaatsen (eenmalig geocoden via Nominatim, net als de bestaande adres-zoekfunctie al gebruikt; daarna cachen — coördinaten van dorpen/steden veranderen niet). Gebruik in `event_html()`/de afstandsberekening per event de eigen stad-coördinaten i.p.v. de vaste bron-coördinaten, met de huidige `VENUE_LOC`-waarde alleen nog als fallback voor events zonder herkenbare `city`.
- [ ] Lookuptabel bouwen (254 plaatsen, eenmalige geocode-actie)
- [ ] `gen_uitjes.py` aanpassen: per-event coördinaten i.p.v. per-bron
- [ ] Verifiëren met het Annen/Zuidlaren-voorbeeld van Michiel

## SPOT-scraper achterhaald + genre-classificatie te ambigu (gevonden 2026-08-11)
- **SPOT-data verouderd**: live heeft spotgroningen.nl/programma/ nu 621 events, onze opgeslagen data maar 325 — SPOT zat niet bij de 5 wekelijkse scrapers. Bestaande regex in `scraping_recipes.json` werkt nog prima (621 matches op de live pagina), gewoon niet recent gedraaid.
- **Bonus-vondst**: SPOT's HTML bevat `data-description`/`data-title`-attributen met een genre-signaal (bv. "...rockit-jazz-kwartet", "absolute-top-uit-de-hedendaagse-jazzscene" bij Peter Bernstein Quartet) dat de huidige scraper niet meepakt — alleen de `<h2>`-titel wordt gebruikt.
- **Genre-bug**: `classify()` in `gen_uitjes.py` heeft 'quartet'/'kwartet'/'trio'/'ensemble' in de klassiek-keywordlijst — genre-ambigu, want jazz gebruikt dezelfde woorden. Peter Bernstein Quartet (jazz) kreeg daardoor 🎻 Klassiek / Opera.
- [ ] Nieuwe `scrape_spotgroningen.py` bouwen die ook `data-description` meepakt
- [ ] `classify()`: 'quartet'/'kwartet'/'trio'/'ensemble' weghalen uit de klassiek-lijst; waar beschikbaar `data-description` gebruiken voor jazz- vs klassiek-onderscheid

## Later / open items (uit ARCHITECTURE.md)
- [ ] Ticketmaster Discovery API (gratis tier, 5.000 req/dag) — key aanvragen op developer.ticketmaster.com
- [ ] Lycurgus — seizoen nog niet gestart, later toevoegen
- [ ] GIJS Groningen — URL onbekend
- [ ] Hurry-Up — website geeft 404
- [ ] Stadspark Groningen (Summer Stage, Hullaballoo) — revisit zomer 2027
- [ ] 14/57 scraping-recipes nog zonder werkende methode — nalopen
