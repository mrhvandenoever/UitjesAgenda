# Scrapers — overzicht per bron

Wie/wat scraped welke venue, hoe, en of daar nog AI (Chrome MCP) bij nodig is
of dat het volledig automatisch draait. Broninformatie komt uit
`scraping_recipes.json` (technische recipes) — dit bestand is de
snel-scanbare status-samenvatting daarvan, plus welke bronnen al een eigen
`.py`-script hebben.

Laatst samengesteld: 2026-08-13.

## Legenda

| Status | Betekenis |
|---|---|
| ✅ Geautomatiseerd | Los `.py`-script, `python scrape_X.py` — geen AI nodig, kan in de wekelijkse refresh |
| 🔧 Kan zonder AI | Werkende scrape-code staat al in `scraping_recipes.json`, alleen nog geen los script gebouwd — rechttoe-rechtaan te automatiseren |
| 🌐 AI/Chrome nodig | Site is client-side gerenderd (JS/SPA) of blokkeert plain requests (bot-bescherming) — vereist een AI-agent met browsertoegang, tenzij er alsnog een verborgen API gevonden wordt (zoals gebeurde bij SPOT, handbal.nl, Martiniplaza — zagen er eerst uit als 🌐, bleken met wat graafwerk toch 🔧) |
| ✋ Handmatig | Vast jaarlijks event, hardcoded in `scrape_handmatig.py` — geen live bron om te scrapen |
| 📍 Eenmalig opgelost | Data staat er, ooit lokaal/via Chrome opgelost, maar geen herhaalbaar script — bij een volgende refresh moet dit opnieuw met AI |
| ❌ Geblokkeerd | Bekend probleem (404, DNS-fout, site geeft geen data) — zie notitie in `scraping_recipes.json` |
| ❓ Onbekend | Nog nooit geprobeerd |

## ✅ Geautomatiseerd (29 bronnen, 27 scripts)

| Bron | Script |
|---|---|
| Spot (Oosterpoort/Stadsschouwburg) | `scrape_spotgroningen.py` |
| Drenthe.nl (aggregator) | `scrape_drenthe.py` |
| Friesland.nl (aggregator) | `scrape_friesland.py` |
| Visitgroningen (aggregator) | `scrape_visitgroningen.py` |
| Hurry-Up (handbal) | `scrape_handbal.py` |
| E&O (handbal) | `scrape_handbal.py` |
| FC Twente | `scrape_fctwente.py` |
| SC Cambuur | `scrape_cambuur.py` |
| Go Ahead Eagles | `scrape_goahead.py` |
| PEC Zwolle | `scrape_peczwolle.py` |
| SC Heerenveen | `scrape_heerenveen.py` |
| FC Emmen | `scrape_fcemmen.py` |
| Kielzog | `scrape_kielzog.py` |
| Forum | `scrape_forum.py` |
| Geert Teis | `scrape_geertteis.py` |
| USVA | `scrape_usva.py` (~6/10 events, rest heeft geen herkenbaar datumformaat) |
| Martiniplaza | `scrape_martiniplaza.py` (via theater.nl, JSON-LD, 60 events) |
| De Tamboer | `scrape_detamboer.py` |
| Posthuis | `scrape_posthuistheater.py` |
| Bostheater | `scrape_bostheater.py` |
| GC Zuidlaren | `scrape_gczuidlaren.py` |
| Nieuwe Kolk (denieuwekolk.nl) | `scrape_denieuwekolk.py` (37 events, alleen /theater/ + /bios/, /bieb/-activiteiten bewust overgeslagen) |
| Lycurgus | `scrape_lycurgus.py` |
| CRAFT Sudosa | `scrape_sudosa.py` |
| Friso Sneek | `scrape_friso.py` |
| Dorpshuis Annen | `scrape_dorpshuisannen.py` |
| Nienoord | `scrape_nienoord.py` (site-structuur gewijzigd, regex herbouwd — 3 events, kleiner dan de oude ~9) |

Plus `scrape_naarzuidlaren.py` (lokale Zuidlaren-evenementen, geen eigen SRC-badge)
en `scrape_handmatig.py` (zie ✋ hieronder).

## 🌐 AI/Chrome nodig (16 bronnen)

