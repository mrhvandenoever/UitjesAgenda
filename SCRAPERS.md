# Scrapers — overzicht per bron

Wie/wat scraped welke venue, hoe, en of daar nog AI (Chrome MCP) bij nodig is
of dat het volledig automatisch draait. Broninformatie komt uit
`scraping_recipes.json` (technische recipes) — dit bestand is de
snel-scanbare status-samenvatting daarvan, plus welke bronnen al een eigen
`.py`-script hebben.

Laatst samengesteld: 2026-08-11.

## Legenda

| Status | Betekenis |
|---|---|
| ✅ Geautomatiseerd | Los `.py`-script, `python scrape_X.py` — geen AI nodig, kan in de wekelijkse refresh |
| 🔧 Kan zonder AI | Werkende scrape-code staat al in `scraping_recipes.json`, alleen nog geen los script gebouwd — rechttoe-rechtaan te automatiseren |
| 🌐 AI/Chrome nodig | Site is client-side gerenderd (JS/SPA) — vereist een AI-agent met browsertoegang om uit te lezen, tenzij er alsnog een verborgen API gevonden wordt (zoals dit weekend gebeurde bij SPOT en handbal.nl — zag er eerst uit als 🌐, bleek met wat graafwerk toch 🔧) |
| ✋ Handmatig | Vast jaarlijks event, hardcoded in `scrape_handmatig.py` — geen live bron om te scrapen |
| 📍 Eenmalig opgelost | Data staat er, ooit lokaal/via Chrome opgelost, maar geen herhaalbaar script — bij een volgende refresh moet dit opnieuw met AI |
| ❌ Geblokkeerd | Bekend probleem (404, DNS-fout, site geeft geen data) — zie notitie in `scraping_recipes.json` |
| ❓ Onbekend | Nog nooit geprobeerd |

## ✅ Geautomatiseerd (6 bronnen, 5 scripts)

| Bron | Script |
|---|---|
| Spot (Oosterpoort/Stadsschouwburg) | `scrape_spotgroningen.py` |
| Drenthe.nl (aggregator) | `scrape_drenthe.py` |
| Friesland.nl (aggregator) | `scrape_friesland.py` |
| Visitgroningen (aggregator) | `scrape_visitgroningen.py` |
| Hurry-Up (handbal) | `scrape_handbal.py` |
| E&O (handbal) | `scrape_handbal.py` |

Plus `scrape_naarzuidlaren.py` (lokale Zuidlaren-evenementen, geen eigen SRC-badge)
en `scrape_handmatig.py` (zie ✋ hieronder).

## 🌐 AI/Chrome nodig — bevestigd client-rendered (13 bronnen)

| Bron | Verwachte omvang | Notitie |
|---|---|---|
| Atlas Emmen | ~185 events | — |
| Vera | ~60 events | — |
| Simplon | ~47 events | — |
| Grand Theatre (Groningen) | ~25 events | innerText-parsing nodig, geen bruikbare CSS-classes |
| Winsinghhof (theaterroden) | ~71 events | — |
| EM2 Groningen | ~21 events | — |
| Neushoorn | onbekend | bevestigd SPA, nog geen geteste extractiecode |
| Groninger Museum | onbekend | bevestigd SPA, nog geen geteste extractiecode |
| Drents Museum | onbekend | bevestigd SPA, nog geen geteste extractiecode |
| Zuidhaege Assen | onbekend | bevestigd SPA, nog geen geteste extractiecode |
| Koornbeurs | onbekend | bevestigd SPA, nog geen geteste extractiecode |
| FC Groningen | 18 thuiswedstrijden (data staat er al) | eenmalig via Chrome gehaald, geen los script |
| GIJS Groningen (ijshockey) | — | site toont nog seizoen 2025-2026, herchecken zodra nieuw seizoen live is |

## 🔧 Kan zonder AI — recipe werkt, script nog niet gebouwd (29 bronnen)

Dit zijn de snelste volgende overwinningen: de scrape-code in
`scraping_recipes.json` is al geverifieerd, er hoeft alleen nog een los
`scrape_<naam>.py`-bestand van gemaakt te worden (naar het patroon van
`scrape_spotgroningen.py`/`scrape_handbal.py`).

| Bron | Verwachte omvang | Bijzonderheid |
|---|---|---|
| Kielzog | ~129-160 events | Echte JSON-API |
| Forum | ~55-99 events | Skip-lijst nodig (mixt bibliotheek-activiteiten) |
| Nieuwe Kolk (denieuwekolk.nl) | ~99-400 events | Per-event-URL nog niet geïmplementeerd (zie ARCHITECTURE.md) |
| Martiniplaza | ~6-57 events | Via theater.nl-aggregator, niet martiniplaza.nl direct |
| Zummerbühne | ~25 events | 1 vaste voorstelling, meerdere data |
| USVA | ~10 events | — |
| Geert Teis | ~10-12 events | schema.org itemprop-attributen |
| Nienoord | ~9 events | Jaartal niet in de data, moet afgeleid worden |
| GC Zuidlaren | ~6 events | — |
| Geke Hoogstins | ~2 events | — |
| Machinefabriek | ~2 events | — |
| Dorpshuis Annen | ~6 events | — |
| Noorderbron | klein | — |
| De Tamboer | ~15 events | Via JSON-LD |
| Posthuis | ~77 events | Paginering via ?page=N |
| OntdekPoort | ~216 events | Theater Sneek + Het Bolwerk, gedeelde WP REST API |
| Bostheater | ~6 events | Zomerseizoen only |
| Hunebedcentrum | — | Domein is .eu, niet .nl |
| AFAS Live | — | — |
| FC Emmen | 19 thuiswedstrijden | ESPN.nl |
| SC Heerenveen | 24 thuiswedstrijden | Statische HTML met embedded JSON |
| SC Cambuur | 17 thuiswedstrijden | ESPN.nl |
| FC Twente | 17 thuiswedstrijden | ESPN.nl |
| Go Ahead Eagles | 17 thuiswedstrijden | ESPN.nl |
| PEC Zwolle | 17 thuiswedstrijden | ESPN.nl (let op: slug is fc_zwolle) |
| Donar | 14 thuiswedstrijden | — |
| Lycurgus | 7 thuiswedstrijden (halve seizoen) | Nevobo RSS-feed |
| CRAFT Sudosa | 7 thuiswedstrijden (halve seizoen) | Nevobo RSS-feed |
| Friso Sneek | 7 thuiswedstrijden (halve seizoen) | Nevobo RSS-feed |

## ❌ Geblokkeerd (3 bronnen)

| Bron | Probleem |
|---|---|
| Unis Flyers (ijshockey) | Schema 2026-2027 nog niet gepubliceerd |
| OG Capitals (ijshockey) | Redirect-loop, niet bereikbaar zonder browser |
| LDODK (korfbal) | Competitie zelf zegt: seizoen start pas 6-8 nov 2026 |

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

## DOS'46 (korfbal) en overige sport — niet in bovenstaande telling

DOS'46: ❌ geblokkeerd (mijn.korfbal.nl laadt leeg, geen data om te scrapen).
