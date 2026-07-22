"""
BetMachine / Miliardarul — aplicatie unificata
=================================================
Doua motoare, un singur loc:

  1. "Motor Poisson (Miliardarul)" — pipeline.py: Decay + Shrinkage Bayesian +
     reconciliere lambda/mu + Dixon-Coles + scanner de piete, pe date reale
     din API-Football (via data_source.py). Asta e sursa principala.

  2. "Model rapid (RandomForest)" — semnal ML secundar, antrenat pe
     model_1x2.joblib. Foloseste-l doar ca a doua parere, nu ca sursa
     principala: are nevoie de statistici per meci (xG, sut-uri, cornere)
     pe care API-ul gratuit nu le da mereu.

Ruleaza cu: streamlit run app.py
"""

from __future__ import annotations

import joblib
import pandas as pd
import streamlit as st

import data_source
from pipeline import analizeaza_meci

st.set_page_config(page_title="Miliardarul — BetMachine", layout="wide")
st.title("⚽ Miliardarul — BetMachine")
st.caption("Motor Poisson/Dixon-Coles pe date reale + semnal ML secundar, intr-un singur loc.")

tab_poisson, tab_rapid, tab_despre = st.tabs([
    "🧮 Motor Poisson (Miliardarul)",
    "🎯 Model rapid (RandomForest)",
    "ℹ️ Despre",
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1 — MOTORUL PRINCIPAL: Poisson + Dixon-Coles, date reale
# ═══════════════════════════════════════════════════════════════════════
with tab_poisson:
    st.subheader("Meciurile de azi")

    if st.button("📅 Incarca meciurile de azi", key="btn_meciuri_azi"):
        try:
            with st.spinner("Se incarca de la API-Football..."):
                meciuri = data_source.meciuri_azi()
            st.session_state["meciuri_azi"] = meciuri
        except RuntimeError as e:
            st.error(str(e))

    meciuri = st.session_state.get("meciuri_azi", [])
    if meciuri:
        df_meciuri = pd.DataFrame(meciuri)
        st.dataframe(
            df_meciuri[["fixture_id", "echipa_gazda", "echipa_oaspete", "scor", "status"]],
            use_container_width=True,
        )

        optiuni = {
            f"{m['echipa_gazda']} — {m['echipa_oaspete']}": m
            for m in meciuri
        }
        ales = st.selectbox("Alege un meci de analizat", list(optiuni.keys()))
        meci = optiuni[ales]

        col1, col2, col3 = st.columns(3)
        half_life = col1.slider("Half-life decay (zile)", 10, 90, 30)
        k_shrinkage = col2.slider("Shrinkage (k)", 1, 30, 10)
        n_meciuri_istoric = col3.slider("Meciuri istorice per echipa", 5, 30, 20)

        if st.button("🧮 Analizeaza meciul", type="primary"):
            try:
                with st.spinner("Se trage istoricul si se calculeaza matricea..."):
                    istoric_gazda = data_source.istoric_echipa(meci["echipa_gazda_id"], n_meciuri_istoric)
                    istoric_oaspete = data_source.istoric_echipa(meci["echipa_oaspete_id"], n_meciuri_istoric)

                    if len(istoric_gazda) < 3 or len(istoric_oaspete) < 3:
                        st.warning(
                            "Prea putine meciuri istorice gasite pentru una din echipe "
                            "(sub 3) — rezultatul poate fi nesigur."
                        )

                    rezultat = analizeaza_meci(
                        istoric_gazda, istoric_oaspete,
                        half_life_zile=half_life, k_shrinkage=k_shrinkage,
                    )
                st.session_state["ultima_analiza"] = (meci, rezultat)
            except RuntimeError as e:
                st.error(str(e))

    if "ultima_analiza" in st.session_state:
        meci, rezultat = st.session_state["ultima_analiza"]
        st.markdown(f"### 📊 {meci['echipa_gazda']} — {meci['echipa_oaspete']}")

        rec = rezultat["reconciliere"]
        c1, c2 = st.columns(2)
        c1.metric("λ (goluri asteptate gazde)", f"{rec['lambda_gazde']:.2f}")
        c2.metric("μ (goluri asteptate oaspeti)", f"{rec['mu_oaspeti']:.2f}")

        st.markdown("#### Piete (probabilitate reala, din matricea de scor)")
        piete = rezultat["piete"]
        df_piete = pd.DataFrame([
            {"Piata": k, "Probabilitate": f"{v:.1%}", "Cota corecta": f"{(1 / v):.2f}" if v > 0 else "—"}
            for k, v in piete.items()
        ])
        st.dataframe(df_piete, use_container_width=True, hide_index=True)

        st.markdown("#### Top 5 scoruri probabile")
        df_scoruri = pd.DataFrame(
            [{"Scor": f"{h}-{a}", "Probabilitate": f"{p:.1%}"} for h, a, p in rezultat["top_scoruri"]]
        )
        st.dataframe(df_scoruri, use_container_width=True, hide_index=True)

        # Bonus: predictia proprie (nu e disponibila la acest API, vezi api_football.py)
        with st.expander("🔍 Comparatie cu predictia externa (bonus)"):
            pred = data_source.predictie_oficiala(meci["fixture_id"])
            if pred:
                st.json(pred)
            else:
                st.info("Nu e disponibila o predictie externa pentru acest API de date.")

    st.divider()
    st.caption(
        "Sursa principala de adevar: pipeline.py (Decay + Shrinkage + Dixon-Coles). "
        "Nu foloseste date inventate — doar istoricul real venit din API-Football."
    )

# ═══════════════════════════════════════════════════════════════════════
# TAB 2 — MODEL RAPID: RandomForest + cote de pe piata (semnal secundar)
# ═══════════════════════════════════════════════════════════════════════
with tab_rapid:
    st.subheader("Model rapid — cote + RandomForest")
    st.warning(
        "⚠️ Acest tab e un semnal SECUNDAR. Modelul a fost antrenat pe statistici "
        "reale per meci (xG, sut-uri, cornere) — daca nu ai acele date pentru "
        "meciul curent, nu inventa valori default; foloseste doar motorul Poisson din primul tab."
    )

    @st.cache_resource
    def incarca_model_1x2():
        try:
            return joblib.load("model_1x2.joblib")
        except Exception as e:
            st.error(f"Nu am putut incarca model_1x2.joblib: {e}")
            return None

    model_1x2 = incarca_model_1x2()

    FEATURES_1X2 = [
        "shots_home", "shots_away",
        "shots_on_target_home", "shots_on_target_away",
        "xG_home", "xG_away",
        "corners_home", "corners_away",
        "form_home", "form_away",
        "league_strength",
    ]

    st.markdown("#### Introdu statisticile reale ale meciului")
    st.caption("Fara valori inventate — completeaza doar ce ai confirmat (ex. din /fixtures/statistics).")

    cols = st.columns(3)
    valori = {}
    for i, feat in enumerate(FEATURES_1X2):
        valori[feat] = cols[i % 3].number_input(feat, value=None, step=0.1, format="%.2f")

    odd_1 = st.number_input("Cota 1", min_value=1.01, value=2.00, step=0.01)
    odd_X = st.number_input("Cota X", min_value=1.01, value=3.30, step=0.01)
    odd_2 = st.number_input("Cota 2", min_value=1.01, value=3.60, step=0.01)

    if st.button("🎯 Ruleaza modelul"):
        lipsesc = [f for f, v in valori.items() if v is None]
        if lipsesc:
            st.error(f"Lipsesc valori pentru: {', '.join(lipsesc)}. Nu completez automat cu date inventate.")
        elif model_1x2 is None:
            st.error("Modelul nu e incarcat.")
        else:
            X = [[valori[f] for f in FEATURES_1X2]]
            pred = model_1x2.predict(X)[0]
            proba = model_1x2.predict_proba(X)[0]

            inv = 1 / odd_1 + 1 / odd_X + 1 / odd_2
            prob_piata = {"1": (1 / odd_1) / inv, "X": (1 / odd_X) / inv, "2": (1 / odd_2) / inv}

            st.markdown(f"**Predictie model:** {['1', 'X', '2'][pred]}")
            df_comp = pd.DataFrame({
                "Rezultat": ["1", "X", "2"],
                "Probabilitate model": [f"{p:.1%}" for p in proba],
                "Probabilitate piata (din cote)": [f"{prob_piata[k]:.1%}" for k in ["1", "X", "2"]],
                "Cota": [odd_1, odd_X, odd_2],
            })
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — DESPRE
# ═══════════════════════════════════════════════════════════════════════
with tab_despre:
    st.markdown("""
    ### Despre Miliardarul

    Aplicatie personala de analiza a meciurilor de fotbal, construita pe doua motoare:

    - **Motor principal** — Poisson + Dixon-Coles, portat din sistemul Excel:
      decay exponential pe istoric, shrinkage Bayesian pentru esantioane mici,
      reconciliere λ/μ, corectie Dixon-Coles pentru scoruri mici, scanner de piete
      care calculeaza fiecare piata direct din matricea de scor (nu prin inmultire
      naiva de cote).
    - **Semnal secundar** — un model RandomForest antrenat pe statistici reale
      (xG, sut-uri, cornere), folosit doar ca a doua parere.

    Fara date inventate, niciodata — daca o statistica nu exista, campul ramane gol
    in loc sa fie completat cu o valoare default.

    ---
    *Uz personal. Nu constituie sfat financiar.*
    """)
