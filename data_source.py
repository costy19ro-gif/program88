"""
Sursa de date reale — client API (SportAPI7 via RapidAPI)
===========================================================
Trage meciuri de azi + istoricul echipelor, cu cache pe disc ca sa nu
consumi degeaba din cota zilnica (100 cereri/zi pe planul gratuit
echivalent api-football; SportAPI7/RapidAPI are propriile limite de plan,
verifica in dashboard-ul tau exact cota disponibila).

Cheia API se citeste DOAR din variabila de mediu / st.secrets, niciodata
hardcodata in fisier.
"""

from __future__ import annotations
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from pipeline import MeciIstoric

BASE_URL = "https://sportapi7.p.rapidapi.com"
CACHE_DIR = Path(".cache_miliardarul")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 6 * 3600  # 6 ore — datele istorice nu se schimba des


def _headers() -> dict:
    api_key = os.environ.get("RAPIDAPI_KEY") or os.environ.get("SPORTAPI7_KEY")
    if not api_key:
        raise RuntimeError(
            "Nu am gasit cheia API. Seteaz-o ca variabila de mediu "
            "RAPIDAPI_KEY (sau in st.secrets['RAPIDAPI_KEY'] pentru Streamlit)."
        )
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "sportapi7.p.rapidapi.com",
    }


def _get_cached(path: str, params: dict | None = None) -> dict:
    """GET cu cache pe disc, ca sa nu ardem cereri degeaba la reincarcari."""
    cache_key = path.replace("/", "_") + "_" + json.dumps(params or {}, sort_keys=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return json.loads(cache_file.read_text())

    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    cache_file.write_text(json.dumps(data))
    return data


def meciuri_azi(sport: str = "football", timezone_offset: int = 0) -> list[dict]:
    """Returneaza toate meciurile de azi, grupate implicit pe toate categoriile."""
    astazi = date.today().strftime("%Y-%m-%d")
    categorii = _get_cached(f"/api/v1/sport/{sport}/{astazi}/{timezone_offset}/categories")

    toate_meciurile = []
    for cat in categorii.get("categories", []):
        cat_id = cat["category"]["id"]
        evenimente = _get_cached(f"/api/v1/category/{cat_id}/scheduled-events/{astazi}")
        toate_meciurile.extend(evenimente.get("events", []))
    return toate_meciurile


def istoric_echipa(team_id: int, n_meciuri: int = 20) -> list[MeciIstoric]:
    """
    Trage ultimele `n_meciuri` jucate de o echipa si le converteste in
    obiecte MeciIstoric (gata de pipeline).

    NOTA IMPORTANTA: endpoint-ul exact pentru istoricul unei echipe
    ("previous events") nu a fost confirmat explicit in documentatia
    primita — modelul uzual pentru API-uri de tip SofaScore este
    `/api/v1/team/{team_id}/events/last/{page}`. Verifica in dashboard-ul
    RapidAPI/documentatia exacta a planului tau si ajusteaza linia de mai
    jos daca raspunsul nu se potriveste.
    """
    meciuri: list[MeciIstoric] = []
    pagina = 0
    while len(meciuri) < n_meciuri:
        raspuns = _get_cached(f"/api/v1/team/{team_id}/events/last/{pagina}")
        evenimente = raspuns.get("events", [])
        if not evenimente:
            break

        for ev in evenimente:
            if ev.get("status", {}).get("type") != "finished":
                continue

            home_id = ev["homeTeam"]["id"]
            este_gazda = home_id == team_id

            scor_gazde = ev["homeScore"].get("current")
            scor_oaspeti = ev["awayScore"].get("current")
            scor_gazde_pauza = ev["homeScore"].get("period1")
            scor_oaspeti_pauza = ev["awayScore"].get("period1")

            if scor_gazde is None or scor_oaspeti is None:
                continue

            marcate = scor_gazde if este_gazda else scor_oaspeti
            primite = scor_oaspeti if este_gazda else scor_gazde
            marcate_pauza = scor_gazde_pauza if este_gazda else scor_oaspeti_pauza
            primite_pauza = scor_oaspeti_pauza if este_gazda else scor_gazde_pauza

            data_meci = datetime.fromtimestamp(ev["startTimestamp"]).date()

            meciuri.append(
                MeciIstoric(
                    data=data_meci,
                    goluri_marcate=marcate,
                    goluri_primite=primite,
                    goluri_marcate_pauza=marcate_pauza,
                    goluri_primite_pauza=primite_pauza,
                )
            )

        pagina += 1
        if pagina > 5:  # limita de siguranta, sa nu bata cereri la infinit
            break

    return meciuri[:n_meciuri]
