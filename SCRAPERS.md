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

## ✅ Geautomatiseerd (66 bronnen, 66 scripts)

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
| Forum | `scrape_forum.py` (groepeert opeenvolgende dagen per slug tot één event met `date_end` sinds 2026-08-17 — forum.nl levert doorlopende dingen als "Marilyn Expositie" anders als een losse rij per dag, zie overleg.md punt 12) |
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
| TivoliVredenburg | `scrape_tivolivredenburg.py` (2026-08-17 herzien — bleek GEEN Cloudflare-blokkade meer te hebben, zie decisions.md. Directe agenda-paginering (`/agenda/page/N/`, tot een 404), datum staat gewoon in de event-URL. Volledige agenda i.p.v. alleen Songkick's live-muziek-subset — 853 events/run, was 9) |
| Neushoorn (Leeuwarden) | `scrape_neushoorn.py` — **eerste Playwright-scraper** (headless Chromium rendert de Webflow-SPA, daarna regex op de DOM), 110 events. Zie ARCHITECTURE.md §Playwright-scrapers. |
| GelreDome (Arnhem) | `scrape_gelredome.py` (Playwright, zelfde Webflow-platform als Neushoorn, mix van Vitesse-thuiswedstrijden + concerten/evenementen, volgt paginering, 21 events) |
| Simplon (Groningen) | `scrape_simplon.py` (Playwright, derde scraper — Stager-platform net als Vera, maar eigen programma-pagina heeft wél een simpel regex-baar DOM-patroon zonder Vera's AJAX-paginering-probleem, 48 events) |
| Effenaar (Eindhoven) | `scrape_effenaar.py` (Playwright, vierde scraper — eerdere check gebruikte de verkeerde URL `/programma` i.p.v. `/agenda`, vandaar de vroegere "CMS-metadata"-conclusie; juiste URL geeft een schoon `agenda-card`-grid, 125 events) |
| Winsinghhof (Roden) | `scrape_theaterroden.py` (geen Playwright nodig — domein verhuisd naar theaterroden.nl, oude `winsinghhof.nl` bestaat niet meer; gewoon server-rendered HTML, 68 events. podiuminfo.nl gaf hier maar 12/71 — dekt alleen concerten, niet dit vooral-theater-programma) |
| Koornbeurs (Franeker) | `scrape_koornbeurs.py` (Playwright, vijfde scraper — geen verborgen API zoals bij Atlas Emmen ondanks vergelijkbare bestandsstructuur, wel client-side gerenderd zonder API, 117 events) |
| Grand Theatre (Groningen) | `scrape_grandtheatregroningen.py` (Playwright, zesde scraper — geen data-attributen maar wel een consistente DOM-structuur per event, meerdaagse shows worden meerdere events, 61 events) |
| Doornroosje (Nijmegen) | `scrape_doornroosje.py` (Playwright, zevende scraper — meerdere shows per dag delen één datum-blok, "samedate"-items hergebruiken de laatst geziene datum, 223 events) |
| De Doelen (Rotterdam) | `scrape_dedoelen.py` (Playwright, achtste scraper — verkeerde URL in eerdere sessie (`/programma` i.p.v. `/nl/agenda`), zelfde patroon als Effenaar/Winsinghhof, 49 events) |
| Ziggo Dome (Amsterdam) | `scrape_ziggodome.py` — **vervangen** van podiuminfo.nl naar de Ticketmaster Discovery API (tip Michiel): 83 events tot mei 2027, was 25 tot okt 2026. Zie `ticketmaster.py`. |
| Rotterdam Ahoy | `scrape_ahoy.py` (Ticketmaster Discovery API, 41 events — was "AI/Chrome nodig", geen API-sporen gevonden in eigen site) |
| Het Paard (Den Haag) | `scrape_paard.py` (via denhaag.com/nl/paard — tip van Michiel — geen Playwright nodig, gewone `?page=N`-paginering, 92 events; eigen site paard.nl bleef leeg zelfs met Playwright) |
| Paradiso (Amsterdam) | `scrape_paradiso.py` (Playwright, negende scraper — juiste URL was een specifieke landingspagina, niet vanaf de homepage vindbaar, 100 events) |
| Concertgebouw (Amsterdam) | `scrape_concertgebouw.py` (Playwright, tiende scraper — juiste URL `/concerten-en-tickets` (tip Michiel), ~40 pagina's paginering, 600 events — grootste scraper van het project) |
| Rotown (Rotterdam) | `scrape_rotown.py` (geen Playwright nodig — de HOMEPAGE zelf bevat 139 losse JSON-LD Event-blokken, `/agenda/` als listing-URL bestond gewoon niet; gefilterd op `location.name=='Rotown'`, 97 events) |
| Vera (Groningen) | `scrape_vera.py` (Playwright, elfde scraper — bleek géén Cloudflare-blokkade maar gewoon een infinite-scroll die curl niet kon triggeren; een echte browser-scroll laadt gewoon alles, 69 events) |
| Geke Hoogstins (Eext) | `scrape_gekehoogstins.py` (2026-08-17 — was bewust niet gebouwd zolang doorlopende exposities niet in het datamodel pasten; sinds de Exposities-modus (`date_end`) wél mogelijk. Site is vrije tekst, maar de "EXPOSITIES `<jaar>`"-sectie is gestructureerde HTML (`<p><strong>datumbereik</strong> titel</p>`) — regex-baar zonder AI. 3 events/jaar) |
| Kunstpunt Groningen (aggregator) | `scrape_kunstpuntgroningen.py` (2026-08-17, overleg.md punt 13 — dekt in één keer tientallen Groningse musea/galerieën, o.a. Museum Nienoord, Synagoge Groningen, K38, De Stadsgalerie. Server-rendered WordPress, alleen categorie "Exhibition" meegenomen, 2 pagina's. Detailpagina per expositie geeft ook precieze lat/lon + de specifiekste beschikbare link. In `AGGREGATOR_SOURCES` — venue wint bij een botsing, zelfde regel als Uitjes. `SKIP_VENUES` sluit Galerie DSG en Groninger Museum uit — die hebben inmiddels een eigen, preciezere directe scraper. 24 events/run) |
| Groninger Museum | `scrape_groningermuseum.py` (2026-08-17 — was 2026-08-15 nog "geparkeerd als moeilijk": GraphQL-endpoints gaven 404, Playwright bleef leeg. Bleek achteraf helemaal geen GraphQL nodig te hebben: een plain, publieke JSON-API (`/api/exhibitions`, `/api/activities`, beide met `?type=now\|soon\|past`) — gevonden via een Playwright-netwerkcheck die de onderliggende `fetch()`-call zag. Dekt zowel exposities (met `date`/`date_end`) als losse eenmalige activiteiten (bv. Groninger Museumnacht) — generiek-terugkerende activiteiten ("Ieder weekend") bewust overgeslagen, passen niet in het single-date-model. 9 events/run) |
| Uitzinnig.nl (aggregator, Drenthe/Groningen/Friesland) | `scrape_uitzinnig.py` (2026-08-17, overleg.md punt 13 — 3 "provincie"-pagina's die in de praktijk overlappen, dus gededupliceerd op URL. Echte start-/einddatum via ISO-meta-tags op de detailpagina (beter dan kunstinzicht.nl, dat bewust niet gebouwd is — zie hieronder). Geeft ook een eerste (deel-)win voor Hunebedcentrum zonder de bot-bescherming te omzeilen. In `AGGREGATOR_SOURCES`. 13 events/run) |
| Staatsbosbeheer (natuuractiviteiten + wandelroutes, Groningen/Drenthe/Friesland/Overijssel) | `scrape_staatsbosbeheer.py` (2026-08-18/19, overleg.md punt 15 — de listingpagina is een React-app, maar heeft een publieke, schone JSON-API (`/api/activities?perPage[]=N&page[]=N`, gevonden via een netwerkcheck), geen Playwright nodig. 1213 resultaten NL-breed, drie types: `activity` → events-DB (echte datum + coördinaten, genre `'actief'` expliciet via `cats`, ~68-71/run), `route` → **`routes.json`** (2026-08-19, geen datum dus buiten de events-DB om — voedt de 4e topniveau-modus "Wandelingen/tochten", zie ARCHITECTURE.md, 220/run), `accomodation` (kampeerterreinen, overgeslagen)) |
| Into Nature "extra activiteiten" (Roderwolde, Drenthe) | `scrape_intonature.py` (2026-08-18, overleg.md punt 15 — React-app, wél Playwright nodig. Geen per-activiteit HTML-element, alleen een platte H3(dag)/H5(titel, niet altijd aanwezig)/P(vrije tekst)-opeenvolging binnen 1 container — op-volgorde-lopende parser i.p.v. CSS-selectors. Terugkerend laagdrempelig "Boswachters met bakfiets"-inloopmoment bewust overgeslagen (titel-check, want kreeg 1x per ongeluk toch een H5). **Kleine, bewust niet-generieke bron**: 1 tentoonstelling/seizoen, volgend jaar andere URL/titel — dan opnieuw bekijken i.p.v. dit script automatisch te laten meedraaien. 11 events/run) |
| Akerk (Groningen) | `scrape_akerk.py` (2026-08-19 — React-app, maar publieke JSON-API (`events.json`, gepagineerd) gevonden via netwerkcheck, geen Playwright nodig. `eventTypes`-array als genre-signaal (`EVENTTYPE_CAT_MAP`: Expositie→expositie, Orgelconcert/Koor→klassiek, Festival→festival). Vaste locatie (1 gebouw). 11 events/run) |
| Drents Museum De Buitenplaats (Eelde) | `scrape_debuitenplaats.py` (2026-08-21, overleg.md punt 13 — geen Playwright nodig, server-rendered: listingpagina linkt naar per-expositie-pagina's met een `<meta name="description">` die het datumbereik in vrije tekst noemt. Alleen het volledige "Van X t/m Y"-patroon meegenomen; permanente attracties (Museumtuin, Nijsinghhuis, geen datum) en einddatum-zonder-start-gevallen ("Beauty of the Beast") bewust overgeslagen — geen startdatum verzinnen, zelfde principe als punt 15. 1 event/run) |
| Keramiekmuseum Princessehof (Leeuwarden) | `scrape_princessehof.py` (2026-08-21, overleg.md punt 13 — Nuxt.js/Vue-app, wél Playwright nodig (geen JSON-API gevonden, content client-side gehydrateerd). Listingpagina heeft 3 tabs ("Nu in het museum"/"Verwacht"/"Geweest") die client-side wisselen welke links zichtbaar zijn — scraper klikt ook op "Verwacht" om die exposities niet te missen. Datumtekst staat niet altijd in hetzelfde `<article>`-element en de bron gebruikt zowel "D maand JJJJ t/m D maand JJJJ" als "van D maand JJJJ tot en met D maand JJJJ" — beide varianten in 1 regex. Permanente presentaties ("Van Oost en West") en pagina's zonder datumpatroon ("Gouden Vrienden", "Josiah Wedgwood") bewust overgeslagen. 3 events/run) |
| Universiteitsmuseum Groningen (rug.nl) | `scrape_universiteitsmuseum.py` (2026-08-21, overleg.md punt 13 — eerder (2026-08-17) verkeerd ingeschat als "Playwright nodig", dat gold voor het verkeerde domein (universiteitsmuseum.nl redirect't naar UMU Utrecht). Draait op rug.nl (standaard RUG-CMS), volledig server-rendered, geen Playwright nodig. "Masterminds" (permanent, geen datum) en "Puin Hoop: herdruk van de jaren '80" (alleen "T/m"-einddatum, geen zichtbare start — mede door GRID Grafisch Museum, dezelfde skip-reden als bij punt 13's eerdere GRID-verdict) bewust overgeslagen. 2 events/run) |

Plus `scrape_naarzuidlaren.py` (lokale Zuidlaren-evenementen, geen eigen SRC-badge)
en `scrape_handmatig.py` (zie ✋ hieronder).

## 🌐 AI/Chrome nodig — geparkeerd als "moeilijk" (6 bronnen)

Michiel, 2026-08-15: "parkeren we deze even als moeilijk, pakken we stuk
voor stuk op als we zin hebben" — geen actieve vervolgstap gepland, dit is
bewust de rustplek voor bronnen waar de dag-technieken (verkeerde-URL-check,
Playwright, Ticketmaster) niet meer verder komen zonder een wezenlijk
andere aanpak (wachten op een seizoen, of een mens die door een
cookie-flow/GraphQL-schema heen gaat). Alle 25 andere bronnen die op
2026-08-15 nog "AI/Chrome nodig" waren, zijn inmiddels opgelost — zie de
`## ✅ Geautomatiseerd`-sectie hierboven en decisions.md voor de volledige
geschiedenis per bron.

**Groninger Museum alsnog opgelost (2026-08-17)** — zie decisions.md: bleek
géén GraphQL nodig te hebben, gewoon een publieke JSON-API die een
Playwright-netwerkcheck blootlegde. **Drents Museum draait op dezelfde Craft
CMS** — waarschijnlijk een vergelijkbare `/api/exhibitions`-achtige endpoint,
nog niet apart herchecked, maar een sterke kandidaat om ook op te lossen.

OntdekPoort en Hunebedcentrum zijn hier bewust anders dan de andere 4:
échte bot-bescherming (403), een principiële grens (nooit omzeild), geen
"nog niet gelukt".

| Bron | Verwachte omvang | Notitie |
|---|---|---|
| EM2 Groningen | ~21 events | WordPress met custom `event`-post-type, WEL via `/wp-json/wp/v2/event` opvraagbaar — maar de evenementdatum staat los in vrije tekst zonder vast patroon ("De Gipsy Jazz Sessie op 12 juli is...", datum niet aan het begin zoals bij Zuidhaege) en sommige entries lijken terugkerende events zonder duidelijke enkele datum. Deels opgelost (API gevonden) maar datum-extractie te onbetrouwbaar bevonden om nu te bouwen. |
| Drents Museum | onbekend | zelfde Craft CMS als Groninger Museum (nu opgelost, zie hierboven) — waarschijnlijk een vergelijkbare `/api/exhibitions`-achtige JSON-endpoint, nog niet herchecked sinds die vondst. |
| Zummerbühne | ~25 events | Ticketwidget in iframe, geen data in ruwe HTML. Met Playwright de iframe geïdentificeerd: een widget van platform "Slinger" — bleek bij nader onderzoek een **ride-share/carpool-widget** te zijn (rides/routebeschrijving), niet de ticketverkoop zelf. Doodlopend spoor, geen Ticketmaster-match ook. |
| OntdekPoort | ~216 events | Bot-bescherming — zelfs de homepage geeft 403, niet op te lossen met alleen headers (2026-08-13, herbevestigd 2026-08-15) |
| Hunebedcentrum | onbekend | Bot-bescherming, 403 (2026-08-13, herbevestigd 2026-08-15) |
| GIJS Groningen (ijshockey) | — | site toont nog seizoen 2025-2026 (herchecked 2026-08-15, nog steeds oud), herchecken zodra nieuw seizoen live is |

## 🔧 Kan zonder AI — structureel lastig te automatiseren (0 bronnen)

Leeg sinds 2026-08-17 — Geke Hoogstins (de laatste in deze categorie) is
opgelost zodra de Exposities-modus doorlopende exposities kon representeren,
zie de ✅-sectie hierboven.

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

## ❓ Landelijke podia — allemaal opgelost 2026-08-15 (geschiedenis)

Bij de eerste check (2026-08-14, plain requests) bleken deze grote,
commerciële venues consistent zwaar client-rendered — geen bruikbare
JSON-LD/`__NEXT_DATA__` gevonden. Op 2026-08-15 opnieuw gecheckt met een
bredere test (tellen van datum-achtige strings in de ruwe HTML i.p.v. alleen
JSON-LD/`__NEXT_DATA__`): **Melkweg en 013 Tilburg bleken alsnog gewoon
server-rendered** (de eerdere check keek specifiek naar `__NEXT_DATA__`/
JSON-LD en miste dat de HTML zelf al complete event-lijsten bevat) — nu
opgelost, zie ✅ hierboven. Landstede Hammers is ook al opgelost (2026-08-15,
zie eigen sectie hierboven — BNXT League-API, niet deze site).

TivoliVredenburg werd eerst opgelost via een Songkick-omweg (aanname: de site
zelf toonde een "Just a moment..."-Cloudflare-challenge, bewust niet
omzeild) — **op 2026-08-17 bleek die aanname niet meer te kloppen** (of nooit
volledig juist te zijn geweest) en is de scraper herzien naar een directe
aanpak, zie ✅ hierboven en decisions.md 2026-08-17.

Hedon Zwolle bleek een lege Angular-SPA-shell (7KB) te zijn, maar heeft een
eigen `/api/events`-endpoint — opgelost, zie ✅ hierboven
(`scrape_hedon.py`). GelreDome (Webflow, client-side CMS-collectie) is
opgelost met Playwright. Ziggo Dome via Ticketmaster, Ahoy via Ticketmaster,
Effenaar/De Doelen/Paradiso/Concertgebouw/Rotown/Het Paard bleken stuk voor
stuk verkeerde-URL-fouten (zie decisions.md), Doornroosje/Grand Theatre
gewoon Playwright.

**Alle 15 oorspronkelijke landelijke podia zijn nu opgelost** (2026-08-15).

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
