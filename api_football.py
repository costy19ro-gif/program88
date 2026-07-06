from __future__ import annotations
import requests
import streamlit as st
from datetime import datetime
from pipeline import MeciIstoric

# CONEXIUNEA OFICIALĂ DIRECTĂ CONFORM DASHBOARD.API-FOOTBALL.COM
BASE_URL = "https://api-sports.io"

def get_headers():
    if "apisports_key" not in st.secrets:
        st.error("Cheia 'apisports_key' lipsește din Streamlit Secrets!")
        return {}
    return {
        "x-apisports-key": st.secrets["apisports_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

def meciuri_azi() -> list[dict]:
    """Preia meciurile de azi direct de pe serverul api-sports.io (FĂRĂ CACHE)."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    params = {"date": date_str}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Dacă pe data serverului lista e goală (din cauza fusului orar UTC), aducem meciurile live
        raw_fixtures = data.get("response", [])
        if not raw_fixtures:
            response = requests.get(url, headers=headers, params={"live": "all"}, timeout=10)
            raw_fixtures = response.json().get("response", [])
            
        mapped_fixtures = []
        for f in raw_fixtures:
            teams_info = f.get("teams", {})
            mapped_fixtures.append({
                "fixture_id": f.get("fixture", {}).get("id"),
                "homeTeam": {
                    "id": teams_info.get("home", {}).get("id"),
                    "name": teams_info.get("home", {}).get("name")
                },
                "awayTeam": {
                    "id": teams_info.get("away", {}).get("id"),
                    "name": teams_info.get("away", {}).get("name")
                },
                "tournament": {
                    "name": f.get("league", {}).get("name")
                }
            })
        return mapped_fixtures
    except Exception as e:
        st.error(f"Eroare directă de conexiune API-Sports: {e}")
        return []

def istoric_echipa(team_id: int, n_meciuri: int = 20) -> list[MeciIstoric]:
    """Preia istoricul echipei adaptat complet pentru planul gratuit API-Sports."""
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    current_year = datetime.now().year
    
    # Folosim statusul FT (meciuri terminate) - NU folosim parametrul 'last' (interzis pe planul free)
    params = {"team": team_id, "season": current_year, "status": "FT"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("response"):
            params["season"] = current_year - 1
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
        raw_fixtures = data.get("response", [])
        raw_fixtures.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
        
        meciuri_pipeline = []
        for f in raw_fixtures[-n_meciuri:]:
            full_date_str = f.get("fixture", {}).get("date", "")
            just_date_str = full_date_str.split("T")[0] if "T" in full_date_str else full_date_str
            
            try:
                m_date = datetime.strptime(just_date_str, "%Y-%m-%d").date()
            except Exception:
                m_date = datetime.today().date()
                
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            
            meciuri_pipeline.append(MeciIstoric(
                data=m_date,
                home_id=teams.get("home", {}).get("id"),
                away_id=teams.get("away", {}).get("id"),
                home_goals=goals.get("home", 0) if goals.get("home") is not None else 0,
                away_goals=goals.get("away", 0) if goals.get("away") is not None else 0
            ))
        return meciuri_pipeline
    except Exception:
        return []

def predictie_oficiala(fixture_id: int) -> dict | None:
    """Preia predicțiile oficiale interne de pe api-sports.io."""
    url = f"{BASE_URL}/predictions"
    headers = get_headers()
    try:
        response = requests.get(url, headers=headers, params={"fixture": fixture_id}, timeout=10)
        res_list = response.json().get("response", [])
        return res_list if res_list else None
    except Exception:
        return None

def predictii_bonus_rapidapi(params: dict | None = None) -> list[dict] | None:
    return None
