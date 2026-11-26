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
# CONFIGURAZIONE PAGINA E COSTANTI
# ==============================================================================
st.set_page_config(
    page_title="Check Risultati Tennis (9 Colonne)",
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
    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
}

STATUS_KEYWORDS = {
    "Annullata": ["cancelled", "canceled", "abandoned", "annullata", "void"],
    "Posticipata": ["postponed", "posticipata", "rescheduled"],
    "Rimandata": ["suspended", "interrupted", "delayed", "rimandata", "rain delay"],
}


# ==============================================================================
# FUNZIONI DI UTILITÀ PER NORMALIZZAZIONE NOMI E MATCHING
# ==============================================================================
def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def parse_player_tokens(player_label: str) -> Tuple[str, str]:
    """
    Estrae (cognome_normalizzato, iniziale_nome) da stringhe tipo:
    - 'Perego G.' -> ('perego', 'g')
    - 'Dutra Da Silva D.' -> ('dutra da silva', 'd')
    - 'Giulio Perego' -> ('perego', 'g')
    """
    cleaned = strip_accents(str(player_label)).lower().strip()
    cleaned = re.sub(r"[^a-z\s\.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    parts = cleaned.split(" ")
    if not parts:
        return "", ""

    # Caso standard export OddsPortal: "Cognome N." oppure "Cognome N. M."
    if len(parts) >= 2 and (len(parts[-1].replace(".", "")) == 1):
        # Gestisce anche doppie iniziali finali tipo "Dev S D P."
        idx = len(parts) - 1
        while idx > 0 and len(parts[idx].replace(".", "")) == 1:
            idx -= 1
        surname = " ".join(parts[: idx + 1]).replace(".", "").strip()
        initial = parts[idx + 1].replace(".", "")[:1]
        return surname, initial

    # Caso nome completo: "Nome Cognome"
    if len(parts) >= 2:
        initial = parts[0][:1]
        surname = " ".join(parts[1:]).replace(".", "").strip()
        return surname, initial

    return parts[0].replace(".", ""), ""


def name_matches_text(player_label: str, text: str) -> bool:
    """Verifica se un giocatore compare in modo plausibile in un testo/nome completo."""
    surname, initial = parse_player_tokens(player_label)
    if not surname or len(surname) < 3:
        return False

    norm_text = strip_accents(text).lower()
    norm_text = re.sub(r"[^a-z\s]", " ", norm_text)
    norm_text = re.sub(r"\s+", " ", norm_text)

    if f" {surname} " not in f" {norm_text} ":
        return False

    if initial:
        # Controlla presenza dell'iniziale vicino al cognome (es. "giulio perego" o "perego g")
        pattern = rf"\b({initial}[a-z]*\s+{re.escape(surname)}|{re.escape(surname)}\s+{initial}[a-z]*)\b"
        if re.search(pattern, norm_text):
            return True
        # Fallback su cognome univoco lungo (>= 6 caratteri)
        return len(surname) >= 6

    return True


def detect_match_status(text: str) -> Optional[str]:
    norm = strip_accents(text).lower()
    for label, keywords in STATUS_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", norm):
                return label
    return None


def infer_winner_from_snippet(
    snippet: str, p1_label: str, p2_label: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Analizza un estratto testuale/titolo per capire:
    1) Se il match è stato annullato/posticipato/rimandato
    2) Quale dei due giocatori ha vinto (senza estrarre il punteggio)
    Restituisce (valore_vincitore, dettaglio_log).
    """
    if not snippet:
        return None, None

    # 1. Controllo stati anomali
    status = detect_match_status(snippet)
    if status:
        return status, f"Stato rilevato: {status}"

    norm = strip_accents(snippet).lower()
    s1, i1 = parse_player_tokens(p1_label)
    s2, i2 = parse_player_tokens(p2_label)

    # Pattern espliciti di vittoria in inglese/italiano
    win_patterns = [
        r"\b([a-z\s\.\-]{3,35})\s+(?:def\.|defeats|defeated|beats|beat|batte|supera|wins against|vince contro)\s+([a-z\s\.\-]{3,35})\b",
        r"\bwinner[:\s]+([a-z\s\.\-]{3,35})\b",
        r"\bvincitore[:\s]+([a-z\s\.\-]{3,35})\b",
    ]

    for pat in win_patterns:
        for m in re.finditer(pat, norm):
            winner_chunk = m.group(1).strip()
            if s1 and s1 in winner_chunk and (not s2 or s2 not in winner_chunk):
                return p1_label, f"Match esplicito su '{winner_chunk}'"
            if s2 and s2 in winner_chunk and (not s1 or s1 not in winner_chunk):
                return p2_label, f"Match esplicito su '{winner_chunk}'"

    # Pattern punteggio tennis (es. "Faurel T. - Domingues J. 6-3, 6-1" o "2-0")
    # Se compaiono entrambi i giocatori seguiti da un risultato netto a 2/3 set,
    # si identifica il vincitore dal conteggio set senza salvare il punteggio.
    score_match = re.search(
        r"([a-z\s\.\-]{3,40})\s*(?:-|vs\.?|v)\s*([a-z\s\.\-]{3,40})[:\s]+(\d\s*[-:]\s*\d(?:\s*,\s*\d\s*[-:]\s*\d){1,2})",
        norm,
    )
    if score_match:
        left_name = score_match.group(1)
        right_name = score_match.group(2)
        raw_sets = score_match.group(3)
        sets = re.findall(r"(\d)\s*[-:]\s*(\d)", raw_sets)
        if len(sets) >= 2:
            left_wins = sum(1 for a, b in sets if int(a) > int(b))
            right_wins = sum(1 for a, b in sets if int(b) > int(a))
            if left_wins != right_wins:
                winner_side = left_name if left_wins > right_wins else right_name
                if s1 and s1 in winner_side and (not s2 or s2 not in winner_side):
                    return p1_label, "Dedotto da esito tabellino"
                if s2 and s2 in winner_side and (not s1 or s1 not in winner_side):
                    return p2_label, "Dedotto da esito tabellino"

    return None, None


# ==============================================================================
# CATENA DI FALLBACK MULTI-SORGENTE
# ==============================================================================
def source_1_sofascore_api(
    session: requests.Session, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    """
    Sorgente 1: API pubblica eventi tennis Sofascore per data (YYYY-MM-DD).
    Molto veloce e strutturata per ATP, WTA, Challenger e molti ITF.
    """
    try:
        # Controlla la data del match e il giorno successivo (per fusi orari)
        base_dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        dates_to_check = [
            base_dt.strftime("%Y-%m-%d"),
            (base_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
        ]

        for d in dates_to_check:
            url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{d}"
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            events = resp.json().get("events", [])
            for ev in events:
                home_name = ev.get("homeTeam", {}).get("name", "")
                away_name = ev.get("awayTeam", {}).get("name", "")

                p1_is_home = name_matches_text(p1, home_name) and name_matches_text(p2, away_name)
                p2_is_home = name_matches_text(p2, home_name) and name_matches_text(p1, away_name)

                if not (p1_is_home or p2_is_home):
                    continue

                status_type = str(ev.get("status", {}).get("type", "")).lower()
                status_desc = str(ev.get("status", {}).get("description", "")).lower()

                if status_type in {"canceled", "cancelled"} or "cancel" in status_desc:
                    return "Annullata", "Sofascore API (Annullata)"
                if status_type == "postponed" or "postpon" in status_desc:
                    return "Posticipata", "Sofascore API (Posticipata)"
                if status_type in {"interrupted", "suspended"} or "suspend" in status_desc:
                    return "Rimandata", "Sofascore API (Rimandata)"

                winner_code = ev.get("winnerCode")  # 1 = homeTeam, 2 = awayTeam
                if winner_code in (1, 2):
                    if p1_is_home:
                        winner = p1 if winner_code == 1 else p2
                    else:
                        winner = p2 if winner_code == 1 else p1
                    return winner, f"Sofascore API ({d})"

        return None, "Sofascore API: match non trovato o non concluso"
    except Exception as exc:
        return None, f"Sofascore API errore: {exc}"


def source_2_thesportsdb_api(
    session: requests.Session, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    """
    Sorgente 2 (Fallback 1): TheSportsDB endpoint gratuito eventi del giorno (Tennis).
    """
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={date_str[:10]}&s=Tennis"
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None, f"TheSportsDB HTTP {resp.status_code}"

        events = resp.json().get("events") or []
        for ev in events:
            home_name = ev.get("strHomeTeam") or ""
            away_name = ev.get("strAwayTeam") or ""
            event_title = ev.get("strEvent") or ""
            status_str = ev.get("strStatus") or ""

            match_found = (
                (name_matches_text(p1, home_name) and name_matches_text(p2, away_name))
                or (name_matches_text(p2, home_name) and name_matches_text(p1, away_name))
                or (name_matches_text(p1, event_title) and name_matches_text(p2, event_title))
            )
            if not match_found:
                continue

            status_detected = detect_match_status(status_str)
            if status_detected:
                return status_detected, f"TheSportsDB ({status_detected})"

            h_score = ev.get("intHomeScore")
            a_score = ev.get("intAwayScore")
            if h_score is not None and a_score is not None:
                try:
                    hs, as_ = int(h_score), int(a_score)
                    if hs != as_:
                        p1_is_home = name_matches_text(p1, home_name)
                        if p1_is_home:
                            winner = p1 if hs > as_ else p2
                        else:
                            winner = p2 if hs > as_ else p1
                        return winner, "TheSportsDB API"
                except ValueError:
                    pass

        return None, "TheSportsDB: nessun riscontro"
    except Exception as exc:
        return None, f"TheSportsDB errore: {exc}"


def source_3_duckduckgo_html(
    session: requests.Session, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    """
    Sorgente 3 (Fallback 2): Ricerca web HTML su DuckDuckGo Lite/HTML
    mirata su siti tennis (TennisExplorer, Flashscore, Sofascore, ITF/ATP/WTA).
    """
    try:
        s1, _ = parse_player_tokens(p1)
        s2, _ = parse_player_tokens(p2)
        query = f'"{s1}" "{s2}" tennis {date_str[:10]} winner OR result OR postponed OR cancelled'
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = session.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return None, f"Web Search 1 HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select(".result")
        for res in results[:8]:
            title_el = res.select_one(".result__title")
            snippet_el = res.select_one(".result__snippet")
            combined = " ".join(
                [
                    title_el.get_text(" ", strip=True) if title_el else "",
                    snippet_el.get_text(" ", strip=True) if snippet_el else "",
                ]
            )
            if not (name_matches_text(p1, combined) and name_matches_text(p2, combined)):
                continue

            winner, detail = infer_winner_from_snippet(combined, p1, p2)
            if winner:
                return winner, f"DuckDuckGo Web ({detail})"

        return None, "DuckDuckGo Web: esito non chiaro negli snippet"
    except Exception as exc:
        return None, f"DuckDuckGo Web errore: {exc}"


def source_4_bing_web_fallback(
    session: requests.Session, date_str: str, p1: str, p2: str
) -> Tuple[Optional[str], str]:
    """
    Sorgente 4 (Fallback 3): Ricerca web alternativa su Bing (utile per ITF/Challenger minori).
    """
    try:
        s1, _ = parse_player_tokens(p1)
        s2, _ = parse_player_tokens(p2)
        query = f'{s1} vs {s2} tennis {date_str[:10]}'
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        resp = session.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return None, f"Web Search 2 HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("li.b_algo")[:8]:
            text = item.get_text(" ", strip=True)
            if not (name_matches_text(p1, text) and name_matches_text(p2, text)):
                continue

            winner, detail = infer_winner_from_snippet(text, p1, p2)
            if winner:
                return winner, f"Bing Web ({detail})"

        return None, "Bing Web: nessun risultato univoco"
    except Exception as exc:
        return None, f"Bing Web errore: {exc}"


def resolve_match_with_fallback(
    session: requests.Session,
    date_str: str,
    p1: str,
    p2: str,
    enabled_sources: List[str],
    delay_sec: float = 0.6,
) -> Tuple[str, str]:
    """
    Esegue la catena di fallback in ordine finché una sorgente non restituisce
    un vincitore valido o uno stato (Annullata/Posticipata/Rimandata).
    """
    pipeline = [
        ("1. Sofascore API", source_1_sofascore_api),
        ("2. TheSportsDB API", source_2_thesportsdb_api),
        ("3. Web Search (DuckDuckGo)", source_3_duckduckgo_html),
        ("4. Web Search Fallback (Bing)", source_4_bing_web_fallback),
    ]

    logs: List[str] = []
    for source_label, fn in pipeline:
        if source_label not in enabled_sources:
            continue
        winner, info = fn(session, date_str, p1, p2)
        logs.append(f"{source_label} -> {info}")
        if winner:
            return winner, " | ".join(logs)
        time.sleep(delay_sec)

    return "", " | ".join(logs) if logs else "Nessuna sorgente selezionata"


# ==============================================================================
# NORMALIZZAZIONE DEL CSV DI INPUT NEL FORMATO A 9 COLONNE
# ==============================================================================
def format_odds(val) -> str:
    if pd.isna(val) or str(val).strip() == "":
        return ""
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val).strip()


def build_reduced_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Estrae esattamente le 9 colonne richieste, preservando l'ordine delle righe,
    e garantendo che 'Esito' sia sempre completamente vuota ('').
    """
    col_map: Dict[str, str] = {c.strip().lower(): c for c in raw_df.columns}

    def get_col(name: str) -> pd.Series:
        key = name.lower()
        if key in col_map:
            return raw_df[col_map[key]]
        return pd.Series([""] * len(raw_df))

    reduced = pd.DataFrame(
        {
            "Data": get_col("Data").fillna("").astype(str).str.strip(),
            "Giocatore 1": get_col("Giocatore 1").fillna("").astype(str).str.strip(),
            "Quota 1": get_col("Quota 1").apply(format_odds),
            "Giocatore 2": get_col("Giocatore 2").fillna("").astype(str).str.strip(),
            "Quota 2": get_col("Quota 2").apply(format_odds),
            "Miglior Lato": get_col("Miglior Lato").fillna("").astype(str).str.strip(),
            "Quota Scelta": get_col("Quota Scelta").apply(format_odds),
            "Vincitore": get_col("Vincitore").fillna("").astype(str).str.strip(),
            # REGOLA INDEROGABILE: la colonna Esito deve sempre restare vuota
            "Esito": [""] * len(raw_df),
        }
    )

    return reduced[TARGET_COLUMNS]


