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
- **Sport-events bypassen `classify()` volledig**: sportwedstrijden (bv. "FC Twente - PEC Zwolle") matchten geen enkel titel-keyword en vielen terug op `overig`. `event_html()` gebruikt nu `genre='sport'` + het `sport`-veld uit de JSON rechtstreeks voor icoon/label (nieuwe `SPORT_ICONS`/`SPORT_LABELS`-dicts), i.p.v. via `classify()` te gokken.
- **`scrape_handbal.py` gebouwd (E&O + Hurry-Up)**: de standaard datumfilter op handbal.nl toont maar 2 weken vooruit, wat ten onrechte de indruk gaf dat er niks gepubliceerd was (gemeld door Michiel). Onderliggende Sportlink-API (`api.handbal.nl/.../program`) accepteert een `filters[date]=VAN><TOT`-range en een grotere paginagrootte — daarmee blijkt het hele seizoen al gepubliceerd. Lost ook Hurry-Up's oude 404 op (nieuwe bron: officiële NHV-clubpagina i.p.v. de kapotte eigen site). Alleen 1e senioren-teams (HS1/DS1) meegenomen, jeugdteams bewust uitgesloten.
- **Afstand handmatig invoerbaar gemaakt**: klik op het "≤ X km"-label naast de slider opent een `prompt()` voor een eigen kilometerwaarde — herstel van functionaliteit die in een eerdere versie blijkbaar is weggevallen.
- **`scrape_spotgroningen.py` herbouwd + KRITIEKE FIX in `insert_event()`**: SPOT's eigen `data-location`/`data-genres`/`data-subgenres`-attributen geven een preciezer venue (Oosterpoort vs Stadsschouwburg) en genre-signaal dan titel-keywords gokken. Bij het herscrapen bleek de eigenlijke oorzaak dieper te zitten: `insert_event()` liet bij een titel+datum-botsing altijd de *eerst ingevoegde* bron winnen, ongeacht kwaliteit — dus als een aggregator toevallig eerder gescraped was dan de venue-specifieke bron, won de aggregator structureel, en kreeg de cross-source-dedup-logica (hierboven) nooit de kans omdat de betere rij al bij het invoegen was geweigerd. Fix: bij zo'n botsing overschrijft een nieuwe directe-venue-rij nu een bestaande aggregator-rij. Dit is een generieke fix (niet SPOT-specifiek) die voorkomt dat ditzelfde patroon zich elke week bij andere bronnen herhaalt — maar heeft pas effect zodra een bron opnieuw gescraped wordt.
- **Architectuurprincipe voor scrapers herbevestigd**: één klein, op zichzelf staand `scrape_<bron>.py`-bestand per bron (i.p.v. één gedeeld/groot scraper-bestand), ook als dat duplicatie tussen bestanden betekent (bv. meerdere venues op hetzelfde ticketing-platform). Reden: kleinere bestanden zijn veiliger te editen (zie KRITIEKE REGEL over `gen_uitjes.py`-truncatie) en een fout is meteen te lokaliseren tot precies het juiste bestand. `SCRAPERS.md` toegevoegd als overzicht: welke bronnen al zo'n script hebben, welke een kant-en-klare recipe zonder script, en welke nog AI/Chrome-onderzoek nodig hebben. Einddoel (Michiel): de wekelijkse refresh volledig automatisch laten draaien zonder AI — AI wordt alleen eenmalig ingezet om de scrape-methode van een bron te ontdekken, niet structureel bij elke run.

