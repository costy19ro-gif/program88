import streamlit as st
import pandas as pd
import requests

# ─────────────────────────────────────────────
# 🔑 CONFIGURARE PAGINĂ
st.set_page_config(page_title="BetMachine RapidAPI", layout="wide")
st.title("⚽ BetMachine RapidAPI – AI Predictions")

# ─────────────────────────────────────────────
# 🔧 FUNCȚII RAPIDAPI
RAPIDAPI_KEY = "xxxxxxxx"  # înlocuiește cu cheia ta RapidAPI
BASE_URL = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

def get_fixtures(league_id=39, season=2024):
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    params = {"league": league_id, "season": season}
    response = requests.get(BASE_URL, headers=headers, params=params)
    data = response.json()
    fixtures = []
    for item in data.get("response", []):
        fixtures.append({
            "match_id": item["fixture"]["id"],
            "home_team": item["teams"]["home"]["name"],
            "away_team": item["teams"]["away"]["name"],
            "date": item["fixture"]["date"],
            "status": item["fixture"]["status"]["short"]
        })
    return pd.DataFrame(fixtures)

# ─────────────────────────────────────────────
# 🧠 FUNCȚII AI GENERATOARE
def add_value_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["value_1"] = df["prob_1"] * df["odd_1"]
    df["value_X"] = df["prob_X"] * df["odd_X"]
    df["value_2"] = df["prob_2"] * df["odd_2"]
    df["value_over"] = df["prob_over"] * df["odd_over"]
    df["value_under"] = df["prob_under"] * df["odd_under"]
    df["value_gg"] = df["prob_gg"] * df["odd_gg"]
    df["value_ng"] = df["prob_ng"] * df["odd_ng"]
    return df

def generator_SIGUR(df, min_prob=0.75, max_odd=1.70, max_matches=6):
    tickets = []
    for _, row in df.iterrows():
        if row["prob_1"] >= min_prob and row["odd_1"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "1", "prob": row["prob_1"], "odd": row["odd_1"]})
        elif row["prob_2"] >= min_prob and row["odd_2"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "2", "prob": row["prob_2"], "odd": row["odd_2"]})
        elif row["prob_over"] >= min_prob and row["odd_over"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "Over 2.5", "prob": row["prob_over"], "odd": row["odd_over"]})
        elif row["prob_gg"] >= min_prob and row["odd_gg"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "GG", "prob": row["prob_gg"], "odd": row["odd_gg"]})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["prob"], reverse=True)[:max_matches])

def generator_COMBO(df, min_prob=0.60, min_odd=1.70, max_odd=2.20, max_matches=10):
    tickets = []
    for _, row in df.iterrows():
        candidates = []
        if row["prob_1"] >= min_prob and min_odd <= row["odd_1"] <= max_odd:
            candidates.append(("1", row["prob_1"], row["odd_1"]))
        if row["prob_2"] >= min_prob and min_odd <= row["odd_2"] <= max_odd:
            candidates.append(("2", row["prob_2"], row["odd_2"]))
        if row["prob_over"] >= min_prob and min_odd <= row["odd_over"] <= max_odd:
            candidates.append(("Over 2.5", row["prob_over"], row["odd_over"]))
        if row["prob_gg"] >= min_prob and min_odd <= row["odd_gg"] <= max_odd:
            candidates.append(("GG", row["prob_gg"], row["odd_gg"]))
        if candidates:
            tip, prob, odd = max(candidates, key=lambda x: x[1])
            tickets.append({"match_id": row["match_id"], "tip": tip, "prob": prob, "odd": odd})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["prob"], reverse=True)[:max_matches])

def generator_BOMBA(df, min_prob=0.50, min_odd=2.20, max_matches=15):
    tickets = []
    for _, row in df.iterrows():
        candidates = []
        if row["prob_1"] >= min_prob and row["odd_1"] >= min_odd:
            candidates.append(("1", row["prob_1"], row["odd_1"], row["value_1"]))
        if row["prob_2"] >= min_prob and row["odd_2"] >= min_odd:
            candidates.append(("2", row["prob_2"], row["odd_2"], row["value_2"]))
        if row["prob_over"] >= min_prob and row["odd_over"] >= min_odd:
            candidates.append(("Over 2.5", row["prob_over"], row["odd_over"], row["value_over"]))
        if row["prob_gg"] >= min_prob and row["odd_gg"] >= min_odd:
            candidates.append(("GG", row["prob_gg"], row["odd_gg"], row["value_gg"]))
        if candidates:
            tip, prob, odd, value = max(candidates, key=lambda x: x[3])
            tickets.append({"match_id": row["match_id"], "tip": tip, "prob": prob, "odd": odd, "value": value})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["value"], reverse=True)[:max_matches])

# ─────────────────────────────────────────────
# 📊 INTERFAȚĂ STREAMLIT
st.sidebar.header("⚙️ Setări")
league_id = st.sidebar.number_input("League ID", value=39)
season = st.sidebar.number_input("Season", value=2024)
if st.sidebar.button("🔄 Actualizează meciuri"):
    fixtures = get_fixtures(league_id, season)
    st.success(f"{len(fixtures)} meciuri găsite")
    st.dataframe(fixtures)

uploaded = st.file_uploader("📂 Încarcă fișier cu probabilități + cote (CSV)")
if uploaded:
    df = pd.read_csv(uploaded)
    df = add_value_columns(df)

    st.header("🎯 Generatoare AI")
    st.subheader("Bilet SIGUR")
    st.dataframe(generator_SIGUR(df))

    st.subheader("Bilet COMBO")
    st.dataframe(generator_COMBO(df))

    st.subheader("Bilet BOMBA")
    st.dataframe(generator_BOMBA(df))
# ─────────────────────────────────────────────
# 🔮 PREDICȚII LIVE DIN RAPIDAPI
def get_live_predictions(league_id=39, season=2024):
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    params = {"league": league_id, "season": season}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    matches = []
    for item in data.get("response", []):
        odds = item.get("bookmakers", [])[0].get("bets", [])
        odds_dict = {}
        for bet in odds:
            for val in bet.get("values", []):
                odds_dict[val["value"]] = float(val["odd"])

        # probabilități simple (inverse cote normalizate)
        total_inv = sum(1 / v for v in odds_dict.values() if v > 0)
        probs = {k: (1 / v) / total_inv for k, v in odds_dict.items() if v > 0}

        matches.append({
            "match_id": item["fixture"]["id"],
            "home_team": item["fixture"]["teams"]["home"]["name"],
            "away_team": item["fixture"]["teams"]["away"]["name"],
            "odd_1": odds_dict.get("Home", None),
            "odd_X": odds_dict.get("Draw", None),
            "odd_2": odds_dict.get("Away", None),
            "prob_1": probs.get("Home", None),
            "prob_X": probs.get("Draw", None),
            "prob_2": probs.get("Away", None)
        })

    return pd.DataFrame(matches)
