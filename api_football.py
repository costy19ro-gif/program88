"""
Sursa de date reale: "Free API Live Football Data" (RapidAPI, host
free-api-live-football-data.p.rapidapi.com) — inlocuieste API-Football
clasic (api-sports), care nu mai e disponibil in marketplace-ul RapidAPI.

Structura raspunsului la /football-get-matches-by-date (confirmata din
raspuns real, nu presupusa):

{
  "status": "success",
  "response": {
    "matches": [
      {
        "id": 4621624,
        "leagueId": 894202,
        "time": "06.11.2024 21:00",      # format DD.MM.YYYY HH:MM
        "home": {"id": ..., "name": ..., "longName": ..., "score": ...},
        "away": {"id": ..., "name": ..., "longName": ..., "score": ...},
        "status": {
          "utcTime": "2024-11-06T20:00:00.000Z",
          "finished": true, "started": true, "cancelled": false,
          "scoreStr": "1 - 3",
          "reason": {"short": "FT", "long": "Full-Time"},
        },
        "timeTS": 1730923200000           # epoch ms
      },
      ...
    ]
  }
}

Important: parametrul `date` la acest endpoint e in format YYYYMMDD
(ex. "20241107"), NU "YYYY-MM-DD" ca la API-Football clasic.

Nu exista (inca) un endpoint confirmat pentru "ultimele N meciuri ale unei
echipe" — vezi istoric_echipa() mai jos, care ridica explicit o eroare in
loc sa ghiceasca un format si sa arda cota gratuita.
"""

from __future__ import annotations

from datetime import date, datetime

from api_client import RapidAPIClient

_client: RapidAPIClient | None = None


def _get_client() -> RapidAPIClient:
    global _client
    if _client is None:
        _client = RapidAPIClient()
    return _client


def _parseaza_data_meci(time_str: str) -> date:
    """Converteste 'DD.MM.YYYY HH:MM' in date()."""
    return datetime.strptime(time_str, "%d.%m.%Y %H:%M").date()


def meciuri_pe_data(zi: date) -> list[dict]:
    """Meciurile programate/jucate intr-o zi anume."""
    raw = _get_client().get(
        "football-get-matches-by-date", {"date": zi.strftime("%Y%m%d")}
    )
    if raw.get("status") != "success":
        raise RuntimeError(f"API-ul a raspuns neasteptat: {raw}")

    matches = raw.get("response", {}).get("matches", [])
    meciuri = []
    for m in matches:
        status = m.get("status", {})
        meciuri.append({
            "fixture_id": m["id"],
            "league_id": m["leagueId"],
            "data": m["time"],
            "echipa_gazda": m["home"]["name"],
            "echipa_gazda_id": m["home"]["id"],
            "echipa_oaspete": m["away"]["name"],
            "echipa_oaspete_id": m["away"]["id"],
            "scor": status.get("scoreStr"),
            "status": status.get("reason", {}).get("short"),
            "terminat": status.get("finished", False),
        })
    return meciuri


def meciuri_azi() -> list[dict]:
    """Meciurile de azi (nume pastrat pentru compatibilitate cu data_source.py)."""
    return meciuri_pe_data(date.today())


def istoric_echipa(team_id: int, n_meciuri: int = 20):
    """
    NEIMPLEMENTAT INCA — acest API nu are (momentan confirmat) un endpoint
    dedicat de tipul "ultimele N meciuri ale echipei X". Fara el, motorul
    Poisson din pipeline.py nu are din ce calcula decay/shrinkage.

    Nu implementez o solutie de tip "scanez zi cu zi si filtrez dupa
    team_id" — ar consuma cota zilnica gratuita (100 req/zi) in cateva
    analize, fara sa fie de incredere.

    Cauta in sidebar-ul RapidAPI Studio, sub 'Teams' sau un tab de tip
    'H2H'/'Fixtures', un endpoint gen 'Team Last Matches' sau similar —
    trimite-mi codul si raspunsul exemplu, la fel ca pentru fixtures.
    """
    raise RuntimeError(
        "istoric_echipa() nu e inca implementat pentru acest API. "
        "Trebuie identificat endpoint-ul corect de istoric per echipa "
        "in RapidAPI Studio, sub 'Teams' — vezi docstring-ul functiei."
    )


def predictie_oficiala(fixture_id: int) -> dict | None:
    """Nu exista echivalent confirmat la acest API — bonus dezactivat."""
    return None
