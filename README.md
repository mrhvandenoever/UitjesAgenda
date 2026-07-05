# UitjesAgenda

Onafhankelijke evenementenagenda voor Noord-Nederland en omgeving. Toont uitjes (theater, muziek, expo, etc.) en sportwedstrijden, filterbaar op genre, bron, provincie en afstand.

**Live:** https://uitjesagenda.pages.dev

## Hoe het werkt

`python3 gen_uitjes.py` → `index.html`  
Cloudflare Pages bouwt automatisch bij elke push naar `main`.

## Bestanden

- `gen_uitjes.py` — HTML-generator (leest JSON, schrijft index.html)
- `events_categorized.json` — alle events (brondata)
- `scraping_recipes.json` — scraping-methode per bron
- `ARCHITECTURE.md` — technische documentatie, definities, werkwijze

## Technische details

Zie [ARCHITECTURE.md](ARCHITECTURE.md).

## Contact

Rechthebbenden / aanpassingen: chielemans@hotmail.com
