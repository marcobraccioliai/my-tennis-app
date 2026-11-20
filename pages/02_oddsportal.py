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
# 1. DATABASE, ARCHIVIO JEFF SACKMANN E MOTORE MONTE CARLO (PIANO A & B)
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
    low = superficie.strip().lower()
    if "terra" in low:
        return "Terra Battuta"
    if "erba" in low:
        return "Erba"
    return "Cemento"


def estrai_dati_modello_A(nome_giocatore: str) -> Tuple[Dict[str, Any], str]:
    nome_pulito = nome_giocatore.lower()
    for key, dati in DATABASE_TENNISTI.items():
        if key in nome_pulito:
            return dati, "DB Locale"
    return (
        {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}},
        "Default (Circuito Base)",
    )


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
    seed: int = 42,
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


def costruisci_tabella_piano(
    rows: List[Dict[str, Any]],
    g1: str,
    g2: str,
    prob_1_pct: float,
    prob_2_pct: float,
    bankroll: float,
) -> pd.DataFrame:
    tabella_risultati: List[Dict[str, Any]] = []
    fair_1 = round(100.0 / prob_1_pct, 2) if prob_1_pct > 0 else None
    fair_2 = round(100.0 / prob_2_pct, 2) if prob_2_pct > 0 else None

    for r in rows:
        edge_1, stake_1, verdetto_1 = valuta_scommessa(prob_1_pct, r["Quota 1"], bankroll)
        edge_2, stake_2, verdetto_2 = valuta_scommessa(prob_2_pct, r["Quota 2"], bankroll)

        e1_cmp = edge_1 if edge_1 is not None else -9999.0
        e2_cmp = edge_2 if edge_2 is not None else -9999.0

        if e1_cmp >= e2_cmp:
            best_side = f"1 · {g1}"
            best_quota = r["Quota 1"]
            best_prob = prob_1_pct
            best_fair = fair_1
            best_edge = edge_1
            best_stake = stake_1
            best_esito = verdetto_1
        else:
            best_side = f"2 · {g2}"
            best_quota = r["Quota 2"]
            best_prob = prob_2_pct
            best_fair = fair_2
            best_edge = edge_2
            best_stake = stake_2
            best_esito = verdetto_2

        tabella_risultati.append(
            {
                "Bookmaker": r["Bookmaker"],
                "Payout": r["Payout"],
                f"Q1 ({g1})": r["Quota 1"],
                f"Q2 ({g2})": r["Quota 2"],
                "Miglior Lato": best_side,
                "Quota Scelta": best_quota,
                "Quota Equa": best_fair,
                "Prob. Modello (%)": round(best_prob, 1),
                "Edge (%)": round(best_edge, 2) if best_edge is not None else None,
                "Stake (€)": best_stake,
                "Esito": best_esito,
                "_sort_edge": best_edge if best_edge is not None else -9999.0,
            }
        )

    return (
        pd.DataFrame(tabella_risultati)
        .sort_values(by="_sort_edge", ascending=False)
        .drop(columns=["_sort_edge"])
        .reset_index(drop=True)
    )


# ==============================================================================
# 2. PARSER ELASTICO PER SINGOLO MATCH (ODDSPORTAL / CENTROQUOTE)
# ==============================================================================
NOISE_EXACT = {
    "richiedi bonus",
    "finale",
    "1° set",
    "2° set",
    "home/away",
    "over/under",
    "asian handicap",
    "correct score",
    "odd or even",
    "tutti i bonus",
    "quote pre-partita",
    "quote in tempo reale",
    "bookmakers",
    "payout",
    "1",
    "2",
    "-",
    ":",
    "/",
    ",",
    "(",
    ")",
}

NOISE_SUBSTRINGS = [
    "richiedi bonus",
    "tutti i bonus",
    "quote pre-partita",
    "quote in tempo reale",
    "home/away",
    "over/under",
    "asian handicap",
    "correct score",
    "odd or even",
    "1° set",
    "2° set",
    "1st set",
    "2nd set",
    "3rd set",
    "oggi,",
    "domani,",
    "ieri,",
]

MONTH_PATTERN = re.compile(
    r"^\d{1,2}\s+(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\w*(\s+\d{4})?,?$",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")
FLOAT_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
PCT_PATTERN = re.compile(r"^\d+(?:\.\d+)?%$")
BOOKIE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9.\-_ ]{1,30}$")


def _is_noise_line(line: str) -> bool:
    low = line.strip().lower()
    if not low:
        return True
    if low in NOISE_EXACT:
        return True
    if low.startswith("pastone"):
        return True
    if PCT_PATTERN.match(low):
        return True
    if TIME_PATTERN.match(low) or MONTH_PATTERN.match(low):
        return True
    if any(sub in low for sub in NOISE_SUBSTRINGS):
        return True
    return False


