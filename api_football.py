import requests
import streamlit as st
from datetime import datetime, timedelta

# Configurare URL de bază pentru API-Football direct
BASE_URL = "https://api-sports.io"

def get_headers():
    """Prelucrează cheia API salvată în Streamlit Secrets."""
    if "apisports_key" not in st.secrets:
        st.error("Cheia 'apisports_key' lipsește din Streamlit Secrets!")
        return {}
    return {
        "x-apisports-key": st.secrets["apisports_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

@st.cache_data(ttl=timedelta(minutes=15))
def get_fixtures_by_date(date_str=None):
    """
    Aduce meciurile relevante. Pentru a evita problemele de fus orar (UTC vs local),
    dacă nu găsește meciuri la data fixă, interoghează automat meciurile live/active.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    params = {"date": date_str}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        raw_fixtures = data.get("response", [])
        
        # REPLIERE INTELIGENTĂ: Dacă pe data locală e gol din cauza UTC-ului, cerem meciurile live
        if not raw_fixtures:
            print("[API-Football] Data fixă e goală din cauza fusului orar. Extrag meciurile live...")
            params = {"live": "all"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            raw_fixtures = data.get("response", [])

        if data.get("errors"):
            print(f"[API-Football] Eroare API: {data['errors']}")
            return []
            
        mapped_fixtures = []
        for f in raw_fixtures:
            fixture_info = f.get("fixture", {})
            league_info = f.get("league", {})
            teams_info = f.get("teams", {})
            
            mapped_fixtures.append({
                "fixture_id": fixture_info.get("id"),
                "homeTeam": {
                    "id": teams_info.get("home", {}).get("id"),
                    "name": teams_info.get("home", {}).get("name")
                },
                "awayTeam": {
                    "id": teams_info.get("away", {}).get("id"),
                    "name": teams_info.get("away", {}).get("name")
                },
                "tournament": {
                    "name": league_info.get("name")
                }
            })
            
        print(f"[API-Football] Succes! Am mapat {len(mapped_fixtures)} meciuri în interfață.")
        return mapped_fixtures
    except Exception as e:
        print(f"[API-Football] Excepție la încărcare: {e}")
        return []

@st.cache_data(ttl=timedelta(hours=6))
def get_team_history(team_id, max_matches=20):
    """
    Istoricul meciurilor adaptat pentru planul gratuit.
    Convertește datele brute direct în obiecte MeciIstoric necesare pipeline.py
    """
    from pipeline import MeciIstoric
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    current_year = datetime.now().year
    
    params = {
        "team": team_id,
        "season": current_year,
        "status": "FT"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errors") or not data.get("response"):
            params["season"] = current_year - 1
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
        raw_fixtures = data.get("response", [])
        if not raw_fixtures:
            return []
            
        raw_fixtures.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
        last_fixtures = raw_fixtures[-max_matches:]
        
        meciuri_pipeline = []
        for f in last_fixtures:
            full_date_str = f.get("fixture", {}).get("date", "")
            
            # REZOLVARE CHIRURGICALĂ: Extragem strict primul element ca string curat folosind [0]
            if "T" in full_date_str:
                just_date_str = full_date_str.split("T")[0]
            else:
                just_date_str = full_date_str
            
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
    except Exception as e:
        print(f"[API-Football] Eroare istoric echipă {team_id}: {e}")
        return []

@st.cache_data(ttl=timedelta(hours=6))
def get_fixture_predictions(fixture_id):
    """Prelucrează predicțiile interne brute."""
    url = f"{BASE_URL}/predictions"
    headers = get_headers()
    params = {"fixture": fixture_id}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        res_list = data.get("response", [])
        return res_list if res_list else None
    except Exception:
        return None

# Alias-uri cerute de data_source.py pentru a păstra conexiunile intacte
meciuri_azi = get_fixtures_by_date
istoric_echipa = get_team_history
predictie_oficiala = get_fixture_predictions
