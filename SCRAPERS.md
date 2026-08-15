# Scrapers — overzicht per bron

Wie/wat scraped welke venue, hoe, en of daar nog AI (Chrome MCP) bij nodig is
of dat het volledig automatisch draait. Broninformatie komt uit
`scraping_recipes.json` (technische recipes) — dit bestand is de
snel-scanbare status-samenvatting daarvan, plus welke bronnen al een eigen
`.py`-script hebben.

Laatst samengesteld: 2026-08-13, bijgewerkt 2026-08-15.

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

## ✅ Geautomatiseerd (38 bronnen, 36 scripts)

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
| Machinefabriek | `scrape_machinefabriek.py` (via podiuminfo.nl, JSON-LD, 2 events) |
| Noorderbron | `scrape_noorderbron.py` (WP Event Manager, 1 event) |
| AFAS Live | `scrape_afaslive.py` (92 events) |
| Donar (basketbal, BNXT League) | `scrape_donar.py` (via bnxtleague.com/Sportpress-API, zie decisions.md 2026-08-15 — 15 thuiswedstrijden) |
| Landstede Hammers (basketbal, BNXT League) | `scrape_landstede.py` (zelfde API/aanpak als Donar, 15 thuiswedstrijden) |
| Atlas Emmen | `scrape_atlastheater.py` (Umbraco-ticketing-API, `GetPerformances`, 192 events — was "AI/Chrome nodig") |
| Podium Zuidhaege (Assen) | `scrape_podiumzuidhaege.py` (WP REST `event_listing`-post-type + tekst-regex voor datum, 22 events — was "AI/Chrome nodig") |
| Melkweg (Amsterdam) | `scrape_melkweg.py` (server-rendered HTML, regex, 257 events — was "AI/Chrome nodig") |
| 013 Tilburg | `scrape_013.py` (server-rendered HTML, regex, 154 events — was "AI/Chrome nodig") |

Plus `scrape_naarzuidlaren.py` (lokale Zuidlaren-evenementen, geen eigen SRC-badge)
en `scrape_handmatig.py` (zie ✋ hieronder).

## 🌐 AI/Chrome nodig (25 bronnen, incl. landelijke-podia-tabel verderop)

6 bronnen hieronder OPGELOST 2026-08-15 (zie decisions.md) — bleken bij
nader onderzoek toch geen browser nodig: Atlas Emmen (Umbraco-ticketing-API),
Zuidhaege Assen (WP REST `event_listing`-post-type), Melkweg en 013 Tilburg
(server-rendered HTML, geen client-side rendering zoals eerder aangenomen —
`__NEXT_DATA__`/JSON-LD-check miste dit toen).

| Bron | Verwachte omvang | Notitie |
|---|---|---|
| Vera | ~60 events | WordPress, maar geen custom event-post-type via REST + programma-pagina zelf is echt client-rendered (te weinig datums in ruwe HTML) |
| Simplon | ~47 events | zelfde als Vera — WordPress zonder REST-exposed events |
| Grand Theatre (Groningen) | ~25 events | innerText-parsing nodig, geen bruikbare CSS-classes, geen Umbraco/wp-json-API gevonden |
| Winsinghhof (theaterroden) | ~71 events | client-rendered, domein gaf SSL-connectfout bij laatste check, nog niet grondig onderzocht |
| EM2 Groningen | ~21 events | WordPress (generator-tag bevestigd), maar nog niet gecheckt op custom event-post-type/REST — waarschijnlijk vergelijkbaar met Vera/Simplon, niet onderzocht |
| Neushoorn | onbekend | bevestigd SPA |
| Groninger Museum | onbekend | Craft CMS (SEOmatic-generator) — mogelijk GraphQL-API, niet onderzocht |
| Drents Museum | onbekend | zelfde Craft CMS als Groninger Museum |
| Koornbeurs | onbekend | eigen JS-bundle bevat geen Umbraco/API-endpoints (anders dan Atlas Emmen, ondanks vergelijkbare bestandsstructuur) |
| Zummerbühne | ~25 events | Ticketwidget in iframe, geen data in ruwe HTML (2026-08-13 herchecked — eerdere recipe ging uit van markdown-fetch, klopt niet met plain HTML) |
| OntdekPoort | ~216 events | Bot-bescherming — zelfs de homepage geeft 403, niet op te lossen met alleen headers (2026-08-13, herbevestigd 2026-08-15) |
| Hunebedcentrum | onbekend | Bot-bescherming, 403 (2026-08-13, herbevestigd 2026-08-15) |
| FC Groningen | 18 thuiswedstrijden (data staat er al) | eenmalig via Chrome gehaald, geen los script |
| GIJS Groningen (ijshockey) | — | site toont nog seizoen 2025-2026, herchecken zodra nieuw seizoen live is |

## 🔧 Kan zonder AI — structureel lastig te automatiseren (1 bron)

| Bron | Verwachte omvang | Bijzonderheid |
|---|---|---|
| Geke Hoogstins | ~2 "events" | Zijn eigenlijk maandenlange doorlopende exposities ("22 mei t/m eind oktober"), geen losse datums — past niet goed in ons single-date-event-model. Bewust niet gebouwd. |

