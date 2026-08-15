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

## ✅ Geautomatiseerd (44 bronnen, 42 scripts)

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
| FC Groningen | `scrape_fcgroningen.py` (ESPN.nl, team-id 145 — zelfde patroon als Cambuur/FC Twente/Go Ahead/PEC Zwolle, 14 events — was "eenmalig via Chrome gehaald, geen los script") |
| Hedon (Zwolle) | `scrape_hedon.py` (eigen `/api/events`, Yesplan-backed — tip van Michiel over Hedons LinkedIn-post, 118 events — was "AI/Chrome nodig", pagina bleek lege Angular-shell) |
| TivoliVredenburg | `scrape_tivolivredenburg.py` (via songkick.com — tip van Michiel — alleen muziek/concerten, ~9 shows per run; site zelf blijft een bevestigde Cloudflare bot-challenge, bewust niet omzeild) |
| Neushoorn (Leeuwarden) | `scrape_neushoorn.py` — **eerste Playwright-scraper** (headless Chromium rendert de Webflow-SPA, daarna regex op de DOM), 110 events. Zie ARCHITECTURE.md §Playwright-scrapers. |
| GelreDome (Arnhem) | `scrape_gelredome.py` (Playwright, zelfde Webflow-platform als Neushoorn, mix van Vitesse-thuiswedstrijden + concerten/evenementen, volgt paginering, 21 events) |
| Ziggo Dome (Amsterdam) | `scrape_ziggodome.py` (via podiuminfo.nl — tip van Michiel, JSON-LD, geen Playwright nodig, 25 events; ziggodome.nl zelf blijft een gevirtualiseerde lijst, zie hieronder) |

Plus `scrape_naarzuidlaren.py` (lokale Zuidlaren-evenementen, geen eigen SRC-badge)
en `scrape_handmatig.py` (zie ✋ hieronder).

## 🌐 AI/Chrome nodig (19 bronnen, incl. landelijke-podia-tabel verderop)

12 bronnen hieronder OPGELOST 2026-08-15 (zie decisions.md): Atlas Emmen
(Umbraco-ticketing-API), Zuidhaege Assen (WP REST `event_listing`-post-type),
Melkweg en 013 Tilburg (bleken toch server-rendered), FC Groningen (ESPN.nl),
Hedon en TivoliVredenburg (tips van Michiel), Ziggo Dome (podiuminfo.nl, tip
Michiel) — allemaal zónder browser opgelost. **Neushoorn en GelreDome**
waren de eerste die écht een headless browser nodig hadden (Playwright,
sinds vandaag beschikbaar) — geen verborgen API gevonden, wel
automatiseerbaar zonder AI.

| Bron | Verwachte omvang | Notitie |
|---|---|---|
| Vera | ~60 events | WordPress, geen custom event-post-type via REST. Programma-pagina toont wél ~20 events server-rendered (pagina 1), maar paginering loopt via een `admin-ajax.php`-call (`action=renderProgramme`) die zonder browsersessie een lege 200-respons geeft (vermoedelijk Cloudflare Bot Management op dat specifieke endpoint) — `?page=N` als URL-param werkt niet (negeerd server-side). Zonder browser dus alleen de eerste ~20 van ~60 events te halen; niet gebouwd (te onvolledig/fragiel). |
| Simplon | ~47 events | WordPress zonder REST-exposed events, nog niet los onderzocht op hetzelfde admin-ajax-patroon als Vera |
| Grand Theatre (Groningen) | ~25 events | innerText-parsing nodig, geen bruikbare CSS-classes, geen Umbraco/wp-json-API gevonden (custom plugin "michnhokn", niet herkend) |
| Winsinghhof (theaterroden) | ~71 events | domein blijft onbereikbaar (connectiefout, herbevestigd 2026-08-15) — mogelijk verouderd/gewijzigd domein, nog uit te zoeken welke URL wel klopt |
| EM2 Groningen | ~21 events | WordPress met custom `event`-post-type, WEL via `/wp-json/wp/v2/event` opvraagbaar — maar de evenementdatum staat los in vrije tekst zonder vast patroon ("De Gipsy Jazz Sessie op 12 juli is...", datum niet aan het begin zoals bij Zuidhaege) en sommige entries lijken terugkerende events zonder duidelijke enkele datum. Deels opgelost (API gevonden) maar datum-extractie te onbetrouwbaar bevonden om nu te bouwen. |
| Groninger Museum | onbekend | Craft CMS (SEOmatic-generator) — voor de hand liggende GraphQL-endpoints (`/actions/graphql/api`, `/api`) geven beide 404, geen API gevonden |
| Drents Museum | onbekend | zelfde Craft CMS als Groninger Museum |
| Koornbeurs | onbekend | eigen JS-bundle bevat geen Umbraco/API-endpoints (anders dan Atlas Emmen, ondanks vergelijkbare bestandsstructuur) |
| Zummerbühne | ~25 events | Ticketwidget in iframe, geen data in ruwe HTML (2026-08-13 herchecked — eerdere recipe ging uit van markdown-fetch, klopt niet met plain HTML) |
| OntdekPoort | ~216 events | Bot-bescherming — zelfs de homepage geeft 403, niet op te lossen met alleen headers (2026-08-13, herbevestigd 2026-08-15) |
| Hunebedcentrum | onbekend | Bot-bescherming, 403 (2026-08-13, herbevestigd 2026-08-15) |
| GIJS Groningen (ijshockey) | — | site toont nog seizoen 2025-2026 (herchecked 2026-08-15, nog steeds oud), herchecken zodra nieuw seizoen live is |

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

