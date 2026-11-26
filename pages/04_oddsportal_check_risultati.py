import io
import re
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="04 - Check Risultati Tennis (9 Colonne)",
    page_icon="🎾",
    layout="wide",
)

TARGET_COLUMNS = [
    "Data",
    "Giocatore 1",
    "Quota 1",
    "Giocatore 2",
    "Quota 2",
    "Miglior Lato",
    "Quota Scelta",
    "Vincitore",
    "Esito",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

MULTI_WORD_SURNAMES = {
    "dutra da silva",
    "romero gormaz",
    "herrero linana",
    "martinez vaquero",
    "carballes baena",
    "bittoun kouzmine",
    "de la pena",
    "van de zandschulp",
}

STATUS_PATTERNS = {
    "Annullata": [
        r"\bcancel+ed\b",
        r"\babandoned\b",
        r"\bannullat[aoei]\b",
        r"\bwalkover\b",
        r"\bw/?o\b",
        r"\bvoid\b",
    ],
    "Posticipata": [
        r"\bpostponed\b",
        r"\bposticipat[aoei]\b",
        r"\brescheduled\b",
    ],
    "Rimandata": [
        r"\bsuspended\b",
        r"\binterrupted\b",
        r"\bdelayed\b",
        r"\brimandat[aoei]\b",
        r"\brain\b",
    ],
}


# ==============================================================================
# NORMALIZZAZIONE E LOGICA BASATA SUL COGNOME
# ==============================================================================
def normalize_text(text: str) -> str:
    if not text:
        return ""
    no_accents = "".join(
        c
        for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    )
    lowered = no_accents.lower().replace("’", "'").replace("'", " ")
    lowered = re.sub(r"[^a-z0-9\s\-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def extract_surname(player_label: str) -> str:
    """
    Estrae il cognome normalizzato da etichette tipo:
    - 'Duran T.' -> 'duran'
    - 'Dev S D P.' -> 'dev'
    - 'Dutra Da Silva D.' -> 'dutra da silva'
    - 'Tuncay Duran' -> 'duran'
    """
    norm = normalize_text(player_label)
    if not norm:
        return ""

    # Controlla cognomi composti noti
    for comp in MULTI_WORD_SURNAMES:
        if re.search(rf"\b{re.escape(comp)}\b", norm):
            return comp

    tokens = norm.split(" ")
    # Rimuove eventuali iniziali singole (es. 't', 's', 'd', 'p', 'c', 'e')
    non_initial = [t for t in tokens if len(t) > 1]
    if non_initial:
        # Nei formati 'Cognome N.' il primo token lungo è quasi sempre il cognome;
        # nei formati 'Nome Cognome' l'ultimo token lungo è il cognome.
        if len(tokens) >= 2 and len(tokens[-1]) == 1:
            return non_initial[0]
        return non_initial[-1]

    return tokens[0]


def surname_in_text(surname: str, text: str) -> bool:
    if not surname or len(surname) < 2:
        return False
    norm_txt = normalize_text(text)
    if not norm_txt:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(surname.replace('-', '[\\s\\-]?'))}(?![a-z0-9])"
    return re.search(pattern, norm_txt) is not None


def detect_status(text: str) -> Optional[str]:
    norm_txt = normalize_text(text)
    if not norm_txt:
        return None
    for status_label, patterns in STATUS_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, norm_txt):
                return status_label
    return None


