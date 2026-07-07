import requests
import streamlit as st

# -------------------------------------------------------------
# CONFIGURARE RAPIDAPI — DOAR PATH-UL TREBUIE COMPLETAT MANUAL
# -------------------------------------------------------------
BASE_URL = "https://api-football-v1.p.rapidapi.com"   # gateway RapidAPI
ENDPOINT_PATH = "/v3/predictions"                     # <-- MODIFICĂ dacă folosești alt API tipster

def get_headers():
    """Header-ele necesare pentru RapidAPI."""
    if "apisports_key" not in st.secrets:
        st.error("Cheia 'apisports_key' lipsește din Streamlit Secrets!")
        return {}

    return {
        "x-rapidapi-key": st.secrets["apisports_key"],
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }


# -------------------------------------------------------------
# FUNCȚIA PRINCIPALĂ — BONUS PREDICȚII RAPIDAPI
# -------------------------------------------------------------
@st.cache_data(ttl=3600)
def predictii_bonus_rapidapi():
    """
    Funcție bonus — nu afectează pipeline-ul principal.
    Returnează primele predicții disponibile din endpoint-ul RapidAPI.
    """
    url = f"{BASE_URL}{ENDPOINT_PATH}"
    headers = get_headers()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # API-urile tipster au structuri diferite, dar toate au un "response" sau "data"
        if "response" in data:
            return data["response"]
        if "data" in data:
            return data["data"]

        return None

    except Exception as e:
        st.warning(f"Nu am putut încărca predicțiile RapidAPI: {e}")
        return None
