import streamlit as st
import pandas as pd
import requests
import joblib

# ─────────────────────────────────────────────
# 🔧 CONFIGURARE PAGINĂ
st.set_page_config(page_title="BetMachine RapidAPI", layout="wide")
st.title("⚽ BetMachine RapidAPI – AI Predictions")

# ─────────────────────────────────────────────
# 🔑 RAPIDAPI CONFIG
RAPIDAPI_KEY = "INTRODU_CHEIA_TA_AICI"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# ─────────────────────────────────────────────
# 📡 FUNCȚIE FIXTURES
def get_fixtures(league_id=39, season=2024):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

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
# 🔮 FUNCȚIE ODDS + PROBABILITĂȚI LIVE
def get_live_predictions(league_id=39, season=2024):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    params = {"league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    matches = []
    for item in data.get("response", []):
        try:
            odds = item["bookmakers"][0]["bets"][0]["values"]
        except:
            continue

        odd_1 = float(odds[0]["odd"])
        odd_X = float(odds[1]["odd"])
        odd_2 = float(odds[2]["odd"])

        inv = (1/odd_1 + 1/odd_X + 1/odd_2)
        prob_1 = (1/odd_1) / inv
        prob_X = (1/odd_X) / inv
        prob_2 = (1/odd_2) / inv

        matches.append({
            "match_id": item["fixture"]["id"],
            "home_team": item["fixture"]["teams"]["home"]["name"],
            "away_team": item["fixture"]["teams"]["away"]["name"],
            "odd_1": odd_1,
            "odd_X": odd_X,
            "odd_2": odd_2,
            "prob_1": prob_1,
            "prob_X": prob_X,
            "prob_2": prob_2
        })

    return pd.DataFrame(matches)

# ─────────────────────────────────────────────
# 🤖 MODEL AI 1X2
FEATURES_1X2 = [
    "shots_home", "shots_away",
    "shots_on_target_home", "shots_on_target_away",
    "xG_home", "xG_away",
    "corners_home", "corners_away",
    "form_home", "form_away",
    "league_strength"
]

model_1x2 = joblib.load("model_1x2.joblib")

def predict_1x2(row):
    X = row[FEATURES_1X2].values.reshape(1, -1)
    pred = model_1x2.predict(X)[0]
    proba = model_1x2.predict_proba(X)[0]
    return pred, proba

# ─────────────────────────────────────────────
# 🧮 FUNCȚII GENERATOARE AI
def add_value_columns(df):
    df["value_1"] = df["prob_1"] * df["odd_1"]
    df["value_X"] = df["prob_X"] * df["odd_X"]
    df["value_2"] = df["prob_2"] * df["odd_2"]
    return df

def generator_SIGUR(df, min_prob=0.75, max_odd=1.70, max_matches=6):
    tickets = []
    for _, r in df.iterrows():
        if r["prob_1"] >= min_prob and r["odd_1"] <= max_odd:
            tickets.append({"match_id": r["match_id"], "tip": "1", "prob": r["prob_1"], "odd": r["odd_1"]})
        elif r["prob_2"] >= min_prob and r["odd_2"] <= max_odd:
            tickets.append({"match_id": r["match_id"], "tip": "2", "prob": r["prob_2"], "odd": r["odd_2"]})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["prob"], reverse=True)[:max_matches])

def generator_COMBO(df, min_prob=0.60, min_odd=1.70, max_odd=2.20, max_matches=10):
    tickets = []
    for _, r in df.iterrows():
        candidates = []
        if r["prob_1"] >= min_prob and min_odd <= r["odd_1"] <= max_odd:
            candidates.append(("1", r["prob_1"], r["odd_1"]))
        if r["prob_2"] >= min_prob and min_odd <= r["odd_2"] <= max_odd:
            candidates.append(("2", r["prob_2"], r["odd_2"]))
        if candidates:
            tip, prob, odd = max(candidates, key=lambda x: x[1])
            tickets.append({"match_id": r["match_id"], "tip": tip, "prob": prob, "odd": odd})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["prob"], reverse=True)[:max_matches])

def generator_BOMBA(df, min_prob=0.50, min_odd=2.20, max_matches=15):
    tickets = []
    for _, r in df.iterrows():
        candidates = []
        if r["prob_1"] >= min_prob and r["odd_1"] >= min_odd:
            candidates.append(("1", r["prob_1"], r["odd_1"], r["value_1"]))
        if r["prob_2"] >= min_prob and r["odd_2"] >= min_odd:
            candidates.append(("2", r["prob_2"], r["odd_2"], r["value_2"]))
        if candidates:
            tip, prob, odd, value = max(candidates, key=lambda x: x[3])
            tickets.append({"match_id": r["match_id"], "tip": tip, "prob": prob, "odd": odd, "value": value})
    return pd.DataFrame(sorted(tickets, key=lambda x: x["value"], reverse=True)[:max_matches])

# ─────────────────────────────────────────────
# 📊 INTERFAȚĂ STREAMLIT
st.sidebar.header("⚙️ Setări")
league_id = st.sidebar.number_input("League ID", value=39)
season = st.sidebar.number_input("Season", value=2024)

# FIXTURES
if st.sidebar.button("📅 Afișează meciuri"):
    fixtures = get_fixtures(league_id, season)
    st.subheader("📅 Meciuri")
    st.dataframe(fixtures)

# PREDICȚII LIVE
if st.sidebar.button("🔮 Predicții Live AI"):
    df_live = get_live_predictions(league_id, season)

    # completăm cu statistici default pentru model
    df_live["shots_home"] = 5
    df_live["shots_away"] = 5
    df_live["shots_on_target_home"] = 3
    df_live["shots_on_target_away"] = 3
    df_live["xG_home"] = 1.2
    df_live["xG_away"] = 0.9
    df_live["corners_home"] = 4
    df_live["corners_away"] = 4
    df_live["form_home"] = 3
    df_live["form_away"] = 2
    df_live["league_strength"] = 1

    preds = []
    for _, row in df_live.iterrows():
        pred, proba = predict_1x2(row)
        preds.append({
            "match_id": row["match_id"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "pred_1x2": ["1", "X", "2"][pred],
            "prob_1": proba[0],
            "prob_X": proba[1],
            "prob_2": proba[2],
            "odd_1": row["odd_1"],
            "odd_X": row["odd_X"],
            "odd_2": row["odd_2"]
        })

    df_live = pd.DataFrame(preds)
    df_live = add_value_columns(df_live)

    st.subheader("🔮 Predicții AI 1X2")
    st.dataframe(df_live)

    st.subheader("🎯 Bilet SIGUR")
    st.dataframe(generator_SIGUR(df_live))

    st.subheader("🎯 Bilet COMBO")
    st.dataframe(generator_COMBO(df_live))

    st.subheader("🎯 Bilet BOMBA")
    st.dataframe(generator_BOMBA(df_live))
