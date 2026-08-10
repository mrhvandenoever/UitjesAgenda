# Onboarding — voor wie UitjesAgenda gaat beheren

Praktische gids om dit project over te nemen of mee te draaien. Voor de technische opzet zie [ARCHITECTURE.md](ARCHITECTURE.md); voor de tool zelf zie [README.md](README.md).

## Wat je nodig hebt

- **GitHub-toegang**: repo is [mrhvandenoever/UitjesAgenda](https://github.com/mrhvandenoever/UitjesAgenda). Push-rechten nodig om updates live te zetten.
- **Cloudflare-toegang**: account met het Pages-project `uitjesagenda` (dash.cloudflare.com → Workers & Pages). Alleen nodig om build-instellingen of domeinen te wijzigen — de gewone workflow (push → auto-build) heeft dit niet nodig.
- **Python 3** lokaal geïnstalleerd (voor de scrapers en `gen_uitjes.py`). `requirements.txt` is leeg — alleen stdlib.
- **Git** lokaal geïnstalleerd.

## De wekelijkse cyclus

Elke maandag (gepland 08:04) horen de volgende stappen te draaien vanaf een lokale clone:

```
cd C:\dev\uitjesagenda
python scrape_drenthe.py
python scrape_visitgroningen.py
python scrape_friesland.py
python scrape_handmatig.py
python scrape_naarzuidlaren.py
python events_db.py export
python gen_uitjes.py
git add -A
git commit -m "auto refresh"
git push
```

Na de push bouwt Cloudflare Pages automatisch (`python3 gen_uitjes.py`), live binnen ~30–60 seconden. **Cloudflare draait zelf nooit de scrapers** — die moeten altijd lokaal.

Dit liep via een Cowork scheduled task op een vaste pc. Als die pc niet beschikbaar is, staat de site stil totdat iemand de stappen hierboven handmatig (of vanaf een andere machine) draait.

## Zelf een keer handmatig draaien

Zie de stappen hierboven. Controleer na `gen_uitjes.py` altijd eerst `git diff` / `git status` voordat je commit+pusht — dat is de live site.

## Als er iets misgaat

- **`gen_uitjes.py` corrupt na een edit**: bestand is ~661 regels; editors die op regel ~500 afkappen breken het. Altijd via `open().read()` → `str.replace()` → `open('w').write()`, en verifiëren met `ast.parse()` voor je commit.
- **`events_categorized.json` corrupt**: zelfde aanpak, verifiëren met `json.load()`.
- **Scraper geeft geen/rare data**: check `scraping_recipes.json` voor de laatst bekende werkende methode per bron (`render_type`, `scrape_code`, `last_verified`).
- **Git lock-bestanden vastgelopen** (`.git/index.lock`, `.git/HEAD.lock`): zie de "Git-quirks" sectie in ARCHITECTURE.md.

## Nieuwe bron of sportclub toevoegen

Stappenplan staat in ARCHITECTURE.md onder "Nieuwe bron toevoegen" / "Sport club toevoegen".

## Contact

Rechthebbenden / aanpassingen: chielemans@hotmail.com
