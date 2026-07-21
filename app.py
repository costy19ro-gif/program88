import pandas as pd
import streamlit as st
st.set_page_config(page_title="BetMachine RapidAPI", layout="wide")
st.write("✅ Streamlit a pornit corect")

def add_value_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["value_1"] = df["prob_1"] * df["odd_1"]
    df["value_X"] = df["prob_X"] * df["odd_X"]
    df["value_2"] = df["prob_2"] * df["odd_2"]

    df["value_over"] = df["prob_over"] * df["odd_over"]
    df["value_under"] = df["prob_under"] * df["odd_under"]

    df["value_gg"] = df["prob_gg"] * df["odd_gg"]
    df["value_ng"] = df["prob_ng"] * df["odd_ng"]

    return df


def generator_SIGUR(df: pd.DataFrame,
                    min_prob: float = 0.75,
                    max_odd: float = 1.70,
                    max_matches: int = 6) -> pd.DataFrame:

    tickets = []

    for _, row in df.iterrows():
        if row["prob_1"] >= min_prob and row["odd_1"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "1", "prob": row["prob_1"], "odd": row["odd_1"]})
        elif row["prob_2"] >= min_prob and row["odd_2"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "2", "prob": row["prob_2"], "odd": row["odd_2"]})
        elif row["prob_over"] >= min_prob and row["odd_over"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "Over 2.5", "prob": row["prob_over"], "odd": row["odd_over"]})
        elif row["prob_under"] >= min_prob and row["odd_under"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "Under 2.5", "prob": row["prob_under"], "odd": row["odd_under"]})
        elif row["prob_gg"] >= min_prob and row["odd_gg"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "GG", "prob": row["prob_gg"], "odd": row["odd_gg"]})
        elif row["prob_ng"] >= min_prob and row["odd_ng"] <= max_odd:
            tickets.append({"match_id": row["match_id"], "tip": "NG", "prob": row["prob_ng"], "odd": row["odd_ng"]})

    tickets = sorted(tickets, key=lambda x: x["prob"], reverse=True)
    return pd.DataFrame(tickets[:max_matches])


def generator_COMBO(df: pd.DataFrame,
                    min_prob: float = 0.60,
                    min_odd: float = 1.70,
                    max_odd: float = 2.20,
                    max_matches: int = 10) -> pd.DataFrame:

    tickets = []

    for _, row in df.iterrows():
        candidates = []

        if row["prob_1"] >= min_prob and min_odd <= row["odd_1"] <= max_odd:
            candidates.append(("1", row["prob_1"], row["odd_1"]))
        if row["prob_X"] >= min_prob and min_odd <= row["odd_X"] <= max_odd:
            candidates.append(("X", row["prob_X"], row["odd_X"]))
        if row["prob_2"] >= min_prob and min_odd <= row["odd_2"] <= max_odd:
            candidates.append(("2", row["prob_2"], row["odd_2"]))

        if row["prob_over"] >= min_prob and min_odd <= row["odd_over"] <= max_odd:
            candidates.append(("Over 2.5", row["prob_over"], row["odd_over"]))
        if row["prob_under"] >= min_prob and min_odd <= row["odd_under"] <= max_odd:
            candidates.append(("Under 2.5", row["prob_under"], row["odd_under"]))

        if row["prob_gg"] >= min_prob and min_odd <= row["odd_gg"] <= max_odd:
            candidates.append(("GG", row["prob_gg"], row["odd_gg"]))
        if row["prob_ng"] >= min_prob and min_odd <= row["odd_ng"] <= max_odd:
            candidates.append(("NG", row["prob_ng"], row["odd_ng"]))

        if candidates:
            tip, prob, odd = max(candidates, key=lambda x: x[1])
            tickets.append({"match_id": row["match_id"], "tip": tip, "prob": prob, "odd": odd})

    tickets = sorted(tickets, key=lambda x: x["prob"], reverse=True)
    return pd.DataFrame(tickets[:max_matches])


def generator_BOMBA(df: pd.DataFrame,
                    min_prob: float = 0.50,
                    min_odd: float = 2.20,
                    max_matches: int = 15) -> pd.DataFrame:

    tickets = []

    for _, row in df.iterrows():
        candidates = []

        if row["prob_1"] >= min_prob and row["odd_1"] >= min_odd:
            candidates.append(("1", row["prob_1"], row["odd_1"], row["value_1"]))
        if row["prob_X"] >= min_prob and row["odd_X"] >= min_odd:
            candidates.append(("X", row["prob_X"], row["odd_X"], row["value_X"]))
        if row["prob_2"] >= min_prob and row["odd_2"] >= min_odd:
            candidates.append(("2", row["prob_2"], row["odd_2"], row["value_2"]))

        if row["prob_over"] >= min_prob and row["odd_over"] >= min_odd:
            candidates.append(("Over 2.5", row["prob_over"], row["odd_over"], row["value_over"]))
        if row["prob_under"] >= min_prob and row["odd_under"] >= min_odd:
            candidates.append(("Under 2.5", row["prob_under"], row["odd_under"], row["value_under"]))

        if row["prob_gg"] >= min_prob and row["odd_gg"] >= min_odd:
            candidates.append(("GG", row["prob_gg"], row["odd_gg"], row["value_gg"]))
        if row["prob_ng"] >= min_prob and row["odd_ng"] >= min_odd:
            candidates.append(("NG", row["prob_ng"], row["odd_ng"], row["value_ng"]))

        if candidates:
            tip, prob, odd, value = max(candidates, key=lambda x: x[3])
            tickets.append({"match_id": row["match_id"], "tip": tip, "prob": prob, "odd": odd, "value": value})

    tickets = sorted(tickets, key=lambda x: x["value"], reverse=True)
    return pd.DataFrame(tickets[:max_matches])
