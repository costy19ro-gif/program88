import requests
import streamlit as st
from datetime import datetime, timedelta

# Configurare URL de bază pentru API-Football direct (api-sports.io)
BASE_URL = "https://v3.football.api-sports.io"

def get_headers():
    """
    Prelucrează cheia API salvată în Streamlit Secrets.
    Folosește header-ul oficial cerut de API-Sports.
    """
    if "apisports_key" not in st.secrets:
        st.error("Cheia 'apisports_key' lipsește din Streamlit Secrets!")
        return {}
    return {
        "x-apisports-key": st.secrets["apisports_key"],
        "x-rapidapi-host": "v3.football.api-sports.io"
    }

@st.cache_data(ttl=timedelta(hours=6))
def get_fixtures_by_date(date_str):
    """
    Prelucrează meciurile dintr-o anumită zi (Format: YYYY-MM-DD).
    """
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    params = {"date": date_str}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errors"):
            st.error(f"Eroare API-Football: {data['errors']}")
            return []
            
        return data.get("response", [])
    except Exception as e:
        st.error(f"Eroare la conexiunea cu API-Football: {e}")
        return []

@st.cache_data(ttl=timedelta(hours=6))
def get_team_history(team_id, max_matches=20):
    """
    Prelucrează istoricul meciurilor terminate ale unei echipe.
    MODIFICAT PENTRU PLANUL FREE: Nu mai folosește parametrul 'last' (care dă eroare).
    Descarcă meciurile din sezonul curent și păstrează ultimele N meciuri direct în Python.
    """
    url = f"{BASE_URL}/fixtures"
    headers = get_headers()
    
    # Determinăm automat anul sezonului curent (folosim 2026 conform mediului curent)
    current_year = datetime.now().year
    
    # Parametri curați, acceptați de planul gratuit
    params = {
        "team": team_id,
        "season": current_year,
        "status": "FT"  # Doar meciurile încheiate la timp regulamentar (Full Time)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Verificăm dacă structura de erori a API-ului a returnat ceva
        if data.get("errors"):
            # Dacă sezonul curent nu a început încă sau e gol, încercăm o repliere pe anul trecut
            if "not access" in str(data["errors"]) or not data.get("response"):
                params["season"] = current_year - 1
                response = requests.get(url, headers=headers, params=params, timeout=10)
                data = response.json()
            else:
                st.error(f"Eroare API-Football: {data['errors']}")
                return []
        
        fixtures = data.get("response", [])
        
        if not fixtures:
            return []
            
        # Sortăm meciurile după dată, cronologic (de la cel mai vechi la cel mai recent)
        fixtures.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
        
        # Extragem doar ultimele N meciuri (implicit 20) direct în Python
        return fixtures[-max_matches:]
        
    except Exception as e:
        st.error(f"Eroare la descărcarea istoricului echipei: {e}")
        return []

@st.cache_data(ttl=timedelta(hours=6))
def get_fixture_predictions(fixture_id):
    """
    Prelucrează predicțiile interne generate direct de API-Football pentru un meci (Modul Bonus).
    """
    url = f"{BASE_URL}/predictions"
    headers = get_headers()
    params = {"fixture": fixture_id}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errors"):
            return None
            
        res_list = data.get("response", [])
        return res_list[0] if res_list else None
    except Exception:
        return None
# Scurtături pentru compatibilitate cu restul aplicației tale:
meciuri_azi = get_fixtures_by_date
istoric_echipa = get_team_history
