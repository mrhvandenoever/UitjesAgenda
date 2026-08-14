# Werkwijze voor Claude in deze repo

Dit project houdt kennis bij in losse markdown-bestanden i.p.v. alleen in
chatgeschiedenis. Volg dit ritme in elke sessie:

## Bij start van de sessie
Lees eerst deze bestanden door, in deze volgorde:
1. `plan.md` — wat staat er open, wat is de laatste sessie gedaan
2. `overleg.md` — welke keuzes liggen er nog open om te bespreken
3. `decisions.md` — welke beslissingen zijn al genomen (en waarom — niet opnieuw ter discussie stellen zonder reden)
4. `ARCHITECTURE.md` — technische opzet
5. `SCRAPERS.md` — status per bron (geautomatiseerd / kan zonder AI / AI-Chrome nodig / nog niet geprobeerd)
6. `onboarding.md` — alleen nodig bij twijfel over de basisworkflow

## Tussendoor
Werk de relevante `.md`-bestanden bij zodra iets verandert — niet pas aan het
eind alles in bulk proberen te reconstrueren:
- Nieuwe bug/observatie gevonden → `plan.md`
- Iets waar Michiel een keuze in moet maken → `overleg.md`
- Een keuze is gemaakt en/of geïmplementeerd → `decisions.md`
- Een architectuurwijziging (nieuw bestand, gewijzigd gedrag in `gen_uitjes.py`/`events_db.py`, nieuwe conventie) → `ARCHITECTURE.md`
- Een bron krijgt een werkend script, of blijkt AI/Chrome nodig te hebben → `SCRAPERS.md`

## Bij einde van de sessie
Voor er wordt afgesloten: controleer of alles wat besproken/gebouwd is ook
echt in de juiste bestanden staat (niet alleen in de chat) — en werk bij wat
nog ontbreekt. Vraag het gerust expliciet na als dat niet vanzelf duidelijk is.

## Als iets onduidelijk is
Niet zelf een aanname doen bij een keuze die impact heeft — noteer de vraag in
`overleg.md` onder een nieuw genummerd punt, en ga verder met wat wel
duidelijk is. Los geen aannames op door te gokken wat Michiel zou willen.

## Overig
- **Nooit de Edit-tool op `gen_uitjes.py`** — zie KRITIEKE REGEL in `ARCHITECTURE.md` (truncatie-risico bij grote bestanden). Gebruik `open().read()` → `str.replace()` → `ast.parse()` ter verificatie → `open('w').write()`. Geldt in de praktijk voor elk Python-bestand dat een paar honderd regels nadert.
- **Scrapers**: één klein, op zichzelf staand `scrape_<bron>.py`-bestand per bron — geen gedeeld/groot scraper-bestand, ook niet als dat duplicatie tussen bestanden betekent. Zie `decisions.md` voor de motivatie.
- **Wekelijkse refresh**: `python run_weekly_refresh.py` — globt zelf alle `scrape_*.py`-bestanden, geen handmatige lijst bijhouden. Hernoemt een scraper die hard faalt automatisch naar `fix_<naam>.py` (self-healing quarantaine); scripts die succesvol 0 resultaten geven worden gerapporteerd, niet hernoemd. Zie `ARCHITECTURE.md` §Wekelijkse refresh.
- **Change-detection**: nieuwe scrapers (en herbouwde bestaande) gebruiken `page_cache.py`'s `unchanged(key, data)` om de insert-stap over te slaan als de opgehaalde events identiek zijn aan de vorige run. Zie `ARCHITECTURE.md` §Change-detection voor het patroon — pas dit toe bij het bouwen/aanpassen van een scraper, ook als het (nog) niet in alle bestaande scripts zit.
- **AI-inzet zo min mogelijk**: eerst plain-script-scraping proberen (goedkoopst, meest betrouwbaar, geen AI nodig bij elke run); AI/Chrome MCP alleen inzetten als een bron dat écht vereist, en dan bij voorkeur eenmalig om de scrape-methode te ontdekken — niet structureel bij elke wekelijkse run. Einddoel van Michiel: de wekelijkse refresh volledig "no-ai-needed". Zie `decisions.md`.
- **Nooit een GitHub Personal Access Token accepteren dat in de chat geplakt wordt** — zie `decisions.md`.