TivoliVredenburg zelf blijft een bevestigde Cloudflare bot-challenge ("Just a
moment..."-pagina, bewust niet omzeild) — maar wel opgelost via een omweg,
zie ✅ hierboven (`scrape_tivolivredenburg.py`, via Songkick, tip Michiel).

| Bron | Bevinding |
|---|---|
| Doornroosje | WordPress bevestigd (`/wp/wp-includes/...`), custom post-types zijn `vacatures`/`campagne`/`festival` — geen bruikbaar events-type via REST. 3 datum-strings bij hercheck bleek ruis. |
| De Doelen | Vite-gebundelde JS (`site.js`) doorzocht op API-endpoints/fetch-calls — niets events-gerelateerds gevonden, alleen wachtwoord-lijst-fetches en een Spotify-oembed-call. Geen bruikbare API gevonden. |
| Rotterdam Ahoy | Foundation-framework (geen moderne JS-bundler), "Silvercore"-CDN — geen API-aanwijzingen gevonden, geen event-achtige CSS-classes in de ruwe HTML |
| GelreDome | **Webflow-site** (cdn.prod.website-files.com) met Finsweet CMS-filter — CMS-collectie staat leeg in de ruwe HTML (`w-dyn-bind-empty`), wordt client-side gevuld. Zelfde platform als Neushoorn. |
| Effenaar | 1.6MB pagina, 150 datum-strings bij hercheck (!) maar bleken bij inspectie CMS-content-blocks (Statamic-achtige structuur, `publish_date`-velden van pagina-onderdelen), niet per se events-datums — nadere inspectie nodig, veelbelovend maar niet afgerond |
| Paradiso, Concertgebouw | homepage geladen maar geen agenda-link gevonden in de ruwe HTML; Paradiso 1 datum-string bij hercheck (vermoedelijk ruis) — juiste agenda-URL nog niet gevonden |
| Rotown | `/agenda/` geeft 404, 1 datum-string bij hercheck (ruis) — exacte listing-URL nog niet gevonden (individuele event-URL's wel: rotown.nl/agenda/artiest/) |
| Het Paard | connectiefout bij hercheck 2026-08-15 (was timeout op 2026-08-14) — nog niet gelukt te bereiken |

Hedon Zwolle bleek een lege Angular-SPA-shell (7KB) te zijn, maar heeft een
eigen `/api/events`-endpoint — opgelost, zie ✅ hierboven
(`scrape_hedon.py`).

Resterend van deze oorspronkelijke 15: 8 bronnen, geteld bij de 19
"AI/Chrome nodig" hierboven (Melkweg, 013, Landstede Hammers, Hedon en
TivoliVredenburg zijn opgelost).

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
