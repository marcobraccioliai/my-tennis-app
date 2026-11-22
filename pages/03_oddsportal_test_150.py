import csv
from datetime import date, timedelta
import html
import io
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# COSTANTI OPERATIVE FISSE (ALLINEATE A 01_CONVERTER_TENNIS.PY)
# ==============================================================================
SOGLIA_EDGE = 0.05      # Soglia minima Edge: 5.0%
FRAZIONE_KELLY = 0.25   # Quarter-Kelly
DEFAULT_N_SIM = 200000  # Allineato a 01_converter_tennis.py

MESI_IT: Dict[str, int] = {
    "gen": 1, "gennaio": 1,
    "feb": 2, "febbraio": 2,
    "mar": 3, "marzo": 3,
    "apr": 4, "aprile": 4,
    "mag": 5, "maggio": 5,
    "giu": 6, "giugno": 6,
    "lug": 7, "luglio": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "sett": 9, "settembre": 9,
    "ott": 10, "ottobre": 10,
    "nov": 11, "novembre": 11,
    "dic": 12, "dicembre": 12,
}


# ==============================================================================
# 1. DATABASE, ARCHIVIO JEFF SACKMANN E MOTORE MONTE CARLO (SOLO PIANO B)
# ==============================================================================
DATABASE_TENNISTI: Dict[str, Dict[str, Any]] = {
    "sinner": {"serv": 0.70, "ret": 0.43, "bonus": {"Cemento": 0.015, "Terra Battuta": 0.00, "Erba": 0.01}},
    "alcaraz": {"serv": 0.69, "ret": 0.44, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": 0.015}},
    "djokovic": {"serv": 0.69, "ret": 0.42, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.005, "Erba": 0.015}},
    "medvedev": {"serv": 0.68, "ret": 0.41, "bonus": {"Cemento": 0.02, "Terra Battuta": -0.02, "Erba": 0.00}},
    "zverev": {"serv": 0.71, "ret": 0.36, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.01, "Erba": -0.01}},
    "musetti": {"serv": 0.64, "ret": 0.39, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": 0.01}},
    "cobolli": {"serv": 0.63, "ret": 0.39, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": -0.01}},
    "berrettini": {"serv": 0.72, "ret": 0.33, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.005, "Erba": 0.025}},
    "arnaldi": {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "sonego": {"serv": 0.67, "ret": 0.35, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.005, "Erba": 0.01}},
    "darderi": {"serv": 0.64, "ret": 0.39, "bonus": {"Cemento": -0.015, "Terra Battuta": 0.025, "Erba": -0.02}},
    "tiafoe": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.015, "Erba": 0.005}},
    "prizmic": {"serv": 0.65, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "moroni": {"serv": 0.60, "ret": 0.35, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.015, "Erba": -0.015}},
    "passaro": {"serv": 0.64, "ret": 0.37, "bonus": {"Cemento": -0.005, "Terra Battuta": 0.015, "Erba": -0.01}},
    "basilashvili": {"serv": 0.68, "ret": 0.35, "bonus": {"Cemento": 0.01, "Terra Battuta": -0.005, "Erba": 0.01}},
    "masarova": {"serv": 0.62, "ret": 0.38, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.01, "Erba": -0.01}},
    "hercog": {"serv": 0.61, "ret": 0.38, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.015, "Erba": -0.01}},
    "podoroska": {"serv": 0.60, "ret": 0.40, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": -0.02}},
    "romero gormaz": {"serv": 0.59, "ret": 0.40, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": -0.02}},
    "samsonova": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.015}},
}


@st.cache_data(ttl=86400)
def scarica_archivio_sackmann() -> Dict[str, Dict[str, str]]:
    urls = [
        "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_players.csv",
        "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_players.csv",
    ]
    giocatori_web: Dict[str, Dict[str, str]] = {}
    for url in urls:
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    cognome = (row.get("name_last") or "").strip().lower()
                    if cognome and len(cognome) > 3:
                        giocatori_web[cognome] = {
                            "nome_completo": f"{(row.get('name_first') or '').strip()} {(row.get('name_last') or '').strip()}".strip(),
                            "paese": (row.get("ioc") or "").strip(),
                        }
        except Exception:
            continue
    return giocatori_web


def _normalizza_superficie(superficie: str) -> str:
    low = (superficie or "").strip().lower()
    if "terra" in low:
        return "Terra Battuta"
    if "erba" in low:
        return "Erba"
    return "Cemento"


