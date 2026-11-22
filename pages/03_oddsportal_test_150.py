import csv
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


# ==============================================================================
# 1. DATABASE, ARCHIVIO JEFF SACKMANN E MOTORE MONTE CARLO (PIANO B - COMMENTATO)
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


def badge_fonte_html(nome_giocatore: str, fonte: str) -> str:
    """Restituisce un badge HTML colorato ad alta leggibilità per la provenienza dati."""
    if fonte.startswith("DB Locale"):
        bg = "#143D29"
        border = "#00FF7F"
        fg = "#00FF7F"
        icona = "🟢"
    elif fonte.startswith("Sackmann"):
        bg = "#103247"
        border = "#00D4FF"
        fg = "#00D4FF"
        icona = "🔵"
    else:
        bg = "#4A2E0B"
        border = "#FFB347"
        fg = "#FFB347"
        icona = "🟠"
    return (
        f'<span style="display:inline-block; background-color:{bg}; color:{fg}; '
        f'border:1px solid {border}; border-radius:6px; padding:4px 10px; '
        f'font-size:13px; font-weight:bold; margin:3px 6px 3px 0;">'
        f'{icona} {nome_giocatore}: {fonte}</span>'
    )


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


# --- SIMULAZIONI MONTE CARLO PIANO B (COMMENTATE TEMPORANEAMENTE PER TEST PARSER) ---
# def estrai_dati_modello_B(
#     nome_giocatore: str,
#     quota_giocatore: float,
#     quota_avversario: float,
#     archivio_sackmann: Dict[str, Dict[str, str]],
# ) -> Tuple[Dict[str, Any], str]:
#     nome_pulito = nome_giocatore.lower()
#     for key, dati in DATABASE_TENNISTI.items():
#         if key in nome_pulito:
#             return dati, "DB Locale"
#
#     trovato_sackmann = False
#     info_player = ""
#     for cognome_ws, dati in archivio_sackmann.items():
#         if cognome_ws in nome_pulito:
#             trovato_sackmann = True
#             info_player = f"{dati['nome_completo']} ({dati['paese']})"
#             break
#
#     prob_mercato = (1.0 / quota_giocatore) / ((1.0 / quota_giocatore) + (1.0 / quota_avversario))
#     correzione = (prob_mercato - 0.50) * 0.08
#     serv_stimato = float(np.clip(0.61 + correzione, 0.53, 0.68))
#     ret_stimato = float(np.clip(0.37 + correzione, 0.30, 0.44))
#
#     etichetta = f"Sackmann ({info_player})" if trovato_sackmann else "Stima Circuito (Market)"
#     return (
#         {
#             "serv": serv_stimato,
#             "ret": ret_stimato,
#             "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0},
#         },
#         etichetta,
#     )
#
#
# def simula_punto(p_serv: float, rng: np.random.Generator) -> bool:
#     return bool(rng.random() < p_serv)
#
#
# def simula_game(p_serv: float, rng: np.random.Generator) -> bool:
#     punti_serv, punti_risp = 0, 0
#     while True:
#         if punti_serv >= 3 and punti_risp >= 3:
#             p1, p2 = simula_punto(p_serv, rng), simula_punto(p_serv, rng)
#             if p1 and p2:
#                 return True
#             if not p1 and not p2:
#                 return False
#         else:
#             if simula_punto(p_serv, rng):
#                 punti_serv += 1
#             else:
#                 punti_risp += 1
#             if punti_serv >= 4 and punti_serv - punti_risp >= 2:
#                 return True
#             if punti_risp >= 4 and punti_risp - punti_serv >= 2:
#                 return False
#
#
# def simula_tiebreak(p_serv_1: float, p_serv_2: float, rng: np.random.Generator) -> bool:
#     p1_pts, p2_pts = 0, 0
#     while True:
#         serv_1 = ((p1_pts + p2_pts) // 1) % 2 == 0
#         p_curr = p_serv_1 if serv_1 else (1.0 - p_serv_2)
#         if simula_punto(p_curr, rng):
#             p1_pts += 1
#         else:
#             p2_pts += 1
#         if (p1_pts >= 7 or p2_pts >= 7) and abs(p1_pts - p2_pts) >= 2:
#             return p1_pts > p2_pts
#
#
# def simula_set(p_serv_1: float, p_serv_2: float, rng: np.random.Generator) -> bool:
#     g1, g2 = 0, 0
#     while True:
#         t1 = (g1 + g2) % 2 == 0
#         p_curr = p_serv_1 if t1 else (1.0 - p_serv_2)
#         vince_g1 = simula_game(p_curr, rng) if t1 else not simula_game(1.0 - p_serv_2, rng)
#         if t1 and vince_g1:
#             g1 += 1
#         elif t1 and not vince_g1:
#             g2 += 1
#         elif not t1 and not vince_g1:
#             g1 += 1
#         else:
#             g2 += 1
#         if g1 == 6 and g2 == 6:
#             return simula_tiebreak(p_serv_1, p_serv_2, rng)
#         if (g1 >= 6 or g2 >= 6) and abs(g1 - g2) >= 2:
#             return g1 > g2
#
#
# def esegui_monte_carlo(
#     p_serv_1: float,
#     p_serv_2: float,
#     n_sim: int = DEFAULT_N_SIM,
#     seed: int = 1042,
# ) -> float:
#     rng = np.random.default_rng(seed)
#     vittorie_1 = 0
#     for _ in range(n_sim):
#         s1, s2 = 0, 0
#         while s1 < 2 and s2 < 2:
#             if simula_set(p_serv_1, p_serv_2, rng):
#                 s1 += 1
#             else:
#                 s2 += 1
#         if s1 == 2:
#             vittorie_1 += 1
#     return (vittorie_1 / n_sim) * 100.0
#
#
# def arrotonda_per_snai(importo_euro: float) -> float:
#     if importo_euro < 1.0:
#         return 0.0
#     return round(max(1.0, round(importo_euro / 0.05) * 0.05), 2)
#
#
# def valuta_scommessa(
#     prob_percentuale: float,
#     quota_bookmaker: Optional[float],
#     bankroll: float,
#     frazione: float = FRAZIONE_KELLY,
#     edge_minimo: float = SOGLIA_EDGE,
# ) -> Tuple[Optional[float], float, str]:
#     if quota_bookmaker is None or quota_bookmaker <= 1.0:
#         return None, 0.0, "Quota non disp."
#
#     p = prob_percentuale / 100.0
#     q = 1.0 - p
#     b = quota_bookmaker - 1.0
#     if b <= 0:
#         return None, 0.0, "No Value"
#
#     edge = (p * quota_bookmaker) - 1.0
#     if edge <= 0:
#         return edge * 100.0, 0.0, "No Value"
#     if edge < edge_minimo:
#         return edge * 100.0, 0.0, "Stai fermo (Edge < 5%)"
#
#     kelly_pieno = (b * p - q) / b
#     stake_euro = arrotonda_per_snai(bankroll * (kelly_pieno * frazione))
#     if stake_euro <= 0:
#         return edge * 100.0, 0.0, "Stai fermo (< 1.00€)"
#
#     return edge * 100.0, stake_euro, "VALUE BET"
#
#
# def costruisci_tabella_piano(
#     rows: List[Dict[str, Any]],
#     g1: str,
#     g2: str,
#     prob_1_pct: float,
#     prob_2_pct: float,
#     bankroll: float,
# ) -> pd.DataFrame:
#     tabella_risultati: List[Dict[str, Any]] = []
#     fair_1 = round(100.0 / prob_1_pct, 2) if prob_1_pct > 0 else None
#     fair_2 = round(100.0 / prob_2_pct, 2) if prob_2_pct > 0 else None
#
#     for r in rows:
#         edge_1, stake_1, verdetto_1 = valuta_scommessa(prob_1_pct, r["Quota 1"], bankroll)
#         edge_2, stake_2, verdetto_2 = valuta_scommessa(prob_2_pct, r["Quota 2"], bankroll)
#
#         e1_cmp = edge_1 if edge_1 is not None else -9999.0
#         e2_cmp = edge_2 if edge_2 is not None else -9999.0
#
#         if e1_cmp >= e2_cmp:
#             best_side = f"1 · {g1}"
#             best_quota = r["Quota 1"]
#             best_prob = prob_1_pct
#             best_fair = fair_1
#             best_edge = edge_1
#             best_stake = stake_1
#             best_esito = verdetto_1
#         else:
#             best_side = f"2 · {g2}"
#             best_quota = r["Quota 2"]
#             best_prob = prob_2_pct
#             best_fair = fair_2
#             best_edge = edge_2
#             best_stake = stake_2
#             best_esito = verdetto_2
#
#         tabella_risultati.append(
#             {
#                 "Bookmaker": r["Bookmaker
