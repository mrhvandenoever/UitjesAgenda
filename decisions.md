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

## 2026-08-17 — Geke Hoogstins gebouwd + een echte bug in events_db.py export_json() gevonden
Was eerder bewust niet gebouwd (zie SCRAPERS.md/eerdere sessie): "maandenlange
doorlopende exposities, geen losse datums, past niet in ons single-date-
event-model". Sinds de Exposities-modus (2026-08-16, `date_end` wordt nu
echt gebruikt) is die reden vervallen — Michiel vroeg hem alsnog te bouwen.

**Site-analyse**: de exposities-pagina zelf is vrije tekst (proza), maar de
"EXPOSITIES `<jaar>`"-sectie bovenaan bleek verrassend gestructureerde HTML:
een `<h2>`-heading met het jaartal, gevolgd door exact `<p><strong>datum-
bereik</strong> titel</p>` per expositie — regex-baar zonder AI/Chrome nodig.
De rest van de pagina (uitgebreidere vrije-tekst-beschrijving per expositie)
wordt bewust genegeerd.

**Drie datumbereik-formaten gevonden en afgehandeld** in een nieuwe
`parse_range()`-functie: "22 mei t/m eind oktober" (geen einddag, "eind
<maand>" → laatste dag van die maand via `calendar.monthrange()`), "3 juli
t/m 5 september" (beide kanten dag+maand, jaartal impliciet uit de
heading), en "13 november t/m 9 januari 2027" (expliciet jaartal aan de
eindkant bij een jaarwisseling — wint altijd als aanwezig). Alle 3 correct
getest.

**Bijvangst: de bestaande (handmatig ooit ingevoerde) DB-rij voor "DSG
groepsexpositie" bleek een verkeerde `date_end` te hebben** — `2027-11-13`
(exact 1 jaar na de startdatum, een gok/placeholder) terwijl de site zelf
"13 november t/m 9 januari 2027" zegt. De nieuwe scraper geeft het juiste
`2027-01-09`. Bevestigt de eerdere aanname in ARCHITECTURE.md ("die ziet
eruit als een placeholder"). Er bleken zelfs 2 oude handmatige rijen te
staan (niet 1 zoals eerder aangenomen) — beide met een foutieve `date_end`,
beide opgeruimd vóór de nieuwe live-scrape (zelfde `insert_event()`-
conflict-resolutie-beperking als bij de forum.nl-fix vandaag: een same-
source-herscrape update een bestaande rij niet automatisch).

**Belangrijke, aparte bug gevonden tijdens het verifiëren**: 2 van de 3
nieuwe events (de exposities die al vóór vandaag zijn begonnen maar nog
lopen) verschenen niet op de site, ook al stonden ze correct in de DB.
Oorzaak: `events_db.py`'s `export_json()` filtert met `WHERE date >= ?
AND date <= '2027-12-31'` — een harde ondergrens op de STARTdatum, zonder
enige kennis van `date_end`. Events die vóór vandaag begonnen maar nog
lopen vielen dus al weg vóórdat `gen_uitjes.py`'s eigen (correcte) expo-
aware `event_is_valid()`-logica er ooit aan toekwam. Dit gat bestond al
sinds de Exposities-bouw (2026-08-16) maar was onzichtbaar omdat op dat
moment vrijwel geen enkel event een zinvolle `date_end` had — pas nu, met
de eerste "al begonnen, nog lopende" expositie, werd het zichtbaar. Fix:
`WHERE (date >= ? OR (date_end IS NOT NULL AND date_end >= ?)) AND date <=
'2027-12-31'` — een event blijft nu ook mee als de STARTdatum al voorbij is
zolang de EINDdatum dat nog niet is. Geen genre-check nodig op dit niveau
(puur een datumbereik-vraag), dus dekt dit automatisch ook toekomstige
bronnen met hetzelfde patroon, niet alleen Geke Hoogstins.

**Resultaat, geverifieerd lokaal vóór commit**: alle 3 Geke Hoogstins-events
zichtbaar in Exposities (was 1, met foutieve datum). Exposities-totaal 9 →
11. `gekehoogstins.nl` toegevoegd aan `EXPO_VENUES` in `gen_uitjes.py` als
defensieve fallback (momenteel niet strikt nodig — alle 3 titels bevatten
toevallig al "expositie" als keyword — maar logisch voor een bron die
uitsluitend exposities toont).

## 2026-08-17 — Kunstpunt Groningen gebouwd (nieuwe aggregator voor Exposities), 2 bugs gevonden en gefixt
Vervolg op punt 13 (overleg.md): Michiel vroeg Kunstpunt Groningen te
verkennen en daarna te bouwen, met 2 expliciete eisen: "venue gaat boven de
aggregator, zoals bij de uitjes" en "check of de link ook naar de goede
site gaat (dus de specifieke van die expositie)".

**Technische verkenning**: server-rendered WordPress (geen Playwright
nodig), consistente HTML per expositie (`<article class="m-post...">` met
categorie/titel/venue/datumbereik). Slechts 2 pagina's, 26-38 items
(schommelt). Categorie-filter nodig: de kalender bevat ook workshops/
lezingen/concerten/wandelroutes (40+ categorieën) — alleen "Exhibition"
meegenomen.

**Link-check (2e eis)**: gecontroleerd op de detailpagina van een
voorbeeld-expositie (K38) of er een link naar de venue's EIGEN site stond
naast Kunstpunt's eigen artikel — die bleek er te zijn maar wees alleen
naar de algemene homepage van de galerie (`kunstencentrumk38.nl`), niet
naar een expositie-specifieke pagina. De meeste kleine galerieën hebben
kennelijk geen eigen per-expositie-pagina's. Conclusie: Kunstpunt's eigen
`/en/agenda/<slug>/`-URL (die de listing-pagina al aanlevert) is de
specifiekste beschikbare link, en is wat de scraper gebruikt.

**Bonusvondst tijdens de verkenning**: elke detailpagina bevat ook de
exacte lat/lon van de venue, ingebed als kaart-marker-data
(`&quot;lat&quot;:53.14,&quot;lng&quot;:6.43` — let op de HTML-entity-
encoded quotes, een eerste regex-poging met literale `"` miste dit
volledig). Preciezer dan de bestaande `city_coords.json`-lookup (die 3 van
de 26 voorkomende plaatsen sowieso niet kent: Zuidhorn, Sappemeer,
Slochteren). **Bleek dat `gen_uitjes.py` per-event `lat`/`lon` nooit las** —
`events_db.py` sloeg het al op en exporteerde het, maar `event_html()`/
`expo_card_html()` keken alleen naar `CITY_COORDS`/`VENUE_LOC`, nooit naar
het event zelf. Beide functies uitgebreid met een nieuwe hoogste-prioriteit-
tier: event-eigen `lat`/`lon` > `CITY_COORDS` (plaatsnaam) > `VENUE_LOC`
(bron-niveau fallback). Bewust GEEN entry voor `kunstpuntgroningen` in
`VENUE_LOC` toegevoegd — dat zou de per-event `province`-override
(`prov = loc[2] if loc else e.get('province', 'Onbekend')`) juist
onbruikbaar maken voor een aggregator die over meerdere provincies gaat.

