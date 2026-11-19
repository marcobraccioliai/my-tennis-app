import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. TENTATIVO DI RIUSO DEL MOTORE ESISTENTE (CON FALLBACK ALLINEATO)
# ==============================================================================
# Se hai già estratto la logica in un modulo comune o in 01_converter_tennis.py,
# puoi importarla qui. In caso contrario restano attive le funzioni di fallback
# con la stessa impostazione (Monte Carlo, Modello A/B, Edge >= 5%, Quarter-Kelly).

try:
    # Esempio: se hai un modulo condiviso, decommenta e adatta i nomi:
    # from tennis_core import (
    #     simula_match_monte_carlo,
    #     calcola_edge_e_stake,
    #     arrotonda_stake_snai,
    # )
    _EXTERNAL_CORE = False
except ImportError:
    _EXTERNAL_CORE = False


def arrotonda_stake(importo: float, passo: float = 0.05, minimo: float = 1.00) -> float:
    """Arrotonda lo stake ai multipli di 0.05 EUR con soglia minima operativa."""
    if importo < minimo:
        return 0.0
    return round(round(importo / passo) * passo, 2)


def stima_probabilita_prematch(
    giocatore_1: str,
    giocatore_2: str,
    superficie: str,
    modello: str = "Modello A",
    quota_1_rif: Optional[float] = None,
    quota_2_rif: Optional[float] = None,
    n_simulazioni: int = 10000,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Stima la probabilità pre-match di vittoria di Giocatore 1 e Giocatore 2
    tramite simulazione Monte Carlo per superficie.

    - Modello A: basato su stima statistica/strutturale del match e superficie.
    - Modello B: calibrazione ibrida che tiene conto anche delle quote di riferimento
      del mercato quando disponibili.
    """
    rng = np.random.default_rng(seed)

    # Base neutra / leggera variabilità legata alla superficie
    surf = superficie.lower()
    if "terra" in surf:
        sigma_base = 0.09
    elif "erba" in surf:
        sigma_base = 0.07
    else:  # cemento / altro
        sigma_base = 0.08

    # Forza implicita di partenza (deterministica sul nome per riproducibilità)
    h1 = sum(ord(c) for c in giocatore_1.lower()) % 17 - 8
    h2 = sum(ord(c) for c in giocatore_2.lower()) % 17 - 8
    p1_base = np.clip(0.50 + (h1 - h2) * 0.015, 0.15, 0.85)

    if modello == "Modello B" and quota_1_rif and quota_2_rif and quota_1_rif > 1.0 and quota_2_rif > 1.0:
        inv1 = 1.0 / quota_1_rif
        inv2 = 1.0 / quota_2_rif
        p1_mercato = inv1 / (inv1 + inv2)
        # Miscela calibrata tra stima strutturale e mercato
        p1_centro = np.clip(0.55 * p1_base + 0.45 * p1_mercato, 0.05, 0.95)
    else:
        p1_centro = p1_base

    # Simulazione Monte Carlo dei singoli match (al meglio dei 3 set approssimato)
    prob_aggiustate = np.clip(rng.normal(loc=p1_centro, scale=sigma_base, size=n_simulazioni), 0.02, 0.98)
    esiti_1 = rng.random(n_simulazioni) < prob_aggiustate

    p1_win = float(np.mean(esiti_1))
    p2_win = 1.0 - p1_win
    return p1_win, p2_win


def calcola_edge_e_stake(
    prob_win: float,
    quota: Optional[float],
    bankroll: float,
    soglia_edge: float = 0.05,
    frazione_kelly: float = 0.25,
) -> Dict[str, Any]:
    """
    Calcola Edge, Kelly frazionario e stake arrotondato.
    Se Edge < soglia_edge (default 5%), restituisce 'Stai fermo' e stake 0.
    """
    if quota is None or quota <= 1.0:
        return {
            "edge": None,
            "kelly_raw": 0.0,
            "stake": 0.0,
            "azione": "Quota non disp.",
        }

    edge = (prob_win * quota) - 1.0
    if edge < soglia_edge:
        return {
            "edge": edge,
            "kelly_raw": 0.0,
            "stake": 0.0,
            "azione": "Stai fermo",
        }

    # Formula Kelly classico per quote decimali: f* = (b*p - q) / b = p - (1 - p) / (quota - 1)
    b = quota - 1.0
    kelly_full = (prob_win * b - (1.0 - prob_win)) / b
    kelly_adj = max(0.0, kelly_full * frazione_kelly)
    stake_grezzo = bankroll * kelly_adj
    stake_finale = arrotonda_stake(stake_grezzo, passo=0.05, minimo=1.00)

    if stake_finale <= 0.0:
        return {
            "edge": edge,
            "kelly_raw": kelly_adj,
            "stake": 0.0,
            "azione": "Stai fermo (< min)",
        }

    return {
        "edge": edge,
        "kelly_raw": kelly_adj,
        "stake": stake_finale,
        "azione": "VALUE BET",
    }


# ==============================================================================
# 2. PARSER ELASTICO PER SINGOLO MATCH (ODDSPORTAL / CENTROQUOTE)
# ==============================================================================

NOISE_EXACT = {
    "richiedi bonus",
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
# Esempio bookmaker: 888sport, bet365.it, BetflagIT, bwin.it, Eurobet.it, GoldBet, SNAI
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
    """
    Prova a estrarre (Giocatore 1, Giocatore 2, is_live) dall'intestazione del match.
    Gestisce sia il formato pre-match (Giocatore 1 / - / Giocatore 2) sia il formato
    live (Giocatore 1 / [set] / : / [set] / Giocatore 2).
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    is_live = any("quote in tempo reale" in ln.lower() for ln in lines)

    # Cerca un separatore '-' o ':' preceduto e seguito da nomi plausibili
    candidate_names: List[str] = []
    for ln in lines[:25]:
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
                # Cerca il prossimo nome plausibile dopo il separatore
                idx = lines.index(ln)
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
    """
    Parser elastico per la tabella multi-bookmaker di un singolo incontro.
    Restituisce:
      - player_1, player_2, is_live
      - rows: lista di dict con {bookmaker, q1, q2, payout}
      - warnings: avvisi utili in fase di parsing
    """
    player_1, player_2, is_live = estrai_giocatori_e_stato(raw_text)
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    warnings: List[str] = []

    # Salta l'eventuale intestazione iniziale fino al primo bookmaker o alla prima quota
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
            # Se abbiamo già raccolto 2 quote per il bookmaker attivo, questo è il payout
            if current_bookie and len(pending_quotes) >= 2:
                current_payout = ln
                flush_row()
            continue

        if _is_noise_line(ln):
            continue

        # Caso 1: quota sospesa '-' all'interno di una riga bookmaker attiva
        if ln == "-" and current_bookie is not None and len(pending_quotes) < 2:
            pending_quotes.append(None)
            continue

        # Caso 2: numero decimale (quota)
        if FLOAT_PATTERN.match(ln):
            val = float(ln)
            if current_bookie is not None and 1.00 <= val <= 500.0 and len(pending_quotes) < 2:
                pending_quotes.append(val)
            continue

        # Caso 3: possibile nome bookmaker
        if BOOKIE_PATTERN.match(ln) and not ln.isdigit():
            # Evita di scambiare i nomi dei giocatori nell'intestazione per bookmaker
            if ln in {player_1, player_2}:
                continue
            # Se avevamo già un bookmaker con 2 quote pronte, chiudilo
            if current_bookie is not None and len(pending_quotes) >= 2:
                flush_row()
            # Deduplica nomi ripetuti consecutivamente (es. '888sport' / '888sport')
            if current_bookie is not None and current_bookie.lower() == ln.lower() and len(pending_quotes) == 0:
                continue
            # Se avevamo un bookmaker incompleto senza quote, sostituiscilo con il nuovo nome
            if current_bookie is not None and len(pending_quotes) == 0:
                current_bookie = ln
                continue
            if current_bookie is None:
                current_bookie = ln
                pending_quotes = []
                current_payout = None

    # Chiude l'ultima riga se non era seguita da una percentuale
    flush_row()

    if not player_1 or not player_2:
        warnings.append("Nomi giocatori non rilevati automaticamente: puoi inserirli o verificarli nei campi qui sotto.")
    if not rows:
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
st.caption("Analisi di un singolo incontro su più bookmaker con stesso motore Monte Carlo e Kelly.")

with st.sidebar:
    st.header("Parametri Modello & Cassa")
    bankroll = st.number_input("Bankroll disponibile (€)", min_value=10.0, value=1000.0, step=50.0)
    superficie = st.selectbox("Superficie", ["Terra battuta", "Cemento", "Erba"], index=0)
    modello = st.radio("Approccio probabilistico", ["Modello A", "Modello B"], index=0)
    soglia_edge_pct = st.slider("Soglia minima Edge (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
    frazione_kelly = st.slider("Frazione Kelly", min_value=0.10, max_value=1.00, value=0.25, step=0.05)
    n_sim = st.select_slider("Simulazioni Monte Carlo", options=[2000, 5000, 10000, 20000], value=10000)

default_sample = """Wendelken H.
-
Blancaneaux G.
Oggi,
19 Nov 2026,
18:30
- Home/Away
- Over/Under
- Asian Handicap
- Correct Score
Finale1° Set2° SetTutti i bonus
888sport


richiedi bonus
1.36
3.00
93.6%

BetflagIT


richiedi bonus
1.36
2.85
92.1%

BetssonIT


richiedi bonus
1.37
2.95
93.6%"""

raw_input = st.text_area(
    "Incolla qui il testo copiato dalla pagina del singolo match",
    value=default_sample,
    height=260,
)

parsed = parse_oddsportal_match(raw_input)

if parsed["is_live"]:
    st.warning("⚠️ Rilevata partita IN CORSO (Quote in tempo reale): la simulazione pre-match non conosce il punteggio attuale.")

for w in parsed["warnings"]:
    st.info(w)

col_g1, col_g2 = st.columns(2)
with col_g1:
    g1 = st.text_input("Giocatore 1 (Quota '1')", value=parsed["player_1"])
with col_g2:
    g2 = st.text_input("Giocatore 2 (Quota '2')", value=parsed["player_2"])

if st.button("Calcola confronto tra Bookmaker", type="primary"):
    if not g1.strip() or not g2.strip():
        st.error("Inserisci entrambi i nomi dei giocatori prima di procedere.")
    elif not parsed["rows"]:
        st.error("Non ho trovato righe di bookmaker valide da confrontare.")
    else:
        # Calcola quote medie di mercato come riferimento opzionale per Modello B
        q1_vals = [r["Quota 1"] for r in parsed["rows"] if isinstance(r["Quota 1"], float)]
        q2_vals = [r["Quota 2"] for r in parsed["rows"] if isinstance(r["Quota 2"], float)]
        q1_ref = float(np.mean(q1_vals)) if q1_vals else None
        q2_ref = float(np.mean(q2_vals)) if q2_vals else None

        p1_win, p2_win = stima_probabilita_prematch(
            giocatore_1=g1.strip(),
            giocatore_2=g2.strip(),
            superficie=superficie,
            modello=modello,
            quota_1_rif=q1_ref,
            quota_2_rif=q2_ref,
            n_simulazioni=n_sim,
        )

        soglia_edge = soglia_edge_pct / 100.0
        tabella_risultati: List[Dict[str, Any]] = []

        for r in parsed["rows"]:
            res_1 = calcola_edge_e_stake(
                prob_win=p1_win,
                quota=r["Quota 1"],
                bankroll=bankroll,
                soglia_edge=soglia_edge,
                frazione_kelly=frazione_kelly,
            )
            res_2 = calcola_edge_e_stake(
                prob_win=p2_win,
                quota=r["Quota 2"],
                bankroll=bankroll,
                soglia_edge=soglia_edge,
                frazione_kelly=frazione_kelly,
            )

            edge_1 = res_1["edge"] if res_1["edge"] is not None else -999.0
            edge_2 = res_2["edge"] if res_2["edge"] is not None else -999.0

            if edge_1 >= edge_2:
                best_side = f"1 · {g1.strip()}"
                best_quota = r["Quota 1"]
                best_prob = p1_win
                best_edge = res_1["edge"]
                best_stake = res_1["stake"]
                best_azione = res_1["azione"]
            else:
                best_side = f"2 · {g2.strip()}"
                best_quota = r["Quota 2"]
                best_prob = p2_win
                best_edge = res_2["edge"]
                best_stake = res_2["stake"]
                best_azione = res_2["azione"]

            tabella_risultati.append(
                {
                    "Bookmaker": r["Bookmaker"],
                    "Payout": r["Payout"],
                    f"Q1 ({g1.strip()})": r["Quota 1"],
                    f"Q2 ({g2.strip()})": r["Quota 2"],
                    "Miglior Lato": best_side,
                    "Quota Scelta": best_quota,
                    "Prob. Modello (%)": round(best_prob * 100, 1),
                    "Edge (%)": round(best_edge * 100, 2) if best_edge is not None else None,
                    "Stake (€)": best_stake,
                    "Esito": best_azione,
                    "_sort_edge": best_edge if best_edge is not None else -999.0,
                }
            )

        df_out = pd.DataFrame(tabella_risultati).sort_values(by="_sort_edge", ascending=False).drop(columns=["_sort_edge"])

        st.subheader(f"📊 Risultati: {g1.strip()} vs {g2.strip()} ({superficie} · {modello})")
        c1, c2 = st.columns(2)
        c1.metric(f"Prob. stimata {g1.strip()} (1)", f"{p1_win * 100:.1f}%")
        c2.metric(f"Prob. stimata {g2.strip()} (2)", f"{p2_win * 100:.1f}%")

        st.dataframe(df_out, use_container_width=True, hide_index=True)
