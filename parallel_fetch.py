"""
parallel_fetch.py — gedeelde helper om meerdere pagina's gelijktijdig op te
halen i.p.v. sequentieel (Niveau B van overleg.md punt 2 / decisions.md
2026-08-16).

Bevat GEEN scraping- of parse-logica — dat blijft per bron in het eigen
scrape_<bron>.py-bestand (zelfde afspraak als ssl_fix.py/page_cache.py/
ticketmaster.py, zie overleg.md punt 8). Dit bestand doet precies één ding:
een lijst URL's (of pagina-nummers) gelijktijdig ophalen via een door de
scraper zelf meegegeven fetch-functie, met een lage default-concurrency om
geen rate-limiting te triggeren op sites die nu één sequentiële request
tegelijk gewend zijn.

Twee gebruikspatronen, zie ARCHITECTURE.md §Parallelle scrapers:
  1. Bekend aantal pagina's vooraf (bv. friesland.nl, kielzog.nl):
     gebruik fetch_many() direct op de volledige lijst.
  2. Aantal pagina's pas bekend terwijl je gaat (bv. drenthe.nl, die stopt
     zodra 2 pagina's op rij leeg zijn): gebruik fetch_batches(), die in
     kleine batches ophaalt en per batch een stop-conditie laat checken.
"""

from concurrent.futures import ThreadPoolExecutor

DEFAULT_MAX_WORKERS = 5


def fetch_many(items, fetch_fn, max_workers=DEFAULT_MAX_WORKERS):
    """
    Haalt `items` (URL's, pagina-nummers, wat de scraper's fetch_fn nodig
    heeft) gelijktijdig op. Retourneert een lijst even lang als `items`, in
    dezelfde volgorde, met (resultaat, None) bij succes of (None, exception)
    bij een fout — nooit een crash, zodat de scraper zelf per pagina kan
    beslissen wat te doen bij een fout (net als het bestaande try/except
    per pagina in de sequentiële versie).
    """
    def _one(item):
        try:
            return (fetch_fn(item), None)
        except Exception as e:
            return (None, e)

    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
        return list(ex.map(_one, items))


def fetch_batches(start, fetch_fn, should_stop_fn, batch_size=DEFAULT_MAX_WORKERS,
                   max_batches=20, stop_after_consecutive=1):
    """
    Voor scrapers die het aantal pagina's niet vooraf weten: haalt pagina's
    op in batches van `batch_size` tegelijk (i.p.v. één voor één), en stopt
    zodra `stop_after_consecutive` pagina's op rij het eind-signaal geven
    volgens `should_stop_fn(page, resultaat)`. Bounded: haalt bij de laatste
    batch mogelijk een paar pagina's te veel op (nooit meer dan
    batch_size-1 voorbij het echte einde) — bewuste afweging voor de
    snelheidswinst.

    LET OP (les uit de praktijk, drenthe.nl/visitgroningen.nl, 2026-08-16):
    kies het eind-signaal zorgvuldig. "0 events op deze pagina" lijkt een
    voor de hand liggend signaal, maar sommige sites geven bij een pagina
    ver voorbij het echte einde gewoon een fallback-pagina terug (bv. de
    laatste geldige pagina nogmaals) — dan is er NOOIT een lege pagina en
    haalt dit door tot `max_batches`. Het betrouwbare signaal was hier
    juist het ONTBREKEN van een "volgende pagina"-link in de HTML, wat wél
    meteen (stop_after_consecutive=1) optreedt bij de eerste pagina voorbij
    het echte einde — zie scrape_drenthe.py/scrape_visitgroningen.py.

    `start`: eerste pagina-nummer (bv. 1 of 2 als pagina 1 al apart is
    opgehaald voor een totaal-telling).
    `fetch_fn(page)`: haalt één pagina op, zelfde functie als voorheen in
    de sequentiële loop.
    `should_stop_fn(page, resultaat)`: True als déze pagina het eind-signaal
    geeft (bv. geen "volgende pagina"-link meer in de HTML).

    Retourneert een lijst van (page, resultaat_of_None, exception_of_None)
    tuples, in paginavolgorde, alleen voor de pagina's die daadwerkelijk
    opgehaald zijn (inclusief de laatste, mogelijk overtollige batch).
    """
    all_results = []
    page = start
    consecutive = 0

    for _ in range(max_batches):
        batch_pages = list(range(page, page + batch_size))
        fetched = fetch_many(batch_pages, fetch_fn, max_workers=batch_size)

        stop = False
        for p, (result, exc) in zip(batch_pages, fetched):
            all_results.append((p, result, exc))
            if exc is not None:
                continue
            if should_stop_fn(p, result):
                consecutive += 1
                if consecutive >= stop_after_consecutive:
                    stop = True
            else:
                consecutive = 0

        if stop:
            break
        page += batch_size

    return all_results
