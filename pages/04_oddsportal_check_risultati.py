import io
from datetime import datetime
from typing import Dict

import pandas as pd
import streamlit as st

# ==============================================================================
# CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="04 - Tabella Ridotta Tennis (10 Colonne)",
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
    "esito",
    "Vincitore",
    "risultato",
]


# ==============================================================================
# COSTRUZIONE TABELLA A 10 COLONNE
# ==============================================================================
def format_odds(val) -> str:
    if pd.isna(val) or str(val).strip() == "":
        return ""
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val).strip()


def to_ten_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Estrae e normalizza le 10 colonne richieste dall'export di 03_oddsportal_test_150.py:
    - 'esito' contiene l'esito della simulazione ('VALUE BET' oppure 'Stai fermo' / 'stai fermo')
      letto dalla colonna 'Esito' del file sorgente.
    - 'Vincitore' conserva l'eventuale valore già presente ed è modificabile a mano.
    - 'risultato' sostituisce la vecchia colonna 'Esito' ed è sempre completamente vuota ('').
    """
    # Mappatura case-sensitive prima, poi fallback case-insensitive
    exact_cols = set(raw_df.columns)
    lower_lookup: Dict[str, str] = {c.strip().lower(): c for c in raw_df.columns}

    def get_series(preferred_names, default_empty: bool = False) -> pd.Series:
        if default_empty:
            return pd.Series([""] * len(raw_df))
        for name in preferred_names:
            if name in exact_cols:
                return raw_df[name]
        for name in preferred_names:
            key = name.strip().lower()
            if key in lower_lookup:
                return raw_df[lower_lookup[key]]
        return pd.Series([""] * len(raw_df))

    # Nel file generato da 03_oddsportal_test_150.py la colonna con 'VALUE BET' / 'Stai fermo'
    # si chiama 'Esito' (con la E maiuscola), mentre 'esito' minuscola in fondo era vuota.
    sim_outcome_series = get_series(["Esito"])

    # Eventuale vincitore già valorizzato ('Vincitore' o 'vincitore')
    winner_series = get_series(["Vincitore", "vincitore"])

    df_10 = pd.DataFrame(
        {
            "Data": get_series(["Data"]).fillna("").astype(str).str.strip(),
            "Giocatore 1": get_series(["Giocatore 1"]).fillna("").astype(str).str.strip(),
            "Quota 1": get_series(["Quota 1"]).apply(format_odds),
            "Giocatore 2": get_series(["Giocatore 2"]).fillna("").astype(str).str.strip(),
            "Quota 2": get_series(["Quota 2"]).apply(format_odds),
            "Miglior Lato": get_series(["Miglior Lato"]).fillna("").astype(str).str.strip(),
            "Quota Scelta": get_series(["Quota Scelta"]).apply(format_odds),
            "esito": sim_outcome_series.fillna("").astype(str).str.strip(),
            "Vincitore": winner_series.fillna("").astype(str).str.strip(),
            # Vincolo assoluto: la colonna 'risultato' deve sempre restare completamente vuota
            "risultato": [""] * len(raw_df),
        }
    )
    return df_10[TARGET_COLUMNS]


# ==============================================================================
# INTERFACCIA STREAMLIT
# ==============================================================================
st.title("🎾 04 - Tabella Ridotta Tennis (10 Colonne)")
st.caption(
    "Carica il file CSV generato da **03_oddsportal_test_150.py** per ottenere subito la tabella a **10 colonne** "
    "con l'esito della simulazione (**esito**), il campo editabile **Vincitore** e la colonna **risultato** sempre vuota."
)

uploaded_file = st.file_uploader(
    "Carica il file CSV generato da 03_oddsportal_test_150.py",
    type=["csv"],
)

if uploaded_file is not None:
    sig = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("upload_sig_10") != sig:
        raw = pd.read_csv(uploaded_file)
        st.session_state["table_10"] = to_ten_columns(raw)
        st.session_state["upload_sig_10"] = sig

    working_df = st.session_state["table_10"].copy()

    m1, m2, m3 = st.columns(3)
    m1.metric("Match totali", len(working_df))
    m2.metric(
        "VALUE BET",
        int(working_df["esito"].str.upper().str.contains("VALUE BET", na=False).sum()),
    )
    m3.metric(
        "Vincitore compilato",
        int((working_df["Vincitore"].str.strip() != "").sum()),
    )

    st.subheader("Tabella a 10 Colonne")
    edited = st.data_editor(
        working_df,
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
            "esito",
            "risultato",
        ],
    )

    clean_df = edited[TARGET_COLUMNS].copy()
    clean_df["Vincitore"] = clean_df["Vincitore"].fillna("").astype(str).str.strip()
    clean_df["risultato"] = ""
    st.session_state["table_10"] = clean_df

    st.divider()
    st.subheader("Output: Download CSV e Copia-Incolla")

    buf = io.StringIO()
    clean_df.to_csv(buf, index=False)
    csv_output = buf.getvalue()

    dates_present = [d for d in clean_df["Data"].unique() if d]
    file_date = dates_present[0] if len(dates_present) == 1 else datetime.now().strftime("%Y-%m-%d")
    download_name = f"{file_date}_tabella_10_colonne.csv"

    st.download_button(
        label=f"⬇️ Scarica {download_name}",
        data=csv_output.encode("utf-8"),
        file_name=download_name,
        mime="text/csv",
        type="primary",
    )

    st.markdown("**Blocco CSV da copiare e incollare:**")
    st.code(csv_output, language="csv")