# ==============================================================================
# INTERFACCIA UTENTE STREAMLIT
# ==============================================================================
st.title("🎾 Check Risultati & Tabella Ridotta (9 Colonne)")
st.markdown(
    "Carica il file `.csv` esportato da **`03_oddsportal_test_150.py`**. "
    "L'app estrae le **9 colonne standard**, cerca in rete chi ha vinto (o se il match è stato "
    "**annullato / posticipato / rimandato**) tramite catena di fallback multi-sorgente, "
    "compila **solo `Vincitore`** e lascia **`Esito` sempre vuota**."
)

with st.sidebar:
    st.header("⚙️ Impostazioni Ricerca")
    selected_sources = st.multiselect(
        "Catena di fallback attiva (in ordine):",
        options=[
            "1. Sofascore API",
            "2. TheSportsDB API",
            "3. Web Search (DuckDuckGo)",
            "4. Web Search Fallback (Bing)",
        ],
        default=[
            "1. Sofascore API",
            "2. TheSportsDB API",
            "3. Web Search (DuckDuckGo)",
            "4. Web Search Fallback (Bing)",
        ],
    )
    request_delay = st.slider(
        "Pausa tra richieste di fallback (sec)",
        min_value=0.2,
        max_value=2.5,
        value=0.6,
        step=0.1,
    )
    skip_already_filled = st.checkbox(
        "Salta righe dove 'Vincitore' è già compilato",
        value=True,
    )

