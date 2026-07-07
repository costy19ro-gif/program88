from __future__ import annotations
import requests
import streamlit as st
from datetime import datetime
from pipeline import MeciIstoric

BASE_URL = "https://sportapi7.p.rapidapi.com"

def get_headers():
    """Header-ele necesare pentru autentificarea SportAPI7 via RapidAPI."""
    return {
        "X-RapidAPI-Key": "41b44ba4afmshbebf0e0637fc807p12bf84jsn0471b6bfcfea",
        "X-RapidAPI-Host": "sportapi7.p.rapidapi.com"
    }

def meciuri_azi(date_str: str = None) -> list[dict]:
    """Preia toate meciurile de fotbal dintr-o anumită zi folosind SportAPI7."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    headers = get_headers()
    timezone_offset = 0 # UTC 
    
    try:
        # Pasul 1: Preluăm categoriile de fotbal din acea zi
        cat_url = f"{BASE_URL}/api/v1/sport/football/{date_str}/{timezone_offset}/categories"
        cat_resp = requests.get(cat_url, headers=headers, timeout=10)
        categories_data = cat_resp.json()
        
        mapped_fixtures = []
        categories = categories_data.get("categories", [])
        
        if not categories or not isinstance(categories, list):
            return []
            
        # Pasul 2: Parcurgem primele 5 categorii active (pentru a evita blocarea pe planul gratuit)
        for cat in categories[:5]:
            cat_id = cat["category"]["id"]
            events_url = f"{BASE_URL}/api/v1/category/{cat_id}/scheduled-events/{date_str}"
            events_resp = requests.get(events_url, headers=headers, timeout=10)
            events_data = events_resp.json()
            
            for event in events_data.get("events", []):
                # Protecție împotriva erorilor de structură (precum KeyError-ul raportat)
                tournament_info = event.get("tournament", {})
                unique_t = tournament_info.get("uniqueTournament", {})
                tournament_id = unique_t.get("id") if unique_t else tournament_info.get("id")
                
                mapped_fixtures.append({
                    "fixture_id": event.get("id"),
                    "homeTeam": {
                        "id": event.get("homeTeam", {}).get("id"),
                        "name": event.get("homeTeam", {}).get("name")
                    },
                    "awayTeam": {
                        "id": event.get("awayTeam", {}).get("id"),
                        "name": event.get("awayTeam", {}).get("name")
                    },
                    "tournament": {
                        "name": tournament_info.get("name", "Unknown Tournament"),
                        "id": tournament_id,
                        "season_id": event.get("season", {}).get("id")
                    }
                })
        return mapped_fixtures
    except Exception as e:
        st.error(f"Eroare SportAPI7 meciuri: {e}")
        return []

def istoric_echipa(team_id: int, n_meciuri: int = 20) -> list[MeciIstoric]:
    """Preia ultimele meciuri jucate de o echipă folosind endpoint-ul de evenimente SportAPI7."""
    # Folosește endpoint-ul de evenimente trecute ale echipei
    url = f"{BASE_URL}/api/v1/team/{team_id}/events/last/{n_meciuri}"
    headers = get_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        meciuri_pipeline = []
        for event in data.get("events", []):
            # Luăm doar meciurile încheiate (statusul trebuie să fie finalizat)
            if event.get("status", {}).get("type") != "finished":
                continue
                
            timestamp = event.get("startTimestamp")
            m_date = datetime.fromtimestamp(timestamp).date() if timestamp else datetime.today().date()
            
            home_id = event.get("homeTeam", {}).get("id")
            away_id = event.get("awayTeam", {}).get("id")
            
            home_goals = event.get("homeScore", {}).get("current", 0)
            away_goals = event.get("awayScore", {}).get("current", 0)
            
            meciuri_pipeline.append(MeciIstoric(
                data=m_date,
                home_id=home_id,
                away_id=away_id,
                home_goals=home_goals if home_goals is not None else 0,
                away_goals=away_goals if away_goals is not None else 0
            ))
        return meciuri_pipeline
    except Exception as e:
        st.error(f"Eroare preluare istoric SportAPI7: {e}")
        return []

def predictie_oficiala(fixture_id: int) -> dict | None:
    """Preia cotele evenimentului ca alternativă la predicții."""
    url = f"{BASE_URL}/api/v1/event/{fixture_id}/odds/1/all"
    headers = get_headers()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception:
        return None

def predictii_bonus_rapidapi(params: dict | None = None) -> list[dict] | None:
    return None
