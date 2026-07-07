"""
data_source.py
==============
Strat de orchestrare care face legatura intre interfata (app.py) 
si clientii de retea (api_football.py si rapidapi_predictions.py).
"""

import api_football
import rapidapi_predictions

def meciuri_azi(date_str=None):
    """
    Prelucreaza si returneaza meciurile programate pentru o anumita data.
    Daca nu se specifica nicio data, se poate folosi o valoare implicita in api_football.
    """
    try:
        # Trimite parametrul date_str mai departe catre clientul principal API-Football
        return api_football.get_fixtures(date_str)
    except Exception as e:
        print(f"[data_source] Eroare la preluarea meciurilor: {e}")
        return []

def istoric_echipa(team_id, n_meciuri=20):
    """
    Aduce ultimele n meciuri terminate ale unei echipe.
    """
    try:
        return api_football.get_team_history(team_id, n_meciuri)
    except Exception as e:
        print(f"[data_source] Eroare la preluarea istoricului pentru echipa {team_id}: {e}")
        return []

def predictie_oficiala(fixture_id):
    """
    Aduce predictia nativa generata direct de API-Football (Bonus).
    """
    try:
        return api_football.get_predictions(fixture_id)
    except Exception as e:
        print(f"[data_source] Eroare la preluarea predictiei oficiale {fixture_id}: {e}")
        return None

def predictii_bonus_rapidapi():
    """
    Modul optional pentru predictiile tipstar din platforma externa RapidAPI.
    """
    try:
        return rapidapi_predictions.get_bonus_predictions()
    except Exception as e:
        print(f"[data_source] Modulul bonus RapidAPI nu este configurat complet: {e}")
        return None