def infer_winner_by_surname(
    text: str, p1_label: str, p2_label: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Determina il vincitore (o stato Annullata/Posticipata/Rimandata) usando
    esclusivamente il cognome dei due giocatori. Non restituisce mai punteggi.
    """
    if not text:
        return None, None

    status = detect_status(text)
    if status:
        return status, f"Stato: {status}"

    s1 = extract_surname(p1_label)
    s2 = extract_surname(p2_label)
    if not s1 or not s2:
        return None, None

    has_s1 = surname_in_text(s1, text)
    has_s2 = surname_in_text(s2, text)
    if not (has_s1 and has_s2):
        return None, None

    norm_txt = normalize_text(text)
    s1_pat = re.escape(s1.replace("-", " "))
    s2_pat = re.escape(s2.replace("-", " "))

    # 1. Espressioni esplicite "VincitoreX batte/supera/defeats PerdenteY"
    verb_pat = r"(?:def\.?|defeats?|defeated|beats?|beat|batte|supera|vince\s+su|wins\s+against|vince\s+contro)"
    if re.search(rf"\b{s1_pat}\b[^\n\r]{{0,35}}\b{verb_pat}\b[^\n\r]{{0,35}}\b{s2_pat}\b", norm_txt):
        return p1_label, f"Vittoria cognome '{s1}'"
    if re.search(rf"\b{s2_pat}\b[^\n\r]{{0,35}}\b{verb_pat}\b[^\n\r]{{0,35}}\b{s1_pat}\b", norm_txt):
        return p2_label, f"Vittoria cognome '{s2}'"

    # 2. Espressioni tipo "Winner: Cognome" / "Vincitore: Cognome"
    for m in re.finditer(r"\b(?:winner|vincitore)\s*[:\-]?\s*([a-z\s\-]{2,35})", norm_txt):
        chunk = m.group(1)
        m1 = surname_in_text(s1, chunk)
        m2 = surname_in_text(s2, chunk)
        if m1 and not m2:
            return p1_label, f"Tag vincitore '{s1}'"
        if m2 and not m1:
            return p2_label, f"Tag vincitore '{s2}'"

    # 3. Pattern tipo "Cognome1 vs Cognome2 ... 6-3 6-1" o "Cognome1 - Cognome2 2-0"
    pair_score_pat = re.search(
        rf"\b({s1_pat})\b\s*(?:vs\.?|v|-|–)\s*\b({s2_pat})\b[^\n\r]{{0,45}}?(\d\s*[-:]\s*\d(?:\s*,\s*\d\s*[-:]\s*\d|\s+\d\s*[-:]\s*\d){{0,2}})",
        norm_txt,
    )
    if pair_score_pat:
        sets = re.findall(r"(\d)\s*[-:]\s*(\d)", pair_score_pat.group(3))
        if sets:
            w1 = sum(1 for a, b in sets if int(a) > int(b))
            w2 = sum(1 for a, b in sets if int(b) > int(a))
            if w1 > w2:
                return p1_label, f"Set vinti da '{s1}'"
            if w2 > w1:
                return p2_label, f"Set vinti da '{s2}'"

    return None, None


# ==============================================================================
# MOTORI DI RICERCA E CATENA DI FALLBACK
# ==============================================================================
def fetch_search_results(
    session: requests.Session, query: str, max_results: int = 8
) -> List[str]:
    """
    Esegue una ricerca web su DuckDuckGo HTML con fallback su Bing
    e restituisce una lista di testi (titolo + URL + snippet) da analizzare.
    """
    texts: List[str] = []

    # Tentativo su DuckDuckGo HTML
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = session.get(ddg_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for res in soup.select(".result")[:max_results]:
                title = res.select_one(".result__title")
                snippet = res.select_one(".result__snippet")
                link = res.select_one(".result__url")
                chunk = " | ".join(
                    part.get_text(" ", strip=True)
                    for part in [title, link, snippet]
                    if part is not None
                )
                if chunk:
                    texts.append(chunk)
    except Exception:
        pass

    if texts:
        return texts

    # Fallback su Bing HTML
    try:
        bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"
        resp = session.get(bing_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select("li.b_algo")[:max_results]:
                txt = item.get_text(" ", strip=True)
                if txt:
                    texts.append(txt)
    except Exception:
        pass

    return texts


def fallback_1_tennistonic(
    session: requests.Session, s1: str, s2: str, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    query = f'site:tennistonic.com "{s1}" "{s2}"'
    snippets = fetch_search_results(session, query)
    for snip in snippets:
        winner, reason = infer_winner_by_surname(snip, p1, p2)
        if winner:
            return winner, f"TennisTonic ({reason})"
    return None, "TennisTonic: nessun riscontro"


def fallback_2_aiscore(
    session: requests.Session, s1: str, s2: str, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    query = f'site:aiscore.com "{s1}" "{s2}" tennis'
    snippets = fetch_search_results(session, query)
    for snip in snippets:
        winner, reason = infer_winner_by_surname(snip, p1, p2)
        if winner:
            return winner, f"AiScore ({reason})"
    return None, "AiScore: nessun riscontro"


def fallback_3_livescore(
    session: requests.Session, s1: str, s2: str, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    query = f'site:livescore.com "{s1}" "{s2}" tennis'
    snippets = fetch_search_results(session, query)
    for snip in snippets:
        winner, reason = infer_winner_by_surname(snip, p1, p2)
        if winner:
            return winner, f"LiveScore ({reason})"
    return None, "LiveScore: nessun riscontro"


def fallback_4_general_web(
    session: requests.Session, s1: str, s2: str, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    queries = [
        f'"{s1}" "{s2}" tennis {date_str[:10]}',
        f'"{s1}" vs "{s2}" tennis result',
    ]
    for q in queries:
        snippets = fetch_search_results(session, q)
        for snip in snippets:
            winner, reason = infer_winner_by_surname(snip, p1, p2)
            if winner:
                return winner, f"Web Search ({reason})"
    return None, "Web Search: nessun riscontro"


def fallback_5_sofascore_api(
    session: requests.Session, s1: str, s2: str, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    try:
        base_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        for offset in (0, 1, -1):
            d = (base_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
            url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{d}"
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            for ev in resp.json().get("events", []):
                home = ev.get("homeTeam", {}).get("name", "")
                away = ev.get("awayTeam", {}).get("name", "")
                p1_home = surname_in_text(s1, home) and surname_in_text(s2, away)
                p2_home = surname_in_text(s2, home) and surname_in_text(s1, away)
                if not (p1_home or p2_home):
                    continue

                st_type = str(ev.get("status", {}).get("type", "")).lower()
                st_desc = str(ev.get("status", {}).get("description", "")).lower()
                if "cancel" in st_type or "cancel" in st_desc:
                    return "Annullata", "Sofascore API (Annullata)"
                if "postpon" in st_type or "postpon" in st_desc:
                    return "Posticipata", "Sofascore API (Posticipata)"
                if "interrupt" in st_type or "suspend" in st_type or "delay" in st_desc:
                    return "Rimandata", "Sofascore API (Rimandata)"

                w_code = ev.get("winnerCode")
                if w_code in (1, 2):
                    if p1_home:
                        return (p1 if w_code == 1 else p2), f"Sofascore API ({d})"
                    return (p2 if w_code == 1 else p1), f"Sofascore API ({d})"
    except Exception as exc:
        return None, f"Sofascore API err: {exc}"
    return None, "Sofascore API: nessun riscontro"


def resolve_match_winner(
    session: requests.Session,
    date_str: str,
    p1: str,
    p2: str,
    active_steps: List[str],
    delay: float,
) -> Tuple[str, str]:
    s1 = extract_surname(p1)
    s2 = extract_surname(p2)

    steps_map = {
        "1. TennisTonic": fallback_1_tennistonic,
        "2. AiScore": fallback_2_aiscore,
        "3. LiveScore": fallback_3_livescore,
        "4. Web Search Generica": fallback_4_general_web,
        "5. Sofascore API": fallback_5_sofascore_api,
    }

    trace_items: List[str] = []
    for step_name, fn in steps_map.items():
        if step_name not in active_steps:
            continue
        winner, msg = fn(session, s1, s2, date_str, p1, p2)
        trace_items.append(f"{step_name}: {msg}")
        if winner:
            return winner, " -> ".join(trace_items)
        time.sleep(delay)

    return "", " -> ".join(trace_items) if trace_items else "Nessuna fonte attiva"


# ==============================================================================
# COSTRUZIONE TABELLA A 9 COLONNE
# ==============================================================================
def format_odds(val) -> str:
    if pd.isna(val) or str(val).strip() == "":
        return ""
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val).strip()


def to_nine_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    col_lookup: Dict[str, str] = {c.strip().lower(): c for c in raw_df.columns}

    def col_series(name: str) -> pd.Series:
        key = name.lower()
        if key in col_lookup:
            return raw_df[col_lookup[key]]
        return pd.Series([""] * len(raw_df))

    df_9 = pd.DataFrame(
        {
            "Data": col_series("Data").fillna("").astype(str).str.strip(),
            "Giocatore 1": col_series("Giocatore 1").fillna("").astype(str).str.strip(),
            "Quota 1": col_series("Quota 1").apply(format_odds),
            "Giocatore 2": col_series("Giocatore 2").fillna("").astype(str).str.strip(),
            "Quota 2": col_series("Quota 2").apply(format_odds),
            "Miglior Lato": col_series("Miglior Lato").fillna("").astype(str).str.strip(),
            "Quota Scelta": col_series("Quota Scelta").apply(format_odds),
            "Vincitore": col_series("Vincitore").fillna("").astype(str).str.strip(),
            # Vincolo assoluto: la colonna Esito resta sempre completamente vuota
            "Esito": [""] * len(raw_df),
        }
    )
    return df_9[TARGET_COLUMNS]


# ==============================================================================
# INTERFACCIA STREAMLIT
# ==============================================================================
st.title("🎾 04 - Check Risultati Tennis (Tabella 9 Colonne)")
st.caption(
    "Matching basato sul **cognome** con catena di fallback multi-sorgente. "
    "Compila solo **Vincitore** (o stato Annullata/Posticipata/Rimandata) e lascia **Esito sempre vuota**."
)

with st.sidebar:
    st.header("Catena di Fallback")
    all_steps = [
        "1. TennisTonic",
        "2. AiScore",
        "3. LiveScore",
        "4. Web Search Generica",
        "5. Sofascore API",
    ]
    selected_steps = st.multiselect(
        "Ordine di consultazione:",
        options=all_steps,
        default=all_steps,
    )
    pause_sec = st.slider("Pausa tra tentativi (sec)", 0.2, 2.0, 0.5, 0.1)
    only_missing = st.checkbox("Cerca solo dove 'Vincitore' è vuoto", value=True)

uploaded_file = st.file_uploader(
    "Carica il file CSV generato da 03_oddsportal_test_150.py",
    type=["csv"],
)

if uploaded_file is not None:
    sig = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("upload_sig") != sig:
        raw = pd.read_csv(uploaded_file)
        st.session_state["table_9"] = to_nine_columns(raw)
        st.session_state["run_logs"] = []
        st.session_state["upload_sig"] = sig

    working_df = st.session_state["table_9"].copy()

    m1, m2, m3 = st.columns(3)
    m1.metric("Match totali", len(working_df))
    m2.metric("Vincitore compilato", int((working_df["Vincitore"].str.strip() != "").sum()))
    m3.metric("Da compilare", int((working_df["Vincitore"].str.strip() == "").sum()))

    if st.button("🚀 Avvia Ricerca Vincitori", type="primary"):
        prog = st.progress(0)
        status_txt = st.empty()
        logs: List[Dict[str, str]] = []

        with requests.Session() as sess:
            n_rows = len(working_df)
            for i, row in working_df.iterrows():
                p1 = row["Giocatore 1"]
                p2 = row["Giocatore 2"]
                dt_str = row["Data"]
                cur_win = row["Vincitore"].strip()

                if only_missing and cur_win:
                    logs.append(
                        {
                            "Match": f"{p1} vs {p2}",
                            "Cognomi": f"{extract_surname(p1)} / {extract_surname(p2)}",
                            "Vincitore": cur_win,
                            "Log": "Già presente",
                        }
                    )
                    prog.progress((i + 1) / n_rows)
                    continue

                status_txt.info(f"({i + 1}/{n_rows}) {p1} vs {p2} ({dt_str})...")
                found_winner, trace = resolve_match_winner(
                    session=sess,
                    date_str=dt_str,
                    p1=p1,
                    p2=p2,
                    active_steps=selected_steps,
                    delay=pause_sec,
                )

                if found_winner:
                    working_df.at[i, "Vincitore"] = found_winner
                working_df.at[i, "Esito"] = ""

                logs.append(
                    {
                        "Match": f"{p1} vs {p2}",
                        "Cognomi": f"{extract_surname(p1)} / {extract_surname(p2)}",
                        "Vincitore": found_winner if found_winner else "-",
                        "Log": trace,
                    }
                )
                prog.progress((i + 1) / n_rows)

        status_txt.success("Ricerca completata.")
        st.session_state["table_9"] = working_df
        st.session_state["run_logs"] = logs
        st.rerun()

    st.subheader("Tabella a 9 Colonne")
    edited = st.data_editor(
        st.session_state["table_9"],
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Data",
            "Giocatore 1",
            "Quota 1",
            "Giocatore 2",
            "Quota 2",
            "Miglior Lato",
            "Quota Scelta",
            "Esito",
        ],
    )

    clean_df = edited[TARGET_COLUMNS].copy()
    clean_df["Vincitore"] = clean_df["Vincitore"].fillna("").astype(str).str.strip()
    clean_df["Esito"] = ""
    st.session_state["table_9"] = clean_df

    if st.session_state.get("run_logs"):
        with st.expander("Dettaglio fallback per riga"):
            st.dataframe(
                pd.DataFrame(st.session_state["run_logs"]),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    st.subheader("Output: Download CSV e Copia-Incolla")

    buf = io.StringIO()
    clean_df.to_csv(buf, index=False)
    csv_output = buf.getvalue()

    dates_present = [d for d in clean_df["Data"].unique() if d]
    file_date = dates_present[0] if len(dates_present) == 1 else datetime.now().strftime("%Y-%m-%d")
    download_name = f"{file_date}_tabella_9_colonne_vincitori.csv"

    st.download_button(
        label=f"⬇️ Scarica {download_name}",
        data=csv_output.encode("utf-8"),
        file_name=download_name,
        mime="text/csv",
        type="primary",
    )

    st.markdown("**Blocco CSV da copiare e incollare:**")
    st.code(csv_output, language="csv")
