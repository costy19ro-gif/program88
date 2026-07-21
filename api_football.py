"""
Sursa PRINCIPALA de date reale: API-Football, rutat prin RapidAPI.

Expune functiile de nivel inalt pe care le apeleaza data_source.py
(meciuri_azi, istoric_echipa, predictie_oficiala) — inainte, aceste
functii nu existau aici, desi data_source.py le apela deja, ceea ce
dadea AttributeError la prima folosire.

Pastreaza si clasa FootballAPI pentru acces de nivel jos (folosita
de ex. pentru cote/odds in app.py, tab-ul "model rapid").
"""

from __future__ import annotations

from datetime import date, datetime

from api_client import RapidAPIClient
from pipeline import MeciIstoric

_client: RapidAPIClient | None = None


def _get_client() -> RapidAPIClient:
    global _client
    if _client is None:
        _client = RapidAPIClient()
    return _client


class FootballAPI:
    """Acces de nivel jos la endpoint-uri, cand ai nevoie de raspunsul brut."""

    def __init__(self, api_key: str | None = None):
        self.client = RapidAPIClient(api_key)

    def fixtures_by_date(self, date_str: str):
        return self.client.get("fixtures", {"date": date_str})

    def fixtures_by_league(self, league_id: int, season: int):
        return self.client.get("fixtures", {"league": league_id, "season": season})

    def fixtures_by_team(self, team_id: int, last: int = 20):
        return self.client.get("fixtures", {"team": team_id, "last": last, "status": "FT-AET-PEN"})

    def odds(self, fixture_id: int):
        return self.client.get("odds", {"fixture": fixture_id})

    def predictions(self, fixture_id: int):
        return self.client.get("predictions", {"fixture": fixture_id})

    def standings(self, league_id: int, season: int):
        return self.client.get("standings", {"league": league_id, "season": season})

    def teams(self, league_id: int, season: int):
        return self.client.get("teams", {"league": league_id, "season": season})


# ---------------------------------------------------------------------------
# Functii de nivel inalt — astea sunt apelate de data_source.py
# ---------------------------------------------------------------------------

def meciuri_azi() -> list[dict]:
    """Meciurile programate azi, intr-un format simplu (dict), gata de afisat."""
    azi = date.today().isoformat()
    raw = _get_client().get("fixtures", {"date": azi})
    meciuri = []
    for item in raw:
        meciuri.append({
            "fixture_id": item["fixture"]["id"],
            "data": item["fixture"]["date"],
            "liga": item["league"]["name"],
            "tara": item["league"]["country"],
            "echipa_gazda": item["teams"]["home"]["name"],
            "echipa_gazda_id": item["teams"]["home"]["id"],
            "echipa_oaspete": item["teams"]["away"]["name"],
            "echipa_oaspete_id": item["teams"]["away"]["id"],
            "status": item["fixture"]["status"]["short"],
        })
    return meciuri


def istoric_echipa(team_id: int, n_meciuri: int = 20) -> list[MeciIstoric]:
    """
    Ultimele n_meciuri TERMINATE ale unei echipe, convertite direct in
    obiecte MeciIstoric — formatul pe care il asteapta pipeline.py.
    """
    raw = _get_client().get(
        "fixtures", {"team": team_id, "last": n_meciuri, "status": "FT-AET-PEN"}
    )
    istoric = []
    for item in raw:
        fixture = item["fixture"]
        teams = item["teams"]
        goals = item["goals"]
        score = item.get("score", {})

        e_gazda = teams["home"]["id"] == team_id
        goluri_marcate = goals["home"] if e_gazda else goals["away"]
        goluri_primite = goals["away"] if e_gazda else goals["home"]
        if goluri_marcate is None or goluri_primite is None:
            continue  # meci fara scor final valid, il sarim

        ht = score.get("halftime") or {}
        gm_pauza = ht.get("home") if e_gazda else ht.get("away")
        gp_pauza = ht.get("away") if e_gazda else ht.get("home")

        istoric.append(MeciIstoric(
            data=datetime.fromisoformat(fixture["date"].replace("Z", "+00:00")).date(),
            goluri_marcate=goluri_marcate,
            goluri_primite=goluri_primite,
            goluri_marcate_pauza=gm_pauza,
            goluri_primite_pauza=gp_pauza,
        ))
    return istoric


def predictie_oficiala(fixture_id: int) -> dict | None:
    """Predictia proprie API-Football pentru un meci (doar bonus/comparatie)."""
    raw = _get_client().get("predictions", {"fixture": fixture_id})
    return raw[0] if raw else None