def estrai_giocatori_e_stato(raw_text: str) -> Tuple[str, str, bool]:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    is_live = any("quote in tempo reale" in ln.lower() for ln in lines)

    candidate_names: List[str] = []
    for idx, ln in enumerate(lines[:25]):
        low = ln.lower()
        if low.startswith("pastone"):
            continue
        if _is_noise_line(ln) and ln not in {"-", ":"}:
            continue
        if ln == ":":
            is_live = True
        if ln in {"-", ":"}:
            if candidate_names:
                g1 = candidate_names[-1]
                for nxt in lines[idx + 1 : idx + 6]:
                    nxt_clean = nxt.strip()
                    if nxt_clean.isdigit():
                        continue
                    if nxt_clean in {"-", ":", "/", "(", ")", ","}:
                        continue
                    if _is_noise_line(nxt_clean):
                        continue
                    if not FLOAT_PATTERN.match(nxt_clean) and not PCT_PATTERN.match(nxt_clean):
                        return g1, nxt_clean, is_live
        else:
            if not ln.isdigit() and not FLOAT_PATTERN.match(ln) and not PCT_PATTERN.match(ln):
                candidate_names.append(ln)

    return "", "", is_live


def parse_oddsportal_match(raw_text: str) -> Dict[str, Any]:
    player_1, player_2, is_live = estrai_giocatori_e_stato(raw_text)
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    warnings: List[str] = []

    rows: List[Dict[str, Any]] = []
    current_bookie: Optional[str] = None
    pending_quotes: List[Optional[float]] = []
    current_payout: Optional[str] = None

    def flush_row() -> None:
        nonlocal current_bookie, pending_quotes, current_payout
        if current_bookie and len(pending_quotes) >= 2:
            rows.append(
                {
                    "Bookmaker": current_bookie,
                    "Quota 1": pending_quotes[0],
                    "Quota 2": pending_quotes[1],
                    "Payout": current_payout or "-",
                }
            )
        current_bookie = None
        pending_quotes = []
        current_payout = None

    for ln in lines:
        if PCT_PATTERN.match(ln):
            if current_bookie and len(pending_quotes) >= 2:
                current_payout = ln
                flush_row()
            continue

        if _is_noise_line(ln):
            continue

        if ln == "-" and current_bookie is not None and len(pending_quotes) < 2:
            pending_quotes.append(None)
            continue

        if FLOAT_PATTERN.match(ln):
            val = float(ln)
            if current_bookie is not None and 1.00 <= val <= 500.0 and len(pending_quotes) < 2:
                pending_quotes.append(val)
            continue

        if BOOKIE_PATTERN.match(ln) and not ln.isdigit():
            if ln in {player_1, player_2}:
                continue
            if current_bookie is not None and len(pending_quotes) >= 2:
                flush_row()
            if (
                current_bookie is not None
                and current_bookie.lower() == ln.lower()
                and len(pending_quotes) == 0
            ):
                continue
            if current_bookie is not None and len(pending_quotes) == 0:
                current_bookie = ln
                continue
            if current_bookie is None:
                current_bookie = ln
                pending_quotes = []
                current_payout = None

    flush_row()

    if raw_text.strip() and (not player_1 or not player_2):
        warnings.append(
            "Nomi giocatori non rilevati automaticamente: puoi inserirli o verificarli nei campi qui sotto."
        )
    if raw_text.strip() and not rows:
        warnings.append("Nessuna riga bookmaker/quote riconosciuta nel testo incollato.")

    return {
        "player_1": player_1,
        "player_2": player_2,
        "is_live": is_live,
        "rows": rows,
        "warnings": warnings,
    }


# ==============================================================================
# 3. INTERFACCIA STREAMLIT (PAGES/02_ODDSPORTAL.PY)
# ==============================================================================
st.set_page_config(page_title="02 - OddsPortal Multi-Bookmaker", layout="wide")
st.title("🎾 02 · Confronto Multi-Bookmaker (OddsPortal / CentroQuote)")
st.caption("Analisi automatica in Piano A e Piano B allineata al motore Sackmann / Monte Carlo.")

with st.sidebar:
    st.header("Parametri Modello & Cassa")
    bankroll = st.number_input("Bankroll disponibile (€)", min_value=10.0, value=200.0, step=10.0)
    superficie = st.selectbox("Superficie", ["Cemento", "Terra Battuta", "Erba"], index=0)
    n_sim = st.select_slider(
        "Simulazioni Monte Carlo",
        options=[20000, 50000, 100000, 200000],
        value=DEFAULT_N_SIM,
    )

raw_input = st.text_area(
    "Incolla qui il testo copiato dalla pagina del singolo match",
    value="",
    height=260,
)

parsed = parse_oddsportal_match(raw_input)

if parsed["is_live"]:
    st.warning(
        "⚠️ Rilevata partita IN CORSO (Quote in tempo reale): la simulazione pre-match non conosce il punteggio attuale."
    )

