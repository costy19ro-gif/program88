"""
Miliardarul — Poisson Avansat (Decay + Shrinkage + Dixon-Coles)
==================================================================
Aplicatie Streamlit care ruleaza pipeline-ul statistic REAL (nu date
simulate) pe baza istoricului real de meciuri, tras dintr-un API.
"""

from datetime import date
import streamlit as st

from pipeline import analizeaza_meci
import data_source as ds

st.set_page_config(page_title="Miliardarul — Poisson Avansat", layout="wide")
st.title("📊 Miliardarul — Decay + Shrinkage + Dixon-Coles")
st.caption("Date reale, pipeline statistic complet — nu simulare bazata pe hash")

# ---------------------------------------------------------------------------
# Sidebar — parametrii pipeline-ului (aceiasi pe care i-am ales impreuna in Excel)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Parametrii pipeline-ului")
    half_life = st.slider("Half-life decay (zile)", 15, 90, 30, step=5)
    k_shrinkage = st.slider("k Shrinkage Bayesian", 5, 20, 10)
    rho = st.slider("ρ (rho) Dixon-Coles", -0.30, 0.0, -0.18, step=0.01)
    n_meciuri_istoric = st.slider("Nr. meciuri istoric per echipa", 10, 30, 20)
    cota_minima = st.number_input("Cotă minimă (prag calificare piață)", 1.01, 5.0, 1.30, step=0.01)

st.markdown("---")

# ---------------------------------------------------------------------------
# Selectorul de meci — tras din API, nu din lista statica hash-uita
# ---------------------------------------------------------------------------
try:
    with st.spinner("Se încarcă meciurile de azi..."):
        meciuri_azi = ds.meciuri_azi()
except Exception as e:
    st.error(f"Nu am putut încărca meciurile din API: {e}")
    st.info(
        "Verifică: (1) ai setat APISPORTS_KEY ca variabilă de mediu / secret Streamlit, "
        "(2) cheia e validă și nu ai depășit cota zilnică (planul gratuit are o limită de cereri/zi)."
    )
    st.stop()

if not meciuri_azi:
    st.warning("Nu am găsit meciuri pentru azi.")
    st.stop()

optiuni = {
    f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} "
    f"({m.get('tournament', {}).get('name', '')})": m
    for m in meciuri_azi
}
selectie = st.selectbox("🏟️ Alege meciul:", list(optiuni.keys()))
meci = optiuni[selectie]

home_id = meci["homeTeam"]["id"]
away_id = meci["awayTeam"]["id"]
gazde_nume = meci["homeTeam"]["name"]
oaspeti_nume = meci["awayTeam"]["name"]
fixture_id = meci.get("fixture_id")