| Bron | Verwachte omvang | Notitie |
|---|---|---|
| Atlas Emmen | ~185 events | client-rendered |
| Vera | ~60 events | client-rendered |
| Simplon | ~47 events | client-rendered |
| Grand Theatre (Groningen) | ~25 events | innerText-parsing nodig, geen bruikbare CSS-classes |
| Winsinghhof (theaterroden) | ~71 events | client-rendered |
| EM2 Groningen | ~21 events | client-rendered |
| Neushoorn | onbekend | bevestigd SPA |
| Groninger Museum | onbekend | bevestigd SPA |
| Drents Museum | onbekend | bevestigd SPA |
| Zuidhaege Assen | onbekend | bevestigd SPA |
| Koornbeurs | onbekend | bevestigd SPA |
| Zummerbühne | ~25 events | Ticketwidget in iframe, geen data in ruwe HTML (2026-08-13 herchecked — eerdere recipe ging uit van markdown-fetch, klopt niet met plain HTML) |
| OntdekPoort | ~216 events | Bot-bescherming — zelfs de homepage geeft 403, niet op te lossen met alleen headers (2026-08-13) |
| Hunebedcentrum | onbekend | Bot-bescherming, 403 (2026-08-13) |
| FC Groningen | 18 thuiswedstrijden (data staat er al) | eenmalig via Chrome gehaald, geen los script |
| GIJS Groningen (ijshockey) | — | site toont nog seizoen 2025-2026, herchecken zodra nieuw seizoen live is |

## 🔧 Kan zonder AI — recipe werkt, script nog niet gebouwd (3 bronnen)

| Bron | Verwachte omvang | Bijzonderheid |
|---|---|---|
| Geke Hoogstins | ~2 events | Tekst-structuur rommelig (datums en titels niet netjes gekoppeld), nog uit te zoeken |
| Machinefabriek | ~2 events | Via podiuminfo.nl-aggregator, nog niet geprobeerd |
| Noorderbron | klein | Vergaderlocatie met incidentele publieke activiteiten, nog niet geprobeerd |
| AFAS Live | onbekend | Geen JSON-LD/datetime-markers gevonden bij eerste check, verder uitzoeken |

## ❌ Geblokkeerd (4 bronnen)

| Bron | Probleem |
|---|---|
| Unis Flyers (ijshockey) | Schema 2026-2027 nog niet gepubliceerd |
| OG Capitals (ijshockey) | Redirect-loop, niet bereikbaar zonder browser |
| LDODK (korfbal) | Competitie zelf zegt: seizoen start pas 6-8 nov 2026 |
| Donar (basketbal) | Zie aparte sectie hieronder — 3 platforms onderzocht, nog geen werkende data-bron voor 2026-2027 |

### Donar — stand van zaken (2026-08-13)
Drie routes onderzocht, geen van alle direct werkend voor het huidige BNXT-seizoen:
1. **donar.nl/wedstrijden** — Next.js/React Server Components, data gefragmenteerd over cross-referenced chunks, geen simpele regex-extractie voor tegenstander-naam.
2. **basketball.nl "Vereniging zoeken"** — draait op extern platform "Foys" (`api.foys.io`), werkende endpoints voor clubinfo/teams gevonden, maar geen werkende club-search/list-endpoint om Donar's orgId te vinden zonder handmatig doorklikken.
3. **NBB officiële database** (db.basketball.nl/help/koppelingen) — gedocumenteerde JSON-API `api.basketballstats.nl/db/json/wedstrijd.pl?clb_ID=359&seizoen=YYYY-YYYY` (Donar clb_ID=359). Werkt voor seizoen 2025-2026 (72 wedstrijden), maar geeft 0 wedstrijden + "Onbekende competitie" voor 2026-2027 — BNXT League lijkt nog niet (volledig) in dit systeem gevuld.
4. **livescore.com/nl/basketbal/bnxt-league** (tip van Michiel) — ook Next.js, endpoint nog niet gevonden.

Vervolgstap: periodiek de basketballstats.nl-API herproberen, of livescore.com verder reverse-engineeren met Chrome MCP.

## ❓ Nog nooit geprobeerd (15 bronnen)

TivoliVredenburg, Melkweg, Paradiso, 013 Tilburg, Ziggo Dome, Effenaar,
Doornroosje, Rotterdam Ahoy, Het Paard, Hedon Zwolle, Rotown, De Doelen,
GelreDome, Concertgebouw, Landstede Hammers (basketbal — DNS-fout bij laatste
poging, mogelijk verouderd domein).

## 📍 Eenmalig opgelost, geen herhaalbaar script (2 bronnen)

| Bron | Notitie |
|---|---|
| De Lawei | 320 events staan er, ooit lokaal bevestigd — geen script |
| Van Beresteyn | 98 events staan er, ooit lokaal bevestigd — geen script |

## ✋ Handmatig / jaarlijks vast (1)

Be-Wonder (~1 event) + de vaste jaarevenementen in `scrape_handmatig.py`
(Bommen Berend, Zuidlaarder Paardenmarkt, Muzieknacht Zuidlaren).

## DOS'46 (korfbal) — niet in bovenstaande telling

❌ geblokkeerd (mijn.korfbal.nl laadt leeg, geen data om te scrapen).