for w in parsed["warnings"]:
    st.info(w)

col_g1, col_g2 = st.columns(2)
with col_g1:
    g1 = st.text_input("Giocatore 1 (Quota '1')", value=parsed["player_1"])
with col_g2:
    g2 = st.text_input("Giocatore 2 (Quota '2')", value=parsed["player_2"])

if st.button("Simula Piano A e Piano B", type="primary"):
    g1_clean = g1.strip()
    g2_clean = g2.strip()

    if not g1_clean or not g2_clean:
        st.error("Inserisci entrambi i nomi dei giocatori prima di procedere.")
    elif not parsed["rows"]:
        st.error("Non ho trovato righe di bookmaker valide da confrontare.")
    else:
        surf_key = _normalizza_superficie(superficie)
        archivio_sackmann = scarica_archivio_sackmann()

        q1_vals = [r["Quota 1"] for r in parsed["rows"] if isinstance(r["Quota 1"], float)]
        q2_vals = [r["Quota 2"] for r in parsed["rows"] if isinstance(r["Quota 2"], float)]
        q1_ref = float(np.mean(q1_vals)) if q1_vals else 2.0
        q2_ref = float(np.mean(q2_vals)) if q2_vals else 2.0

        with st.spinner(f"Esecuzione {n_sim:,} simulazioni Monte Carlo (Piano A & Piano B)..."):
            # Piano A (Interno / DB Locale + bonus superficie)
            s1_a, src1_a = estrai_dati_modello_A(g1_clean)
            s2_a, src2_a = estrai_dati_modello_A(g2_clean)
            p_serv_1_a = float(np.clip(((s1_a["serv"] + (1.0 - s2_a["ret"])) / 2.0) + s1_a["bonus"][surf_key], 0.05, 0.95))
            p_serv_2_a = float(np.clip(((s2_a["serv"] + (1.0 - s1_a["ret"])) / 2.0) + s2_a["bonus"][surf_key], 0.05, 0.95))
            prob_1_a = esegui_monte_carlo(p_serv_1_a, p_serv_2_a, n_sim=n_sim, seed=42)
            prob_2_a = 100.0 - prob_1_a

            # Piano B (Sackmann / Market + bonus superficie)
            s1_b, src1_b = estrai_dati_modello_B(g1_clean, q1_ref, q2_ref, archivio_sackmann)
            s2_b, src2_b = estrai_dati_modello_B(g2_clean, q2_ref, q1_ref, archivio_sackmann)
            p_serv_1_b = float(np.clip(((s1_b["serv"] + (1.0 - s2_b["ret"])) / 2.0) + s1_b["bonus"][surf_key], 0.05, 0.95))
            p_serv_2_b = float(np.clip(((s2_b["serv"] + (1.0 - s1_b["ret"])) / 2.0) + s2_b["bonus"][surf_key], 0.05, 0.95))
            prob_1_b = esegui_monte_carlo(p_serv_1_b, p_serv_2_b, n_sim=n_sim, seed=1042)
            prob_2_b = 100.0 - prob_1_b

        df_piano_a = costruisci_tabella_piano(
            rows=parsed["rows"],
            g1=g1_clean,
            g2=g2_clean,
            prob_1_pct=prob_1_a,
            prob_2_pct=prob_2_a,
            bankroll=bankroll,
        )
        df_piano_b = costruisci_tabella_piano(
            rows=parsed["rows"],
            g1=g1_clean,
            g2=g2_clean,
            prob_1_pct=prob_1_b,
            prob_2_pct=prob_2_b,
            bankroll=bankroll,
        )

        st.divider()
        st.subheader(f"🅰️ Tabella 1 · Piano A — {g1_clean} vs {g2_clean} ({surf_key})")
        st.markdown(
            f"{badge_fonte_html(g1_clean, src1_a)} {badge_fonte_html(g2_clean, src2_a)}",
            unsafe_allow_html=True,
        )
        ca1, ca2 = st.columns(2)
        ca1.metric(f"Prob. Piano A · {g1_clean} (1)", f"{prob_1_a:.1f}%")
        ca2.metric(f"Prob. Piano A · {g2_clean} (2)", f"{prob_2_a:.1f}%")
        st.dataframe(df_piano_a, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader(f"🅱️ Tabella 2 · Piano B — {g1_clean} vs {g2_clean} ({surf_key})")
        st.markdown(
            f"{badge_fonte_html(g1_clean, src1_b)} {badge_fonte_html(g2_clean, src2_b)}",
            unsafe_allow_html=True,
        )
        cb1, cb2 = st.columns(2)
        cb1.metric(f"Prob. Piano B · {g1_clean} (1)", f"{prob_1_b:.1f}%")
        cb2.metric(f"Prob. Piano B · {g2_clean} (2)", f"{prob_2_b:.1f}%")
        st.dataframe(df_piano_b, use_container_width=True, hide_index=True)