def _estrai_data_da_testo(testo: str, data_riferimento: date) -> Optional[str]:
    """
    Estrae una data esplicita da una riga del pastone (es. '24 novembre 2026',
    '24 Nov 2026', '24/11', '24/11/2026', oppure 'domani'/'ieri').
    """
    if not testo:
        return None
    low = testo.strip().lower()

    m_slash = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", low)
    if m_slash:
        giorno = int(m_slash.group(1))
        mese = int(m_slash.group(2))
        anno_raw = m_slash.group(3)
        if anno_raw:
            anno = int(anno_raw)
            if anno < 100:
                anno += 2000
        else:
            anno = data_riferimento.year
            if data_riferimento.month == 12 and mese == 1:
                anno += 1
            elif data_riferimento.month == 1 and mese == 12:
                anno -= 1
        if 1 <= mese <= 12 and 1 <= giorno <= 31:
            try:
                return date(anno, mese, giorno).isoformat()
            except ValueError:
                pass

    m_txt = re.search(r"\b(\d{1,2})\s+([a-zà-ÿ]+)(?:\s+(\d{4}))?\b", low)
    if m_txt:
        giorno = int(m_txt.group(1))
        mese = MESI_IT.get(m_txt.group(2))
        anno_raw = m_txt.group(3)
        if mese and 1 <= giorno <= 31:
            anno = int(anno_raw) if anno_raw else data_riferimento.year
            if not anno_raw:
                if data_riferimento.month == 12 and mese == 1:
                    anno += 1
                elif data_riferimento.month == 1 and mese == 12:
                    anno -= 1
            try:
                return date(anno, mese, giorno).isoformat()
            except ValueError:
                pass

    if "domani" in low:
        return (data_riferimento + timedelta(days=1)).isoformat()
    if "ieri" in low:
        return (data_riferimento - timedelta(days=1)).isoformat()
    return None


def estrai_dati_modello_B(
    nome_giocatore: str,
    quota_giocatore: float,
    quota_avversario: float,
    archivio_sackmann: Dict[str, Dict[str, str]],
) -> Tuple[Dict[str, Any], str]:
    nome_pulito = nome_giocatore.lower()
    for key, dati in DATABASE_TENNISTI.items():
        if key in nome_pulito:
            return dati, "DB Locale"

    trovato_sackmann = False
    info_player = ""
    for cognome_ws, dati in archivio_sackmann.items():
        if cognome_ws in nome_pulito:
            trovato_sackmann = True
            info_player = f"{dati['nome_completo']} ({dati['paese']})"
            break

    prob_mercato = (1.0 / quota_giocatore) / ((1.0 / quota_giocatore) + (1.0 / quota_avversario))
    correzione = (prob_mercato - 0.50) * 0.08
    serv_stimato = float(np.clip(0.61 + correzione, 0.53, 0.68))
    ret_stimato = float(np.clip(0.37 + correzione, 0.30, 0.44))

    etichetta = f"Sackmann ({info_player})" if trovato_sackmann else "Stima Circuito (Market)"
    return (
        {
            "serv": serv_stimato,
            "ret": ret_stimato,
            "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0},
        },
        etichetta,
    )


def simula_punto(p_serv: float, rng: np.random.Generator) -> bool:
    return bool(rng.random() < p_serv)


def simula_game(p_serv: float, rng: np.random.Generator) -> bool:
    punti_serv, punti_risp = 0, 0
    while True:
        if punti_serv >= 3 and punti_risp >= 3:
            p1, p2 = simula_punto(p_serv, rng), simula_punto(p_serv, rng)
            if p1 and p2:
                return True
            if not p1 and not p2:
                return False
        else:
            if simula_punto(p_serv, rng):
                punti_serv += 1
            else:
                punti_risp += 1
            if punti_serv >= 4 and punti_serv - punti_risp >= 2:
                return True
            if punti_risp >= 4 and punti_risp - punti_serv >= 2:
                return False


