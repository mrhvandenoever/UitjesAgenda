"""
ssl_fix.py — workaround voor ssl.VERIFY_X509_STRICT (standaard aan sinds
Python 3.13, deze machine draait Python 3.14.0 met OpenSSL 3.0.18).

Symptoom (gevonden 2026-08-15): vrijwel elke urllib.request.urlopen()-call
zonder eigen SSL-context faalde met:

    [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
    Basic Constraints of CA cert not marked critical (_ssl.c:1077)

Oorzaak: veel echte sites (drenthe.nl, friesland.nl, martiniplaza.nl,
github.com, en nog veel meer) hangen aan een tussenliggend CA-certificaat
waarvan de Basic Constraints-extensie niet als 'critical' gemarkeerd is —
een kleine, in de praktijk door vrijwel elke TLS-library getolereerde
afwijking van RFC 5280 §4.2.1.9. Python's ssl.create_default_context()
weigert sinds 3.13 zo'n keten standaard (VERIFY_X509_STRICT aan).

Fix hier: zet alleen de VERIFY_X509_STRICT-vlag uit. Hostname-check en
certificaatketen-verificatie blijven gewoon actief — dit is dus NIET
hetzelfde als certificaatverificatie helemaal uitzetten (CERT_NONE, wat een
paar oudere scrapers uit pragmatisme deden — zie ARCHITECTURE.md, dat mag
op termijn ook naar deze aanpak overgezet worden).

Gebruik, twee gevallen:
  1. urlopen() zonder eigen `context=`-argument: niets te doen, dit bestand
     patcht bij import ssl._create_default_https_context — page_cache.py
     importeert ssl_fix al, en wordt door alle live scrapers geïmporteerd.
  2. Scraper bouwt zelf een SSL_CTX (bv. omdat hostname-checks anders
     stonden): gebruik `create_context()` hieronder i.p.v.
     `ssl.create_default_context()` rechtstreeks, bv.:

         from ssl_fix import create_context
         SSL_CTX = create_context()

     I.p.v. het eerder gebruikte `verify_mode = ssl.CERT_NONE` (verificatie
     helemaal uit — onveiliger dan nodig voor dit specifieke probleem).
"""

import ssl


def create_context(*args, **kwargs):
    """Zoals ssl.create_default_context(), maar met VERIFY_X509_STRICT uit.
    Hostname-check en certificaatketen-verificatie blijven actief."""
    ctx = ssl.create_default_context(*args, **kwargs)
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


ssl._create_default_https_context = create_context