st.markdown(
    f"<div style='background-color:#00e6ff;padding:12px;border-radius:4px;"
    f"text-align:center;margin-bottom:20px;'>"
    f"<h2 style='color:black;margin:0;'>{gazde_nume} &nbsp;:&nbsp; {oaspeti_nume}</h2></div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Rulam pipeline-ul complet pe date reale
# ---------------------------------------------------------------------------
if st.button("🔄 Analizează (rulează pipeline-ul complet)", type="primary"):
    try:
        with st.spinner(f"Se încarcă istoricul lui {gazde_nume}..."):
            istoric_gazde = ds.istoric_echipa(home_id, n_meciuri_istoric)
        with st.spinner(f"Se încarcă istoricul lui {oaspeti_nume}..."):
            istoric_oaspeti = ds.istoric_echipa(away_id, n_meciuri_istoric)
    except Exception as e:
        st.error(f"Eroare la încărcarea istoricului: {e}")
        st.stop()

    if len(istoric_gazde) < 5 or len(istoric_oaspeti) < 5:
        st.warning(
            f"Istoric insuficient (Gazde: {len(istoric_gazde)} meciuri, "
            f"Oaspeți: {len(istoric_oaspeti)} meciuri). Rezultatele pot fi nesigure "
            "sub 5 meciuri per echipă."
        )

    rezultat = analizeaza_meci(
        istoric_gazde, istoric_oaspeti,
        data_referinta=date.today(),
        half_life_zile=half_life,
        k_shrinkage=k_shrinkage,
        rho=rho,
    )

    st.session_state["rezultat"] = rezultat
    st.session_state["nume_echipe"] = (gazde_nume, oaspeti_nume)
    st.session_state["fixture_id"] = fixture_id

# ---------------------------------------------------------------------------
# Afisare rezultate (daca exista deja o analiza in sesiune)
# ---------------------------------------------------------------------------
if "rezultat" in st.session_state:
    rez = st.session_state["rezultat"]
    gazde_nume, oaspeti_nume = st.session_state["nume_echipe"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Decay + Shrinkage")
        g, o, r = rez["gazde_stats"], rez["oaspeti_stats"], rez["reconciliere"]
        st.write(f"**{gazde_nume}** — Atac decay: `{g['atac_decay']:.2f}` | "
                 f"Apărare decay: `{g['aparare_decay']:.2f}` | n efectiv: `{g['n_efectiv']:.1f}`")
        st.write(f"**{oaspeti_nume}** — Atac decay: `{o['atac_decay']:.2f}` | "
                 f"Apărare decay: `{o['aparare_decay']:.2f}` | n efectiv: `{o['n_efectiv']:.1f}`")
        st.markdown("---")
        st.metric("λ Gazde (canonic, shrunk)", f"{r['lambda_gazde']:.3f}")
        st.metric("μ Oaspeți (canonic, shrunk)", f"{r['mu_oaspeti']:.3f}")

    with col2:
        st.subheader("🎯 Scoruri cele mai probabile (Dixon-Coles)")
        for h, a, p in rez["top_scoruri"]:
            st.write(f"**{h} - {a}** → `{p:.1%}`")

    st.markdown("---")
    st.subheader("📋 Scanner de piețe")

    piete = rez["piete"]
    randuri = []
    for nume, prob in piete.items():
        cota_echiv = 1 / prob if prob > 0 else float("inf")
        califica = "✅ DA" if cota_echiv <= cota_minima else "—"
        randuri.append({"Piață": nume, "Probabilitate": f"{prob:.1%}",
                         "Cotă echivalentă": f"{cota_echiv:.2f}", "Califică": califica})

    st.dataframe(randuri, use_container_width=True, hide_index=True)

    st.caption(
        f"Parametri folosiți: half-life={half_life} zile, k={k_shrinkage}, "
        f"ρ={rho}, prag cotă minimă={cota_minima}"
    )

    # -----------------------------------------------------------------------
    # Sectiune BONUS — comparatie cu predictii externe (nu inlocuieste pipeline-ul)
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 Comparație cu predicții externe (bonus)")

    fid = st.session_state.get("fixture_id")
    predictie_af = ds.predictie_oficiala(fid) if fid else None
    predictii_rapid = ds.predictii_bonus_rapidapi()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**API-Football (predicție proprie)**")
        if predictie_af:
            p = predictie_af.get("predictions", {})
            st.write(f"Câștigător favorit: `{p.get('winner', {}).get('name', 'N/A')}`")
            st.write(f"Under/Over sugerat: `{p.get('under_over', 'N/A')}`")
            st.write(f"Goluri — Gazde: `{p.get('goals', {}).get('home', 'N/A')}` | "
                     f"Oaspeți: `{p.get('goals', {}).get('away', 'N/A')}`")
        else:
            st.caption("Nu este disponibilă pentru acest meci (sau planul gratuit nu o include).")

    with col_b:
        st.markdown("**RapidAPI — tipstar (bonus)**")
        if predictii_rapid:
            st.json(predictii_rapid[:3])
        else:
            st.caption(
                "Neconfigurat încă — completează `ENDPOINT_PATH` în "
                "`rapidapi_predictions.py` cu path-ul real din Code Snippets "
                "(vezi comentariul din fișier). Pipeline-ul principal nu depinde de asta."
            )
