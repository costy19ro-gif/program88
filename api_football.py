"""
Client pentru API-Football (api-sports.io) — sursa PRINCIPALA de date reale
=============================================================================
Foloseste planul de pe dashboard.api-football.com (acelasi cont/cheie
folosit deja: b5b1816fbcf28d2f3567bf691e18f86a).

Header necesar: x-apisports-key (NU x-rapidapi-key — aici apelam direct
api-sports.io, nu prin platforma RapidAPI).

Cheia se citeste DOAR din st.secrets["APISPORTS_KEY"] sau din variabila
de mediu APISPORTS_KEY, niciodata hardcodata in fisier.

Endpoint-urile de mai jos sunt cele documentate oficial:
  GET /fixtures?date=YYYY-MM-DD             -> meciurile dintr-o zi
  GET /fixtures?team={id}&last={n}&status=  -> ultimele n meciuri TERMINATE
  GET /predictions?fixture={id}             -> predictia proprie API-Football
                                                (bonus, doar comparatie)
"""

from __future__ import annotations
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import requests

from pipeline import MeciIstoric

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path(".cache_apifootball")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 6 * 3600  # 6 ore — planul gratuit are cota zilnica limitata


def _get_key() -> str:
    """Citeste cheia din st.secrets (Streamlit Cloud) sau din mediu (local)."""
    try:
        import streamlit as st
        if "APISPORTS_KEY" in st.secrets:
            return st.secrets["APISPORTS_KEY"]
    except Exception:
        pass

    key = os.environ.get("APISPORTS_KEY")
    if not key:
        raise RuntimeError(
            "Nu am gasit cheia API-Football. Seteaz-o ca variabila de mediu "
            "APISPORTS_KEY, sau adaug-o in .streamlit/secrets.toml ca "
            "APISPORTS_KEY = \"...\" (pe Streamlit Cloud, in Settings > Secrets)."
        )
    return key


def _headers() -> dict:
    return {"x-apisports-key": _get_key()}


def _get_cached(path: str, params: dict | None = None) -> dict:
    """GET cu cache pe disc, ca sa nu ardem cereri degeaba la reincarcari repetate."""
    cache_key = path.replace("/", "_") + "_" + json.dumps(params or {}, sort_keys=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return json.loads(cache_file.read_text())

    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errors"):
        raise RuntimeError(f"API-Football a returnat o eroare: {data['errors']}")

    cache_file.write_text(json.dumps(data))
    return data


def meciuri_azi() -> list[dict]:
    """
    Meciurile programate azi, standardizate in formatul folosit de app.py:
    homeTeam/awayTeam/tournament + fixture_id pentru apeluri ulterioare
    (istoric, predictie oficiala).
    """
    astazi = date.today().strftime("%Y-%m-%d")
    raspuns = _get_cached("/fixtures", {"date": astazi})

    meciuri = []
    for item in raspuns.get("response", []):
        meciuri.append({
            "fixture_id": item["fixture"]["id"],
            "homeTeam": {"id": item["teams"]["home"]["id"], "name": item["teams"]["home"]["name"]},
            "awayTeam": {"id": item["teams"]["away"]["id"], "name": item["teams"]["away"]["name"]},
            "tournament": {"name": item["league"]["name"]},
        })
    return meciuri


def istoric_echipa(team_id: int, n_meciuri: int = 20) -> list[MeciIstoric]:
    """Ultimele n_meciuri jucate si TERMINATE ale unei echipe (toate competitiile)."""
    raspuns = _get_cached("/fixtures", {
        "team": team_id,
        "last": n_meciuri,
        "status": "FT-AET-PEN",  # doar meciuri complet terminate
    })

    meciuri: list[MeciIstoric] = []
    for item in raspuns.get("response", []):
        home_id = item["teams"]["home"]["id"]
        este_gazda = home_id == team_id

        gh = item["goals"]["home"]
        ga = item["goals"]["away"]
        if gh is None or ga is None:
            continue

        ht = item.get("score", {}).get("halftime", {}) or {}
        ht_h, ht_a = ht.get("home"), ht.get("away")

        marcate = gh if este_gazda else ga
        primite = ga if este_gazda else gh
        marcate_pauza = ht_h if este_gazda else ht_a
        primite_pauza = ht_a if este_gazda else ht_h

        data_meci = datetime.fromisoformat(item["fixture"]["date"]).date()

        meciuri.append(MeciIstoric(
            data=data_meci,
            goluri_marcate=marcate,
            goluri_primite=primite,
            goluri_marcate_pauza=marcate_pauza,
            goluri_primite_pauza=primite_pauza,
        ))

    return meciuri


def predictie_oficiala(fixture_id: int) -> dict | None:
    """Bonus: predictia proprie API-Football pentru un meci (doar comparatie, nu inlocuieste pipeline-ul)."""
    try:
        raspuns = _get_cached("/predictions", {"fixture": fixture_id})
        rez = raspuns.get("response", [])
        return rez[0] if rez else None
    except Exception:
        return None