def simula_tiebreak(p_serv_1: float, p_serv_2: float, rng: np.random.Generator) -> bool:
    p1_pts, p2_pts = 0, 0
    while True:
        serv_1 = ((p1_pts + p2_pts) // 1) % 2 == 0
        p_curr = p_serv_1 if serv_1 else (1.0 - p_serv_2)
        if simula_punto(p_curr, rng):
            p1_pts += 1
        else:
            p2_pts += 1
        if (p1_pts >= 7 or p2_pts >= 7) and abs(p1_pts - p2_pts) >= 2:
            return p1_pts > p2_pts


def simula_set(p_serv_1: float, p_serv_2: float, rng: np.random.Generator) -> bool:
    g1, g2 = 0, 0
    while True:
        t1 = (g1 + g2) % 2 == 0
        p_curr = p_serv_1 if t1 else (1.0 - p_serv_2)
        vince_g1 = simula_game(p_curr, rng) if t1 else not simula_game(1.0 - p_serv_2, rng)
        if t1 and vince_g1:
            g1 += 1
        elif t1 and not vince_g1:
            g2 += 1
        elif not t1 and not vince_g1:
            g1 += 1
        else:
            g2 += 1
        if g1 == 6 and g2 == 6:
            return simula_tiebreak(p_serv_1, p_serv_2, rng)
        if (g1 >= 6 or g2 >= 6) and abs(g1 - g2) >= 2:
            return g1 > g2


def esegui_monte_carlo(
    p_serv_1: float,
    p_serv_2: float,
    n_sim: int = DEFAULT_N_SIM,
    seed: int = 1042,
) -> float:
    rng = np.random.default_rng(seed)
    vittorie_1 = 0
    for _ in range(n_sim):
        s1, s2 = 0, 0
        while s1 < 2 and s2 < 2:
            if simula_set(p_serv_1, p_serv_2, rng):
                s1 += 1
            else:
                s2 += 1
        if s1 == 2:
            vittorie_1 += 1
    return (vittorie_1 / n_sim) * 100.0


def arrotonda_per_snai(importo_euro: float) -> float:
    if importo_euro < 1.0:
        return 0.0
    return round(max(1.0, round(importo_euro / 0.05) * 0.05), 2)


def valuta_scommessa(
    prob_percentuale: float,
    quota_bookmaker: Optional[float],
    bankroll: float,
    frazione: float = FRAZIONE_KELLY,
    edge_minimo: float = SOGLIA_EDGE,
) -> Tuple[Optional[float], float, str]:
    if quota_bookmaker is None or quota_bookmaker <= 1.0:
        return None, 0.0, "Quota non disp."

    p = prob_percentuale / 100.0
    q = 1.0 - p
    b = quota_bookmaker - 1.0
    if b <= 0:
        return None, 0.0, "No Value"

    edge = (p * quota_bookmaker) - 1.0
    if edge <= 0:
        return edge * 100.0, 0.0, "No Value"
    if edge < edge_minimo:
        return edge * 100.0, 0.0, "Stai fermo (Edge < 5%)"

    kelly_pieno = (b * p - q) / b
    stake_euro = arrotonda_per_snai(bankroll * (kelly_pieno * frazione))
    if stake_euro <= 0:
        return edge * 100.0, 0.0, "Stai fermo (< 1.00€)"

    return edge * 100.0, stake_euro, "VALUE BET"


def costruisci_tabella_simulazioni_singoli(
    singles: List[Dict[str, Any]],
    archivio_sackmann: Dict[str, Dict[str, str]],
    bankroll: float,
    n_sim: int,
    data_default: str,
    superficie_fallback: str = "Cemento",
) -> pd.DataFrame:
    tabella_risultati: List[Dict[str, Any]] = []
    surf_fb = _normalizza_superficie(superficie_fallback)

    for idx, m in enumerate(singles):
        ordine_pastone = m.get("Ordine Pastone", idx + 1)
        g1 = m["Giocatore 1"]
        g2 = m["Giocatore 2"]
        q1 = m["Quota 1"]
        q2 = m["Quota 2"]
        surf_key = _normalizza_superficie(m.get("Terreno") or surf_fb)

        s1_b, src1_b = estrai_dati_modello_B(g1, q1, q2, archivio_sackmann)
        s2_b, src2_b = estrai_dati_modello_B(g2, q2, q1, archivio_sackmann)

        p_serv_1_b = float(
            np.clip(((s1_b["serv"] + (1.0 - s2_b["ret"])) / 2.0) + s1_b["bonus"].get(surf_key, 0.0), 0.05, 0.95)
        )
        p_serv_2_b = float(
            np.clip(((s2_b["serv"] + (1.0 - s1_b["ret"])) / 2.0) + s2_b["bonus"].get(surf_key, 0.0), 0.05, 0.95)
        )

        prob_1_b = esegui_monte_carlo(p_serv_1_b, p_serv_2_b, n_sim=n_sim, seed=1042 + idx)
        prob_2_b = 100.0 - prob_1_b

        fair_1 = round(100.0 / prob_1_b, 2) if prob_1_b > 0 else None
        fair_2 = round(100.0 / prob_2_b, 2) if prob_2_b > 0 else None

        edge_1, stake_1, verdetto_1 = valuta_scommessa(prob_1_b, q1, bankroll)
        edge_2, stake_2, verdetto_2 = valuta_scommessa(prob_2_b, q2, bankroll)

        e1_cmp = edge_1 if edge_1 is not None else -9999.0
        e2_cmp = edge_2 if edge_2 is not None else -9999.0

        if e1_cmp >= e2_cmp:
            best_side = f"1 · {g1}"
            best_quota = q1
            best_prob = prob_1_b
            best_fair = fair_1
            best_edge = edge_1
            best_stake = stake_1
            best_esito = verdetto_1
        else:
            best_side = f"2 · {g2}"
            best_quota = q2
            best_prob = prob_2_b
            best_fair = fair_2
            best_edge = edge_2
            best_stake = stake_2
            best_esito = verdetto_2

        tabella_risultati.append(
            {
                "Ordine": ordine_pastone,
                "Data": m.get("Data") or data_default,
                "Rif. Pastone": m.get("Rif. Pastone", "-"),
                "Giocatore 1": g1,
                "Quota 1": q1,
                "Giocatore 2": g2,
                "Quota 2": q2,
                "Terreno": surf_key,
                "Torneo": m.get("Torneo", "-"),
                "Fonte G1": src1_b,
                "Fonte G2": src2_b,
                "Miglior Lato": best_side,
                "Quota Scelta": best_quota,
                "Quota Equa": best_fair,
                "Prob. Modello (%)": round(best_prob, 1),
                "Edge (%)": round(best_edge, 2) if best_edge is not None else None,
                "Stake (€)": best_stake,
                "Esito": best_esito,
            }
        )

    if not tabella_risultati:
        return pd.DataFrame(
            columns=[
                "Ordine",
                "Data",
                "Rif. Pastone",
                "Giocatore 1",
                "Quota 1",
                "Giocatore 2",
                "Quota 2",
                "Terreno",
                "Torneo",
                "Fonte G1",
                "Fonte G2",
                "Miglior Lato",
                "Quota Scelta",
                "Quota Equa",
                "Prob. Modello (%)",
                "Edge (%)",
                "Stake (€)",
                "Esito",
            ]
        )

    return (
        pd.DataFrame(tabella_risultati)
        .sort_values(by="Ordine", ascending=True)
        .reset_index(drop=True)
    )


def filtra_edge_positivo_favorito_140(df_sim: pd.DataFrame) -> pd.DataFrame:
    """
    Restituisce il sottoinsieme di righe in cui:
    - La simulazione trova un edge positivo (Edge > 0%, includendo VALUE BET e Stai fermo con edge > 0)
    - La quota del favorito (min tra Quota 1 e Quota 2) è >= 1.40
    Aggiunge all'estrema destra due colonne vuote: 'vincitore' e 'esito'.
    """
    base_cols = list(df_sim.columns) if df_sim is not None else []
    extra_cols = ["vincitore", "esito"]
    all_cols = base_cols + [c for c in extra_cols if c not in base_cols]

    if df_sim is None or df_sim.empty:
        return pd.DataFrame(columns=all_cols)

    q1 = pd.to_numeric(df_sim["Quota 1"], errors="coerce")
    q2 = pd.to_numeric(df_sim["Quota 2"], errors="coerce")
    quota_favorito = pd.concat([q1, q2], axis=1).min(axis=1)

    edge_num = pd.to_numeric(df_sim["Edge (%)"], errors="coerce")
    esito_str = df_sim["Esito"].astype(str)

    cond_edge_pos = (edge_num > 0) | (
        esito_str.isin(["VALUE BET", "Stai fermo (Edge < 5%)", "Stai fermo (< 1.00€)"])
    )
    cond_fav_140 = quota_favorito >= 1.40

    filtered = df_sim[cond_edge_pos & cond_fav_140].copy().reset_index(drop=True)
    filtered["vincitore"] = ""
    filtered["esito"] = ""
    return filtered[all_cols]


# ==============================================================================
# 2. PARSER ELASTICO PER PASTONA GIORNALIERA ODDSPORTAL (SOLO SINGOLI NON INIZIATI)
# ==============================================================================
UI_NOISE_EXACT = {
    "quote scommesse tennis",
    "tutte le partite",
    "live",
    "tutte le partitelive",
    "oggi",
    "domani",
    "ieri",
    "- le mie partite",
    "- calcio",
    "- tennis",
    "- basket",
    "- pallavolo",
    "le mie partite",
    "calcio",
    "basket",
    "pallavolo",
    "di più",
    "eventi",
    "inizio partita",
    "nascondi eventi conclusi",
    "eventiinizio partita",
    "finita",
    "arrow",
}

TERMINATED_TOKENS = {"finita", "annullata", "rinviata", "sospesa", "ritirato", "walkover"}


def _estrai_superficie_da_torneo(line: str) -> Optional[str]:
    m = re.search(r"\(([^)]+)\)\s*$", (line or "").strip())
    if not m:
        return None
    val = m.group(1).strip().lower()
    if "terra" in val:
        return "Terra Battuta"
    if "erba" in val:
        return "Erba"
    if "cemento" in val or "hard" in val:
        return "Cemento"
    return val.title()


def _pulisci_quota_token(tok: str) -> Optional[float]:
    t = (tok or "").strip()
    if t.startswith("-"):
        t = t[1:].strip()
    if not t:
        return None
    t = t.replace(",", ".")
    if re.fullmatch(r"\d+\.\d+", t):
        val = float(t)
        if 1.0 <= val <= 500.0:
            return val
    return None


def _is_stato_o_punteggio(tok: str) -> bool:
    t = (tok or "").strip()
    low = t.lower()
    if low in TERMINATED_TOKENS or low == "live":
        return True
    if re.fullmatch(r"(?:\d{1,2})?\d{2}:\d{2}", t):
        return True
    if re.fullmatch(r"(?:\d{1,2})?\d+S(?:T)?", t, re.IGNORECASE):
        return True
    if re.fullmatch(r"[0123]", t):
        return True
    return False


def _classifica_stato_match(marker: str) -> Tuple[str, str, str]:
    """
    Restituisce (stato, categoria_breve, motivo_esclusione):
    stato in {'NOT_STARTED', 'IN_PROGRESS', 'FINISHED'}.
    """
    m = (marker or "").strip()
    low = m.lower()
    if not m or m == "-":
        return "NOT_STARTED", "", ""
    if low in TERMINATED_TOKENS:
        return "FINISHED", "TERMINATA", f"Partita già terminata/chiusa (marcatore '{m}')"
    if low == "live" or re.fullmatch(r"(?:\d{1,2})?\d+S(?:T)?", m, re.IGNORECASE):
        return "IN_PROGRESS", "IN CORSO", f"Partita già iniziata o in corso (marcatore '{m}')"
    if re.fullmatch(r"(?:\d{1,2})?\d{2}:\d{2}", m):
        return "NOT_STARTED", "", ""
    return "NOT_STARTED", "", ""


def _is_nome_giocatore(s: str) -> bool:
    s_clean = (s or "").strip()
    if not s_clean or s_clean in {"-", ":"} or len(s_clean) < 2:
        return False
    low = s_clean.lower()
    if low in UI_NOISE_EXACT or low.startswith(("quote scommesse", "oggi", "domani", "ieri")):
        return False
    if _is_stato_o_punteggio(s_clean):
        return False
    if re.fullmatch(r"-?\s*\d+(?:[.,]\d+)?", s_clean):
        return False
    if _estrai_data_da_testo(s_clean, date.today()) and not re.search(r"\b[A-Za-zÀ-ÿ]{2,}\.", s_clean):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", s_clean))


def _verifica_doppio(torneo: str, sottotitolo: str, g1: str, g2: str) -> Tuple[bool, str]:
    if "/" in (g1 or "") or "/" in (g2 or ""):
        return True, "Nomi con '/' (coppia di doppio)"
    t_low = (torneo or "").lower()
    s_low = (sottotitolo or "").lower()
    if re.search(r"\bdoppi[oa]?\b", t_low) or re.search(r"\bdoppi[oa]?\b", s_low):
        return True, "Intestazione torneo/fase indicata come Doppio/Doppi"
    return False, ""


def parse_pastone_oddsportal(raw_text: str, data_riferimento: date) -> Dict[str, Any]:
    lines = [ln.strip() for ln in (raw_text or "").splitlines() if ln.strip()]
    data_default_str = data_riferimento.isoformat()

    current_surface: Optional[str] = None
    current_tournament: Optional[str] = None
    current_subheader: str = ""
    current_date_str: str = data_default_str
    last_marker_or_time: str = "-"

    singles_matches: List[Dict[str, Any]] = []
    doubles_matches: List[Dict[str, Any]] = []
    started_or_finished_matches: List[Dict[str, str]] = []
    dirty_items: List[Dict[str, str]] = []
    ordine_counter = 0

    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        low = ln.lower()

        if ln == "/":
            i += 1
            continue

        # Se la riga riporta una data esplicita (es. '24 novembre 2026', '24 Nov 2026', '24/11', 'domani')
        data_riga = _estrai_data_da_testo(ln, data_riferimento)
        if data_riga and not (low == "tennis" and i + 1 < n and (lines[i + 1] == "/" or _is_nome_giocatore(lines[i + 1]))):
            current_date_str = data_riga
            if low.startswith(("oggi", "domani", "ieri")):
                current_subheader = ln
            i += 1
            continue

        if low == "tennis" and i + 1 < n and (lines[i + 1] == "/" or _is_nome_giocatore(lines[i + 1])):
            k = i + 1
            if k < n and lines[k] == "/":
                k += 1
            country = lines[k] if k < n else ""
            k += 1
            if k < n and lines[k] == "/":
                k += 1
            tourn = lines[k] if k < n else ""

            if country and tourn and not tourn.lower().startswith(("oggi", "domani", "ieri")):
                surf = _estrai_superficie_da_torneo(tourn)
                current_tournament = f"{tourn} ({country})"
                current_subheader = ""
                if k + 1 < n:
                    next_ln = lines[k + 1]
                    next_dt = _estrai_data_da_testo(next_ln, data_riferimento)
                    if next_dt or next_ln.lower().startswith(("oggi", "domani", "ieri")):
                        current_subheader = next_ln
                        if next_dt:
                            current_date_str = next_dt
                        k += 1
                if surf:
                    current_surface = surf
                else:
                    dirty_items.append(
                        {
                            "blocco_o_riga": f"{ln} / {country} / {tourn}",
                            "motivo": (
                                f"Superficie non rilevata tra parentesi nell'intestazione del torneo "
                                f"(ereditata/fallback: {current_surface or 'Cemento'})."
                            ),
                        }
                    )
                i = k + 1
                continue

        if low in UI_NOISE_EXACT or low.startswith(("quote scommesse", "oggi", "domani", "ieri")):
            if low.startswith(("oggi", "domani", "ieri")):
                current_subheader = ln
                parsed_dt = _estrai_data_da_testo(ln, data_riferimento)
                if parsed_dt:
                    current_date_str = parsed_dt
            elif low in TERMINATED_TOKENS or low == "live":
                last_marker_or_time = ln
            i += 1
            continue

        if _is_stato_o_punteggio(ln):
            if not re.fullmatch(r"[0123]", ln):
                last_marker_or_time = ln
            i += 1
            continue

        if _is_nome_giocatore(ln) and i + 2 < n and lines[i + 1] in {"-", ":"} and _is_nome_giocatore(lines[i + 2]):
            ordine_counter += 1
            rif_pastone = f"#{ordine_counter} ({last_marker_or_time})"
            g1 = ln
            sep = lines[i + 1]
            g2 = lines[i + 2]
            j = i + 3
            quotes: List[float] = []
            bad_tokens: List[str] = []

            while j < n and len(quotes) < 2:
                tok = lines[j]
                tok_low = tok.lower()

                if tok_low == "tennis" and j + 1 < n and (lines[j + 1] == "/" or _is_nome_giocatore(lines[j + 1])):
                    break
                if _is_nome_giocatore(tok) and j + 2 < n and lines[j + 1] in {"-", ":"} and _is_nome_giocatore(lines[j + 2]):
                    break

                q = _pulisci_quota_token(tok)
                if q is not None:
                    quotes.append(q)
                elif (
                    tok != "-"
                    and not _is_stato_o_punteggio(tok)
                    and not tok_low.startswith(("oggi", "domani", "ieri"))
                ):
                    bad_tokens.append(tok)
                j += 1

            is_dbl, dbl_reason = _verifica_doppio(current_tournament or "", current_subheader, g1, g2)
            stato_match, cat_breve, stato_reason = _classifica_stato_match(last_marker_or_time)
            terreno_effettivo = current_surface or "Cemento"

            if len(quotes) == 2:
                if is_dbl:
                    doubles_matches.append(
                        {
                            "Data": current_date_str,
                            "Rif. Pastone": rif_pastone,
                            "Giocatore 1": g1,
                            "Quota 1": quotes[0],
                            "Giocatore 2": g2,
                            "Quota 2": quotes[1],
                            "Terreno": terreno_effettivo,
                            "Torneo": current_tournament or "-",
                            "Motivo Esclusione": dbl_reason,
                        }
                    )
                elif stato_match != "NOT_STARTED":
                    started_or_finished_matches.append(
                        {
                            "data": current_date_str,
                            "rif": rif_pastone,
                            "categoria": cat_breve,
                            "match": f"{g1} {sep} {g2} ({quotes[0]} / {quotes[1]})",
                            "torneo": current_tournament or "-",
                            "motivo": stato_reason,
                        }
                    )
                else:
                    singles_matches.append(
                        {
                            "Ordine Pastone": ordine_counter,
                            "Data": current_date_str,
                            "Rif. Pastone": rif_pastone,
                            "Giocatore 1": g1,
                            "Quota 1": quotes[0],
                            "Giocatore 2": g2,
                            "Quota 2": quotes[1],
                            "Terreno": terreno_effettivo,
                            "Torneo": current_tournament or "-",
                        }
                    )

                if bad_tokens:
                    dirty_items.append(
                        {
                            "blocco_o_riga": f"{rif_pastone} · {g1} {sep} {g2} (token anomali: {', '.join(bad_tokens)})",
                            "motivo": "Match con quote valide, ma rilevati token imprevisti durante la lettura.",
                        }
                    )
            else:
                dirty_items.append(
                    {
                        "blocco_o_riga": f"{rif_pastone} · {g1} {sep} {g2}",
                        "motivo": f"Match incompleto: trovate {len(quotes)} quote valide su 2 attese (quote assenti o non leggibili).",
                    }
                )

            i = j
            continue

        if ln == "-":
            dash_start = i
            while i < n and lines[i] == "-":
                i += 1
            count_d = i - dash_start
            dirty_items.append(
                {
                    "blocco_o_riga": " / ".join(["-"] * count_d),
                    "motivo": f"Sequenza di {count_d} separatore/i '-' isolato/i senza nomi giocatori o quote associate.",
                }
            )
            continue

        dirty_items.append(
            {
                "blocco_o_riga": ln,
                "motivo": "Riga non riconosciuta come intestazione torneo, match o rumore noto di interfaccia.",
            }
        )
        i += 1

    return {
        "singles": singles_matches,
        "doubles": doubles_matches,
        "started_or_finished": started_or_finished_matches,
        "dirty": dirty_items,
    }


def _render_scarti_courier_10pt(
    doubles: List[Dict[str, Any]],
    started_or_finished: List[Dict[str, str]],
    dirty: List[Dict[str, str]],
) -> str:
    """Formatta doppi esclusi, match già terminati/in corso e righe sporche in Courier 10pt in fondo."""
    righe: List[str] = []
    righe.append("=== MATCH DI DOPPIO ESCLUSI ===")
    if doubles:
        for d in doubles:
            righe.append(
                f"[DOPPIO] {d.get('Data', '-')} | {d.get('Rif. Pastone', '')} | {d.get('Giocatore 1', '')} ({d.get('Quota 1', '-')}) vs "
                f"{d.get('Giocatore 2', '')} ({d.get('Quota 2', '-')}) | "
                f"Terreno: {d.get('Terreno', '-')} | Torneo: {d.get('Torneo', '-')} | "
                f"Motivo: {d.get('Motivo Esclusione', 'Doppio')}"
            )
    else:
        righe.append("(nessun match di doppio escluso)")

    righe.append("")
    righe.append("=== MATCH SCARTATI PERCHÉ GIÀ TERMINATI O IN CORSO ===")
    if started_or_finished:
        for s in started_or_finished:
            cat = s.get("categoria", "TERMINATA / IN CORSO")
            righe.append(
                f"[{cat}] {s.get('data', '-')} | {s.get('rif', '')} | {s.get('match', '')} | "
                f"Torneo: {s.get('torneo', '-')} | {s.get('motivo', '')}"
            )
    else:
        righe.append("(nessun match terminato o in corso scartato)")

    righe.append("")
    righe.append("=== RIGHE / BLOCCHI SPORCHI SCARTATI ===")
    if dirty:
        for item in dirty:
            righe.append(
                f"[SPORCO] {item.get('blocco_o_riga', '')} -> {item.get('motivo', '')}"
            )
    else:
        righe.append("(nessuna riga sporca scartata)")

    testo_escaped = html.escape("\n".join(righe))
    return (
        '<div style="font-family: \'Courier New\', Courier, monospace; font-size: 10pt; '
        'line-height: 1.35; color: #888888; background-color: #111111; '
        'border: 1px dashed #444444; padding: 10px; margin-top: 12px; white-space: pre-wrap;">'
        f"{testo_escaped}</div>"
    )


# ==============================================================================
# 3. INTERFACCIA STREAMLIT (PAGES/03_ODDSPORTAL_TEST_150.PY - SIMULAZIONI PIANO B)
# ==============================================================================
st.set_page_config(page_title="03 - OddsPortal Test 150 (Piano B)", layout="wide")
st.title("🎾 03 · Simulazioni Piano B su Pastone OddsPortal (Solo Singoli Non Iniziati)")
st.caption(
    "Estrazione elastica dei match singoli non ancora iniziati nell'ordine del pastone "
    "ed esecuzione Monte Carlo (Piano B) con valutazione Value / No Value / Edge < 5%."
)

with st.sidebar:
    st.header("Parametri Modello & Cassa")
    data_riferimento = st.date_input("Data di fallback pastone", value=date.today())
    bankroll = st.number_input("Bankroll disponibile (€)", min_value=10.0, value=200.0, step=10.0)
    n_sim = st.select_slider(
        "Simulazioni Monte Carlo",
        options=[20000, 50000, 100000, 200000],
        value=DEFAULT_N_SIM,
    )

raw_input = st.text_area(
    "Incolla qui il pastone della pagina iniziale del tennis di OddsPortal",
    value="",
    height=320,
)

parsed = parse_pastone_oddsportal(raw_input, data_riferimento=data_riferimento)

if st.button("Simula Match Singoli (Piano B)", type="primary"):
    if not raw_input.strip():
        st.warning("Incolla prima il testo del pastone di OddsPortal.")
    else:
        singles = parsed["singles"]
        doubles = parsed["doubles"]
        started_or_finished = parsed["started_or_finished"]
        dirty = parsed["dirty"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Singoli Simulati (Non Iniziati)", len(singles))
        c2.metric("Terminati / In Corso Esclusi", len(started_or_finished))
        c3.metric("Match Doppio Esclusi", len(doubles))
        c4.metric("Righe / Blocchi Sporchi Scartati", len(dirty))

        if singles:
            archivio_sackmann = scarica_archivio_sackmann()
            with st.spinner(f"Esecuzione Piano B ({n_sim:,} simulazioni per match) su {len(singles)} singoli..."):
                df_sim = costruisci_tabella_simulazioni_singoli(
                    singles=singles,
                    archivio_sackmann=archivio_sackmann,
                    bankroll=bankroll,
                    n_sim=n_sim,
                    data_default=data_riferimento.isoformat(),
                )

            st.divider()
            st.subheader("🅱️ Tabella Risultati Simulazione Piano B (Singoli Non Iniziati · Ordine Pastone)")
            st.dataframe(df_sim, use_container_width=True, hide_index=True)

            df_filtered = filtra_edge_positivo_favorito_140(df_sim)
            st.divider()
            st.subheader("🎯 Sottoinsieme Edge Positivo (> 0%) con Favorito ≥ 1.40")
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun match singolo non ancora iniziato valido trovato da simulare.")

        st.divider()
        st.markdown(_render_scarti_courier_10pt(doubles, started_or_finished, dirty), unsafe_allow_html=True)
