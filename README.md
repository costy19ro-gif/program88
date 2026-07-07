# Miliardarul — Poisson Avansat

Pipeline statistic real (Decay exponențial + Shrinkage Bayesian + Dixon-Coles),
portat din sistemul Excel, rulat pe date reale trase din API-Football, cu
un modul bonus opțional de comparație pe RapidAPI (tipstar).

## Instalare

```bash
pip install -r requirements.txt
```

## Configurare chei API

**Nu pune niciodată cheile direct în cod.** Sunt deja puse în `.streamlit/secrets.toml`
(NU urca acest fișier pe GitHub — adaugă-l în `.gitignore`).

**Pe Streamlit Community Cloud:** copiază conținutul din `.streamlit/secrets.toml`
în Settings → Secrets ale aplicației tale.

**Local (alternativ, variabile de mediu):**
```bash
export APISPORTS_KEY="cheia_ta_api_football"
export RAPIDAPI_KEY="cheia_ta_rapidapi"
streamlit run app.py
```

## Fișiere

- `pipeline.py` — motorul matematic pur (Decay, Shrinkage, Dixon-Coles, scanner piețe).
  Nu atinge rețeaua, testabil independent. **Neschimbat.**
- `api_football.py` — client NOU, sursa PRINCIPALĂ de date reale (api-sports.io).
  Endpoint-uri documentate oficial: `/fixtures?date=`, `/fixtures?team=&last=`,
  `/predictions?fixture=` (bonus).
- `rapidapi_predictions.py` — client BONUS opțional pentru predicțiile tipstar
  de pe RapidAPI. **Necesită un pas manual:** completează `ENDPOINT_PATH` cu
  path-ul real copiat din panoul "Code Snippets" (Python) al playground-ului
  RapidAPI — pagina lor e randată prin JavaScript și nu am putut extrage
  automat structura exactă a endpoint-ului. Până completezi asta, funcția
  returnează `None` fără să afecteze restul aplicației.
- `data_source.py` — strat de orchestrare, combină API-Football (principal) +
  RapidAPI (bonus). Păstrează aceleași funcții pe care le apela deja `app.py`.
- `app.py` — interfața Streamlit. Am adăugat o secțiune "🔍 Comparație cu
  predicții externe" la final, care afișează predicția proprie API-Football
  și (dacă e configurat) predicția RapidAPI, alături de rezultatul
  pipeline-ului Poisson — doar pentru comparație, nu înlocuiește analiza ta.

## De ce am schimbat sursa principală de date

Vechiul `data_source.py` folosea SportAPI7 prin RapidAPI, cu un endpoint de
istoric echipă marcat explicit ca **neconfirmat** ("model uzual pentru
SofaScore, verifică"). Am înlocuit-o cu API-Football (api-sports.io), ale
cărei endpoint-uri sunt documentate oficial și confirmate:
- `GET /fixtures?date=YYYY-MM-DD` — meciurile unei zile
- `GET /fixtures?team={id}&last={n}&status=FT-AET-PEN` — ultimele n meciuri
  terminate ale unei echipe
- `GET /predictions?fixture={id}` — predicția proprie API-Football (bonus)

Header-ul corect pentru aceste apeluri e `x-apisports-key` (diferit de
`X-RapidAPI-Key`, folosit doar pentru apelurile prin platforma RapidAPI).

## Cum funcționează pipeline-ul (pe scurt)

1. **Decay exponențial** — meciurile recente contează mult mai mult decât cele
   vechi (half-life configurabil, implicit 30 zile).
2. **Shrinkage Bayesian** — echipele cu istoric puțin (eșantion mic) sunt "trase"
   spre o medie de referință, ca să nu li se supraestimeze forța pe baza a
   2-3 meciuri norocoase.
3. **Reconciliere λ/μ** — o singură sursă de adevăr pentru expected goals,
   calculată din atac/apărare shrunk ale ambelor echipe.
4. **Dixon-Coles τ** — corectează probabilitățile scorurilor mici (0-0, 1-0,
   0-1, 1-1), care în Poisson independent sunt ușor greșite statistic.
5. **Scanner de piețe** — orice piață (1X2, GG, Over/Under, combo) se
   calculează ca probabilitate REALĂ direct din matricea finală, nu prin
   înmulțire naivă de cote (care presupune greșit independență).

## Cota zilnică (planuri gratuite)

Ambele API-uri au limite pe planul gratuit. `api_football.py` folosește cache
pe disc (6 ore) ca să nu ardă cereri degeaba la reîncărcări repetate ale
aceluiași meci. Dacă vezi erori de tip "quota exceeded", așteaptă resetarea
zilnică sau verifică planul din dashboard-ul tău.
