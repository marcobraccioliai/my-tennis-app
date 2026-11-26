# 04_oddsportal_check_risultati.py
# Streamlit page: recupero vincitori tennis con fonti in fallback.
#
# Dipendenze (requirements.txt):
# streamlit
# pandas
# requests
#
# Avvio locale:
# streamlit run 04_oddsportal_check_risultati.py

from __future__ import annotations

import io
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="OddsPortal - Verifica risultati",
    page_icon="🎾",
    layout="wide",
)

OUTPUT_COLUMNS = [
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

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.sofascore.com/",
    }
)

# Timeout breve: una fonte lenta non deve bloccare tutta la catena.
REQUEST_TIMEOUT = 9


# ---------------------------------------------------------------------------
# Normalizzazione CSV
# ---------------------------------------------------------------------------

def _normalizza_colonna(nome: Any) -> str:
    testo = str(nome).strip().lower()
    testo = unicodedata.normalize("NFKD", testo)
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", testo)


def _trova_colonna(df: pd.DataFrame, *nomi: str) -> Optional[str]:
    lookup = {_normalizza_colonna(c): c for c in df.columns}
    for nome in nomi:
        trovato = lookup.get(_normalizza_colonna(nome))
        if trovato is not None:
            return trovato
    return None


def leggi_csv(uploaded_file) -> pd.DataFrame:
    """Legge CSV con separatore/encoding automatici e restituisce 9 colonne."""
    contenuto = uploaded_file.getvalue()
    errori = []

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(
                io.BytesIO(contenuto),
                sep=None,
                engine="python",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
            )
            break
        except Exception as exc:
            errori.append(f"{encoding}: {exc}")
    else:
        raise ValueError("Impossibile leggere il CSV. " + " | ".join(errori))

    mapping = {
        "Data": _trova_colonna(df, "Data"),
        "Giocatore 1": _trova_colonna(df, "Giocatore 1", "Giocatore1"),
        "Quota 1": _trova_colonna(df, "Quota 1", "Quota1"),
        "Giocatore 2": _trova_colonna(df, "Giocatore 2", "Giocatore2"),
        "Quota 2": _trova_colonna(df, "Quota 2", "Quota2"),
        "Miglior Lato": _trova_colonna(df, "Miglior Lato", "MigliorLato"),
        "Quota Scelta": _trova_colonna(df, "Quota Scelta", "QuotaScelta"),
        "Vincitore": _trova_colonna(df, "Vincitore", "vincitore"),
    }

    mancanti = [
        nome for nome, colonna in mapping.items()
        if colonna is None and nome != "Vincitore"
    ]
    if mancanti:
        raise ValueError(
            "Nel CSV mancano queste colonne obbligatorie: "
            + ", ".join(mancanti)
        )

    pulito = pd.DataFrame()
    for destinazione in OUTPUT_COLUMNS:
        sorgente = mapping.get(destinazione)
        if destinazione == "Esito":
            # Regola inderogabile: Esito deve essere sempre vuota.
            pulito[destinazione] = ""
        elif destinazione == "Vincitore":
            pulito[destinazione] = (
                df[sorgente].astype(str).str.strip()
                if sorgente is not None
                else ""
            )
        else:
            pulito[destinazione] = df[sorgente].astype(str).str.strip()

    pulito = pulito[OUTPUT_COLUMNS].fillna("")
    return pulito


# ---------------------------------------------------------------------------
# Matching giocatori
# ---------------------------------------------------------------------------

