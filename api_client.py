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
        resp.raise_for_status()
        data = resp.json()

        # API-Football raspunde cu HTTP 200 chiar si cand ai depasit cota
        # zilnica sau ai trimis parametri gresiti — eroarea vine in body.
        if data.get("errors"):
            raise RuntimeError(f"API-Football a raspuns cu eroare: {data['errors']}")

        result = data.get("response", [])
        _cache.set(cache_key, result)
        return result