**Bug 1, gevonden bij het testen**: van de 26 gescrapete exposities kregen
er maar 2 `genre='expo'` — de rest (Engelse titels als "Coach house",
"SACRED EARTH", "Bakstain") viel terug op `overig`. Oorzaak:
`classify()`'s `cats=='expositie'`-tak vereiste ALTIJD ook nog een
Nederlandse titel-keyword-match (`'expositie','tentoonstelling','galerie',
'expo','schilderij','architect','design','kunst',...`) — het `cats`-signaal
was dus nooit werkelijk gezaghebbend, in tegenspraak met het expliciete
ontwerpprincipe in ARCHITECTURE.md ("bronnen die zelf een genre-signaal
geven zijn betrouwbaarder dan titel-keywords"). Gecheckt: vóór
`scrape_kunstpuntgroningen.py` zette GEEN ENKELE scraper `cats=['expositie']`
— dit pad was dus dood/ongetest sinds het bestond. Gefixt: `c == 'expositie'`
retourneert nu direct `'expo'`, geen extra keyword-eis meer. Zonder
bestaande-bron-risico (niemand gebruikte het pad eerder).

**Bug 2, gevonden bij het handmatig doorlopen van de resultaten**: Kunstpunt's
"The experience of Drenthe" (Galerie DSG, 3 juli–5 sep 2026) bleek exact
dezelfde expositie als `scrape_gekehoogstins.py`'s "groepsexpositie DSG 'De
beleving van Drenthe'" (zelfde datums) — Geke Hoogstins is DSG-lid, haar
site volgt DSG's groepstentoonstellingen al. De bestaande cross-source-dedup
(`AGGREGATOR_SOURCES` + fuzzy titel-matching in `events_db.py`) miste dit
volledig omdat de titels in verschillende talen staan (Engels vs
Nederlands) — geen woord gemeenschappelijk. Michiels expliciete eis "venue
gaat boven de aggregator" werkte dus in de PRAKTIJK niet voor dit geval,
ondanks dat het mechanisme correct was ingesteld. Geen generieke cross-taal-
matcher gebouwd (te veel voor dit ene geval) — pragmatische fix: Kunstpunt's
"Galerie DSG"-venue expliciet overgeslagen in `scrape_kunstpuntgroningen.py`
(`SKIP_VENUES`), met de aanname dat Geke Hoogstins' site DSG-groepsshows al
dekt. Stale rij (de eerste, nog-gedupliceerde live-run) opgeruimd vóór de
herscrape, zelfde patroon als bij forum.nl/Geke Hoogstins eerder vandaag.

**Resultaat, geverifieerd lokaal vóór commit**: 22 kunstpuntgroningen-events
in de export (25 gescraped, 3 al verstreken per vandaag — `date_end`
2026-08-16 < TODAY 2026-08-17, correct gefilterd door de `export_json()`-fix
van eerder vandaag). Exposities-totaal 11 → 34. Elk Kunstpunt-event heeft nu
een precieze, per-venue `data-latlon` (geverifieerd: K38 en Kunstpunt zelf
tonen verschillende coördinaten) en correcte provincie (Roden→Drenthe,
de rest→Groningen).

## 2026-08-17 — Uitzinnig.nl gebouwd (derde expositie-aggregator, Drenthe/Groningen/Friesland-breed)
Michiel wilde verder uitbreiden na Kunstpunt. Kunstinzicht.nl (onderzocht op
Michiels vraag om Appingedam/Hoogezand/Assen/Veendam/Grootegast/Leeuwarden/
Emmen) bleek zwak (dun per plaats, geen startdatum) en is bewust niet
gebouwd — zie overleg.md punt 13. Vervolgens gevonden: **uitzinnig.nl**,
via dezelfde soort zoekopdrachten die kunstinzicht.nl opleverden, maar van
duidelijk hogere kwaliteit.

**Technische verkenning**: `uitzinnig.nl/<provincie>/tentoonstellingsagenda.aspx`
(provincie = drenthe/groningen/friesland) is server-rendered. Bleek bij
nader onderzoek GEEN strikt gefilterde provincie-feed te zijn — dezelfde
expositie (bv. "Mimesis" in Roden/Drenthe) dook op alle 3 provinciepagina's
op. Opgelost door alle 3 op te halen en te dedupliceren op URL (wél uniek
per expositie) i.p.v. als 3 losstaande feeds te behandelen.

**Datumkwaliteit, beter dan kunstinzicht.nl**: de listing-pagina zelf toont
alleen "Vandaag t/m X" (zelfde beperking als kunstinzicht.nl leek te hebben),
maar de DETAILPAGINA bleek een schone ISO-meta-tag te hebben:
`<meta name="startdatum" content="2026-08-01" /><meta name="einddatum"
content="2026-08-23" />` — een echte startdatum, in tegenstelling tot
kunstinzicht.nl. Ook een losse, herkenbare venue-naam per expositie
gevonden op de detailpagina (`.subinfo`-regel: "1 t/m 23 augustus 2026 |
Kunstencentrum K38 | Roden (Noordenveld)") — de listing zelf toont alleen
de plaatsnaam, geen venue.

**Bonus**: "Hunebedcentrum - Beleef 150000 jaar geschiedenis" (Borger) komt
via deze route binnen — de eerste keer dat er data van Hunebedcentrum (één
van de 7 permanent-geparkeerde bronnen, 403 bot-bescherming) in de site
terechtkomt, zonder de bot-bescherming te hoeven omzeilen. Beperkt (1
doorlopend "museum-item", niet hun volledige agenda), maar een concreet
positief neveneffect.

**Aggregator-vs-aggregator-dedup-gat bevestigd, 2e keer** (zie ook de DSG-
episode eerder vandaag bij Kunstpunt): 2 van de 15 gevonden exposities
("Mimesis"/Kunstencentrum K38/Roden, "Overzichtsexpositie Aldrik Salverda en
Lucas Klein"/Kunstruimte De Smederij/Sappemeer) bleken exacte duplicaten van
wat `scrape_kunstpuntgroningen.py` al geeft (zelfde venue, zelfde/bijna-
identieke datums). De generieke fuzzy-titel-dedup in `events_db.py` mist dit
STRUCTUREEL zodra BEIDE botsende bronnen een aggregator zijn
(`find_cross_source_duplicates()`: `if agg_a == agg_b: continue` — skipt het
paar helemaal, ongeacht hoe goed de titels matchen). Dit is dus geen
incidenteel randgeval meer maar een voorspelbaar patroon zodra een 2e/3e
aggregator dezelfde onderliggende bron aggregeert. Zelfde pragmatische fix
als bij DSG: gerichte `SKIP_TITLES = {'Mimesis', 'Overzichtsexpositie
Aldrik Salverda en Lucas Klein'}` in `scrape_uitzinnig.py` i.p.v. een
generieke oplossing. **Genoteerd als iets om ooit structureel op te lossen**
als er een 3e aggregator bijkomt (bv. `find_cross_source_duplicates()` ook
laten draaien tussen twee aggregatoren onderling, niet alleen aggregator-
vs-directe-bron) — voor nu blijft de gerichte-SKIP-aanpak goedkoop genoeg.

**Resultaat, geverifieerd lokaal vóór commit**: 13 nieuwe exposities
(Dwingeloo x2, Emmer-Compascuum, Zweeloo, Emmen, Borger, Delfzijl,
Onstwedde, Sappemeer, Kantens, Leeuwarden x3), verspreid over alle 3
provincies. `uitzinnig` toegevoegd aan `AGGREGATOR_SOURCES` en aan `SRC` in
`gen_uitjes.py` (eerst vergeten, badge toonde de rauwe bronsleutel i.p.v.
"Uitzinnig" — gecorrigeerd vóór commit). Exposities-totaal 34 → 47.

## 2026-08-17 — Kapotte links gemeld door Michiel: 3 gefixt + een belangrijke herontdekking (TivoliVredenburg)
Michiel meldde 2 kapotte links (Groninger Museum's "The Architect & The
Housewife", en TivoliVredenburg's "Filth"/"Alcest" die geen link toonden).

**Groninger Museum**: de opgeslagen URL voor "The Architect & The Housewife"
bleek verkeerd (handmatig ooit fout ingevoerd — Groninger Museum heeft geen
actieve scraper, staat geparkeerd als "moeilijk"). Michiel gaf de juiste URL
door (`/en/art/exhibitions/the-architect-the-housewife-...`), geverifieerd
en direct in de DB gecorrigeerd (`UPDATE events SET url=...`).

**TivoliVredenburg — een echte, structurele bug gevonden**: "Filth" en
"Alcest" hadden `url=NULL`, en bij nader onderzoek bleken ALLE 480
tivolivredenburg-rijen geen URL te hebben. Oorzaak: `scrape_tivolivredenburg.py`
(via Songkick) haalt wél echte per-event-URL's op — geverifieerd door
Songkick rechtstreeks te bevragen: "Alcest" had daar gewoon een echte URL.
Maar `insert_event()`'s conflict-resolutie update een bestaande rij nooit
bij een same-source-herscrape (alleen bij een aggregator-vs-directe-bron-
botsing, zie events_db.py's docstring) — exact hetzelfde patroon als de
forum.nl- en Geke Hoogstins-bugs eerder vandaag. Omdat deze ~9 Songkick-
shows al vanaf het begin in de (oudere, brede) 480-rijen-legacy-dataset
stonden zonder URL, werd de Songkick-scraper's eigen URL-data dus STRUCTUREEL
genegeerd bij elke run sinds die scraper bestaat — niet incidenteel voor
deze 2 events, maar voor alle ~9 Songkick-gedekte shows tegelijk.

Fix, zorgvuldig gescoped (**niet** de hele 480-rijen-dataset aanraken — die
bevat bewust bewaarde, bredere legacy-data die niet via Songkick gedekt
wordt, zie de eerdere sessie-beslissing): alleen de specifieke rijen
verwijderd die zowel (a) matchen met een titel+datum die Songkick NU
aanlevert als (b) zelf nog geen URL hadden. 8 van de 9 matchten en zijn
verwijderd; `page_hash` voor tivolivredenburg gewist; scraper opnieuw live
gedraaid — alle 8 kregen hun echte Songkick-URL terug.

"Filth" zelf staat niet (meer) op Songkick's ~9-shows-venster, dus kreeg
geen URL via de herscrape. Michiel vond zelf de directe TivoliVredenburg-URL
(`tivolivredenburg.nl/agenda/22763649/filth-17-08-2026`) en ook een directe
URL voor Alcest — beide handmatig in de DB gezet (directe venue-link is
beter dan een Songkick-redirect-URL).

**Belangrijke herontdekking tijdens het uitzoeken van "Filth"'s directe
URL**: een plain `urllib`-fetch van die specifieke event-URL werkte
gewoon, GEEN Cloudflare-uitdaging. Verder getest: `tivolivredenburg.nl/agenda/`
(de volledige agenda-listing-pagina) rendert ook gewoon server-side met
alle events + echte per-event-`href`'s in de ruwe HTML — de eerder
gevonden "Cloudflare-blokkade" (2026-08-15, "herbevestigd") bleek bij
hertesten een fout-positief: de string "challenge-platform" komt voor,
maar dat is Cloudflare's passieve JS-bot-analytics-script
(`/cdn-cgi/challenge-platform/scripts/jsd/main.js`), geen daadwerkelijke
"Just a moment..."-interstitial — die tekst staat nergens in de pagina.
Dit weerspreekt de eerder vastgelegde "principiële grens"
(ARCHITECTURE.md/SCRAPERS.md: "TivoliVredenburg... bevestigde Cloudflare
bot-challenge"). Mogelijk is Cloudflare's configuratie sindsdien versoepeld,
of was de eerdere test onvolledig (bv. zonder de juiste User-Agent-header,
of testte een andere sub-pagina). **Nog niet omgezet in een nieuwe volledige
scraper** — dit is een bevinding die aan Michiel voorgelegd moet worden
voor er verder gebouwd wordt (zou de Songkick-omweg overbodig kunnen maken
en volledige TivoliVredenburg-dekking mogelijk maken, i.p.v. alleen de
~9 Songkick-shows).

**Ook gemeld door Michiel, nog te onderzoeken**: Groninger Museumnacht
(19 september) ontbreekt als Uitje — gezien op `groningermuseum.nl/
?type=soon&page=1&perPage=6`. Eerste check: die specifieke pagina is
client-side gerenderd (geen "Museumnacht" in de ruwe HTML via plain
`urllib`) — vraagt om een Playwright-haalbaarheidscheck, uitbesteed aan een
subagent, resultaat nog niet binnen bij het schrijven van deze entry.

## 2026-08-17 — Groninger Museum opgelost (was 5+ jaar "geparkeerd als moeilijk"), TivoliVredenburg herzien naar directe scraper
Vervolg op de kapotte-links-melding hierboven. Michiel: "ok, ik ga nu weg,
pas alle fixes nu direct toe die je hierboven beschrijft en voor tivoli
vredenburg" — expliciete go-ahead om door te bouwen zonder verdere
tussentijdse bevestiging.

**Groninger Museum — echte oplossing gevonden via een Playwright-
netwerkcheck**: eerdere conclusie (2026-08-15) was "Craft CMS, voor de hand
liggende GraphQL-endpoints geven 404, Playwright-rendering blijft leeg,
genuine dead end". Een subagent kreeg de opdracht om specifiek
`groningermuseum.nl/?type=soon&page=1&perPage=6` (de URL uit Michiels
screenshot) met Playwright te renderen én het netwerkverkeer mee te lezen —
dat legde een simpele, publieke JSON-endpoint bloot:
`/api/activities?type=<now|soon|past>&page=N&perPage=N` en
`/api/exhibitions?type=<now|soon>&page=N&perPage=N`. Geen GraphQL, geen
sessie/cookie/referrer nodig, gewoon een directe HTTP-GET. `scrape_
groningermuseum.py` gebouwd: exhibitions geven een schoon `prettyDate`
("19 september 2026 t/m 9 mei 2027", altijd dag+maand+jaar aan beide
kanten in de geziene data) → Exposities met `date_end`; activities zijn
grotendeels generiek-terugkerend ("Ieder weekend en in de schoolvakanties")
en worden overgeslagen tenzij er een concrete losse datum in staat (zoals
"Groninger Museumnacht", Michiels oorspronkelijke melding) — 9 events in
totaal. Bestaande 2 handmatige rijen (waarvan 1 met foutieve URL, zie
hierboven, en "Kinderbiënnale" die op de site inmiddels omgedoopt/vervangen
bleek door "Playing House...") opgeruimd vóór de live-run.

**Bijvangst-dedup-gat, 3e keer (nieuw patroon, niet cross-taal maar
cross-datum)**: "Bakstain" bleek zowel via `scrape_kunstpuntgroningen.py`
(05-08) als via de nieuwe directe `scrape_groningermuseum.py` (05-09) te
komen — 1 dag verschil in startdatum. `find_cross_source_duplicates()`
groepeert strikt per EXACTE datum (`by_date[r['date']].append(r)`), dus dit
paar werd nooit met elkaar vergeleken ondanks identieke titels. Zelfde
pragmatische fix als bij DSG: `scrape_kunstpuntgroningen.py`'s
`SKIP_VENUES` uitgebreid met `'Groninger Museum'` (nu dat er een eigen,
preciezere directe scraper is, is Kunstpunt's dekking van dat ene venue
sowieso overbodig geworden). Stale Kunstpunt-rij verwijderd, herscraped.

**TivoliVredenburg — het echte verhaal achter Filth/Alcest**: bleek een
structurele bug (alle 480 rijen hadden `url=NULL`, niet alleen deze 2) —
zie de vorige decisions.md-sectie hierboven voor de root-cause-analyse
(`insert_event()` update nooit bestaande same-source-rijen). Michiel vond
zelf directe TivoliVredenburg-URL's voor beide events, wat leidde tot de
ontdekking dat de site zelf helemaal niet (meer) door Cloudflare
geblokkeerd wordt — zie de nieuwe ARCHITECTURE.md §Playwright-scrapers-les
hierover.

Vervolgens is `scrape_tivolivredenburg.py` volledig herzien: i.p.v. de
Songkick-omweg (alleen live-muziek, ~9 shows) haalt hij nu direct
`tivolivredenburg.nl/agenda/page/N/` op. Paginering loopt door tot een 404
(2026-08-17: pagina 43, dynamisch bepaald via `parallel_fetch.fetch_batches()`
i.p.v. hardcoded, zodat dit niet achterloopt als het aantal groeit) — 853
events, alle 20 items per pagina hebben de datum al in hun eigen URL-slug
(`.../filth-17-08-2026`), dus geen aparte datumtekst-parsing nodig.

**Bug tijdens het bouwen**: `fetch_batches(1, page_url, should_stop, ...)`
gaf 0 resultaten — `page_url` bouwt alleen de URL-string, fetcht 'm niet.
Moest `lambda p: fetch(page_url(p))` zijn. Meteen gevonden via een
kleinschalige test (`--max 3`) vóór de volle 43-pagina's-run — zelfde
voorzichtige aanpak als bij eerdere paginering-bugs dit project.

**Stale-data-audit vóór het legacy-dataset vervangen** (480 oude rijen,
eerder expliciet bewaard omdat ze breder waren dan Songkick): fresh scrape
(853) vergeleken met de oude 480. Eerste ruwe vergelijking gaf 102
"legacy-only" rijen, wat schrikbarend leek — bleken bij nadere inspectie
bijna allemaal al-verstreken events (vóór vandaag) te zijn, dus sowieso al
gefilterd door de datumfilter. Van de 400 nog-toekomstige legacy-rijen
bleken er bij een naïeve title-match 22 "ontbrekend" in de fresh scrape —
maar `normalize_title()` blijkt geaccentueerde tekens (bv. "Paco Peña")
volledig te STRIPPEN i.p.v. te transcriberen naar hun kale vorm, waardoor
zulke titels nooit matchen met hun accent-loze variant elders. Na handmatig
accent-folden (`unicodedata.normalize('NFKD', ...)` + combining-tekens
verwijderen) bleven er maar 10 échte "legacy-only"-events over (van de 400)
— waarschijnlijk simpelweg afgelaste/verschoven shows sinds de oude pull.
Gezien de fresh scrape 853 vs 480 events dekt en nog geen 3% van de oude
toekomstige data écht ontbreekt, is de hele oude dataset vervangen (niet
losse rijen bijgehouden) — dit is de eerste keer in dit project dat een
volledige legacy-dataset zo vervangen wordt i.p.v. ernaast bewaard, bewust
zo gedaan omdat de nieuwe scraper nu aantoonbaar breder én preciezer is
(events zonder ooit een URL, tegen nu 100% met URL).

**Restpunt, niet gefixt (buiten scope voor nu)**: `normalize_title()` in
events_db.py strip geaccentueerde tekens i.p.v. ze te folden — kan in
theorie ELDERS in het project ook near-duplicates laten glippen bij
titels met accenten (Frans/Spaans/Portugese artiestennamen komen relatief
vaak voor bij muziekprogrammering). Nog niet structureel aangepakt, alleen
opgemerkt tijdens deze stale-data-audit.

**Resultaat, geverifieerd lokaal vóór commit**: Filth/Alcest/Groninger
Museum-links werken, TivoliVredenburg 0/853 zonder URL (was 480/480 zonder
URL), Groninger Museumnacht zichtbaar als Uitje, Groninger Museum-scraper
dekt 8 exposities + 1 activiteit. SCRAPERS.md's "geparkeerd als moeilijk"-
lijst: 7 → 6 bronnen.

## 2026-08-17 — meerdaagse events op drenthe.nl/friesland.nl/visitgroningen (n.a.v. Michiels vraag over Zomerfeest Eext)

Michiel vroeg of https://www.drenthe.nl/evenementen-activiteiten/4218330043/zomerfeest-eext
(vr 21 t/m zo 23 augustus 2026) wel op alle drie de dagen genoteerd stond.
Bleek niet zo — root cause: `parse_date()` in alle drie de "plaece.nl"-scrapers
(drenthe.nl/friesland.nl/visitgroningen, near-identieke copy-paste-code) had
een regex `(\d{1,2})\s*(?:t/m\s*\d{1,2}\s*)?(maand)` waarin de `t/m N` een
NON-capturing group is — het cijfer na "t/m" werd dus wel herkend maar meteen
weggegooid, met als gevolg dat een 3-daags event alleen op zijn eerste dag in
de agenda stond.

**Scope van de bug** (gemeten op drenthe.nl, 1469 datumteksten): 252 bevatten
"t/m" — daarvan 102 volledige bereiken ("21 t/m 23 augustus", start- én
einddag, altijd dezelfde maand in alle geziene gevallen) en 150 end-only
("t/m 23 augustus", geen zichtbare startdag — vermoedelijk al eerder begonnen
doorlopende dingen).

**Fix**: `parse_date()` in alle drie de scrapers herschreven van
`str | None` naar `tuple[start_iso, end_iso|None] | None`. Nieuwe regex-tak
herkent volledige bereiken expliciet en levert nu een echte `date_end` op.
De end-only-vorm is **bewust ongewijzigd gelaten** — een fix zou een gok over
de onbekende startdatum vereisen, en dat wilde ik niet zonder overleg doen
(zie CLAUDE.md-regel over aannames). Call sites in alle drie bestanden
aangepast om het tuple uit te pakken en `date_end` alleen te zetten als die
afwijkt van de startdatum.

**Bug tijdens het bouwen**: `MONTHS_NL`-dict geeft maandnummers als
zero-padded STRINGS (`'08'`), niet ints — een `date(year, month_n, day)`-call
binnen de nieuwe `make_date()`-helper crashte eerst met
`TypeError: 'str' object cannot be interpreted as an integer` doordat de
`int()`-conversie (die in de oude code alleen op het uiteindelijke
`date()`-aanroeppunt stond) niet was meegenomen. Gefixt.

**Belangrijkere vervolgvondst — `event_is_valid()` gebruikte `date_end` alleen
voor expo's, niet voor gewone events**: zelfs met de parse-fix zou
Zomerfeest Eext na 21 augustus alsnog uit de agenda verdwijnen, want de
validity-check in `gen_uitjes.py` filterde niet-expo events uitsluitend op
`d >= TODAY` (startdatum), `date_end` werd daar helemaal niet gelezen. Dat
raakt de kern van Michiels vraag — "staat het er nog op dag 2/3" — dus ook
gefixt: `event_is_valid()` houdt een niet-expo event nu zichtbaar zolang
`date_end >= TODAY`, met de startdatum-regel als fallback wanneer er geen
`date_end` is (anders dan bij expo's, die zónder `date_end` juist altijd
geldig blijven — dat bestaande gedrag is bewust niet aangeraakt).

**Weergave uitgebreid**: `event_html()` toont nu een bereik ("vr 21 t/m zo 23
aug") i.p.v. alleen de startdag zodra `date_end` afwijkt van `date` — nieuwe
`fmt_date_range()`-helper, kort formaat (in tegenstelling tot expo's lange
"vanaf ... t/m ..."-stijl, past beter bij de kleinere event-date-regel).
`data-date`/`data-dateend`-attributen toegevoegd aan de event-div voor
consistentie met expo-kaarten (nog niet door JS gebruikt, wel beschikbaar
voor toekomstig gebruik zoals per-dag filteren).

**Opruimen vóór live-run**: `insert_event()`'s bekende beperking (zie eerdere
sessies) dat een same-source herscrape een bestaande rij nooit update, dus
het simpelweg herdraaien van de scrapers zou de nieuwe `date_end`-info niet
in bestaande rijen krijgen. Preciese cleanup: voor elk van de drie bronnen
eerst een fresh parse gedaan, en alleen de specifieke bestaande DB-rijen
verwijderd waarvoor de fresh parse een `date_end` oplevert én de bestaande
rij nog `date_end IS NULL` had (geen blanket wipe). Resultaat: 15 unieke
meerdaagse events op drenthe.nl, 35 op friesland.nl, 6 op visitgroningen nu
met correcte `date_end` in de DB.

**Geverifieerd lokaal vóór commit**: unit-tests voor alle datumformaten in
alle drie bestanden, live dry-run bevestigt Zomerfeest Eext specifiek
(`date_end: '2026-08-23'`), live scrape + export + generate uitgevoerd,
gegenereerde `index.html` gecontroleerd — Zomerfeest Eext toont nu
"vr 21 t/m zo 23 aug" en blijft (gesimuleerd) zichtbaar t/m 23 augustus,
verdwijnt pas op 24 augustus.

## 2026-08-17 — Zummerbühne toont verkeerde afstand (Oostwold-verwarring)

Michiel meldde dat Zummerbühne (Oostwold) op de site ~20km toont, maar Google
Maps vanaf huis een veel grotere afstand (35,7km rijdend). Root cause: er
bestaan **twee verschillende plaatsen genaamd "Oostwold" in Noord-Nederland**
— één in Oldambt (Groningen, bij Scheemda/Winschoten, waar Zummerbühne
daadwerkelijk zit: Polderweg 26/28, 9682 XS) en één in Westerkwartier (bij
Leek, ~40km verderop richting het westen). `city_coords.json`'s "Oostwold"-
entry (via Nominatim-geocoding, zie `build_city_coords.py`) wees naar de
VERKEERDE (Westerkwartier) — de bestaande `VIEWBOX`-bounding-box voor Noord-
Nederland dekt beide plaatsen, dus disambigueert niet tussen ze; Nominatim gaf
gewoon zijn top-ranked match terug (`limit: 1`), zonder enige garantie dat
dat de bedoelde plaats is.

**Bijkomende factor**: de 25 Zummerbühne-rijen (`source='zummerbuhne'`,
handmatig ingevoerd — er bestaat geen `scrape_zummerbuhne.py`, zie
SCRAPERS.md: de site's ticketwidget bleek een ride-share/carpool-widget, geen
scrapbare ticketverkoop) hadden helemaal geen `city`/`lat`/`lon` ingevuld,
dus vielen sowieso terug op `VENUE_LOC['zummerbuhne']` — een hardcoded
fallback-coördinaat `(52.85, 6.75, 'Drenthe')` die BEIDEN fout bleek: niet
alleen de coördinaat zelf (ergens in zuidelijk Drenthe, nergens bij Oostwold),
maar ook de provincie (Oldambt is Groningen, niet Drenthe — dus deze events
stonden al die tijd ook onterecht onder het Drenthe-provinciefilter i.p.v.
Groningen).

**Fix, drie plekken**:
1. `city_coords.json`'s `"Oostwold"`-entry gecorrigeerd naar de Oldambt-
   coördinaten (53.208276, 7.041508) — enige huidige gebruiker in de dataset
   is de visitgroningen-aggregator-rij voor dezelfde Zummerbühne, dus geen
   ander event breekt hierdoor.
2. Alle 25 handmatige `zummerbuhne`-rijen in de DB kregen expliciet
   `lat`/`lon`/`city` (zelfde prioriteitsketen als Kunstpunt eerder deze
   sessie: event-eigen lat/lon wint sowieso van CITY_COORDS/VENUE_LOC) —
   preciezer dan via de plaatsnaam-lookup, en maakt deze events onafhankelijk
   van een eventuele toekomstige hernieuwde Oostwold-verwarring.
3. `VENUE_LOC['zummerbuhne']` in `gen_uitjes.py` gecorrigeerd naar dezelfde
   coördinaten + provincie 'Groningen' (was 'Drenthe') — blijft nu een
   correcte fallback mocht een toekomstige handmatige rij weer zonder
   lat/lon ingevoerd worden.

**Resterend verschil, geen bug**: haversine (hemelsbreed) geeft nu ~27km
Annen-Oostwold, Google Maps rijdend ~35,7km — dat verschil is inherent aan
hemelsbrede-afstand-vs-rijafstand (de Dollard/Reiderland-polders in die hoek
van de provincie hebben geen directe wegen) en is een bekende, geaccepteerde
beperking van de haversine-aanpak, niet apart opgelost.

**Restpunt, niet gefixt**: `build_city_coords.py`'s Nominatim-geocoding kan
in theorie hetzelfde soort fout maken bij elke andere plaatsnaam die
dubbel voorkomt binnen de Noord-Nederland-viewbox — nu alleen ontdekt en
gefixt voor dit ene concrete geval (Oostwold), geen generieke disambiguatie
gebouwd (zou een provincie/gemeente-hint per plaatsnaam vereisen, die de
brondata niet altijd meegeeft).

## 2026-08-17 — Claude Design-integratie + eerste design-review verwerkt

Michiel voegde de `claude-design` MCP-server toe (`claude mcp add --scope user
--transport http claude-design https://api.anthropic.com/v1/design/mcp`) en
vroeg om een design-system-project "Uitjesagenda" aan te maken zodat Claude
Design de live site kan bekijken en met verbetersuggesties komt.

**Werkverdeling vastgelegd**: Claude Design bekijkt/adviseert, ik (Claude
Code) bouw. De site is geen los HTML-bestand maar wordt gegenereerd door
`gen_uitjes.py` — alles wat in het design-system-project zelf "gebouwd" zou
worden staat los van die pipeline en wordt bij de eerstvolgende wekelijkse
refresh toch overschreven. Project aangemaakt (`b3a7bf05-...`), een kopie
van `index.html` gepusht als preview-kaart (`pages/index.html`, met een
`@dsCard`-marker), NIET het bronbestand zelf.

**Eerste review-resultaat verwerkt**: voordat er iets doorgevoerd werd zijn
een aantal concrete, verifieerbare claims eerst gecheckt tegen de echte code
(niet blind vertrouwd) — allemaal bevestigd als echte bugs:
- `src_css()` zette bij ALLE bronnen `color:#fff` op de actieve chip-staat,
  ook bij lichte kleuren (cambuur `#ffd700`, lycurgus `#ffcc00`, effenaar
  `#f9a825`, goahead `#f5a623`) — onleesbare witte tekst op geel/oranje.
  `club_css()` had toevallig al een (hardcoded, niet-generieke) uitzondering
  voor dit exacte probleem.
- Beide `target="_blank"`-links (event- en expo-titels) misten `rel="noopener"`.
- `#addr-input` stond op `0.78rem` (~12,5px, root is 16px want er is geen
  `html{font-size}`-override) — onder de 16px-grens die iOS-Safari laat
  inzoomen bij focus.
- `today_str` gebruikte `date.today().strftime('%B')` — locale-afhankelijk
  (Engelse maandnaam op deze Windows-serverlocale), terwijl er al een
  `NL_MONTHS_LONG`-dict bestaat die hier nooit voor gebruikt werd.
- Geen `content-visibility` ergens in de CSS — klopt, met ~8202 events plat
  in de DOM is dat een reële, makkelijk te pakken perf-winst.

**Doorgevoerd** (`gen_uitjes.py`):
1. Nieuwe `_contrast_text(hex_color)`-helper (simpele relatieve-helderheid-
   check) — `src_css()` gebruikt 'm nu voor de actieve-chip-tekstkleur i.p.v.
   altijd wit; `club_css()`'s oude hardcoded ternary vervangen door dezelfde
   helper (consistent, minder duplicatie).
2. `rel="noopener"` toegevoegd aan beide `target="_blank"`-links.
3. `content-visibility:auto;contain-intrinsic-size:auto 62px` op `.event`
   (niet op `.month-section` — een verkeerd geschatte intrinsic-size op een
   container met sterk wisselend aantal events per maand zou juist
   scroll-jank kunnen geven; op het kaart-niveau is de hoogte voorspelbaar).
4. `#addr-input` font-size naar `1rem` (16px).
5. `today_str` herbouwd met `NL_MONTHS_LONG` i.p.v. `strftime('%B')`.
6. Titel-hiërarchie: `.event-title a` van `#1565c0`/weight 500 naar
   `var(--text)`/weight 600/`0.95rem` (blauw+onderstreept alleen nog bij
   hover) — titel is nu de sterkste tekst op de kaart i.p.v. even zwaar als
   venue/badges. `.event-date` iets sterker (`var(--text)`, weight 700).
7. `a:focus-visible,button:focus-visible,input:focus-visible` — ontbrak
   volledig, toetsenbordgebruikers zagen nergens een focus-indicator.
8. Lege-staat-bericht (`#empty-state`) toegevoegd: bij 0 resultaten stond er
   alleen een kleine "Toont 0 van 8202" in de statusbalk, verder een leeg
   scherm zonder uitleg. Nu een concreet bericht incl. waarschijnlijke
   oorzaak ("geen events binnen N km — probeer een grotere afstand").

**Bug tijdens het bouwen (proces-les, geen data-bug)**: eerste poging om
punt 1-3 in één script te bundelen crashte halverwege (de `rel="noopener"`-
match faalde door een kopieerfout in de multi-line `old`-string) — de
`assert` gooide een exception VOORDAT `open(path,'w').write(src)` bereikt
werd, dus de eerdere geslaagde `str.replace()`-stappen (punt 1-2) gingen
he-le-maal verloren, ook al leek de foutmelding alleen over punt 3 te gaan.
Pas bij de verificatie-pass (grep op de output) bleek dat de contrast-fix
er niet in zat. Les: bij een geketende reeks `apply()`-calls in één script
is een gedeeltelijke crash een ALLES-of-NIETS — geen van de eerdere stappen
overleeft, want de write gebeurt pas na de laatste. Simpelweg opnieuw
uitgevoerd met de exacte huidige bestandsinhoud als basis, dit keer
succesvol; nu bewust elke wijziging apart met een `assert`+aparte
`grep`-verificatie gecheckt na de finale write, niet vertrouwd op het
ontbreken van een crash alleen.

**Bewust NIET doorgevoerd, wel gelogd** (grotere/subjectievere
productkeuzes, horen bij Michiel te liggen): zie overleg.md punt 17 voor de
volledige lijst (zoekveld, datumfilter, filterbalk→toolbar+popover-herbouw,
kleurstrategie omgooien, lazy-loading-architectuur, URL/localStorage-state,
sorteren voor Uitjes, mobiele touch-targets, mode-wissel-die-filters-wist,
aria-pressed/role=group).

**Geverifieerd**: alle 13 checks (contrast x4 + 1 ongewijzigde controle,
noopener, content-visibility, addr-input, maandnaam, titel-typografie,
focus-visible, empty-state div+JS) bevestigd via een grep-gebaseerde
verificatie-script tegen de daadwerkelijk gegenereerde `index.html` — niet
alleen "geen crash" aangenomen.

## 2026-08-17 — SPOT Groningen toonde weer generieke "Spot Groningen" i.p.v. Oosterpoort/Stadsschouwburg

Michiel viel op dat de site bij SPOT-events overal "Spot Groningen" toonde,
terwijl `scrape_spotgroningen.py` (gebouwd 2026-08-10, zie decisions.md
onder "Architectuur/2026-08-10") juist specifiek het gebouw (Oosterpoort vs
Stadsschouwburg) uit SPOT's eigen `data-location`-attribuut zou moeten
lezen.

**Root cause: het bekende `insert_event()`-patroon, 4e keer dit project**
(eerder gezien bij forum.nl, Geke Hoogstins, TivoliVredenburg): 611 van de
662 DB-rijen hadden `venue='Spot Groningen'` (de generieke fallback),
terwijl een fresh scrape van de live programma-pagina voor diezelfde
titel+datum gewoon het juiste gebouw teruggaf (337 Oosterpoort/209
Stadsschouwburg op de live pagina op het moment van checken). De
scraper-logica zelf was dus niet stuk — het waren rijen die (waarschijnlijk)
al vóór de venue-differentiatie is toegevoegd, en sindsdien bij elke
herscrape genegeerd werden omdat `insert_event()` een bestaande
same-source-rij nooit update.

**Fix**: zelfde gescopede aanpak als steeds bij dit patroon — fresh scrape
gedraaid, en alleen de specifieke bestaande rijen verwijderd waarvoor
`venue='Spot Groningen'` in de DB stond terwijl de fresh scrape een
specifiek gebouw opleverde (559 rijen), daarna de scraper live opnieuw
gedraaid (626 gevonden, 544 nieuw — het kleine verschil met 559 komt door
een paar events die tussen het verwijderen en herscrapen van datum
wisselden). Resultaat: 329 Oosterpoort, 202 Stadsschouwburg, 32
Machinefabriek, 12 USVA, 12 Lutherse Kerk, 8 A-Theater, nog 67 legitiem
generiek (`elders`/lege `data-location`-waarde op de bron zelf).

**Nog niet structureel opgelost**: dit is de 4e keer dat exact hetzelfde
onderliggende `insert_event()`-gedrag een stille data-veroudering
veroorzaakt. Een generieke fix (bv. altijd een UPDATE proberen bij een
same-source-botsing, niet alleen bij aggregator-vs-directe-bron) zou dit
hele patroon in één keer voorkomen i.p.v. steeds opnieuw per-bron te
ontdekken en handmatig te repareren — nog niet gebouwd, wel de moeite waard
om te overwegen. Zie ook overleg.md.

## 2026-08-17 — insert_event() structureel gefixt (voorkomt een 5e herhaling)

Michiel vroeg door op het zojuist genoemde restpunt ("kan je een kleine
search doen om dat te achterhalen? ik bedoel de insert(event)") — dus
uitgezocht en meteen structureel gefixt i.p.v. het weer als open punt te
laten liggen.

**Analyse eerst**: gecheckt hoe vaak velden per bron daadwerkelijk leeg
zijn (bv. `friesland.nl`/`drenthe.nl`/`visitgroningen` missen structureel
`venue`, `melkweg`/`013` missen bij een deel van de events `url`/`venue`).
Bevestigt het risico dat een naïeve "altijd overschrijven"-regel net zo
gevaarlijk zou zijn als het huidige "nooit overschrijven" — een scraper-run
met één incompleet veld (parse-fout bij een specifiek event) zou dan een
eerder wél gevulde waarde kunnen wissen.

**Fix**: `insert_event()` in `events_db.py` herbouwd met een derde
botsings-geval. Was: (1) aggregator-vs-directe-bron → overschrijven, (2)
overig → altijd negeren. Nu: (1) **zelfde bron** → veld-voor-veld merge via
nieuwe `_merge_values()`-helper (nieuwe waarde wint alleen als die niet leeg
is — `None`/`''`/`'[]'` tellen als leeg), (2) aggregator-vs-directe-bron →
ongewijzigd volledige overschrijving, (3) overig → ongewijzigd genegeerd.
Bijkomende opschoning: `_event_values()`-helper toegevoegd om de
kolom-waarden-dict (voorheen 2x losstaand uitgeschreven, voor INSERT en
UPDATE) te delen.

**Getest tegen een losstaande test-DB** (niet de echte `events.db`) met 6
scenario's vóór toepassing: nieuw event invoegen, identieke same-source-
herscrape (moet no-op zijn, `False`), same-source met een nieuw ingevuld
veld (moet updaten, bestaande velden blijven intact), same-source met een
leeg veld waar eerder een waarde stond (mag NIETS wissen), directe bron
overschrijft aggregator (bestaand gedrag, moet blijven werken), aggregator
ná een directe bron (moet genegeerd blijven). Alle 6 scenario's gaven het
verwachte resultaat. Daarna een read-only check tegen de echte DB
(`events_db.py stats`) en een live herscrape van SPOT Groningen gedraaid
ter controle — die werd door `page_cache.py`'s `unchanged()` als
"ongewijzigd sinds vorige run" geskipt (verwacht, want net dezelfde dag al
herscraped), dus geen directe test van het nieuwe pad tegen productiedata,
maar bevestigt wel dat er niets kapot is gegaan aan de bestaande flow.

**Effect vanaf nu**: de volgende keer dat een scraper een veld toevoegt of
verbetert (nieuwe URL-extractie, betere venue-splitsing, een `date_end`-fix
zoals bij drenthe.nl deze sessie) komt dat automatisch door bij de
eerstvolgende herscrape, zonder dat er eerst weer een handmatige
stale-rijen-opschoning nodig is zoals bij forum.nl/Geke Hoogstins/
TivoliVredenburg/SPOT Groningen. Zie ARCHITECTURE.md §Cross-source dedup
voor de bijgewerkte technische beschrijving.


## 2026-08-17 — Claude Design-review clusters 1-4 gebouwd op een feature-branch

Na overleg.md punt 17 (volledige, geclusterde lijst) heeft Michiel per cluster
besloten wat te bouwen: clusters 1-4 (kleine fixes, nieuwe functionaliteit,
afstand-UI, mobiele layout) goedgekeurd om nu te bouwen; cluster 5 (filterbalk
→ toolbar-herbouw, kleurstrategie, lazy-loading-architectuur) bewust NIET nu —
zie overleg.md voor de motivatie per onderdeel. Op Michiels verzoek dit keer
op een aparte branch (`design-review-clusters-1-4`) i.p.v. direct op `main`,
zodat hij het resultaat eerst kan bekijken voor het gemerged wordt.

### Cluster 1 — kleine veilige fixes
- `line-height:1.45` op body (algemene leesbaarheid; de meeste elementen
  hebben al een eigen kleinere, met opzet compacte font-size — een blanket
  16px-bump zou de informatiedichtheid van deze dense-listing-UI onevenredig
  opblazen, dus bewust NIET gedaan).
- Contrastfout `#aaa` op wit (~2,3:1, faalt WCAG) in footer + `.dist-badge`
  gefixt naar `var(--muted)` (~5,4:1, haalt AA).
- Emoji weg uit de 60 bronchips (badges op de kaarten zelf gebruikten ze al
  niet) — "ruis, geen informatie" per de review.
- "Terug naar boven"-knop (verschijnt na 400px scroll, `scrollTo` smooth).
- Afstanden bijgehouden in een `Map` i.p.v. telkens `dataset.dist`
  lezen/schrijven (JS-perf).
- `aria-pressed` via een MutationObserver, bewust GESCOPED tot alleen de
  filter-containers (`.mode-toggle`,`.filters`) i.p.v. `document.body` — een
  observer op de hele pagina zou ook bij ELKE `.hidden`-toggle op de 8202
  event-kaarten meevuren (gebeurt continu tijdens filteren) en zo precies de
  perf-winst van de Map-gebaseerde `apply()` tenietdoen.
- `role="group"` + `aria-labelledby` op alle 7 filter-groepen + mode-toggle.

### Cluster 3 — afstand-UI
- Range-slider + `window.prompt()` vervangen door zichtbare segmented buttons
  (10/25/50/100/alle) + een inline eigen-km-veld (`type="number"`, 16px
  font-size — voorkomt dezelfde iOS-zoom-bug als eerder bij `#addr-input`).
- Adresrij op mobiel een eigen volle regel (`flex-direction:column`) i.p.v.
  rommelig wrappen tussen label/input/knoppen/afstandsknoppen.

### Cluster 4 — mobiel layout
- Chip-filtergroepen op mobiel: horizontale scroll met randfade
  (`mask-image`) i.p.v. wrappen naar 3-4 regels — toegepast via een nieuwe
  `.chip-scroll`-klasse op de 6 pure-chip-groepen (Sport/Geslacht/Club/
  Genre/Bron/Sorteren). **Bewust NIET** op de Provincie&afstand-groep: die
  bevat ook de complexere adresrij (input/knoppen), niet geschikt voor
  dezelfde scrollstrip als simpele chips.
- Kaart op mobiel herindeeld: `display:block` i.p.v. de 3-koloms-grid, datum
  als kleine kicker boven de titel, bron-badge (`.badge-src`) verborgen
  (genre-badge blijft, nuttige info) — bewust `.event:not(.expo-item)` om de
  Exposities-kaarten (andere HTML-structuur, geen los datum-element) niet
  mee te raken.

### Cluster 2 — nieuwe functionaliteit (grootste stuk)
- **Zoekveld**: debounced (250ms) tekstveld, zoekt op titel+venue via een
  vooraf-berekend `data-search`-attribuut per kaart (lowercased, gezet in
  `event_html()`/`expo_card_html()`) — voorkomt dat elke toetsaanslag 8202x
  child-elementen moet uitlezen en `.toLowerCase()` moet aanroepen. Werkt in
  alle 3 modi.
- **Datumfilter**: Vandaag/Dit weekend/Deze week/Deze maand + een eigen
  van/tot-periode (`<input type="date">`, native picker). Overlapt-logica
  voor meerdaagse events (`data-dateend`): een event matcht zodra zijn
  bereik overlapt met het gekozen venster, niet alleen bij een exacte
  startdatum-match. Alleen zichtbaar/actief in uitjes+sport (niet
  exposities, per definitie langlopend).
- **Sorteren voor Uitjes** (datum/afstand): herordent kaarten BINNEN elke
  maand-sectie i.p.v. de maand-groepering zelf op te heffen zoals bij
  Exposities' platte lijst — lager risico, blijft chronologisch
  navigeerbaar.
- **Actieve-filter-samenvatting**: verwijderbare tokens + "Wis alles".
  Verwijderen delegeert naar de BESTAANDE klik-handler van de bijbehorende
  chip (via `.click()`) i.p.v. filterlogica te dupliceren — voorkomt dat de
  token-rij en de chips zelf uit sync raken.
- **URL-state**: filters/modus/zoekterm in de query-string
  (`history.replaceState`, geen `pushState` — anders krijgt elke chip-klik
  een eigen terug-knop-stap). Adres zelf (async geocode-aanroep) bewust NIET
  meegenomen — zou de init-flow async maken, scope beperkt gehouden.

### Task: modus-wissel bewaart filters waar mogelijk
`setMode()` wiste voorheen bij ELKE modus-wissel alle sport- én
uitjes-specifieke filters. Nu: filters die in de nieuwe modus geen
betekenis hebben vervallen (bv. genre/bron bij het overschakelen naar
Sport), de rest (provincie, afstand, zoekterm) blijft behouden — Michiels
expliciete keuze uit de clustering-vraag.

### Twee echte bugs gevonden tijdens het bouwen, bevestigd met een live browsertest

**1. `requestAnimationFrame`-batching van `apply()` (JS-perf-suggestie uit de
review) bleek een reële betrouwbaarheidsbug.** Eerst gebouwd zoals
voorgesteld; een test tegen een lokale `http.server`-preview liet zien dat
een klik op een filter-chip geen zichtbaar effect meer had. Root cause:
`document.visibilityState==='hidden'` in de niet-actief-zichtbare
browser-tab van de testomgeving — browsers stellen `requestAnimationFrame`-
callbacks dan uit of pauzeren ze helemaal (spec-gedrag, geen bug van de
testomgeving). Bevestigd door `_applyNow()` direct aan te roepen (werkte
meteen correct) vs. via `apply()`→`requestAnimationFrame` (bleef hangen).
Voor een ECHTE gebruiker in een actief tabblad vuurt rAF wel betrouwbaar af
op ~60fps, maar het risico (tabblad wisselen net na een klik, sommige
mobiele/in-app-browser-contexten) woog niet op tegen de marginale winst van
het batchen van één simpele klik-reactie (1 klik = 1 aanroep toch al).
Teruggedraaid; alleen de Map-gebaseerde afstand-optimalisatie gehouden (die
heeft dat risico niet, is een pure data-structuur-verbetering).

**2. Tijdzone-bug in de nieuwe datumfilter-logica.** `computeWhenRange()`
gebruikte aanvankelijk `d.toISOString().slice(0,10)` om een `Date`-object
naar een ISO-datumstring om te zetten — `.toISOString()` converteert echter
altijd naar UTC. Met de Nederlandse zomertijd (UTC+2) gaf `new
Date().setHours(0,0,0,0)` (lokale middernacht) via `.toISOString()` de
datum van de VORIGE dag terug (bevestigd: 17 augustus lokaal → "2026-08-16"
in de ISO-string). Dit had ELKE Nederlandse gebruiker geraakt (heel de
doelgroep van deze site zit in UTC+1/+2). Gefixt door lokale
datumcomponenten (`getFullYear()`/`getMonth()`/`getDate()`) te gebruiken
i.p.v. UTC-conversie.

**Les, breder dan deze twee bugs**: beide zijn typisch het soort fout dat
een grep-gebaseerde verificatie (zoals bij de eerste, kleinere design-fixes
dit project) NOOIT had gevonden — alleen een echte browsertest met
daadwerkelijke klik-interacties en tijdzone-gevoelige datumberekeningen
legde ze bloot. Bij deze grotere, interactievere batch is daarom bewust
overgestapt van "regenereren + grep" naar "regenereren + een lokale
`http.server`-preview + browser-`javascript_exec`-tests die de JS
daadwerkelijk laten draaien".

**Geverifieerd**: alle onderdelen los getest via de lokale preview
(zoeken, datumfilter incl. tijdzone-check, sorteren, filter-tokens
verwijderen, URL-state schrijven+herstellen incl. modus, modus-wissel-
filterbehoud, mobiele layout op 375px-viewport), geen console-errors.
Gepusht naar `design-review-clusters-1-4` (niet naar `main`) — wacht op
Michiels review voor mergen.


## 2026-08-18 — Claude Design-review cluster 5 gebouwd (toolbar + kleurstrategie)

Vervolg op clusters 1-4. Michiel besloot: cluster 5 wél bouwen, MAAR
lazy-loading-architectuur (het derde cluster-5-item) niet — die stond al
vast als "nog niet, later apart bekijken" bij de vorige triage. Blijft op
dezelfde branch (`design-review-clusters-1-4`), niet gemerged.

### Filterbalk → toolbar + popovers + sticky bar
- **Eén sticky wrapper** (`.topbar`, `position:sticky;top:0`) voor logo +
  mode-toggle + meta-regel + toolbar samen — i.p.v. de eerder overwogen
  gestapelde-sticky-aanpak (header op `top:0`, mode-toggle op
  `top:<headerhoogte>`) die kwetsbaar zou zijn voor een header die op smalle
  schermen over twee regels wrapt. Eén wrapper heeft geen offset-berekening
  nodig, lost het sticky-volgorde-probleem (overleg.md punt 17) definitief op.
- **Compacte toolbar**: zoekveld + knoppen `Wanneer/Waar/Genre/Bron/Sport/
  Club/Sorteren` + "Wis filters", i.p.v. 5 altijd-open rijen met ~70 chips.
  Elke knop opent een popover met de bestaande filter-chips erin — de chips
  zelf zijn ONGEWIJZIGD (zelfde `data-*`-attributen, zelfde click-handlers),
  alleen hun presentatie (wel/niet altijd zichtbaar) is anders. Dit hield het
  risico laag: de onderliggende filterlogica in `apply()` is niet aangeraakt.
- **Bron-popover**: 48 bronnen nu gegroepeerd per provincie (afgeleid uit
  `VENUE_LOC`, geen nieuwe data nodig) + een "Landelijk"-groep (de bestaande
  quick-toggle-knop bleef intact) + een eigen zoekveldje dat de chips én
  groep-kopjes live filtert.
- **Filterteller**: elke toolbar-knop toont "(N)" als er N filters actief
  zijn in die categorie — Claude Design's eigen "filterteller"-voorstel.
- **Sport/Geslacht samengevoegd** tot één "Sport"-popover (was 2 losse
  chip-rijen) — geslacht is inhoudelijk een sub-filter van sport-modus.
- **Sorteren** deelt 1 toolbar-knop/popover tussen Uitjes- en Exposities-
  sorteeropties (2 losse content-blokken binnenin, getoogd zoals voorheen
  via bestaande `uitjes-sort`/`expo-filters`-ID's — geen nieuwe logica nodig).
- **Mobiele touch-targets**: toolbar-knoppen en het zoekveld nu 44px
  min-height (was ~24px chips) — dit was in de eerste triage bewust NIET los
  opgepakt omdat losstaand vergroten zonder de balk in te klappen het
  "wall of chips"-probleem juist zou verergeren; nu vanzelf opgelost omdat
  de toolbar zelf al compact is.

### Kleurstrategie omgegooid
`src_css()` gaf voorheen élke bron zijn eigen chip-rand/tekstkleur EN zijn
eigen actieve-achtergrondkleur EN een gekleurde badge-pill op de kaart — met
60 bronnen tegelijk geen visuele rust. Nu: bronchips zijn neutraal (gedeelde
`.btn`-stijl), actief = 1 generieke accentkleur (`#1565c0`, consistent met
hoe genre/sorteer-chips al werkten) — met een `:not([data-src="all"])`-
uitzondering zodat de "Alle bronnen"-knop zijn eigen grijze stijl behoudt.
Per-bron-kleur overleeft alleen nog op de kaart zelf: de 3px linkerrand
(`.event.{{sk}}{{border-left-color:...}}`) en verder niets. `badge-src`
(bron-naam op de kaart) is nu platte grijze tekst (`var(--muted)`, geen
achtergrond/rand meer) i.p.v. een gekleurde pill. Club/sport-chips bewust
ONGEWIJZIGD gelaten — teamkleuren zijn wél betekenisvolle identiteit
(shirtkleur-associatie), anders dan de grotendeels arbitraire bron-kleuren.

### Belangrijke methodologische vondst tijdens het verifiëren

Bij het testen van de kleurstrategie via de lokale `http.server`-preview
bleek `getComputedStyle()` voor **verf-eigenschappen** (`color`,
`background-color`, `border-color`) op elementen die ZOJUIST van
`display:none` (via het `hidden`-attribuut op een popover) naar zichtbaar
zijn gezet, systematisch de OUDE/inactieve waarde terug te geven — ook bij
een handmatig gezette **inline** style (die normaliter altijd wint,
ongeacht CSS-cascade). Grondig gediagnosticeerd:
- Bevestigd met `.matches()` en directe CSS-regel-inspectie dat de juiste
  regel (hoogste specificiteit, laatste in bronvolgorde, geen
  `!important`-conflict) wél correct matcht.
- Bevestigd dat HETZELFDE altijd-zichtbare element (nooit verborgen geweest)
  wél correct de juiste computed style teruggeeft.
- Bevestigd dat LAYOUT-eigenschappen (`width`, `padding`, `left`/`top` van
  een popover) op datzelfde soort net-zichtbaar-gemaakte element WEL correct
  resolven — alleen verf-eigenschappen zijn bevroren.
- Dit is dezelfde onderliggende oorzaak als de al eerder gevonden
  `requestAnimationFrame`-bug (2026-08-17, cluster 1-4): deze testomgeving
  composeert het tabblad niet (`document.visibilityState==='hidden'`), en
  layout kan altijd berekend worden (nodig voor scripting), maar
  verf-resolutie blijkt hier aan een compositor-cyclus gekoppeld die in een
  niet-gecomposeerd tabblad nooit draait.

**Consequentie**: de kleurstrategie-CSS is grondig geverifieerd via
cascade-analyse (niet via visuele/computed-style-verificatie, die was voor
dít specifieke onderdeel niet betrouwbaar beschikbaar in deze omgeving) en
alle FUNCTIONELE logica (popover open/sluiten, filterteller, "Wis filters",
URL-state, setMode-toolbar-zichtbaarheid, bron-zoekveld, mobiele
touch-targets/horizontale-scroll) is wél volledig via de gebruikelijke
property/attribute-checks geverifieerd. **Michiel: bekijk de kleuren zelf
even op de preview-deploy (een normaal, wél gecomposeerd tabblad) om de
laatste visuele stap te bevestigen** — de logica erachter is zo grondig
mogelijk gecontroleerd zonder dat.

**Geverifieerd**: alle popovers openen/sluiten correct (1 tegelijk, sluiten
via backdrop/Escape/modus-wissel), filterteller-badges tellen correct,
"Wis filters" reset alles, bron-zoekveld filtert chips+groepen correct,
setMode() toont/verbergt de juiste toolbar-knoppen per modus, gedeelde
Sorteren-popover toont het juiste blok per modus, URL-state blijft werken
na de herbouw, mobiele toolbar scrollt horizontaal met 44px-knoppen,
mobiele popovers dokken aan de randen (`left:8px`), geen console-errors.


## 2026-08-18 — Popover-sluiten kapot in echte Firefox (gemeld door Michiel, gemist in test)

Direct na het pushen van cluster 5 liet Michiel een screenshot zien van
echte Firefox: meerdere popovers (Sorteren, Club, Bron) stonden tegelijk
open, overlappend, onbruikbaar.

**Root cause**: `.popover{{...display:flex;...}}` (mijn eigen CSS-klasse) is
een AUTEUR-regel. Het `hidden`-HTML-attribuut leunt op een LAGE-specificiteit
regel in de user-agent-stylesheet (`[hidden]{{display:none}}`). Bij gelijke
specificiteit wint auteur-CSS van UA-CSS — dus mijn `display:flex` op
`.popover` overschreef de browser's ingebouwde hidden-gedrag volledig. Een
"gesloten" popover (`hidden` attribuut wél aanwezig) bleef gewoon zichtbaar.

**Waarom dit niet in de sessie zelf ontdekt werd**: de verificatie tijdens
het bouwen checkte `popover.hidden` (de JS-property, reflecteert alleen of
het HTML-attribuut aanwezig is) en `getComputedStyle(...).display` bleek
destijds NIET gecheckt te zijn voor de default/gesloten staat — alleen voor
de OPEN staat (na een klik). Screenshots werkten niet in de gebruikte
test-omgeving (zie de rAF-bug en de kleurstrategie-bevinding eerder deze
sessie, zelfde niet-composerend-tabblad-beperking), dus een puur-visuele
controle was ook niet mogelijk geweest. Achteraf bezien had een simpele
`getComputedStyle(popover).display` check op de STARTSITUATIE (vóór ooit een
popover te openen) dit meteen gevonden — dat specifieke, makkelijke checkje
is over het hoofd gezien.

**Fix**: `.popover` (en `.popover-backdrop`) krijgen nu expliciet zelf
`display:none` als basisregel, met een eigen `:not([hidden])`-uitzondering
voor de zichtbare staat — leunt niet meer op de UA-stylesheet voor het
hidden-gedrag, dus geen specificiteitsstrijd meer mogelijk.

**Herverifieerd, dit keer met de juiste check**: `getComputedStyle(el).display`
voor alle 7 popovers in de default/gesloten staat (allemaal `none`,
bevestigd) én tijdens het schakelen tussen popovers (openen van Club sluit
Bron correct, `display` gaat naar `none`/`flex` zoals het hoort) én bij een
backdrop-klik (alles sluit, `display:none`). Gepusht als vervolgcommit op
dezelfde branch.

**Les**: bij UI-elementen die op het `hidden`-attribuut leunen, altijd
expliciet `display:none` als eigen basisregel zetten i.p.v. te vertrouwen
op de user-agent-stylesheet — met name zodra er ook een class-gebaseerde
`display`-regel voor hetzelfde element bestaat (die wint dan altijd, ook al
lijkt `hidden` in de HTML-broncode/JS-property prima aanwezig).

## 2026-08-18 — Sorteren-popover leeg bij Sport-modus (gemeld door Michiel)

Na de popover-fix meldde Michiel dat de Sorteren-popover bij Sport-modus
leeg bleef. Klopte: `setMode()` toonde het `uitjes-sort`-blok alleen bij
`m==='uitjes'` en het `expo-filters`-blok alleen bij `m==='exposities'` —
voor Sport-modus werd dus geen van beide getoond. De onderliggende
sorteerlogica (op datum/afstand, werkt generiek op `.month-section`-
kinderen) is niet mode-specifiek en werkt net zo goed voor sportwedstrijden
als voor uitjes. Fix: `uitjes-sort` toont nu bij zowel `uitjes` als `sport`;
het label is generiek "Sorteren" geworden (was "Sorteren (Uitjes)").
Geverifieerd via `getComputedStyle(...).display` in beide modi + een
functionele sorteer-test op sportwedstrijden (afstand-sortering correct
oplopend).


## 2026-08-18 — Derde Claude Design-ronde (HTML/CSS/JS-analyse, geen live klik-test)

Michiel vroeg Claude Design nogmaals om feedback op de branch-preview. Ditmaal
kon Claude Design de site niet als screenshot bekijken (cross-origin) en
deed dus een statische analyse van de opgehaalde HTML/CSS/JS -- vond zo
precies het soort bug dat mijn eigen (wel-interactieve, maar niet-volledige)
klik-tests hadden moeten vinden en niet vonden.

**🔴 Blokkerende bug, bevestigd**: het hele "Wanneer"-filter deed niets.
Bij de cluster-5-toolbar-herbouw is de wrapper-div hernoemd van
`id="uitjes-datum"` naar `id="popover-when"`, maar 6 JS-referenties (event-
listeners, de token-render-functie) wezen nog naar de oude id
`#uitjes-datum` -- die matcht niets meer, dus er werden nul click-handlers
gebonden op de 5 preset-knoppen. Klikken op Vandaag/Dit weekend/Deze week/
Deze maand deed zichtbaar niets.

**Waarom mijn eigen verificatie dit miste**: bij het testen van cluster 5
heb ik wél getest dat de Wanneer-POPOVER open/dicht ging (via `tb-when`),
maar nooit de knoppen ERIN daadwerkelijk aangeklikt na de HTML-herbouw --
die test was in cluster 2 wel gedaan, maar niet herhaald na de rename in
cluster 5. Een grep-achtige statische analyse (zoals Claude Design nu deed)
vindt zo'n dode-selector-bug feilloos; een interactieve test mist 'm zodra
je toevallig niet exact het geraakte element aanklikt. Les: na een
structurele HTML-rename altijd opnieuw ELK element in de nieuwe structuur
aanklikken, niet aannemen dat een eerdere test (vóór de rename) nog geldt.

**Fix**: alle 6 `#uitjes-datum` → `#popover-when`. Herverifieerd door
ditmaal ECHT alle 5 preset-knoppen aan te klikken en de resulterende
`selWhenFrom`/`selWhenTo`/actieve-knop-state te controleren (niet alleen de
popover open/dicht-status).

**Twee kleinere regressies uit dezelfde herbouw, ook bevestigd en gefixt**:
- `initAriaPressed()` scande `.mode-toggle,.filters` -- maar de meeste
  popovers (provincie, genre, bron, sport, club, wanneer) hebben geen
  `.filters`-klasse meer sinds cluster 5 (alleen de 2 blokken binnen de
  Sorteren-popover behielden 'm toevallig). Scan uitgebreid met `.popover`.
- `renderActiveFilters()`'s when-token verscheen niet -- zelfde
  `#uitjes-datum`-oorzaak, vanzelf mee opgelost.

**Nieuwe, kleinere bugs uit dit rapport, ook bevestigd en gefixt**:
- "Alle" zag er niet actief uit bij Wanneer en Sorteren, en Datum/Afstand
  zagen er allebei "uit" uit. Oorzaak: de donkere/blauwe actief-stijlen
  waren alleen gedefinieerd voor `data-src`/`data-genre`/`data-prov`/
  `data-sport`/`data-club` -- `data-when` en `data-usort` (nieuw in cluster
  2, geen bestaand patroon om per ongeluk mee te liften) hadden nooit een
  eigen regel gekregen. Toegevoegd: `[data-when="all"].active` bij de
  donkere-groep, `[data-when]:not([data-when="all"]).active` en
  `[data-usort].active` bij de blauwe-groep.
- Adresveld en status spraken elkaar tegen: getypte tekst deed niets tot
  een expliciete Enter/klik op Zoek, terwijl de status eronder het oude
  punt bleef tonen. `blur`-event toegevoegd naast het al-bestaande Enter-
  gedrag (Enter werkte al, alleen blur ontbrak).
- `#dist-label` ("Alle afstanden"/"≤ N km") was nog blauw gestyled uit de
  tijd dat het klikbaar was (cluster 3 verving dat door segmented buttons,
  maar de kleur bleef per ongeluk staan) -- nu `var(--muted)`, een puur
  statuslabel zonder link-uitstraling.
- Statusregel toonde altijd "Toont X van {{TOTAL}}" met een gecombineerde
  uitjes+sport+expo-teller, ongeacht de actieve modus -- klopte in
  Uitjes-modus nooit met "Toont alle" omdat sport/expo ook meetelden in
  TOTAL. Nu drie aparte per-modus-totalen (`TOTAL_UITJES`/`TOTAL_SPORT`/
  `TOTAL_EXPO`, serverside berekend) en een passend zelfstandig naamwoord
  per modus ("uitjes"/"wedstrijden"/"exposities").

**Bug tijdens het bouwen van de blur-fix**: per ongeluk een Python-stijl
`#`-commentaar getypt i.p.v. JS `//` in een nieuw stuk JS -- dit had een
echte browser-syntaxfout gegeven (`ast.parse()` valideert alleen de
PYTHON-kant van het bestand, niet de JS-string-inhoud erin, dus dit soort
fout wordt nooit door de Python-syntaxcheck gevangen). Gevonden en gefixt
vóór het regenereren/testen, dit keer bewust een losse `read_console_messages`
-check gedaan na elke wijziging om dit soort dingen niet nogmaals te missen.

**Nog open, bewust nog niet gebouwd** (grotere/subjectieve voorstellen uit
hetzelfde rapport, wachten op Michiels prioritering): kaart-layout-
herstructurering (`main{{max-width:1000px}}`, badges dichter bij de titel,
dag-groepering i.p.v. datum-herhaling per rij) -- door Claude Design zelf
als "het grootste visuele probleem" bestempeld; URL-state-uitbreiding
(when/sport/club/gender/sort + adres/coördinaten i.p.v. alleen een kale
afstand-getal); localStorage-persistentie (adres, laatste modus);
zoek-normalisatie (diakrieten-folding, meerdere-woorden-AND-split);
actieknoppen in de lege-staat; mobiele toolbar-herindeling (zoekveld op
eigen regel, chips naar 44px); typografie (titel/body naar 15-16px,
`--muted`-contrast naar #6b6b6b).


## 2026-08-18 — Vierde ronde: clusters A/B/C/D uit het derde Claude Design-rapport gebouwd

Michiel koos "ja, graag" op alle 4 resterende clusters uit punt 19. Alles op
dezelfde branch, in volgorde B/C/D (klein/veilig) dan A (grootste).

### Cluster B — kleine fixes
- Chips in popovers naar 44px (was 36px, alleen de toolbar-knoppen zelf
  waren al 44px, niet de chips erin).
- `body` 14px→15px, titel 0.95rem→1rem (16px) — titel is weer duidelijk het
  sterkste element op de kaart.
- `--muted` #757575→#6b6b6b (was 4,4:1 op de achtergrondkleur `--bg`
  #f9f9f9, net onder de 4,5 die kleine tekst nodig heeft voor WCAG AA).
- Lege-staat-melding krijgt nu directe actieknoppen ("Alle afstanden" /
  "Wis filters") i.p.v. alleen tekst.

### Cluster C — URL-state compleet, localStorage, zoek-normalisatie
- `syncURL()`/`restoreFromURL()` volledig herbouwd: `when`/`sport`/`club`/
  `gender`/`usort`/`esort` + `lat`/`lon` toegevoegd (was alleen
  `mode`/`prov`/`d`/`q`/`genre`/`src`). Een gedeelde `d=25`-link betekende
  bij de ontvanger eerder iets anders omdat het middelpunt niet meeging —
  nu wél, via `lat`/`lon` (bewust NIET een geocode-aanroep op basis van een
  `addr`-param, dat zou de init-flow async maken; lat/lon zijn al bekende
  getallen op het moment van opslaan, dus synchroon te herstellen).
- localStorage voor adres+coördinaten+modus. URL-params winnen altijd van
  localStorage (een gedeelde link mag niet stilzwijgend overschreven worden
  door iemands eigen eerder-opgeslagen voorkeur) — dit was in de eerste
  cluster-2-bouwronde bewust uitgesteld vanwege de async-geocode-zorg; nu
  omzeild door lat/lon i.p.v. het adres zelf te bewaren.
- Zoeken: nieuwe `fold_diacritics()` (Python, `unicodedata.normalize`)
  gebruikt bij het bouwen van `data-search`, en een JS-equivalent
  (`String.prototype.normalize('NFD')`) op de getypte term — "zummerbuhne"
  vindt nu "Zummerbühne". Plus meerdere-woorden-AND i.p.v. een letterlijke
  substring-match ("dorpshuis annen" faalde eerder als de titel-tekst niet
  toevallig exact die woordvolgorde had).

### Cluster D — mobiele toolbar
- Zoekveld krijgt op mobiel een eigen volle regel; alleen de knoppen-rij
  (nieuwe `.toolbar-buttons`-wrapper) scrollt nog horizontaal. Was: het
  hele `.toolbar`-blok inclusief het 70vw-brede zoekveld deelde één
  scrollende rij, wat de knoppen grotendeels uit beeld duwde.

### Cluster A — kaart-layout-herstructurering (grootste, laatste)
Door Claude Design zelf "het grootste visuele probleem" genoemd: op brede
schermen stond de badge-kolom (`70px 1fr auto`-grid) tot ~2000px van de
titel af, en de datum herhaalde zich op elke rij ("ma 17 aug" tien keer
onder elkaar).
- `main{{max-width:1000px;margin:0 auto}}` — leeslijst i.p.v. een
  volle-breedte-tabel.
- Kaart vereenvoudigd: geen aparte datum- of badge-kolom meer. Genre-badge
  verhuisd naar direct achter de titel (`.event-title{{display:flex}}`).
  Bron-badge (tekst) volledig weggehaald — de kaart-linkerrandkleur was al
  de bron-indicator, twee keer dezelfde info was overbodig (Claude Design:
  "één van de twee is genoeg").
- Nieuwe dag-groepering: events per maand ook per DAG gegroepeerd
  (`itertools.groupby` op `e['date']`, de lijst is al datum-gesorteerd dus
  geen aparte sortering nodig) onder een `<h3 class="day-header">Maandag 17
  augustus</h3>`-kop — vervangt de datum-per-rij. Voor MEERDAAGSE events
  (start≠einddatum) blijft een klein inline datumbereik-label naast de
  titel staan (`vr 21 t/m zo 23 aug`), want de dag-kop alleen zou anders de
  indruk wekken dat het een eendaags event is; het event verschijnt onder
  zijn STARTdag, niet onder elke dag die het beslaat.
- `expo_card_html()` (Exposities) bewust NIET aangeraakt — die had zijn
  eigen 2-koloms-grid-layout via de (nu vereenvoudigde) basis-`.event`-regel
  geërfd; expliciet `display:grid` teruggezet op `.event.expo-item` zodat
  dat niet stilzwijgend meebrak.
- Sorteren-op-afstand (cluster 2) werkte op `.month-section`-kinderen
  direct; nu events een laag dieper genest zitten (binnen `.day-group`) is
  de sorteerlogica verplaatst naar per-dag-groep sorteren i.p.v. kaarten
  fysiek naar een andere dag te verplaatsen (zou misleidend zijn — een kaart
  onder een dag-kop waar het event niet is).
- `apply()`'s hidden-logica uitgebreid: naast lege maand-secties nu ook lege
  dag-groepen verbergen (anders een dag-kop zonder events eronder na een
  filter).

**Geverifieerd** via de lokale `http.server`-preview: dag-groepering en
inline-datumbereik correct in de output, filtering verbergt lege
dag-groepen correct (243 van 336 bij een Jazz-filter), sorteren-op-afstand
werkt correct binnen een dag-groep, `main` is echt 1000px gecentreerd,
Exposities-modus (2-koloms-grid) ongewijzigd functioneel, mobiele
`.event`-weergave (nu overal gewoon `display:block`, geen aparte
mobiel-specifieke override meer nodig sinds de kolommen sowieso weg zijn),
geen console-errors.

**Twee losse schoonheidsfoutjes tijdens Cluster C gevonden en gefixt**
(cosmetisch, geen functionele impact): een `\u0300-\u036f`-Unicode-escape
raakte tijdens het patchen gemangeld tot letterlijke combinerende tekens in
de bron, en een niet-verdubbelde `\s` in een geneste JS-regex-binnen-
Python-string gaf een `SyntaxWarning` bij het parsen van `gen_uitjes.py`
(werkte functioneel toch correct, maar opgeschoond voor leesbaarheid en om
een `python -W error`-check schoon te houden).

## 2026-08-18 — SPOT Groningen: Stadspark-events tonen nu specifieke locatie

Michiel meldde dat "Jubileum Concert Stadspark – Noordpool Orkest & Friends"
op de site "Spot Groningen" toonde, terwijl de titel zelf al "Stadspark"
noemt. SPOT tagt buiten-events op het Stadspark (de jaarlijkse zomerreeks)
zelf niet met een specifiek `data-location`-gebouw (viel terug op `elders`),
dus onze scraper viel terecht terug op de generieke fallback.

**Fix**: `scrape_spotgroningen.py`'s `parse_block()` gebruikt nu "Stadspark,
Groningen" als venue zodra `data-location` generiek is EN de titel zelf
"stadspark" bevat (case-insensitive) — 2 events in de dataset matchten dit
patroon (1 al verlopen, niet meer op de live pagina om te herscrapen).

**Geen handmatige DB-opschoning nodig ditmaal** — dankzij de eerdere
structurele `insert_event()`-fix (2026-08-17, veld-voor-veld merge bij een
same-source-herscrape) kwam de correctie er bij de eerstvolgende live
scrape gewoon doorheen, precies het scenario waar die fix voor gebouwd is.
Geverifieerd: DB-rij bijgewerkt, export/generate herdraaid, "Stadspark,
Groningen" bevestigd in de gegenereerde HTML.

## 2026-08-18 — "De puntjes": lege venue-rij + Bron-popover afstandstoggle

Na het mergen van `design-review-clusters-1-4` naar `main` vroeg Michiel om
de twee bewust-niet-gebouwde punten uit overleg.md punt 19 alsnog op te
pakken.

**1. Lege venue-rij** (was: "datakwaliteit, geen codefix"). Bij nader
onderzoek bleek het wél netjes met een codefix op te lossen: 1308 events
(concertgebouw, 013, rotown, paradiso, paard, melkweg, ahoy, effenaar,
afaslive, dedoelen, gelredome) hebben geen `venue`/`city`-veld gevuld omdat
die bronnen zelf één vaste locatie zíjn — de scraper hoeft dat dan niet per
event te herhalen. Nieuwe `venue_display(e, src)`-helper in `gen_uitjes.py`:
venue > city > `SRC[src]`-label als laatste redmiddel (voor deze bronnen is
dat label al letterlijk de venue-naam, bv. "013 Tilburg", "Rotterdam Ahoy").
Toegepast in zowel `event_html()` als `expo_card_html()`, en in de
`data-search`-tekst zodat zoeken op "Melkweg" ook weer werkt voor die
events. Geverifieerd: 0 lege venue-rijen meer in de output; "Concertgebouw"
(499×), "Melkweg" (173×), "013 Tilburg" (128×), "Het Paard" (125×) tonen nu
correct.

**2. "Alleen bronnen binnen mijn afstand"-toggle** in de Bron-popover. Elke
bron-knop krijgt nu `data-lat`/`data-lon` (afgeleid uit het al bestaande
`VENUE_LOC`) zodra de bron een betrouwbaar 1-op-1 puntlocatie heeft.
Expositie-aggregators zonder vaste bron-locatie (kunstpuntgroningen,
uitzinnig — hun lat/lon zit per event, niet per bron) blijven bewust zonder
deze attributen; ze verschijnen toch niet in de (uitjes-)Bron-popover, maar
de guard (`!el.dataset.lat` → nooit verbergen) voorkomt sowieso dat de
toggle een bron onterecht wegfiltert wanneer we de afstand niet kennen.

Een nieuwe knop-toggle (`#src-dist-toggle`) in de popover herbergt de
bestaande `filterSrcList()`-logica (was een anonieme inline listener op
`#src-search`, nu een gedeelde functie zodat tekstzoek + afstandsfilter
elkaars `display:none` niet overschrijven). `filterSrcList()` wordt ook
opnieuw aangeroepen zodra `centerLat`/`centerLon` wijzigt (in
`updateDistances()`, dus na geocode/geolocatie/URL-restore/localStorage) en
zodra `maxDist` wijzigt (afstandsknoppen + custom-afstandveld) — anders zou
de toggle een oude afstand blijven gebruiken.

**Geverifieerd** via de lokale `http.server`-preview (JS-niveau, niet
screenshot — de headless testbrowser rendert hier geen frames): bij 50km
vanaf de standaardlocatie (Annen) verdwijnen melkweg/ahoy/013/
tivolivredenburg (allemaal >50km) en blijven vera/simplon/martiniplaza
(Groningen, binnen bereik) zichtbaar; toggle uit → alles weer zichtbaar;
combinatie met tekstzoek ("vera") werkt correct samen met de toggle;
actieve-knop-kleur (blauw, `#1565c0`) en `aria-pressed` werken; geen
console-errors op de live preview.