## 2026-08-14 — deze sessie
- **`run_weekly_refresh.py` toegevoegd** ter vervanging van de handmatige scraper-lijst in `ARCHITECTURE.md`: die liep binnen twee sessies drie kwart achter (31 scrapers bestonden, de lijst noemde er nog 7 — zie `overleg.md` punt 7). Het script globt zelf alle `scrape_*.py`-bestanden, draait elk als subprocess (timeout 300s), en detecteert een harde fout als: non-zero exit, ontbrekende `✓ Klaar:`/`Dry-run:`-regel in de output, of een timeout. Bij een harde fout wordt het script automatisch hernoemd naar `fix_<naam>.py` — matcht de glob niet meer, dus wordt overgeslagen tot iemand het repareert en terugzet. Scripts die succesvol 0 events vinden worden **niet** hernoemd (kan legitiem zijn, bv. buiten seizoen) maar wel gerapporteerd. Reden voor auto-quarantine i.p.v. gewoon laten falen: één kapotte scraper mag de wekelijkse refresh van de andere 30 niet blokkeren, en een stilzwijgend falende scraper (die nooit meer gecheckt wordt) is erger dan een zichtbaar uit-de-roulatie-gehaald bestand.
- **`page_cache.py` toegevoegd** (change-detection/hash-caching, zie `overleg.md` punt 2 en `ARCHITECTURE.md` §Change-detection): een `unchanged(key, data)`-helper die een SHA256-hash van de geëxtraheerde eventdata (niet de ruwe HTML — die bevat te veel ruis zoals advertenties/tokens) vergelijkt met de vorige run, opgeslagen in een nieuwe `page_hash`-tabel in `events.db`. Bij ongewijzigde data wordt de insert-stap overgeslagen. Bewust géén early-stop tijdens het ophalen zelf (zie eerdere afweging in `overleg.md` punt 2) — bespaart CPU/DB-tijd, niet netwerktijd. Toegepast als werkend voorbeeld op `scrape_martiniplaza.py`. Michiel gaf expliciet akkoord om dit patroon over alle 31 scrapers uit te rollen, niet alleen als losstaand voorbeeld te laten staan.
- **`run_weekly_refresh.py`-timeout 300s → 600s**: bij de eerste echte (niet-dry-run) run werd `scrape_friesland.py` automatisch gequarantained (hernoemd naar `fix_friesland.py`) — geconstateerd na onderzoek: geen kapotte scraper, maar friesland.nl's ~69 pagina's à ~3s/pagina zaten (zeker bij netwerkdrukte) over de toenmalige 300s-grens. Timeout verhoogd naar 600s en `scrape_friesland.py` teruggezet. Les: de grote aggregators (drenthe.nl/friesland.nl/visitgroningen, elk tientallen pagina's) hebben structureel meer marge nodig dan de kleine one-page scrapers — een vaste timeout moet op het traagste geval afgestemd zijn, niet op het gemiddelde.
- **Prioriteitsvolgorde voor AI-inzet herbevestigd** (Michiel, expliciet): eerst plain scripts (goedkoopst, automatisch, geen AI nodig bij elke run), AI alleen inzetten wanneer een bron dat echt vereist, en dan bij voorkeur de simpelste/goedkoopste AI-aanpak die werkt. Einddoel blijft dat de wekelijkse refresh volledig "no-ai-needed" wordt — bevestigt en scherpt het eerder vastgelegde einddoel aan (zie hierboven, sessie 2026-08-11) i.p.v. het te wijzigen.

## 2026-08-15 — deze sessie
- **Sync**: lokale repo was 17 commits achter op `origin/main` (GitHub = source of truth). Fast-forward liep eerst vast op een stale `.git/HEAD.lock` (van 6 juli, geen actief proces) — verwijderd, daarna schoon ge-fast-forward.
- **Wekelijkse refresh krijgt een vaste plek**: opgelost, overleg.md punt 1 — deze laptop (`C:\dev\uitjesagenda`, gebruiker `mrhva`), niet de andere (kapotte) pc, niet Cowork. Michiel expliciet: "kan worden gedraaid door een script (zoveel mogelijk) en geen AI" — sluit aan bij het al vastgelegde no-ai-needed-einddoel.
- **Windows Taakplanner-taak "uitjes-agenda-refresh"** vervangt de oude Cowork scheduled task: draait `weekly_refresh.ps1` (nieuw bestand — pure PowerShell-wrapper om `run_weekly_refresh.py`, committen/pushen alleen als `git status --porcelain` iets teruggeeft, logt naar `refresh_log.txt`). Schema: **ma/wo/za 04:00** (was: alleen maandag 08:04) — Michiels expliciete keuze voor 3x/week i.p.v. 1x.
- **Taak-principal op S4U gezet** (niet het standaard "Interactive"): een niet-elevated `Register-ScheduledTask` gaf alleen `LogonType Interactive` (draait alleen bij ingelogde sessie); `S4U` (geen wachtwoord opgeslagen, draait ongeacht inlogstatus) vereiste een `Set-ScheduledTask` vanuit een **verhoogde** PowerShell — kon niet vanuit de sessie zelf (geen adminrechten), Michiel heeft het commando zelf in een Administrator-PowerShell gedraaid.
- **`refresh_log.txt` toegevoegd aan `.gitignore`** — lokaal logbestand van de taak, hoeft niet gecommit te worden (zelfde categorie als `events.db`).
- **Kritieke bug gevonden en gefixt: 24 van de 31 scrapers faalden stilzwijgend op deze laptop.** Python is hier `3.14.0` (OpenSSL 3.0.18); sinds Python 3.13 staat `ssl.VERIFY_X509_STRICT` standaard aan in `ssl.create_default_context()`. Veel echte sites (drenthe.nl, friesland.nl, martiniplaza.nl, github.com, ...) hangen aan een tussenliggend CA-certificaat waarvan Basic Constraints niet als 'critical' gemarkeerd is — een kleine, door vrijwel elke andere TLS-library getolereerde RFC5280-afwijking — en die strengere default weigert zo'n keten. Elke `urlopen()` zonder eigen SSL-context kreeg `certificate verify failed: Basic Constraints of CA cert not marked critical`. Bevestigd via een echte `--dry-run` **in PowerShell** (dezelfde omgeving als de Taakplanner-taak), niet alleen in de Bash-tool.
  - **Waarom dit niet was opgevallen als "harde fout" / quarantaine**: scrapers vangen fetch-fouten af en melden gewoon "0 events gevonden" — dat matcht de self-healing-quarantaine-check in `run_weekly_refresh.py` niet (geen crash, wel een `Dry-run:`/`✓ Klaar:`-regel). Zonder deze fix zou de nieuwe ma/wo/za-taak dus **stilzwijgend** bijna alle bronnen op 0 nieuwe events hebben gezet, zonder duidelijk alarm.
  - **Waarom 7 scrapers (6 + handmatig) hier niet door geraakt werden**: `scrape_drenthe.py`, `scrape_friesland.py`, `scrape_handbal.py`, `scrape_naarzuidlaren.py`, `scrape_spotgroningen.py`, `scrape_visitgroningen.py` bouwen al hun eigen SSL-context met `verify_mode = ssl.CERT_NONE` (certificaatverificatie helemaal uit — vermoedelijk een eerdere, snellere workaround voor precies dit soort SSL-problemen). Werkt, maar is onveiliger dan nodig (geen enkele controle meer, ook geen hostname-check). Nog niet aangepakt — apart, lagere-prioriteit punt, zie `plan.md`.
  - **Fix**: nieuw bestand `ssl_fix.py` — patcht `ssl._create_default_https_context` zodat alleen de `VERIFY_X509_STRICT`-vlag uitgaat (hostname- en ketenverificatie blijven intact, dus geen CERT_NONE-achtige verzwakking). Geïmporteerd als side-effect in `page_cache.py`, dat toch al door alle 30 live scrapers geïmporteerd wordt — dus geen enkel scrape-bestand hoefde individueel aangepast te worden. Alle 24 eerder falende scrapers + `run_weekly_refresh.py --dry-run` opnieuw getest na de fix: allemaal weer echte aantallen i.p.v. SSL-fouten.
  - **Meteen ook de 6 CERT_NONE-scrapers opgeruimd** (`drenthe`, `friesland`, `handbal`, `naarzuidlaren`, `spotgroningen`, `visitgroningen`, zie hierboven): `ssl_fix.py` kreeg een herbruikbare `create_context()`-functie; de 3-regelige `verify_mode = ssl.CERT_NONE`-blokken in deze 6 bestanden vervangen door `SSL_CTX = create_context()` (zelfde read→str.replace→ast.parse→write-methode, geen Edit-tool op de grotere bestanden zoals `scrape_drenthe.py`/`scrape_friesland.py`, ~250-275 regels). Certificaatverificatie staat nu overal weer aan — alleen de te-strenge RFC-nitpick is uitgeschakeld. Alle 6 opnieuw functioneel getest na de wijziging.
- **Donar + Landstede Hammers (basketbal) opgelost — nieuwe bron: BNXT League's eigen site, niet de clubsites.** Michiel vroeg te checken of clubsites in de BNXT League (of hun CMS — WordPress/Joomla-plugins) een API voor wedstrijdschema's gebruiken, "zoeken of iemand dit pad al gelopen heeft". Geen generieke WP/Joomla-plugin gevonden bij de individuele Belgische/Nederlandse clubsites (stuk voor stuk custom/bureau-gebouwd). De echte vondst: **bnxtleague.com zelf** draait op een bespoke CMS "Sportpress" van bureau Webpont ([specifiek voor deze competitie gebouwd](https://webpont.com/sportpress)), met een publieke JSON-API op `bnxt.sportpress.info` — inclusief een statische `X-Authorization`-token die gewoon in de publiek uitgeleverde JS-bundle staat (geen login/secret, zelfde categorie publieke-frontend-key als eerdere reverse-engineered API's in dit project).
  - **API-mechaniek** (uitgezocht via de JS-bundle van bnxtleague.com, geen officiële documentatie): `phase/season/{jaar}` → competition_id + phase_id per fase (Regular season/Supercup/Playoffs); `competition-team/all?competition_id=X` → team-ids per competitie (veranderen elk seizoen); `schedule/club/{seizoen}?phase_id=..&competition_team_id=..&clubs[0]=1&clubs[1]=2&monthCount=12[&month=1..12]` → wedstrijden — het "club" in het pad is verwarrend genoeg het SEIZOEN (bv. "2027" voor 2026-2027), niet een team-id. Zonder `month`-param komen alleen de eerste ~3 maanden mee; door zowel de default-call als `month=1..12` op te halen en op wedstrijd-id te dedupliceren komt het hele seizoen mee (getest: 30 wedstrijden voor Donar, 2 okt 2026 - 31 mei 2027). Volledige uitleg in `scrape_donar.py`'s docstring.
  - **Dit lost tegelijk twee eerder losse problemen op**: Donar (3 eerder onderzochte routes — donar.nl zelf, basketball.nl/Foys, NBB-database — liepen allemaal dood, zie SCRAPERS.md-geschiedenis) én Landstede Hammers (stond op de "geblokkeerd"-lijst, DNS-problemen bij eerdere pogingen). Season/phase/team-id worden dynamisch opgezocht (niet hardcoded), zodat de scraper volgend seizoen niet handmatig bijgewerkt hoeft te worden.
  - **Bijvangst**: de database bevatte nog 14 verouderde, losstaand-ingevoerde Donar-events (andere titelstijl "Donar - X" i.p.v. "Donar Groningen - X", generieke `/wedstrijden`-URL, herkomst niet gedocumenteerd — vermoedelijk een eerdere eenmalige Chrome-pull). Die botsten niet met de titel+datum-UNIQUE-constraint (net iets andere titeltekst) en gaven dus dubbele wedstrijden in de site. Opgeruimd vóór export.
  - **Kwetsbaar punt, bewust geaccepteerd**: de API-token staat in een webpack-JS-bestand met een content-hash in de bestandsnaam — kan bij een toekomstige deploy van bnxtleague.com wijzigen. Als de scraper op een dag met 401's faalt: nieuwe token uit de huidige `/js/app.*.js` halen (zie docstring). Geen structurele oplossing hiervoor gebouwd — lage kans, lage impact (self-healing quarantaine vangt het op als hard-fail).
- **4 bronnen van "AI/Chrome nodig" naar automatisch verplaatst, methodiek: JS-bundle/HTML doorzoeken i.p.v. aannemen dat client-rendered = Chrome nodig.** Vervolg op de Donar-vondst — dezelfde aanpak (JS-bundles/ruwe HTML doorzoeken op verborgen API's of over het hoofd geziene server-rendering) leverde nog 4 wins op:
  - **Atlas Theater Emmen** (`scrape_atlastheater.py`): draait op Umbraco (.NET CMS) met een ticketingplatform (herkenbaar aan `agenda.ticketunie.com`-afbeeldings-URL's). `/Umbraco/Api/PerformanceApi/GetPerformances` geeft zonder auth het hele seizoen (192 events) in één call. Eerdere recipe ging uit van een Chrome-klik-loop op "Laad meer" — bleek niet nodig.
  - **Podium Zuidhaege Assen** (`scrape_podiumzuidhaege.py`): WordPress met een custom `event_listing`-post-type dat WEL via `/wp-json/wp/v2/event_listing` opvraagbaar is (in tegenstelling tot Vera/Simplon, ook WordPress maar zonder REST-exposed events-type — die blijven dus AI/Chrome nodig). De evenementdatum zit niet in een REST-veld (`meta` staat leeg, custom fields niet REST-geregistreerd) maar wél als vrije tekst in `content.rendered` ("Op zaterdag 10 oktober...") — zelfde tekst-regex+jaartal-afleiding-patroon als `scrape_dorpshuisannen.py`.
  - **Melkweg** en **013 Tilburg** (`scrape_melkweg.py`, `scrape_013.py`): de 2026-08-14-check keek specifiek naar `__NEXT_DATA__`/JSON-LD en concludeerde "geen server-rendered events" bij afwezigheid daarvan — maar beide sites renderen de agenda-HTML gewoon zelf server-side (compleet met datum/titel/link in de DOM), los van wat er in de JSON-praps-structuur zit. Ontdekt door simpelweg te tellen hoeveel datum-achtige substrings in de ruwe HTML zitten i.p.v. alleen op JSON-LD/`__NEXT_DATA__` te vertrouwen. Les voor volgende checks: die eerdere aanpak (alleen JSON-LD/`__NEXT_DATA__` checken) kan false negatives geven — een bredere HTML-scan is een goedkope extra stap vóór iets definitief als "AI/Chrome nodig" wordt bestempeld.
  - **Effenaar** lijkt op eenzelfde false-negative te wijzen (150 datum-achtige strings bij hercheck) maar bleek bij inspectie CMS-content-block-metadata te zijn, niet per se events — niet afgerond, zie SCRAPERS.md.
  - **Bijvangst, zelfde patroon als de oude Donar-rijen**: alle 4 bronnen bleken al oudere, ongedocumenteerde losse data in de DB te hebben staan (uit een eerdere, nergens vastgelegde eenmalige pull) — voor Melkweg/013/Atlas Theater waren dit stuk voor stuk **verlopen** events (juni/juli 2026, al voorbij op het moment van scrapen). 252 stale rijen in totaal opgeruimd (61 melkweg, 23 013, 166 atlastheater, 2 podiumzuidhaege) door per bron de vers-gescrapete (titel_norm, datum)-set te bepalen en al het andere te verwijderen. Les: bij het bouwen van een scraper voor een bron die al langer in `gen_uitjes.py`/`SRC` voorkomt, checken of er nog "wees"-data van een eerdere sessie in de DB zit, niet aannemen dat de bron bij nul begint.

## 2026-08-15 vervolg — veilige omgang met API-keys
Michiel plakte per ongeluk een (vermoedelijk Ticketmaster-)API-key in de
chat, gevolgd door een link naar de OAuth-loginpagina. Zelfde risico als het
eerdere GitHub-PAT-incident: een key die eenmaal in een transcript staat,
moet als gecompromitteerd behandeld worden. Afgesproken:
- Michiel regenereert de key op developer.ticketmaster.com.
- Nooit een key in de chat plakken, ook niet expliciet gevraagd — zelfde
  regel als voor GitHub PAT's, nu verbreed naar alle API-keys/secrets.
- Nieuw patroon opgezet: `secrets.local.json` (in `.gitignore`, nooit
  gecommit) + `secrets_local.py` (`get_secret(naam)`-helper) +
  `secrets.local.json.example` (template, wel gecommit). Michiel vult de
  echte waarde zelf lokaal in, buiten de chat om. Zie ARCHITECTURE.md §API-keys.
- Ticketmaster Discovery API zelf: alleen een API-key nodig voor read-only
  requests (`?apikey=...` als query-param), geen OAuth/consumer-secret nodig
  — bevestigd via developer.ticketmaster.com/products-and-docs/apis/getting-started/.
  5.000 calls/dag gratis tier, 5 requests/seconde rate limit.

## 2026-08-15 vervolg — tweede ronde door de 25 resterende AI/Chrome-bronnen
- **FC Groningen opgelost** (`scrape_fcgroningen.py`): stond als "eenmalig via Chrome gehaald, geen los script" (2026-07-05) maar volgt gewoon hetzelfde ESPN.nl-patroon als Cambuur/FC Twente/Go Ahead/PEC Zwolle (team-id 145, gevonden via websearch). Zelfde bijvangst-patroon als Donar/de vorige 4: 18 verouderde rijen in de DB (generieke `tickets.fcgroningen.nl`-URL, uit die eenmalige Chrome-pull) opgeruimd — sommige hadden zelfs een **andere tegenstander** op dezelfde datum dan de verse ESPN-data (schema was kennelijk gewijzigd sinds juli), dus dit was niet alleen overbodig maar deels ook gewoon fout.
- **Methodiek verder aangescherpt — belangrijkste les deze ronde**: "client-rendered" of "SPA" is niet altijd wat het lijkt. Twee concrete valkuilen ontdekt:
  1. Een check die alleen op `__NEXT_DATA__`/JSON-LD let kan mis zijn (zie Melkweg/013 in de vorige sessie) — een simpele telling van datum-achtige substrings in de ruwe HTML is een goedkope extra check.
  2. **Cloudflare bot-challenges herkennen en met rust laten**: TivoliVredenburg bleek een echte "Just a moment..."-Cloudflare-uitdaging te tonen — expliciet NIET geprobeerd te omzeilen (curl-trucs, headers spoofen e.d.), dat hoort bij een echte browser opgelost te worden, niet door bot-detectie te omzeilen. Dit is een principiële grens, niet alleen een praktische ("kan niet") — zie de veiligheidsregels over CAPTCHA/bot-detectie.
- **Nieuw platform herkend: Webflow + Finsweet CMS-filter** (Neushoorn, GelreDome) — CMS-collecties staan als lege placeholder (`w-dyn-bind-empty`) in de ruwe HTML, worden client-side gevuld. Geen voor de hand liggende publieke API (Webflow's CMS-API vereist meestal een site-specifieke key). Beide blijven AI/Chrome nodig.
- **Vera (en waarschijnlijk Simplon)**: gedeeltelijke server-rendering ontdekt (~20 van ~60 events staan al in de ruwe HTML van pagina 1), maar de paginering loopt via een WordPress `admin-ajax.php`-call (`action=renderProgramme`) die zonder browsersessie een lege 200-respons geeft — vermoedelijk Cloudflare Bot Management op dat specifieke endpoint (de gewone paginabezoeken laden wel gewoon). `?page=N` als URL-parameter bleek een dode mus (wordt server-side genegeerd, altijd dezelfde pagina 1-inhoud). Bewust niet gebouwd: een scraper die structureel maar 1/3 van de events vindt zou een verkeerd beeld van "compleet" geven.
- **EM2 Groningen**: WordPress met een custom `event`-post-type dat WEL via REST opvraagbaar is (in tegenstelling tot Vera/Simplon) — maar de datum staat middenin vrije tekst zonder consistent patroon ("De Gipsy Jazz Sessie op 12 juli is...", niet aan het begin zoals bij Zuidhaege). Bewust niet gebouwd deze ronde — te onbetrouwbare regex-extractie voor de verwachte kleine winst (~21 events), kan later opgepakt worden met een zorgvuldiger patroon.
- **Effenaar**: 150 datum-achtige strings gevonden bij de brede check, maar bleken bij inspectie CMS-content-block-metadata (Statamic-achtige structuur), niet per se events-datums. Onderzoek niet afgerond — blijft AI/Chrome nodig voorlopig, wel een kandidaat om nog eens goed naar te kijken.
- **Overig zonder resultaat, gedocumenteerd om herhaling te voorkomen**: Grand Theatre (custom plugin "michnhokn", geen API-sporen), Koornbeurs (geen Umbraco/API ondanks vergelijkbare bestandsstructuur als Atlas Emmen), Groninger/Drents Museum (Craft CMS, voor de hand liggende GraphQL-paden geven 404), De Doelen (Vite-bundle doorzocht, geen API-aanroepen gevonden), Doornroosje (WordPress maar geen bruikbaar events-post-type), Ahoy (Foundation-framework, geen aanwijzingen), Ziggo Dome (Next.js/Turbopack, nog niet grondig gecheckt — kandidaat voor een volgende ronde na de Melkweg-ervaring), Winsinghhof (domein blijft onbereikbaar, connectiefout).

## 2026-08-15 vervolg — Hedon + TivoliVredenburg opgelost dankzij tips van Michiel
- **Hedon Zwolle**: Michiel wees op een LinkedIn-post van Hedon zelf over hun koppeling met **Yesplan** (venue-planningsoftware, via L1NDA). Bleek de sleutel: `hedon-zwolle.nl/api/events` is een simpele, ongeauthenticeerde JSON-API die zijn data uit Yesplan haalt (herkenbaar aan het `yesplanId`-veld). De site zelf leek eerder een lege Angular-SPA-shell (7KB), maar de eigen backend-API bleek gewoon bereikbaar. Bevat ook events die Hedon promoot maar die ELDERS plaatsvinden (Zwolse Theaters, Calluna Ommen) — gefilterd op `venue` beginnend met "Hedon" zodat alleen echte Hedon-locatie-events meekomen. 118 events.
- **TivoliVredenburg**: Michiel opperde songkick.com als alternatieve bron. Songkick's venue-pagina bevat gewoon JSON-LD (schema.org `MusicEvent`) in de ruwe HTML, geen browser nodig. **Bewuste beperking**: Songkick dekt alleen live-muziek/concerten (geen theater/comedy/klassiek-op-de-eigen-zaal), en toont maar de eerstvolgende ~9 shows (`?page=N` wordt genegeerd) — dus dit is gedeeltelijke dekking, vergelijkbaar met USVA's ~6/10.
- **Belangrijk verschil met de eerdere stale-data-opruimingen vandaag (Donar/Melkweg/013/Atlas/FC Groningen)**: bij het checken op oude data bleek `tivolivredenburg` al **480 rijen** in de DB te hebben, waarvan **401 nog in de toekomst liggen** (aug-nov 2026) — dit is GEEN verouderde/foute data zoals bij de eerdere gevallen, maar een omvangrijke, kennelijk ooit handmatig/via Chrome opgehaalde dataset die veel breder is dan wat de nieuwe Songkick-scraper kan leveren (401 vs 8 events). **Bewust NIET opgeruimd** — de nieuwe scraper voegt alleen een klein, herhaalbaar aanvullend stroompje toe (nabije concerten), de oude bredere dataset blijft gewoon staan totdat die vanzelf "opraakt" (events verlopen). Zelfde afweging bij Hedon: 9 toekomstige "wees"-events (bv. "Jimmy Carr (Theater De Spiegel)" — Hedon-georganiseerd maar in een ander pand) niet verwijderd, want legitiem en niet in conflict met de nieuwe scraper-output.
  - **Les, aanvullend op de eerdere Donar-les**: check niet alleen "zijn er oude rijen die botsen/dubbel zijn" maar ook "is de oude data eigenlijk beter/breder dan wat de nieuwe scraper oplevert" vóór je iets verwijdert — de eerdere 5 gevallen vandaag waren stuk voor stuk verlopen/foute data (veilig te verwijderen), dit was de eerste keer dat de oude data juist waardevoller bleek.
- **Playwright toegevoegd als nieuwe dependency** (`pip install playwright`, na expliciet akkoord van Michiel) om de resterende niet-bot-beschermde JS-gerenderde bronnen (Neushoorn, GelreDome, Ziggo Dome, Effenaar e.d.) alsnog zonder AI te kunnen automatiseren — headless Chromium rendert de pagina, een script leest daarna gewoon de DOM uit, geen LLM/AI-agent nodig per run. `requirements.txt` was bewust leeg ("puur Python stdlib") — dit is de eerste keer dat een externe dependency wordt toegevoegd, bewuste afweging (zie overleg met Michiel). **Principiële grens**: bewust NIET ingezet om bot-detectie/CAPTCHA's te omzeilen (TivoliVredenburg, OntdekPoort, Hunebedcentrum blijven daarom buiten schot, ongeacht of een headless browser die blokkade toevallig zou kunnen passeren).
- **`scrape_neushoorn.py` — eerste Playwright-scraper, werkt.** Chromium geïnstalleerd (`playwright install chromium`), 110 events gevonden. Onderweg ontdekt: het onderliggende ticketingplatform heet **"Stager"** (`neushoorn.stager.co`) — hetzelfde platform dat ook bij Vera gebruikt bleek (`vera.stager.co`), maar de venue's eigen programma-pagina (niet Stager's shop-domein zelf) bleek de simpelste bron met een consistent DOM-patroon (`program_row`/`program_date`/`program_title`). Datumtekst zonder jaartal ("15 Aug") — jaartal afgeleid zoals bij `scrape_dorpshuisannen.py`. Klein aantal (2) toekomstige "wees"-events in de DB die niet in de verse set zaten — bewust niet opgeruimd (te klein om de moeite waard te zijn, geen conflict).
- **Les herbevestigd**: bij elke nieuwe/herbouwde scraper voor een bron die al een `SRC`-key had, eerst checken of er oude data in de DB zit vóór je iets aanneemt — soms is die oude data foutief/verlopen (Donar, Melkweg, 013, Atlas, FC Groningen: veilig te verwijderen), soms juist waardevoller dan wat de nieuwe scraper alleen kan bieden (TivoliVredenburg: laten staan), en soms verwaarloosbaar klein (Hedon, Neushoorn: niet de moeite).
- **`scrape_gelredome.py` — tweede Playwright-scraper, ook Webflow (zelfde platform als Neushoorn).** Mix van Vitesse-thuiswedstrijden en concerten/evenementen (Hard Bass, Snuffelmarkt, Mega Piraten Festijn) in dezelfde kaarten-grid. Paginering via Webflow's eigen `?<hash>_page=N`-querystring, client-side maar Playwright voert de JS gewoon uit dus werkt door de "Volgende"-link te volgen. 21 events, 6 kleine onschadelijke "wees"-rijen in de DB gelaten (geen conflict, te klein om op te ruimen).
- **Ziggo Dome opgelost — via podiuminfo.nl i.p.v. Playwright.** Eerst met Playwright onderzocht: bleek een **gevirtualiseerde lijst** (react-window-achtig, ~40 events, maar een deel tegelijk in de DOM) — scroll-simulatie gebouwd en getest, werkte (40 events gevonden). Maar Michiel wees op podiuminfo.nl (al gebruikt voor Machinefabriek) als alternatief: bleek gewoon JSON-LD (schema.org `MusicEvent`) te bevatten via een plain HTTP-request, géén browser nodig. Bewust gekozen vóór de Playwright-aanpak, ondanks iets minder dekking (25 events tot begin okt 2026, vs 40 tot mei 2027 via scroll) — geen browser-overhead, en podiuminfo geeft echte per-event-URL's (ziggodome.nl's eigen kaarten hebben die niet zichtbaar in de DOM). `scrape_ziggodome.py` gebruikt dus podiuminfo.nl; de werkende scroll-Playwright-aanpak is niet als apart bestand bewaard (was alleen verkennend script).
  - **Bijvangst, near-duplicate-variant**: 13 oude "wees"-rijen (zonder URL, uit dezelfde ongedocumenteerde eerdere pull als Tivoli/Hedon) bleken dezelfde concerten als de verse podiuminfo-data, maar met een titel MET tour-subtitel (bv. "JOJI - Solaris Tour" vs verse "Joji") — matchten dus niet op de UNIQUE(title_norm,date)-constraint en gaven zichtbare dubbels. Opgeruimd (verwijderd waar de datum overeenkwam met een verse rij; 3 losse juli-events zonder match, allemaal al verstreken, met rust gelaten).
  - **Belangrijke valkuil ontdekt, relevant voor toekomstige stale-data-opruimingen**: na het handmatig verwijderen van DB-rijen dacht `page_cache.py`'s `unchanged()`-check dat er "niks veranderd" was bij de eerstvolgende scrape (de opgehaalde data zelf was identiek aan de vorige run), en sloeg dus de hele insert-stap over — waardoor één event (KatsEye) helemaal geen rij meer had (de oude blokkerende rij was weg, maar de nieuwe werd nooit ingevoegd). Opgelost door de `page_hash`-rij voor die bron handmatig te verwijderen (`DELETE FROM page_hash WHERE key=...`) en opnieuw te scrapen. **Les**: na een handmatige DB-opruiming voor een bron altijd ook de page_cache-entry van die bron wissen vóór de eerstvolgende (test-)run, anders lijkt de opruiming zichtbaar niet te "pakken".
- **`scrape_simplon.py` — derde Playwright-scraper.** Simplon draait, net als Vera, op het "Stager"-ticketingplatform en is ook WordPress zonder REST-exposed events — maar anders dan Vera heeft Simplon's eigen programma-pagina een simpel, direct regex-baar DOM-patroon (`block--event`/`block__date`/`block__title`) zodra Playwright de pagina rendert, zonder Vera's AJAX-paginering-blokkade. 48 events (matcht de eerder geschatte ~47). Datumtekst zonder jaartal ("vr 16.10"), jaartal afgeleid zoals bij `scrape_dorpshuisannen.py`. Klein aantal (3) toekomstige wees-rijen, niet opgeruimd (te klein, geen conflict).
- **`scrape_effenaar.py` opgelost — bleek een verkeerde-URL-fout, geen echt "AI/Chrome nodig"-geval.** De eerdere sessie (2026-08-14) checkte `/programma`, wat een 404 geeft — maar Effenaar's site rendert zelfs op een 404 nog een generieke CMS-content-blok-structuur (met een `publish_date`-veld per blok), en dát werd toen ten onrechte aangezien voor "150 datum-strings, mogelijk events, niet per se" (het waren gewoon CMS-metadata van de 404-pagina, geen events). De juiste URL is `/agenda` — daar staat een schoon `agenda-card`-grid met titel, subtitel, volledige datum (mét jaartal, geen inferentie nodig) en zaal. Vierde Playwright-scraper, 125 events. **Les**: bij een "veelbelovend maar niet afgerond"-bevinding eerst de URL zelf verifiëren (bv. met een simpele HTTP-statuscode-check) vóór je de content inhoudelijk gaat interpreteren — een 404 kan zelf ook "geldig ogende" troep-content teruggeven.
- **Winsinghhof opgelost — ook een verkeerde-domein-fout, geen browser nodig.** `winsinghhof.nl` bestaat niet meer (connectiefout); het echte domein is `theaterroden.nl` (de `SRC`-sleutel `theaterroden` in `gen_uitjes.py` gaf dit al aan, maar was nooit doorgetrokken naar de scraper-poging). Site is gewoon server-rendered HTML, geen Playwright nodig — `scrape_theaterroden.py`, 68 events. Michiel opperde podiuminfo.nl als alternatief (net als bij Ziggo Dome), maar dat gaf hier maar 12 van de ~71 events — bevestigt de eerder getrokken conclusie dat podiuminfo specifiek concerten dekt, niet het bredere theater/cabaret-programma dat dit podium vooral doet. Eigen site dus beter hier.
  - **Bijvangst, near-duplicate-variant**: 65 oude "wees"-rijen met een generieke URL (`.../voorstellingen`, geen per-event-link) bleken dezelfde voorstellingen als de verse data, maar met alleen de subtitel als titel (bv. oud "Gestrand op Mars (8+)" vs vers "Wijsneuzen - Gestrand op Mars (8+)") — matchten niet op de unique-constraint, gaven dubbels. Opgeruimd (alle rijen met die generieke URL, ook de paar die toevallig niet in de verse set matchten). Meteen ook proactief de `page_hash`-valkuil (zie hierboven, Ziggo Dome) vermeden door de cache-entry gelijk mee te wissen in hetzelfde opruimscript.
- **Koornbeurs opgelost — vijfde Playwright-scraper.** Eerdere JS-bundle-check vond geen Umbraco/API-endpoints (ondanks een bestandsstructuur die op Atlas Emmen leek) — bleek dus gewoon client-side gerenderd zonder verborgen API, geen bijzondere reden. 127 events (`performance-preview`-grid, dag/maand zonder jaartal, artiest+titel niet consistent gevuld — zelfde fallback-aanpak als `scrape_atlastheater.py`). Zelfde near-duplicate-opruiming als bij Winsinghhof: 109 oude wees-rijen met generieke URL (alleen `title` zonder `artist`-prefix) opgeruimd, `page_hash` proactief meegewist.
- **Grand Theatre Groningen opgelost — zesde Playwright-scraper.** De "innerText-parsing nodig, geen bruikbare CSS-classes"-conclusie uit een eerdere sessie klopte gedeeltelijk (geen data-attributen), maar de DOM-structuur zelf is wél consistent genoeg voor regex: elk event zit in een `<li class="event-container">`-blok met een echte (soms externe, bv. naar noorderzon.nl voor "op locatie"-programma) `overlay-link`-URL en één of meer `<h1>wd DD mmm</h1>`-speelmomenten. Meerdaagse voorstellingen worden meerdere losse events (1 per speeldatum) — 38 unieke shows, 61 events totaal. Geen oude data aangetroffen (61/61 nieuw) — eerste keer dat deze bron succesvol gescraped is.
- **Doornroosje opgelost — zevende Playwright-scraper.** WordPress zonder bruikbaar events-type via REST (zoals eerder geconstateerd), maar de programma-pagina zelf rendert een `c-program__item`-lijst zodra Playwright de JS uitvoert. Bijzonderheid: meerdere shows op dezelfde dag delen één datum-blok — alleen het eerste item van die dag heeft een gevulde datum, latere items (`c-program__item--samedate`) hebben een leeg datum-blok en hergebruiken de laatst geziene datum. 223 events. Groninger/Drents Museum ook met Playwright geprobeerd: pagina blijft leeg zelfs na volledige render (mogelijk cookie-banner-blokkade) — niet verder uitgezocht, lagere prioriteit dan podia.
  - **Bijvangst**: 127 near-duplicate wees-rijen opgeruimd (oude titel zonder support-act-info, `url IS NULL`), `page_hash` proactief meegewist.
- **Ticketmaster Discovery API ingezet — nieuwe bron-categorie, geen Playwright/scraping meer nodig voor venues die er via verkopen.** Michiel opperde het idee (na de key-test) dat grote arena's als Ziggo Dome/Ahoy hun tickets vrijwel allemaal via Ticketmaster verkopen — bevestigd. Nieuw `ticketmaster.py` (herbruikbare helper, zoekt venue-id eenmalig op via `find_venue_id()`, daarna hardcoded in de scraper — respecteert de rate limits: 0.25s tussen calls, size=200 om paginering te minimaliseren).
  - **`scrape_ziggodome.py` vervangen** (was podiuminfo.nl, 25 events tot okt 2026) door Ticketmaster: 83 events tot mei 2027 — duidelijk beter.
  - **`scrape_ahoy.py` nieuw** — stond als "AI/Chrome nodig" (geen API-sporen in eigen Foundation-framework-site), Ticketmaster geeft 41 events.
  - **Getest maar NIET bruikbaar**: Paradiso en Concertgebouw hebben wel een Ticketmaster-venue-match maar 0 events (verkopen kennelijk niet via Ticketmaster); Rotown en Het Paard hebben geen Ticketmaster-venue-match (te klein/indie).
  - **Belangrijke afweging herhaald (Ziggo Dome vs Ahoy)**: bij Ziggo Dome bleken de 21 oude podiuminfo-rijen echte duplicaten van de nieuwe Ticketmaster-data (bv. oud "Joji" = nieuw "JOJI: SOLARIS", zelfde show) — opgeruimd. Bij Ahoy bleken de 85 oude wees-rijen juist BREDERE, niet-overlappende programmering (festivals, sport-entertainment, comedy — dingen die niet via Ticketmaster verkocht worden) — bewust NIET opgeruimd, zelfde afweging als bij TivoliVredenburg eerder vandaag. Les: "veel orphans" is geen automatisch signaal om op te ruimen — altijd eerst checken of de oude data dezelfde events zijn (duplicaat, opruimen) of andere events (aanvullend, laten staan).
- **Het Paard opgelost — via denhaag.com, geen Playwright nodig.** `paard.nl` (niet `hetpaard.nl` — dat domein bestaat niet, zelfde soort fout als Winsinghhof) bleef zelfs met Playwright leeg. Michiel opperde denhaag.com/nl/paard (de stads-agenda van The Hague & Partners) als omweg. Die pagina toont 8 events tegelijk met een "Meer activiteiten"-knop (client-side load-more), maar `?page=N` werkt ook gewoon als directe URL — dus plain HTTP-paginering volstaat, geen browser nodig. Twee datumformaten in de kaarten: "zat 22 aug" (los, jaartal afgeleid) en "28 augustus 2026 t/m 29 augustus 2026" (meerdaagse Paardcafé-nachten, jaartal aanwezig, eerste datum gebruikt). 92 events over 12 pagina's.
  - **64 toekomstige "wees"-rijen aangetroffen, bewust NIET opgeruimd**: bleken geen duplicaten maar andere titels met een `paard.nl/en/event/`-URL (blijkbaar een eerdere sessie kreeg wel losse events van de eigen site te pakken) — legitiem aanvullend, zelfde afweging als bij Ahoy/TivoliVredenburg.
- **Paradiso en Concertgebouw alsnog opgelost — bleken géén Ticketmaster-only-gevallen, maar gewoon (weer) een verkeerde-URL-fout.** Michiel vroeg door na "zijn we bij alleen de moeilijke over" — bleek terecht: beide hadden gewoon nog nooit de juiste agenda-URL gehad.
  - **Paradiso** (`scrape_paradiso.py`, negende Playwright-scraper): homepage had geen vindbare agenda-link, maar via websearch bleek er een specifieke landingspagina te bestaan (`/landing/concertagenda-paradiso/2069817`) — niet vanaf de site zelf te vinden, wel via een zoekmachine. Chakra UI (React) met auto-gegenereerde CSS-hash-classes — regex matcht daarom op tagvolgorde i.p.v. specifieke class-namen (iets robuuster tegen toekomstige rebuilds). 100 events, geen paginering nodig (complete lijst op één pagina).
  - **Concertgebouw** (`scrape_concertgebouw.py`, tiende Playwright-scraper): Michiel gaf de juiste URL (`/concerten-en-tickets`) en de tip dat de paginering tot ~39 doorloopt. Vue.js-app, events gegroepeerd per dag-blok. **600 events** — de grootste scraper van het project (~700 concerten/jaar). Belangrijke optimalisatie: één Chromium-instance hergebruikt voor alle ~40 pagina's i.p.v. een nieuwe browser per pagina starten (zou anders traag zijn, zie ARCHITECTURE.md §Playwright-scrapers) — duurt nu ~1,5 minuut voor de hele run.
  - **Les, aanvullend op de eerdere URL-fouten (Effenaar/Winsinghhof/De Doelen/Het Paard)**: "geen agenda-link op de homepage gevonden" is geen bewijs dat een bron AI/Chrome nodig heeft — vaak is het gewoon de verkeerde/niet-voor-de-hand-liggende URL. Een korte websearch naar "de juiste agenda-URL" is goedkoper dan meteen concluderen dat een bron client-side/onbereikbaar is.
- **Vera opgelost — bleek géén Cloudflare-blokkade, gewoon de verkeerde tool voor de klus.** Michiel vroeg door: "zitten we al bij alleen de moeilijke over?" — Vera was het test-geval. Eerdere sessie concludeerde "Cloudflare Bot Management blokkeert de admin-ajax-paginering" op basis van curl-POST-pogingen die steeds een lege respons gaven. Bleek de verkeerde diagnose: het is helemaal geen AJAX-knop maar een **infinite-scroll** (IntersectionObserver-getriggerd) — curl kan niet scrollen, dus leek het net alsof er iets geblokkeerd werd. Een échte Playwright-browser die gewoon `mouse.wheel()` doet, laadt keurig alle 69 events (was: ~20 via alleen de server-rendered eerste pagina). Elfde Playwright-scraper (na wat regex-gepuzzel: Engelse datumtekst met soms dubbele spatie bij eencijferige dagen, en een optionele `pretitle`-h4 zoals "SOLD OUT" vóór de datum).
  - **Belangrijke les**: "de blokkade zit bij Cloudflare" was een aanname op basis van het SYMPTOOM (lege AJAX-respons), niet bevestigd bewijs (geen "Just a moment"-uitdaging zoals bij TivoliVredenburg). Onderscheid dat voortaan expliciet checken: een échte Cloudflare-challenge-pagina (zoals bij Tivoli) is een harde grens; een simpelweg lege/falende AJAX-respons op een curl-only-poging kan net zo goed betekenen dat de interactie zelf (scroll/klik) niet goed nagebootst is — dat is wél oplosbaar met een echte browser, zonder iets te "omzeilen".
  - **34 near-duplicate wees-rijen opgeruimd** (oude titels zonder spatie tussen naam en landcode, bv. "Wednesdayusa" i.p.v. "Wednesday" + losse "USA"-badge — duidt op een eerdere, minder zorgvuldige scrape-poging), `page_hash` meegewist.
- **Rotown opgelost — geen Playwright nodig, laatste van de oorspronkelijke 15 landelijke podia.** `/agenda/` (zonder slug) gaf een 404, waardoor het leek alsof er geen listing-pagina bestond — maar de HOMEPAGE zelf bevat gewoon 139 losse JSON-LD `Event`-blokken (schema.org), plain HTTP-request. Rotown promoot ook events bij andere Rotterdamse venues (V11, De Doelen, Maassilo, Annabel, ...) — gefilterd op `location.name == 'Rotown'`, zelfde aanpak als `scrape_hedon.py`. 97 events. **Alle 15 oorspronkelijke landelijke podia zijn hiermee opgelost.**
- **De Doelen opgelost — achtste Playwright-scraper.** Zelfde verkeerde-URL-fout als Effenaar/Winsinghhof: `/programma` geeft een 404, echte agenda-URL is `/nl/agenda`. `eventCard`-grid met titel, subtitel, datum (mét 2-cijferig jaartal, geen inferentie nodig), tijd en zaal. 49 events. Grootste near-duplicate-opruiming tot nu toe: 151 oude wees-rijen (titel zonder subtitel, wel een echte URL dit keer — alleen de titel-vorm verschilde) opgeruimd, `page_hash` meegewist.

## 2026-08-15 afsluiting — resterende AI/Chrome-bronnen geparkeerd als "moeilijk"
Na het oplossen van 25 van de 31 "AI/Chrome nodig"-bronnen (via verkeerde-URL-fixes,
Playwright en de Ticketmaster Discovery API) resteerden 7 bronnen zonder duidelijk
vervolgpad: EM2 Groningen (datum-extractie te onbetrouwbaar), Groninger Museum en
Drents Museum (Craft CMS, geen API gevonden, blijft leeg zelfs met Playwright),
Zummerbühne (iframe bleek een ride-share-widget, geen ticketing), OntdekPoort en
Hunebedcentrum (échte bot-bescherming, 403 — principiële grens, nooit omzeild), en
GIJS Groningen (site toont nog het oude seizoen). Michiel: "parkeren we deze even
als 'moeilijk', pakken we stuk voor stuk op als we zin hebben" — bewust geen actieve
vervolgstap gepland. Zie SCRAPERS.md voor de per-bron notities.

## 2026-08-15 — productbrainstorm: 3 nieuwe topniveau-knoppen (nog niet gebouwd)
Michiel wil naast Uitjes/Sport drie nieuwe knoppen: **Exposities**, **Favorieten**,
**Admin**. Richting per stuk bepaald, bewust nog niet geïmplementeerd (eerst verder
brainstormen) — zie overleg.md punten 9-11 en plan.md voor de volledige uitwerking.
Kernbeslissingen:
- **Exposities**: `genre='expo'` uit de Uitjes-stroom halen. "Verdwijn-probleem"
  opgelost met **route A**: een expositie blijft zichtbaar totdat een bekende
  `date_end` al voorbij is (dat veld bestaat al in het datamodel maar wordt door
  `gen_uitjes.py` nog nergens gebruikt — vrijwel geen scraper vult het vandaag al
  in). Default sortering op startdatum, met alfabetisch/einddatum als alternatief.
  Afstandsfilter blijft gewoon gelden, geen uitzondering.
- **Favorieten**: een act/team/gezelschap volgen over alle bronnen heen (bevestigt
  het eerder al genoteerde idee, zie overleg.md punt 9) — matching- en UI/opslag-
  ontwerp nog open.
- **Admin**: bewust **alleen lokaal/read-only** (scraper-status, event-aantallen,
  laatste refresh) — expliciet GEEN backend en GEEN bewerkmogelijkheid via de site,
  om het "volledig statisch, geen backend"-architectuurprincipe niet te doorbreken.

## 2026-08-16 — Exposities gebouwd (derde topniveau-modus)
Implementatie van de op 2026-08-15 vastgelegde richting (overleg.md punt 10).
Genre `expo` wordt nu volledig uit `events_valid`/de maand-secties gehaald in
`gen_uitjes.py` en apart bijgehouden (`expo_valid`/`expo_html`, platte lijst,
geen maand-groepering — dat past niet bij "sorteren op alfabet/einddatum").
Zichtbaarheidsregel (route A) geïmplementeerd via `event_is_valid(e)`: voor
expo-events geldt "zichtbaar tenzij een bekende `date_end` al voorbij is",
i.p.v. de normale `TODAY<=date<=2027-12-31`-regel. Dit is de eerste keer dat
`date_end` (stond al in het DB-schema/export sinds eerdere sessies, maar werd
door `gen_uitjes.py` nergens gelezen) daadwerkelijk gebruikt wordt.

Sortering: default startdatum (server-side volgorde), Einddatum/Alfabetisch
als knoppen die client-side de DOM herordenen (`Array.sort()` +
`appendChild()`) — geen 3 losse server-gerenderde varianten nodig. Provincie-
en afstandsfilter werken automatisch mee via het al bestaande gedeelde
filterblok/`apply()`-mechanisme, geen aparte code nodig. Bewust geen eigen
Bron-filter gebouwd bij de huidige kleine omvang (4 events).

**Twee bugs gevonden tijdens de bouw, in dezelfde sessie gefixt:**
1. **`classify()`-substring-bug**: het keyword `'strip'` in de expo-
   titelkeyword-lijst matchte ook `"Striptease"` als substring — 3
   theater/cabaretshows ("Striptease Van De Dood" bij atlastheater,
   spotgroningen.nl, friesland.nl) werden onterecht als `expo` geclassificeerd.
   Dit bestond al langer maar viel pas op zodra Exposities een eigen,
   zichtbare, kleine sectie kreeg — voorheen ging zo'n fout genre-label
   onopgemerkt schuil tussen duizenden Uitjes-events. Gefixt: vervangen door
   specifiekere `'stripverhaal'`/`'stripmuseum'`/`'stripkunst'`. Voor de fix:
   7 events geclassificeerd als expo; na de fix: 4 (de 3 misclassificaties
   weg, geen echte expo's verloren).
2. **Init-apply-bug (niet gerelateerd aan Exposities, maar in hetzelfde
   codepad ontdekt)**: `apply()` (de client-side filterfunctie) werd nergens
   aangeroepen bij het laden van de pagina zelf, alleen vanuit knop-click-
   handlers. Bevestigd op de live site vóórdat dit gefixt werd: 172
   sportwedstrijden stonden zichtbaar tussen de Uitjes-events bij een verse
   paginalaad, tot een gebruiker voor het eerst een filter aanklikte. Gefixt
   door `setMode('uitjes')` (roept zelf `apply()` aan) toe te voegen aan het
   JS-init-blok — ontdekt omdat dezelfde init-code sowieso aangepast moest
   worden voor de nieuwe derde modus.

Lokaal geverifieerd met een tijdelijke `python -m http.server` + de
Chrome-preview-tools (`.claude/launch.json` toegevoegd voor herbruikbaarheid
in latere sessies) vóór het pushen: mode-toggle, filter-branches (uitjes/
sport/exposities), sorteerknoppen, provincie/afstandsfilter, en mobiele
grid-layout van de expo-kaart (`.event.expo-item` met hogere CSS-specificiteit
dan de mobile-media-query-regel, anders zou de 2-koloms-layout breken onder
600px) allemaal getest en werkend bevonden vóór commit.

Zie ARCHITECTURE.md §Exposities voor de volledige technische uitwerking.

## 2026-08-16 — Parallelle requests: aanpak vastgelegd (nog niet gebouwd)
Overleg.md punt 2 verder uitgewerkt op Michiels verzoek — bewust alleen het
ontwerp vastgelegd deze sessie, bouwen volgt later ("eerst alleen vastleggen").

**Twee onafhankelijke niveaus, beide in scope (Michiel koos A+B nadat bleek
dat B niet alle 56 bestanden raakt):**
- **Niveau A** (tussen scrapers): `run_weekly_refresh.py`'s hoofdlus van
  sequentieel naar een `ThreadPoolExecutor` rond de bestaande
  subprocess-call. Aparte concurrency-limiet per scraper-type (Michiels
  expliciete keuze i.p.v. één globale limiet) — plain-HTTP vs Playwright
  (11 losse Chromium-processen, geheugen-zwaar). Type wordt herkend door het
  bestand te grep'en op `"playwright"`, geen aparte config per script.
  Voorstel-startwaarden: 8 gelijktijdig voor plain-HTTP, 3 voor Playwright —
  niet hard vastgezet, bijstellen na een eerste echte run.
- **Niveau B** (binnen één scraper): alleen de 7 scrapers met een echte
  multi-request paginaloop (geteld door alle 56 bestanden te grep'en op
  paginering-patronen en de treffers handmatig te controleren op false
  positives, bv. Playwright's `browser.new_page()` matcht toevallig ook op
  "page" maar is geen paginering): `scrape_drenthe.py`, `scrape_friesland.py`,
  `scrape_visitgroningen.py`, `scrape_forum.py`, `scrape_kielzog.py`,
  `scrape_posthuistheater.py`, `scrape_paard.py`. Bewust NIET
  `scrape_concertgebouw.py`/`scrape_gelredome.py` — die hebben ook paginering
  maar via Playwright met al één hergebruikte browser (zie ARCHITECTURE.md
  §Playwright-scrapers); parallelliseren daarvan is losse browser-tabs/
  contexts, een ander soort wijziging met minder duidelijke winst-per-risico
  — bewust uit scope gehouden voor deze ronde.

**Bouwplan Niveau B**: nieuwe gedeelde helper `parallel_fetch.py` (zelfde
soort klein infra-bestand als `ssl_fix.py`/`page_cache.py`/`ticketmaster.py`
— bevat geen scraping/parse-logica, dus geen conflict met de "één bestand per
bron"-afspraak uit overleg.md punt 8) met een `fetch_pages()`-achtige functie
op `ThreadPoolExecutor` + het bestaande `urllib` (geen nieuwe dependency
nodig, alle 7 kandidaten gebruiken al `urllib`, niet `requests`).
Concurrency-per-scraper bewust laag gehouden (voorstel: 5 gelijktijdige
requests naar dezelfde bron) — deze sites krijgen nu één sequentiële request
tegelijk en zijn daar prima mee; te veel gelijktijdige connecties naar
dezelfde domain kan alsnog rate-limiting/bot-detectie triggeren die er nu
niet is. Change-detection (`unchanged()`) hoeft niet aangepast: die zit al
ná het verzamelen van alle pagina's, ongeacht of dat sequentieel of parallel
gebeurde.

**Randvoorwaarde, ontdekt tijdens het uitwerken**: alle scrapers schrijven
naar dezelfde SQLite-file via `insert_event()` (`events_db.py:83`) — geen
WAL-mode, geen busy-timeout op de connectie. Bij echt gelijktijdige processen
(Niveau A) kan dat een "database is locked"-fout geven zodra twee scrapers
tegelijk proberen te schrijven. Moet vóór of gelijk met Niveau A gebouwd
worden: `PRAGMA journal_mode=WAL` + een `busy_timeout` bij het openen van de
connectie — klein, bekend/standaard SQLite-patroon voor dit scenario.

## 2026-08-16 — Parallelle requests gebouwd (Niveau A+B), inclusief een echte bug gevonden en gefixt
Michiel: "nee, dit gaan we bouwen nu" — meteen na het vastleggen van de aanpak
(zie vorige sectie) alsnog gebouwd in dezelfde sessie.

**Gebouwd, in volgorde:**
1. `events_db.py`'s `get_conn()`: `PRAGMA journal_mode=WAL` + `busy_timeout=30000`
   toegevoegd (randvoorwaarde voor Niveau A). Geverifieerd: `PRAGMA journal_mode`
   geeft `wal` terug, `PRAGMA busy_timeout` geeft `30000`.
2. `run_weekly_refresh.py`: hoofdlus van sequentieel naar twee `ThreadPoolExecutor`-
   pools (plain-HTTP + Playwright, apart aangestuurd, tegelijk draaiend) rond de
   bestaande `run_one()`-subprocess-call. `--max-plain`/`--max-playwright` CLI-
   flags toegevoegd (default 8/3, op 1 = oude sequentiële gedrag). Scraper-type
   herkend via `is_playwright_scraper()` (grep op `"playwright"` in het bestand
   zelf, geen aparte config). Geverifieerd met 11 Playwright-scrapers correct
   herkend, 45 plain-HTTP.
3. `parallel_fetch.py` (nieuw): `fetch_many(items, fetch_fn, max_workers=5)` voor
   bronnen met een bekend aantal pagina's vooraf, `fetch_batches(start, fetch_fn,
   should_stop_fn, batch_size=5, max_batches, stop_after_consecutive=1)` voor
   bronnen die het aantal pagina's pas ontdekken terwijl ze gaan. Beide op
   `concurrent.futures.ThreadPoolExecutor` + de bestaande `urllib`-fetch-functies
   van elke scraper (geen nieuwe dependency). Zelf-test met fake fetch-functies
   gedraaid vóór toepassing op echte scrapers (orde-behoud, foutisolatie, stop-
   logica) — allemaal geslaagd.
4. Toegepast op de 7 kandidaten: `scrape_friesland.py`/`scrape_kielzog.py`
   (bekend-aantal-vooraf, simpele `fetch_many()`-vervanging van de for-loop),
   `scrape_forum.py`/`scrape_posthuistheater.py` (vast klein maximum, hele
   lijst in één keer `fetch_many()`, verwerking blijft sequentieel om exact
   dezelfde stop-bij-eerste-fout/lege-pagina-semantiek te behouden),
   `scrape_paard.py`/`scrape_drenthe.py`/`scrape_visitgroningen.py`
   (`fetch_batches()`, aantal pagina's onbekend vooraf).

**Bug gevonden tijdens het bouwen — belangrijke les**: het eerste ontwerp van
`fetch_batches()` had een `is_empty_fn(resultaat)`-parameter ("stop als N
pagina's op rij 0 events opleveren"). Bij een eerste live test met
`scrape_drenthe.py --dry-run` duurde het genereren 3m34s — nauwelijks sneller
dan de oude sequentiële ~3+ min, terwijl geïsoleerde tests (5 pagina's
gelijktijdig) een duidelijke speedup lieten zien (0.32s wall-time voor 5
pagina's die apart ~0.25s elk kostten). Diagnose: `fetch_batches()` had 105
pagina's opgehaald (tot de veiligheidsgrens) i.p.v. de echte ~41 — drenthe.nl
blijkt voorbij het echte einde gewoon een fallback-pagina terug te geven
(bevestigd: pagina 42/50/60 gaven allemaal 8 events terug, nooit 0), dus het
"0 events"-stopsignaal kwam letterlijk nooit voor. Het WEL betrouwbare signaal
bleek het al langer in de sequentiële code aanwezige `f'page={page+1}' not in
html`-check (ontbrekende "volgende pagina"-link) — die ging bij pagina 41 wél
meteen op `False`. Fix: `fetch_batches()`'s callback hernoemd/herontworpen naar
`should_stop_fn(page, resultaat)` (kreeg zo ook het paginanummer, nodig voor de
next-link-check) met `stop_after_consecutive=1` als default (meteen stoppen,
i.p.v. moeten wachten op 2x op rij). `scrape_drenthe.py` en
`scrape_visitgroningen.py` aangepast om deze functie te gebruiken i.p.v. de
"0 events"-check. Resultaat: drenthe.nl 3m34s → 13.1s (16x), identiek
eventaantal (1221) — de bug kostte alleen tijd, geen foute data.

**Tweede vondst bij dezelfde fix**: `scrape_visitgroningen.py` had een
voorlopige veiligheidsgrens van 60 pagina's (gebaseerd op de aanname "zelfde
soort omvang als drenthe.nl") — bleek te laag: een losse check vond nog
groeiende, echte data tot pagina 70, met het echte einde ergens tussen 70 en
80 (pagina 80 gaf zowel 0 events als geen next-link, een normaal/betrouwbaar
eindsignaal — visitgroningen.nl heeft dus, anders dan drenthe.nl, geen
fallback-content-kwirk). Grens opgehoogd naar 120 met ruime marge. Bij de
eerste live-test met de te-lage grens werden hierdoor maar 489 van de
uiteindelijke 1030 events gevonden — geen crash, gewoon stil te weinig data,
dus dit had onopgemerkt kunnen blijven zonder de vergelijking met de
"pagina 70 had nog has_next_link=True"-probe.

**Eindverificatie — een echte volle `run_weekly_refresh.py`-run** (niet
`--dry-run`, dus met echte gelijktijdige schrijfacties naar `events.db`):
56/56 scrapers OK, 0 self-healing-hernoemingen, 0 "database is locked"-
fouten, 0 "0 resultaten"-waarschuwingen. events_db.py export: 7775 rijen
(was rond de 6669 vóór deze sessie) → `gen_uitjes.py`: 7734 events na
filtering. Toename komt vooral van visitgroningen.nl (+416) en friesland.nl
(+346) die door de Niveau-B-fixes nu voor het eerst hun volledige dataset
betrouwbaar ophalen.

**Bijvangst, niet opgelost deze sessie**: door de volledigere visitgroningen/
friesland-data sprong het aantal Exposities van 4 naar 41 — bleek forum.nl's
"Marilyn Expositie"/"Storyworld" te zijn, die als losse rij per dag i.p.v.
één rij met datumbereik in de data staan. Bestond al sinds forum.nl gescraped
wordt (sessie 2026-08-13), was alleen onzichtbaar tussen de vele Uitjes-
events. Zie overleg.md punt 12 — bewust niet gefixt in deze sessie (ander
onderwerp), drie oplossingsrichtingen genoteerd voor een volgende keer.

## 2026-08-17 — forum.nl doorlopende exposities opgelost (overleg.md punt 12)
Optie A gekozen en gebouwd: `scrape_forum.py` heeft een nieuwe
`merge_consecutive_days(dates)`-functie die per slug een gesorteerde lijst
ISO-datums groepeert in runs van opeenvolgende kalenderdagen (`(start, eind)`
per run). De scrape-loop verzamelt nu eerst alle (slug → verzameling datums)
in een dict i.p.v. meteen losse events te bouwen; pas na het ophalen van alle
pagina's worden de runs bepaald en per run één event aangemaakt (`date_end`
alleen gezet bij een run langer dan 1 dag).

**Waarom dit veilig is voor het genoemde risico** ("een exhibitie die
tussentijds een dag dicht is wordt fout samengevoegd"): het algoritme merged
alleen ECHT opeenvolgende dagen. Een gat in de reeks (ontbrekende dag) breekt
de run vanzelf in tweeën. Dit bleek meteen relevant in de praktijk: Marilyn
Expositie en Storyworld hebben een echt gat op 31 augustus (bevestigd door
de data 2x met een paar minuten ertussen te fetchen — beide keren consistent
afwezig, dus geen toevallige netwerk-hik) — worden nu correct als 2 losse
runs opgeslagen (17-30 aug, 1-4 sep) i.p.v. één (foutieve) doorlopende range
17 aug - 4 sep.

**Generieke bijvangst**: de merge-logica raakt ALLE forum.nl-slugs met
opeenvolgende dagen, niet alleen de 2 expo's die het probleem zichtbaar
maakten — bv. "Taalhuis" (4 opeenvolgende dagen) werd ook 1 rij i.p.v. 4,
en "Noorderzon The Museum Of Small And Overlooked Things" (15 opeenvolgende
dagen, geen gat) werd 1 rij. Wekelijks-terugkerende programma's als
"Informatieplein-Lewenborg" (elke dinsdag, dus NIET opeenvolgend) blijven
terecht losse dag-rijen — het algoritme onderscheidt dit vanzelf zonder een
aparte "is dit een doorlopend evenement"-classificatie nodig te hebben.

**Stale-data-opruiming nodig, zelfde patroon als eerdere sessies**:
`insert_event()`'s conflict-resolutie update alleen bij een aggregator-vs-
directe-bron-botsing (zie events_db.py's docstring) — bij eenzelfde bron die
opnieuw scraped wordt met GEWIJZIGDE data voor een bestaande (title_norm,
date)-sleutel (hier: `date_end` erbij) wordt de bestaande rij bewust NIET
overschreven, dus een simpele her-scrape liet de oude `date_end=NULL`-rijen
onaangeroerd staan. Opgelost door eerst alle forum.nl-rijen met `date >=
TODAY` te verwijderen (95 rijen, allemaal daily-duplicates die door de merge
overbodig worden) plus de `page_hash`-rij voor `forum.nl` te wissen (bekende
valkuil, zie ARCHITECTURE.md §Change-detection), en dan opnieuw live te
scrapen: 41/41 nieuw in DB, correct met `date_end` gevuld.

**Resultaat, geverifieerd lokaal vóór commit**: Exposities 41 → 9 (2x Marilyn
Expositie + 2x Storyworld door het echte gat, 2x Groninger Museum, Geke
Hoogstins, Concertgebouw, plus een Friesland-galerie-expositie die met de
volledigere friesland.nl-data van de parallelle-requests-sessie meekwam).
Forum.nl totaal in DB: 196 → 142 rijen (oude, al-verstreken juni-rijen bewust
niet opgeruimd — onzichtbaar op de site door de datumfilter, geen impact).
