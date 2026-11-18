import streamlit as st
import numpy as np
import pandas as pd
import requests
import csv
import io
from datetime import datetime

st.set_page_config(page_title="Pro Value Betting - Batch Scanner", layout="centered")

# Stile grafico blindato e pulito
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"] h1, 
    .stApp div[data-testid="stMarkdownContainer"] h2, 
    .stApp div[data-testid="stMarkdownContainer"] h3, 
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp label { color: #FFFDD0 !important; }
    .stButton button, .stButton button p, [data-testid="stDownloadButton"] button, [data-testid="stDownloadButton"] button p { 
        color: #000000 !important; 
        background-color: #FFFDD0 !important; 
        font-weight: bold !important; 
    }
    [data-testid="stTextArea"] textarea, [data-testid="stNumberInput"] input { 
        color: #000000 !important; 
        background-color: #FFFFFF !important; 
        -webkit-text-fill-color: #000000 !important; 
    }
    code { color: #B20000 !important; background-color: #FFFDD0 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a { color: #FFFDD0 !important; font-weight: bold; }
    div[role="radiogroup"] label div p { color: #FFFDD0 !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Pro Value Betting - Batch Scanner")

# --- PANNELLO CONFIGURAZIONE RAPIDA ---
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    bankroll = st.number_input("💰 Il tuo Bankroll (€):", min_value=10.0, value=1000.0, step=50.0)
with col_cfg2:
    superficie = st.radio("🏟️ Superficie del torneo:", ["Cemento", "Terra Battuta", "Erba"], horizontal=True)

raw_text = st.text_area(
    "Incolla l'intero blocco match SNAI del torneo:", 
    height=200, 
    placeholder="Incolla qui tutte le partite copiate dal palinsesto SNAI..."
)

# --- 📚 DATABASE LOCALE DI SUPPORTO (ATP & WTA) ---
DATABASE_TENNISTI = {
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
    "samsonova": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.015}}
}

# --- 🌐 INTEGRAZIONE ARCHIVIO JEFF SACKMANN (ATP + WTA) ---
@st.cache_data(ttl=86400)
def scarica_archivio_sackmann():
    urls = [
        "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_players.csv",
        "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_players.csv"
    ]
    giocatori_web = {}
    for url in urls:
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    cognome = row.get("name_last", "").strip().lower()
                    if cognome and len(cognome) > 3:
                        giocatori_web[cognome] = {
                            "nome_completo": f"{row.get('name_first', '')} {row.get('name_last', '')}".strip(),
                            "paese": row.get("ioc", "")
                        }
        except Exception:
            continue
    return giocatori_web

def estrai_dati_modello_A(nome_giocatore):
    """Modello A: Solo DB locale oppure Default puro"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale"
    return {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, "Default"

def estrai_dati_modello_B(nome_giocatore, quota_giocatore, quota_avversario, archivio_sackmann):
    """Modello B: DB locale -> Archivio Sackmann (ATP/WTA) + Calibrazione Bayesiana"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale"
            
    trovato_sackmann = False
    info_player = ""
    for cognome_ws, dati in archivio_sackmann.items():
        if cognome_ws in nome_pulito:
            trovato_sackmann = True
            info_player = f"{dati['nome_completo']} ({dati['paese']})"
            break
            
    prob_mercato = (1 / quota_giocatore) / ((1 / quota_giocatore) + (1 / quota_avversario))
    correzione = (prob_mercato - 0.50) * 0.08
    serv_stimato = np.clip(0.61 + correzione, 0.53, 0.68)
    ret_stimato = np.clip(0.37 + correzione, 0.30, 0.44)
    
    etichetta = f"Sackmann ({info_player})" if trovato_sackmann else "Stima Circuito (Market)"
    return {"serv": serv_stimato, "ret": ret_stimato, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, etichetta

# --- MOTORE MONTE CARLO ISOLATO ---
def simula_punto(p_serv):
    return np.random.random() < p_serv

def simula_game(p_serv):
    punti_serv, punti_risp = 0, 0
    while True:
        if punti_serv >= 3 and punti_risp >= 3:
            p1, p2 = simula_punto(p_serv), simula_punto(p_serv)
            if p1 and p2: return True
            if not p1 and not p2: return False
        else:
            if simula_punto(p_serv): punti_serv += 1
            else: punti_risp += 1
            if punti_serv >= 4 and punti_serv - punti_risp >= 2: return True
            if punti_risp >= 4 and punti_risp - punti_serv >= 2: return False

def simula_tiebreak(p_serv_1, p_serv_2):
    p1_pts, p2_pts = 0, 0
    while True:
        serv_1 = ((p1_pts + p2_pts) // 1) % 2 == 0
        p_curr = p_serv_1 if serv_1 else (1 - p_serv_2)
        if simula_