uploaded_file = st.file_uploader(
    "Carica il file CSV generato da 03_oddsportal_test_150.py",
    type=["csv"],
)

if uploaded_file is not None:
    file_signature = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("last_file_sig") != file_signature:
        raw_df = pd.read_csv(uploaded_file)
        st.session_state["reduced_df"] = build_reduced_dataframe(raw_df)
        st.session_state["search_logs"] = []
        st.session_state["last_file_sig"] = file_signature

    df_work: pd.DataFrame = st.session_state["reduced_df"].copy()

    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("Match caricati", len(df_work))
    col_info2.metric(
        "Vincitore compilato",
        int((df_work["Vincitore"].astype(str).str.strip() != "").sum()),
    )
    col_info3.metric(
        "Da verificare",
        int((df_work["Vincitore"].astype(str).str.strip() == "").sum()),
    )

    if st.button("🔍 Cerca Vincitori in Rete (con Fallback)", type="primary"):
        progress_bar = st.progress(0)
        status_box = st.empty()
        logs_collected: List[Dict[str, str]] = []

        with requests.Session() as session:
            total = len(df_work)
            for idx, row in df_work.iterrows():
                p1 = str(row["Giocatore 1"]).strip()
                p2 = str(row["Giocatore 2"]).strip()
                date_str = str(row["Data"]).strip()
                current_winner = str(row["Vincitore"]).strip()

                if skip_already_filled and current_winner:
                    logs_collected.append(
                        {
                            "Match": f"{p1} vs {p2}",
                            "Esito Ricerca": current_winner,
                            "Dettaglio Fallback": "Già compilato (saltato)",
                        }
                    )
                    progress_bar.progress((idx + 1) / total)
                    continue

                status_box.info(f"Ricerca ({idx + 1}/{total}): **{p1}** vs **{p2}** ({date_str})...")
                winner_found, trace = resolve_match_with_fallback(
                    session=session,
                    date_str=date_str,
                    p1=p1,
                    p2=p2,
                    enabled_sources=selected_sources,
                    delay_sec=request_delay,
                )

                if winner_found:
                    df_work.at[idx, "Vincitore"] = winner_found

                # Forza sempre Esito vuota
                df_work.at[idx, "Esito"] = ""

                logs_collected.append(
                    {
                        "Match": f"{p1} vs {p2}",
                        "Esito Ricerca": winner_found if winner_found else "NON TROVATO",
                        "Dettaglio Fallback": trace,
                    }
                )
                progress_bar.progress((idx + 1) / total)

        status_box.success("Ricerca completata su tutto l'elenco!")
        st.session_state["reduced_df"] = df_work
        st.session_state["search_logs"] = logs_collected
        st.rerun()

    st.subheader("📋 Tabella Ridotta a 9 Colonne (modificabile su 'Vincitore')")
    edited_df = st.data_editor(
        st.session_state["reduced_df"],
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

    # Garantisce in ogni caso l'ordine a 9 colonne e 'Esito' sempre vuota
    final_df = edited_df[TARGET_COLUMNS].copy()
    final_df["Vincitore"] = final_df["Vincitore"].fillna("").astype(str).str.strip()
    final_df["Esito"] = ""
    st.session_state["reduced_df"] = final_df

    if st.session_state.get("search_logs"):
        with st.expander("🔎 Log dettagliato della catena di fallback", expanded=False):
            st.dataframe(
                pd.DataFrame(st.session_state["search_logs"]),
                use_container_width=True,
                hide_index=True,
            )

    # ==========================================================================
    # OUTPUT: DOWNLOAD CSV + BLOCCO COPIA E INCOLLA
    # ==========================================================================
    st.divider()
    st.subheader("📤 Esportazione Dati")

    csv_buffer = io.StringIO()
    final_df.to_csv(csv_buffer, index=False)
    csv_text = csv_buffer.getvalue()

    unique_dates = [d for d in final_df["Data"].unique() if d]
    date_tag = unique_dates[0] if len(unique_dates) == 1 else datetime.now().strftime("%Y-%m-%d")
    out_filename = f"{date_tag}_tabella_ridotta_vincitori.csv"

    st.download_button(
        label=f"⬇️ Scarica CSV ({out_filename})",
        data=csv_text.encode("utf-8"),
        file_name=out_filename,
        mime="text/csv",
        type="primary",
    )

    st.markdown("**Blocco CSV per il copia e incolla:**")
    st.code(csv_text, language="csv")