"""
Client HTTP generic pentru API-Football, rutat prin gateway-ul RapidAPI.

Acest fisier lipsea din proiectul original — api_football.py facea
`from api_client import RapidAPIClient`, dar fisierul nu exista pe disc,
deci aplicatia pica la primul import, inainte sa apuce sa faca vreun apel.

Cheia se ia, in ordine:
1. st.secrets["RAPIDAPI_KEY"]           (recomandat pe Streamlit Cloud)
2. variabila de mediu RAPIDAPI_KEY       (recomandat local)
"""

from __future__ import annotations

import os
import requests

from cache import SimpleCache

HOST = "api-football-v1.p.rapidapi.com"
BASE_URL = f"https://{HOST}/v3"

# cache pe disc/memorie, 6 ore — vezi README, planurile gratuite au cota mica
_cache = SimpleCache(ttl=6 * 3600)


def _get_key() -> str | None:
    try:
        import streamlit as st
        if "RAPIDAPI_KEY" in st.secrets:
            return st.secrets["RAPIDAPI_KEY"]
    except Exception:
        pass
    return os.environ.get("RAPIDAPI_KEY")


class RapidAPIClient:
    """Wrapper subtire peste requests, cu headerele corecte pt. gateway-ul RapidAPI."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or _get_key()
        if not self.api_key:
            raise RuntimeError(
                "Lipseste RAPIDAPI_KEY. Adauga-l in .streamlit/secrets.toml "
                '(RAPIDAPI_KEY = "cheia_ta") sau ca variabila de mediu:\n'
                "  export RAPIDAPI_KEY=cheia_ta"
            )
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": HOST,
        }

    def get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        cache_key = f"{endpoint}?{sorted((params or {}).items())}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params or {}, timeout=15)

        # Prindem eroarea HTTP noi insine si aratam cauza reala (fara cheie),
        # in loc sa lasam exceptia bruta sa urce pana la Streamlit — care
        # redacteaza mesajul original ("This app has encountered an error...")
        # si nu mai vezi de fapt DE CE a picat cererea.
        if resp.status_code == 401:
            raise RuntimeError(
                "RapidAPI a raspuns 401 Unauthorized — cheia RAPIDAPI_KEY este "
                "gresita sau nu e trimisa corect. Verifica in Settings -> Secrets."
            )
        if resp.status_code == 403:
            raise RuntimeError(
                "RapidAPI a raspuns 403 Forbidden — cel mai probabil cheia ta nu "
                "e abonata la API-ul 'API-Football' de pe RapidAPI (fiecare API "
                "necesita abonare separata, chiar daca e gratuit). Verifica pe "
                "rapidapi.com, la pagina API-Football, butonul 'Subscribe'."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "RapidAPI a raspuns 429 Too Many Requests — ai depasit cota "
                "zilnica/lunara de pe planul curent. Asteapta resetarea sau "
                "verifica planul din dashboard-ul RapidAPI."
            )
        if not resp.ok:
            # orice alt cod neasteptat — aratam corpul raspunsului (scurtat),
            # care de obicei contine motivul exact
            raise RuntimeError(
                f"RapidAPI a raspuns cu eroare HTTP {resp.status_code}: {resp.text[:300]}"
            )

        data = resp.json()

        # API-Football raspunde cu HTTP 200 chiar si cand ai depasit cota
        # zilnica sau ai trimis parametri gresiti — eroarea vine in body.
        if data.get("errors"):
            raise RuntimeError(f"API-Football a raspuns cu eroare: {data['errors']}")

        result = data.get("response", [])
        _cache.set(cache_key, result)
        return result