def normalizza_testo(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def iniziale_nome_csv(nome_csv: str) -> str:
    """Estrae l'iniziale dal formato tipico 'Cognome N.'."""
    tokens = re.findall(r"[A-Za-zÀ-ÿ]+", str(nome_csv))
    if not tokens:
        return ""
    # L'ultimo token è normalmente l'iniziale del nome.
    ultimo = tokens[-1]
    if len(ultimo) == 1:
        return ultimo.lower()
    # In alcuni export l'iniziale è scritta senza punto.
    return ""


def cognome_csv(nome_csv: str) -> str:
    tokens = re.findall(r"[A-Za-zÀ-ÿ]+", str(nome_csv))
    if len(tokens) <= 1:
        return normalizza_testo(nome_csv)
    # Il formato del CSV è "Cognome N." oppure "Cognome composto N.".
    if len(tokens[-1]) == 1:
        tokens = tokens[:-1]
    return normalizza_testo(" ".join(tokens))


def corrisponde_giocatore(nome_csv: str, nome_fonte: str) -> bool:
    """
    Confronto prudente tra 'Perego G.' e un nome completo restituito dalla fonte.
    Richiede corrispondenza del cognome e, se presente nel CSV, dell'iniziale.
    """
    csv_norm = normalizza_testo(nome_csv)
    fonte_norm = normalizza_testo(nome_fonte)
    if not csv_norm or not fonte_norm:
        return False

    cognome = cognome_csv(nome_csv)
    if not cognome:
        return False

    # Cognomi composti: accetta la sequenza completa o, come fallback,
    # il token finale del cognome se la fonte abbrevia il nome.
    cognome_tokens = cognome.split()
    if len(cognome_tokens) > 1:
        cognome_ok = cognome in fonte_norm
    else:
        cognome_ok = cognome_tokens[0] in fonte_norm.split()

    if not cognome_ok:
        return False

    iniziale = iniziale_nome_csv(nome_csv)
    if iniziale:
        parole = fonte_norm.split()
        # L'iniziale deve essere compatibile con almeno una parola del nome
        # che non sia parte del cognome. Se la fonte non espone il nome,
        # il match non viene promosso a risultato certo.
        cognome_parole = set(cognome_tokens)
        nomi = [p for p in parole if p not in cognome_parole]
        if nomi and not any(p.startswith(iniziale) for p in nomi):
            return False
    return True


def formato_vincitore(nome_fonte: str, giocatore1: str, giocatore2: str) -> Optional[str]:
    match1 = corrisponde_giocatore(giocatore1, nome_fonte)
    match2 = corrisponde_giocatore(giocatore2, nome_fonte)
    if match1 and not match2:
        return giocatore1
    if match2 and not match1:
        return giocatore2
    return None


def chiave_match(nome1: str, nome2: str) -> set[str]:
    return {normalizza_testo(nome1), normalizza_testo(nome2)}


# ---------------------------------------------------------------------------
# Fonti di ricerca
# Ogni fonte restituisce: {"winner": nome_completo} oppure
# {"status": "Annullata" / "Posticipata" / "Rimandata"} oppure None.
# I punteggi non vengono mai utilizzati.
# ---------------------------------------------------------------------------

def _get_json(url: str, params: Optional[dict] = None) -> Any:
    response = SESSION.get(
        url, params=params, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def cerca_sofascore(g1: str, g2: str, data_match: str) -> Optional[dict]:
    """Fonte 1: API pubblica SofaScore (ricerca eventi/partite)."""
    try:
        # La ricerca per entrambi i cognomi limita i falsi positivi.
        q1 = cognome_csv(g1).split()[-1]
        q2 = cognome_csv(g2).split()[-1]
        query = f"{q1} {q2}"
        payload = _get_json(
            "https://www.sofascore.com/api/v1/search/all",
            {"q": query},
        )
        risultati = payload.get("results", []) if isinstance(payload, dict) else []
        data_target = pd.to_datetime(data_match, errors="coerce")
        if pd.isna(data_target):
            data_target = None

        for item in risultati:
            if item.get("type") not in ("event", "team"):
                continue
            entity = item.get("entity", {}) or {}
            if item.get("type") == "event":
                eventi = [entity]
            else:
                eventi = []

            for evento in eventi:
                if evento.get("sport", {}).get("slug") not in (None, "tennis"):
                    continue
                home = (evento.get("homeTeam") or {}).get("name", "")
                away = (evento.get("awayTeam") or {}).get("name", "")
                if not (
                    (corrisponde_giocatore(g1, home) and corrisponde_giocatore(g2, away))
                    or (corrisponde_giocatore(g1, away) and corrisponde_giocatore(g2, home))
                ):
                    continue

                timestamp = evento.get("startTimestamp")
                if timestamp and data_target is not None:
                    giorno_evento = datetime.fromtimestamp(
                        int(timestamp)
                    ).date()
                    if abs((giorno_evento - data_target.date()).days) > 1:
                        continue

                status = (evento.get("status") or {}).get("description", "").lower()
                if any(x in status for x in ("cancel", "annull")):
                    return {"status": "Annullata"}
                if any(x in status for x in ("postpon", "delay", "suspend")):
                    return {"status": "Posticipata"}

                winner_code = evento.get("winnerCode")
                if winner_code == 1:
                    return {"winner": home}
                if winner_code == 2:
                    return {"winner": away}
        return None
    except Exception:
        return None


def cerca_espn(g1: str, g2: str, data_match: str) -> Optional[dict]:
    """Fonte 2: scoreboard ESPN, endpoint pubblico non autenticato."""
    try:
        dt = pd.to_datetime(data_match, errors="coerce")
        if pd.isna(dt):
            return None
        date_param = dt.strftime("%Y%m%d")
        sport_urls = [
            "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
            "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
        ]

        for url in sport_urls:
            payload = _get_json(url, {"dates": date_param})
            for event in payload.get("events", []):
                competitors = []
                for comp in event.get("competitions", []):
                    competitors.extend(comp.get("competitors", []))
                if len(competitors) < 2:
                    continue

                names = [
                    (c.get("athlete") or {}).get("displayName")
                    or c.get("team", {}).get("displayName", "")
                    for c in competitors[:2]
                ]
                if not (
                    (corrisponde_giocatore(g1, names[0]) and corrisponde_giocatore(g2, names[1]))
                    or (corrisponde_giocatore(g1, names[1]) and corrisponde_giocatore(g2, names[0]))
                ):
                    continue

                status_text = (
                    event.get("status", {}).get("type", {}).get("description", "")
                    or event.get("status", {}).get("type", {}).get("name", "")
                ).lower()
                if any(x in status_text for x in ("canceled", "cancelled")):
                    return {"status": "Annullata"}
                if any(x in status_text for x in ("postponed", "delayed")):
                    return {"status": "Posticipata"}

                winner = next(
                    (c for c in competitors if c.get("winner") is True),
                    None,
                )
                if winner:
                    nome = (
                        (winner.get("athlete") or {}).get("displayName")
                        or winner.get("team", {}).get("displayName", "")
                    )
                    if nome:
                        return {"winner": nome}
        return None
    except Exception:
        return None


def cerca_bing_rss(g1: str, g2: str, data_match: str) -> Optional[dict]:
    """
    Fonte 3: ricerca web tramite feed RSS Bing.
    Viene accettato soltanto un testo esplicito 'X def. Y' / 'X defeated Y'.
    Non si tenta di ricavare il vincitore dai punteggi.
    """
    try:
        c1 = cognome_csv(g1)
        c2 = cognome_csv(g2)
        query = f'tennis "{c1}" "{c2}" results'
        response = SESSION.get(
            "https://www.bing.com/news/search",
            params={"q": query, "format": "rss"},
            headers={"Accept": "application/rss+xml, application/xml"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        testi = []
        for item in root.findall(".//item"):
            title = item.findtext("title", default="")
            desc = item.findtext("description", default="")
            testi.append(re.sub(r"<[^>]+>", " ", f"{title} {desc}"))

        for testo in testi:
            testo_norm = normalizza_testo(testo)
            if not (
                cognome_csv(g1) in testo_norm
                and cognome_csv(g2) in testo_norm
            ):
                continue

            # Pattern volutamente conservativi: non basta che i due nomi
            # compaiano nello stesso articolo.
            for nome_csv, altro_csv in ((g1, g2), (g2, g1)):
                cognome_vincitore = re.escape(cognome_csv(nome_csv))
                cognome_altro = re.escape(cognome_csv(altro_csv))
                patterns = [
                    rf"\b{cognome_vincitore}\b.{{0,35}}\b(def\.?|defeated|beat|beats|d\.|over)\b.{{0,35}}\b{cognome_altro}\b",
                ]
                if any(re.search(p, testo_norm) for p in patterns):
                    return {"winner": nome_csv}
        return None
    except Exception:
        return None


SOURCES = {
    "SofaScore": cerca_sofascore,
    "ESPN": cerca_espn,
    "Bing News": cerca_bing_rss,
}


def cerca_risultato(
    riga: pd.Series,
    fonti_attive: list[str],
    pausa: float,
    log_callback=None,
) -> tuple[str, str, str]:
    """
    Ritorna (valore_vincitore, tipo_esito, fonte).
    tipo_esito: winner / anomalous / not_found.
    """
    g1 = str(riga["Giocatore 1"]).strip()
    g2 = str(riga["Giocatore 2"]).strip()
    data_match = str(riga["Data"]).strip()

    for nome_fonte in fonti_attive:
        funzione = SOURCES[nome_fonte]
        if log_callback:
            log_callback(f"Interrogo {nome_fonte}...")
        risultato = funzione(g1, g2, data_match)

        if risultato:
            if "winner" in risultato:
                vincitore = formato_vincitore(
                    risultato["winner"], g1, g2
                )
                if vincitore:
                    return vincitore, "winner", nome_fonte

            if "status" in risultato:
                stato = risultato["status"]
                if stato in ("Annullata", "Posticipata", "Rimandata"):
                    return stato, "anomalous", nome_fonte

        if pausa > 0:
            time.sleep(pausa)

    return "", "not_found", ""


# ---------------------------------------------------------------------------
# Interfaccia Streamlit
# ---------------------------------------------------------------------------

st.title("🎾 OddsPortal – Verifica risultati")
st.caption(
    "Carica l'esportazione di 03_oddsportal_test_150.py, "
    "cerca i vincitori e scarica il CSV ridotto."
)

with st.sidebar:
    st.header("Impostazioni ricerca")
    pausa = st.slider(
        "Pausa tra le fonti (secondi)",
        min_value=0.0,
        max_value=3.0,
        value=0.5,
        step=0.5,
        help="Intervallo applicato tra una fonte e la successiva per ogni partita.",
    )
    fonti_attive = st.multiselect(
        "Fonti attive (ordine di fallback)",
        options=list(SOURCES.keys()),
        default=list(SOURCES.keys()),
        help="Le fonti vengono interrogate nell'ordine mostrato.",
    )
    st.caption(
        "La disponibilità e la copertura delle API pubbliche possono variare. "
        "Un risultato non verificabile viene lasciato vuoto."
    )

uploaded = st.file_uploader(
    "Carica il CSV prodotto da 03_oddsportal_test_150.py",
    type=["csv"],
    accept_multiple_files=False,
)

if uploaded is not None:
    try:
        if (
            st.session_state.get("uploaded_name") != uploaded.name
            or st.session_state.get("uploaded_bytes") != uploaded.getvalue()
        ):
            st.session_state["uploaded_name"] = uploaded.name
            st.session_state["uploaded_bytes"] = uploaded.getvalue()
            st.session_state["risultati_df"] = leggi_csv(uploaded)
            st.session_state.pop("ricerca_completata", None)

        df = st.session_state["risultati_df"].copy()
    except Exception as exc:
        st.error(f"Errore durante la lettura del CSV: {exc}")
        st.stop()

    date_presenti = sorted(
        {str(x).strip() for x in df["Data"].tolist() if str(x).strip()}
    )
    st.subheader("Riepilogo file")
    c1, c2, c3 = st.columns(3)
    c1.metric("Partite caricate", len(df))
    c2.metric("Date presenti", len(date_presenti))
    c3.metric("Colonne output", len(OUTPUT_COLUMNS))
    st.write("**Date:** " + (", ".join(date_presenti) if date_presenti else "Non indicate"))

    st.subheader("Anteprima tracciato ridotto")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Ricerca automatica dei vincitori")

    if not fonti_attive:
        st.warning("Seleziona almeno una fonte nella barra laterale.")
    else:
        if st.button(
            "🔎 Cerca Vincitori in Rete",
            type="primary",
            use_container_width=True,
        ):
            lavoro = df.copy()
            lavoro["Vincitore"] = lavoro["Vincitore"].fillna("").astype(str)
            lavoro["Esito"] = ""

            progress = st.progress(0)
            stato = st.empty()
            log_area = st.container()
            log_lines = []
            trovati = 0
            anomali = 0
            non_trovati = 0
            totale = len(lavoro)

            for idx, riga in lavoro.iterrows():
                descrizione = (
                    f"{riga['Data']} | {riga['Giocatore 1']} – "
                    f"{riga['Giocatore 2']}"
                )
                stato.info(
                    f"Partita {idx + 1} di {totale}: {descrizione}"
                )

                def aggiorna_log(messaggio: str):
                    log_lines.append(f"**{descrizione}** — {messaggio}")
                    with log_area:
                        st.caption(log_lines[-1])

                valore, tipo, fonte = cerca_risultato(
                    riga,
                    fonti_attive,
                    pausa,
                    log_callback=aggiorna_log,
                )

                if tipo == "winner":
                    lavoro.at[idx, "Vincitore"] = valore
                    trovati += 1
                    log_lines.append(f"✓ Vincitore: {valore} ({fonte})")
                elif tipo == "anomalous":
                    lavoro.at[idx, "Vincitore"] = valore
                    anomali += 1
                    log_lines.append(f"⚠ Stato: {valore} ({fonte})")
                else:
                    # Se non trovato, conserva un eventuale valore già
                    # presente nel CSV; normalmente sarà vuoto.
                    non_trovati += 1
                    log_lines.append("— Nessun risultato verificabile")

                lavoro.at[idx, "Esito"] = ""
                progress.progress((idx + 1) / max(totale, 1))

            lavoro = lavoro[OUTPUT_COLUMNS].fillna("")
            st.session_state["risultati_df"] = lavoro
            st.session_state["ricerca_completata"] = True
            st.session_state["riepilogo_ricerca"] = {
                "trovati": trovati,
                "anomali": anomali,
                "non_trovati": non_trovati,
            }
            stato.success("Ricerca completata.")

    if st.session_state.get("ricerca_completata"):
        riepilogo = st.session_state.get("riepilogo_ricerca", {})
        st.subheader("Riepilogo ricerca")
        a, b, c = st.columns(3)
        a.metric("Trovati", riepilogo.get("trovati", 0))
        b.metric("Rinviati / Annullati", riepilogo.get("anomali", 0))
        c.metric("Non trovati", riepilogo.get("non_trovati", 0))

    st.divider()
    st.subheader("Revisione manuale")

    dati_editor = st.session_state["risultati_df"].copy()
    dati_editor["Esito"] = ""

    modificato = st.data_editor(
        dati_editor,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[col for col in OUTPUT_COLUMNS if col != "Vincitore"],
        column_config={
            "Data": st.column_config.TextColumn("Data"),
            "Giocatore 1": st.column_config.TextColumn("Giocatore 1"),
            "Quota 1": st.column_config.TextColumn("Quota 1"),
            "Giocatore 2": st.column_config.TextColumn("Giocatore 2"),
            "Quota 2": st.column_config.TextColumn("Quota 2"),
            "Miglior Lato": st.column_config.TextColumn("Miglior Lato"),
            "Quota Scelta": st.column_config.TextColumn("Quota Scelta"),
            "Vincitore": st.column_config.TextColumn(
                "Vincitore",
                help="Modifica o inserisci il vincitore nel formato Cognome I.",
            ),
            "Esito": st.column_config.TextColumn(
                "Esito",
                help="Campo bloccato: deve rimanere vuoto.",
            ),
        },
        key="editor_risultati",
    )

    # Protezione ulteriore: qualsiasi valore immesso in Esito viene cancellato.
    modificato = modificato[OUTPUT_COLUMNS].copy()
    modificato["Vincitore"] = modificato["Vincitore"].fillna("").astype(str).str.strip()
    modificato["Esito"] = ""
    st.session_state["risultati_df"] = modificato

    csv_bytes = modificato.to_csv(
        index=False,
        sep=",",
        encoding="utf-8",
        lineterminator="\n",
    ).encode("utf-8")

    date_filename = "risultati"
    if date_presenti:
        try:
            date_filename = pd.to_datetime(
                date_presenti[0], dayfirst=False, errors="raise"
            ).strftime("%Y-%m-%d")
        except Exception:
            date_filename = re.sub(r"[^0-9-]", "-", date_presenti[0]) or "risultati"

    nome_file = f"{date_filename}_risultati_ridotti.csv"

    st.subheader("Esportazione")
    st.download_button(
        label="⬇️ Scarica CSV ridotto",
        data=csv_bytes,
        file_name=nome_file,
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "Il contenuto qui sotto è generato dagli stessi dati del pulsante "
        "di download: 9 colonne, separatore virgola, UTF-8 ed Esito vuota."
    )
    st.code(csv_bytes.decode("utf-8"), language="csv")

else:
    st.info(
        "Carica un file CSV per iniziare. L'app mostrerà il riepilogo, "
        "la tabella ridotta e gli strumenti di ricerca."
    )