## ❌ Geblokkeerd (3 bronnen)

| Bron | Probleem |
|---|---|
| Unis Flyers (ijshockey) | Schema 2026-2027 nog niet gepubliceerd |
| OG Capitals (ijshockey) | Redirect-loop, niet bereikbaar zonder browser |
| LDODK (korfbal) | Competitie zelf zegt: seizoen start pas 6-8 nov 2026 |

### Donar — OPGELOST 2026-08-15
Drie eerder onderzochte routes liepen allemaal dood (donar.nl zelf: Next.js
zonder bruikbare API; basketball.nl/Foys: geen club-search-endpoint zonder
handmatig doorklikken; NBB-database `api.basketballstats.nl`: gaf 0
wedstrijden + "Onbekende competitie" voor 2026-2027 — BNXT League nog niet
gevuld in dat systeem; livescore.com-tip van Michiel: netwerkmonitoring ving
de fixture-call niet).

De doorbraak kwam niet van een club-site maar van **de BNXT League's eigen
officiële site** (bnxtleague.com) — die draait op een bespoke CMS "Sportpress"
(bureau Webpont, specifiek voor deze competitie gebouwd) met een publieke
JSON-API op `bnxt.sportpress.info`. Gevonden door Michiels vraag om te
checken of BNXT-clubs/CMS-en een plugin met API gebruiken — het antwoord was
niet een generieke WP/Joomla-plugin, maar wél een herbruikbare officiële
league-brede API. Zie `scrape_donar.py`'s docstring voor de volledige
API-mechaniek (seizoen/phase/team-id-discovery, paginering-quirk). Bonus:
dezelfde API dekt ook **Landstede Hammers** — zie `scrape_landstede.py`.
Beide: 15 thuiswedstrijden voor seizoen 2026-2027 (okt 2026 - mei 2027).

## ❓ Landelijke podia — herchecked 2026-08-15, 2 bleken toch server-rendered

Bij de eerste check (2026-08-14, plain requests) bleken deze grote,
commerciële venues consistent zwaar client-rendered — geen bruikbare
JSON-LD/`__NEXT_DATA__` gevonden. Op 2026-08-15 opnieuw gecheckt met een
bredere test (tellen van datum-achtige strings in de ruwe HTML i.p.v. alleen
JSON-LD/`__NEXT_DATA__`): **Melkweg en 013 Tilburg bleken alsnog gewoon
server-rendered** (de eerdere check keek specifiek naar `__NEXT_DATA__`/
JSON-LD en miste dat de HTML zelf al complete event-lijsten bevat) — nu
opgelost, zie ✅ hierboven. Landstede Hammers is ook al opgelost (2026-08-15,
zie eigen sectie hierboven — BNXT League-API, niet deze site).

| Bron | Bevinding |
|---|---|
| TivoliVredenburg | JSON-LD aanwezig maar alleen Yoast-SEO-metadata, geen events; 6 datum-strings bij hercheck — vermoedelijk alleen filter-widget, niet grondig genoeg onderzocht om zeker te zijn |
| Doornroosje | JSON-LD aanwezig, alleen metadata; 3 datum-strings bij hercheck — waarschijnlijk ruis, niet client_js bevestigd |
| De Doelen | JSON-LD aanwezig, alleen metadata; nog niet herchecked op server-rendered HTML |
| Ziggo Dome | geen JSON-LD, geen `__NEXT_DATA__`; 0 datum-strings bij hercheck — waarschijnlijk echt client-rendered |
| Rotterdam Ahoy | geen JSON-LD; 0 datum-strings bij hercheck — waarschijnlijk echt client-rendered |
| GelreDome | geen JSON-LD; 0 datum-strings bij hercheck — waarschijnlijk echt client-rendered |
| Effenaar | 1.6MB pagina, 150 datum-strings bij hercheck (!) maar bleken bij inspectie CMS-content-blocks (Statamic-achtige structuur, `publish_date`-velden van pagina-onderdelen), niet per se events-datums — nadere inspectie nodig, veelbelovend maar niet afgerond |
| Paradiso, Concertgebouw | homepage geladen maar geen agenda-link gevonden in de ruwe HTML; Paradiso 1 datum-string bij hercheck (vermoedelijk ruis) — juiste agenda-URL nog niet gevonden |
| Rotown | `/agenda/` geeft 404, 1 datum-string bij hercheck (ruis) — exacte listing-URL nog niet gevonden (individuele event-URL's wel: rotown.nl/agenda/artiest/) |
| Het Paard | connectiefout bij hercheck 2026-08-15 (was timeout op 2026-08-14) — nog niet gelukt te bereiken |
| Hedon Zwolle | pagina laadt maar blijft verdacht klein (7KB, ongewijzigd t.o.v. 2026-08-14) — mogelijk verkeerde URL of redirect, nog uit te zoeken |

Resterend van deze oorspronkelijke 15: 10 bronnen, geteld bij de 25
"AI/Chrome nodig" hierboven (Melkweg, 013 en Landstede Hammers zijn
opgelost).

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
