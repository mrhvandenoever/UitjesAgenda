"""
secrets_local.py — leest secrets.local.json (API-keys e.d.), staat in
.gitignore en wordt nooit gecommit. Zie secrets.local.json.example voor
de verwachte vorm.

Gebruik in een scraper:

    from secrets_local import get_secret
    API_KEY = get_secret('ticketmaster_api_key')

Geeft een duidelijke foutmelding i.p.v. een cryptische KeyError als het
bestand ontbreekt of leeg is — handig omdat dit bestand per machine
lokaal aangemaakt moet worden (nooit in git, dus een verse clone heeft
het nog niet).
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(SCRIPT_DIR, 'secrets.local.json')


def get_secret(name: str) -> str:
    if not os.path.exists(SECRETS_PATH):
        raise RuntimeError(
            f"secrets.local.json ontbreekt. Kopieer secrets.local.json.example "
            f"naar secrets.local.json en vul '{name}' in."
        )
    with open(SECRETS_PATH, encoding='utf-8') as f:
        secrets = json.load(f)
    value = secrets.get(name, '').strip()
    if not value:
        raise RuntimeError(
            f"'{name}' staat niet (of leeg) in secrets.local.json — vul 'm eerst in."
        )
    return value
