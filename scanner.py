"""
Scanner automat de bilete.

Cauta meciuri viitoare din DOUA surse:
  - RapidAPI ('Free API Live Football Data') — scanat pe INTERVAL DE DATE,
    nu pe liga. De ce: endpoint-ul pe liga (football-get-all-matches-by-league)
    are gauri reale de acoperire (verificat — Norvegia/Suedia intorc liste
    goale acolo, desi au meciuri reale). Endpoint-ul pe data
    (football-get-matches-by-date-and-league) e complet — grupeaza automat
    toate ligile active intr-o zi, deci nu mai trebuie sa alegem ligi deloc.
    Bonus: istoricul unei echipe acum include si meciurile din alte
    competitii (cupe etc.), nu doar liga principala.

  - football-data.org (~13 ligi mari, status=SCHEDULED corect, fara
    problema de sezon vechi) — ramane pe competitii alese explicit, pentru
    ca API-ul e organizat asa (nu are un echivalent "toate ligile pe data").

Ruleaza motorul Poisson/Dixon-Coles (pipeline.py) pe fiecare candidat, si
construieste automat categoriile de bilet, dupa regulile lui Julien.

LIMITARI reale — de stiut inainte sa te bazezi pe rezultat:

1. Prima repriza NU e folosita (desi football-data.org o are in raspuns) —
   categoria a fost scoasa complet din bilet.

2. "Data" meciurilor viitoare vine doar ca zi (fara ora exacta afisata) —
   verifica ora reala pe surse oficiale inainte sa pariezi.

3. Cele doua surse au sisteme de ID-uri de echipa COMPLET separate — nu se
   amesteca niciodata (football-data.org e prefixat "fd:").

4. Scanarea RapidAPI pe interval costa un apel per zi (istoric + viitor),
   cache 6h. Cu implicit 45 zile istoric + 7 zile viitor = ~52 apeluri —
   verifica sa nu depasesti cota zilnica gratuita (100/zi) daca mai faci
   si alte scanari in aceeasi zi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import data_source
import football_data_org as fdo
from pipeline import analizeaza_meci


@dataclass
class SelectieBilet:
    data: date
    echipa_gazda: str
    echipa_oaspete: str
    piata: str
    probabilitate: float
    cota: float


def _candidati_rapidapi_interval(
    zile_inainte: int, zile_istoric: int = 45, min_istoric: int = 5,
) -> list[dict]:
    """Toate meciurile viitoare din RapidAPI, indiferent de liga — scanate
    pe interval de date (vezi docstring-ul modulului pentru motiv)."""
    azi = date.today()
    meciuri = data_source.meciuri_interval(
        azi - timedelta(days=zile_istoric), azi + timedelta(days=zile_inainte)
    )

    candidati = []
    for m in meciuri:
        if m["terminat"] or m["data"] is None or m["data"] <= azi:
            continue

        istoric_gazda = data_source.istoric_echipa_din_liga(meciuri, m["echipa_gazda_id"], 20)
        istoric_oaspete = data_source.istoric_echipa_din_liga(meciuri, m["echipa_oaspete_id"], 20)
        if len(istoric_gazda) < min_istoric or len(istoric_oaspete) < min_istoric:
            continue

        rezultat = analizeaza_meci(istoric_gazda, istoric_oaspete)
        candidati.append({
            "data": m["data"],
            "echipa_gazda": m["echipa_gazda"],
            "echipa_oaspete": m["echipa_oaspete"],
            "piete": rezultat["piete"],
            "sursa": "rapidapi",
        })
    return candidati


def _candidati_din_competitie_fd(cod: str, zile_inainte: int, min_istoric: int = 5) -> list[dict]:
    """Meciurile viitoare dintr-o competitie football-data.org, cu piete calculate."""
    meciuri = fdo.meciuri_competitie_toate(cod)

    azi = date.today()
    prag = azi + timedelta(days=zile_inainte)

    candidati = []
    for m in meciuri:
        if m["terminat"] or m["data"] is None:
            continue
        if not (azi <= m["data"] <= prag):
            continue

        istoric_gazda = data_source.istoric_echipa_din_liga(meciuri, m["echipa_gazda_id"], 20)
        istoric_oaspete = data_source.istoric_echipa_din_liga(meciuri, m["echipa_oaspete_id"], 20)
        if len(istoric_gazda) < min_istoric or len(istoric_oaspete) < min_istoric:
            continue

        rezultat = analizeaza_meci(istoric_gazda, istoric_oaspete)
        candidati.append({
            "data": m["data"],
            "echipa_gazda": m["echipa_gazda"],
            "echipa_oaspete": m["echipa_oaspete"],
            "piete": rezultat["piete"],
            "sursa": "football_data",
        })
    return candidati


def verifica_surse_fd(coduri: list[str], zile_inainte: int = 7) -> list[dict]:
    """Verificare rapida (fara motor Poisson) pentru competitiile
    football-data.org alese — cate meciuri viitoare are fiecare."""
    azi = date.today()
    prag = azi + timedelta(days=zile_inainte)

    rezultate = []
    for cod in coduri:
        try:
            meciuri = fdo.meciuri_competitie_toate(cod)
        except RuntimeError as e:
            rezultate.append({"cod": cod, "meciuri_viitoare": None, "eroare": str(e)})
            continue
        nr = sum(
            1 for m in meciuri
            if not m["terminat"] and m["data"] is not None and azi <= m["data"] <= prag
        )
        rezultate.append({"cod": cod, "meciuri_viitoare": nr, "eroare": None})
    return rezultate


def verifica_rapidapi(zile_inainte: int = 7) -> dict:
    """Verificare rapida (fara motor Poisson) — cate meciuri viitoare
    gaseste RapidAPI in total, pe toate ligile, in intervalul dat."""
    azi = date.today()
    try:
        meciuri = data_source.meciuri_interval(azi, azi + timedelta(days=zile_inainte))
    except RuntimeError as e:
        return {"meciuri_viitoare": None, "eroare": str(e)}
    nr = sum(1 for m in meciuri if not m["terminat"] and m["data"] and m["data"] > azi)
    return {"meciuri_viitoare": nr, "eroare": None}


def scaneaza(
    surse_fd: list[str], scaneaza_rapidapi: bool = True,
    zile_inainte: int = 7, zile_istoric_rapidapi: int = 45, min_istoric: int = 5,
    progres_callback=None,
) -> list[dict]:
    """
    Scaneaza sursele alese, intoarce lista de candidati (meci + piete).

    `surse_fd`: lista de coduri football-data.org (ex. ["PL", "PD"]).
    `scaneaza_rapidapi`: daca True, scaneaza si RapidAPI (pe interval de
    date, toate ligile — nu mai e nevoie sa alegi ligi manual).
    """
    pasi = ([("rapidapi", None)] if scaneaza_rapidapi else []) + \
           [("football_data", cod) for cod in surse_fd]

    toti = []
    for i, (tip, ident) in enumerate(pasi):
        if progres_callback:
            progres_callback(i, len(pasi), "RapidAPI (toate ligile)" if tip == "rapidapi" else ident)
        try:
            if tip == "rapidapi":
                toti.extend(_candidati_rapidapi_interval(zile_inainte, zile_istoric_rapidapi, min_istoric))
            elif tip == "football_data":
                toti.extend(_candidati_din_competitie_fd(ident, zile_inainte, min_istoric))
        except RuntimeError:
            continue
    return toti


PIETE_SIGURE = ["1", "X", "2", "1X", "X2"]
PIETE_GOLURI = ["Peste_1.5", "Peste_2.5", "Sub_3.5"]

NUME_PIATA = {
    "1": "1 (victorie gazdă)",
    "X": "X (egal)",
    "2": "2 (victorie oaspete)",
    "1X": "1X",
    "X2": "X2",
    "12": "12 (fără egal)",
    "Peste_1.5": "Peste 1.5 goluri",
    "Peste_2.5": "Peste 2.5 goluri",
    "Sub_3.5": "Sub 3.5 goluri",
    "Gazde_marcheaza": "Gazdele marchează",
    "Oaspeti_marcheaza": "Oaspeții marchează",
    "GG": "Ambele echipe marchează (GG)",
}


def construieste_bilete(
    candidati: list[dict], cota_min_sigur: float = 1.30, cota_max_sigur: float = 1.80,
) -> dict:
    """
    Categoriile de bilet, cate 2 selectii fiecare (cand sunt destule
    meciuri gasite). Un meci apare o singura data in tot biletul.

    Pentru "sigur": cota_min_sigur..cota_max_sigur — un interval, nu doar
    un prag minim. Fara plafon superior, algoritmul ar putea alege tehnic
    o piata care trece de 1.30 dar are de fapt cota 4-5 (nesigura), doar
    pentru ca restul pietelor acelui meci erau si mai proaste.
    """
    folosite = set()

    def _cheie(c):
        return (c["echipa_gazda"], c["echipa_oaspete"], c["data"])

    def _alege(cands, piete_permise, cota_min=1.0, cota_max=float("inf"), n=2):
        optiuni = []
        for c in cands:
            if _cheie(c) in folosite:
                continue
            for piata in piete_permise:
                prob = c["piete"].get(piata)
                if not prob or prob <= 0:
                    continue
                cota = 1 / prob
                if not (cota_min <= cota <= cota_max):
                    continue
                optiuni.append((cota, c, piata, prob))
        optiuni.sort(key=lambda x: x[0])  # cele mai sigure (cota mica) primele

        alese = []
        for cota, c, piata, prob in optiuni:
            if _cheie(c) in folosite:
                continue
            alese.append(SelectieBilet(
                data=c["data"], echipa_gazda=c["echipa_gazda"],
                echipa_oaspete=c["echipa_oaspete"], piata=piata,
                probabilitate=prob, cota=cota,
            ))
            folosite.add(_cheie(c))
            if len(alese) >= n:
                break
        return alese

    return {
        "sigur": _alege(candidati, PIETE_SIGURE, cota_min=cota_min_sigur, cota_max=cota_max_sigur, n=2),
        "goluri": _alege(candidati, PIETE_GOLURI, cota_min=1.0, cota_max=2.0, n=2),
        "scor_echipe": _alege(candidati, ["Gazde_marcheaza", "Oaspeti_marcheaza"], cota_min=1.0, cota_max=2.0, n=2),
        "gg": _alege(candidati, ["GG"], cota_min=1.0, cota_max=2.5, n=2),
    }
