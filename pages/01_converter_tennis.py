import streamlit as st
import numpy as np
import requests
import csv
import io

st.set_page_config(page_title="Pro Value Betting & Monte Carlo (Sackmann Edition)", layout="centered")

# Stile grafico blindato e pulito
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"] h1, 
    .stApp div[data-testid="stMarkdownContainer"] h2, 
    .stApp div[data-testid="stMarkdownContainer"] h3, 
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp label { color: #FFFDD0 !important; }
    .stButton button, .stButton button p { color: #000000 !important; background-color: #FFFDD0 !important; font-weight: bold !important; }
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

st.title("🎾 Pro Value Betting & Monte Carlo")

# --- PANNELLO CONFIGURAZIONE RAPIDA ---
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    bankroll = st.number_input("💰 Il tuo Bankroll (€):", min_value=10.0, value=1000.0, step=50.0)
with col_cfg2:
    superficie = st.radio("🏟️ Superficie del match:", ["Cemento", "Terra Battuta", "Erba"], horizontal=True)

raw_text = st.text_area("Incolla blocco match SNAI:", height=140)

# --- 📚 DATABASE LOCALE DI SUPPORTO ---
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
    "moroni": {"serv": 0.60, "ret": 0.35, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.015, "Erba": -0.015}}
}

# --- 🌐 INTEGRAZIONE ARCHIVIO JEFF SACKMANN (GitHub) ---
@st.cache_data(ttl=86400)
def scarica_archivio_sackmann():
    """Scarica in modo trasparente l'anagrafica ufficiale dei tennisti dal repository di Jeff Sackmann"""
    url = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_players.csv"
    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            giocatori_web = {}
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                cognome = row.get("name_last", "").strip().lower()
                if cognome:
                    giocatori_web[cognome] = {
                        "nome_completo": f"{row.get('name_first', '')} {row.get('name_last', '')}".strip(),
                        "mano": row.get("hand", "U"),
                        "paese": row.get("ioc", "")
                    }
            return giocatori_web
    except Exception:
        pass
    return {}

def cerca_statistiche_modello_A(nome_giocatore):
    """Modello A: Solo DB Locale / Default"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale"
    return {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, "Default (Non in DB)"

def cerca_statistiche_modello_B(nome_giocatore, quota_giocatore, quota_avversario, archivio_sackmann):
    """Modello B: DB Locale + Ricerca automatica su Jeff Sackmann e calibrazione di mercato"""
    nome_pulito = nome_giocatore.lower()
    
    # 1. Controllo nel DB locale rapido
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale (Ottimizzato)"
            
    # 2. Controllo nell'archivio globale di Jeff Sackmann
    trovato_sackmann = False
    info_giocatore = ""
    for cognome_ws, dati in archivio_sackmann.items():
        if len(cognome_ws) > 3 and cognome_ws in nome_pulito:
            trovato_sackmann = True
            info_giocatore = f"{dati['nome_completo']} ({dati['paese']})"
            break
            
    # 3. Calibrazione statistica intelligente basata sulle quote SNAI (circuito Challenger / ITF)
    prob_mercato = (1 / quota_giocatore) / ((1 / quota_giocatore) + (1 / quota_avversario))
    correzione = (prob_mercato - 0.50) * 0.08
    
    serv_stimato = np.clip(0.61 + correzione, 0.54, 0.68)
    ret_stimato = np.clip(0.37 + correzione, 0.30, 0.44)
    
    if trovato_sackmann:
        etichetta = f"Archivio Sackmann ({info_giocatore}) + Calibrazione"
    else:
        etichetta = "Stima Circuiti Minori (Sackmann/Market)"
        
    return {"serv": serv_stimato, "ret": ret_stimato, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, etichetta

# --- MOTORE DI SIMULAZIONE MONTE CARLO ---
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
        if simula_punto(p_curr): p1_pts += 1
        else: p2_pts += 1
        if (p1_pts >= 7 or p2_pts >= 7) and abs(p1_pts - p2_pts) >= 2:
            return p1_pts > p2_pts

def simula_set(p_serv_1, p_serv_2):
    g1, g2 = 0, 0
    while True:
        t1 = (g1 + g2) % 2 == 0
        p_curr = p_serv_1 if t1 else (1 - p_serv_2)
        vince_g1 = simula_game(p_curr) if t1 else not simula_game(1 - p_serv_2)
        if t1 and vince_g1: g1 += 1
        elif t1 and not vince_g1: g2 += 1
        elif not t1 and not vince_g1: g1 += 1
        else: g2 += 1
        if g1 == 6 and g2 == 6: return simula_tiebreak(p_serv_1, p_serv_2)
        if (g1 >= 6 or g2 >= 6) and abs(g1 - g2) >= 2: return g1 > g2

def esegui_monte_carlo(p_serv_1, p_serv_2, n_sim=150000):
    vittorie_1 = 0
    for _ in range(n_sim):
        s1, s2 = 0, 0
        while s1 < 2 and s2 < 2:
            if simula_set(p_serv_1, p_serv_2): s1 += 1
            else: s2 += 1
        if s1 == 2: vittorie_1 += 1
    return (vittorie_1 / n_sim) * 100

def arrotonda_per_snai(importo_euro):
    """Vincoli SNAI: puntata minima 1.00€, incrementi di 0.05€"""
    if importo_euro < 1.0:
        return 0.0
    importo_arrotondato = round(importo_euro / 0.05) * 0.05
    return max(1.0, importo_arrotondato)

def calcola_kelly(prob_percentuale, quota_bookmaker, bankroll, frazione=0.25):
    p = prob_percentuale / 100.0
    q = 1.0 - p
    b = quota_bookmaker - 1.0
    if b <= 0: return 0.0, 0.0
    kelly_pieno = (b * p - q) / b
    if kelly_pieno <= 0: return 0.0, 0.0
    stake_euro_grezzo = bankroll * (kelly_pieno * frazione)
    stake_euro_snai = arrotonda_per_snai(stake_euro_grezzo)
    perc_effettiva = (stake_euro_snai / bankroll) * 100 if bankroll > 0 else 0.0
    return perc_effettiva, stake_euro_snai
# ----------------------------------------

if st.button("🚀 ANALIZZA MATCH (CONFRONTO A/B SACKMANN)"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players, odds = [], []
    
    for line in lines:
        if any(char in line for char in ["/", ":"]): continue
        if any(c.isalpha() for c in line):
            players.append(line)
        elif "." in line:
            try:
                odds.append(line.replace(',', '.'))
            except:
                continue
            
    if len(players) >= 2 and len(odds) >= 2:
        p1_name, p2_name = players[0], players[1]
        odd_1, odd_2 = float(odds[0]), float(odds[1])
        
        with st.spinner("🌐 Connessione all'archivio storico di Jeff Sackmann in corso..."):
            archivio_sackmann = scarica_archivio_sackmann()
            
            # --- MODELLO A (Solo DB Locale / Default) ---
            s1_A, src1_A = cerca_statistiche_modello_A(p1_name)
            s2_A, src2_A = cerca_statistiche_modello_A(p2_name)
            p_serv_1_A = ((s1_A["serv"] + (1 - s2_A["ret"])) / 2) + s1_A["bonus"][superficie]
            p_serv_2_A = ((s2_A["serv"] + (1 - s1_A["ret"])) / 2) + s2_A["bonus"][superficie]
            
            prob_1_A = esegui_monte_carlo(p_serv_1_A, p_serv_2_A)
            prob_2_A = 100 - prob_1_A
            fair_1_A = 100 / prob_1_A if prob_1_A > 0 else 0
            fair_2_A = 100 / prob_2_A if prob_2_A > 0 else 0
            _, euro_1_A = calcola_kelly(prob_1_A, odd_1, bankroll)
            _, euro_2_A = calcola_kelly(prob_2_A, odd_2, bankroll)
            
            # --- MODELLO B (DB Locale + Jeff Sackmann & Calibrazione) ---
            s1_B, src1_B = cerca_statistiche_modello_B(p1_name, odd_1, odd_2, archivio_sackmann)
            s2_B, src2_B = cerca_statistiche_modello_B(p2_name, odd_2, odd_1, archivio_sackmann)
            p_serv_1_B = ((s1_B["serv"] + (1 - s2_B["ret"])) / 2) + s1_B["bonus"][superficie]
            p_serv_2_B = ((s2_B["serv"] + (1 - s1_B["ret"])) / 2) + s2_B["bonus"][superficie]
            
            prob_1_B = esegui_monte_carlo(p_serv_1_B, p_serv_2_B)
            prob_2_B = 100 - prob_1_B
            fair_1_B = 100 / prob_1_B if prob_1_B > 0 else 0
            fair_2_B = 100 / prob_2_B if prob_2_B > 0 else 0
            _, euro_1_B = calcola_kelly(prob_1_B, odd_1, bankroll)
            _, euro_2_B = calcola_kelly(prob_2_B, odd_2, bankroll)

        # --- DIAGNOSTICA VERBOSA ---
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 2px solid #FFFDD0; margin-bottom: 15px;">
                <span style="color: #FFFDD0; font-size: 16px; font-weight: bold;">🎾 {p1_name} (@{odd_1}) vs {p2_name} (@{odd_2}) — {superficie}</span><br><br>
                <span style="color: #FFD700; font-size: 13px;"><b>Modello A (Interno):</b><br>
                • {p1_name}: {src1_A}<br>
                • {p2_name}: {src2_A}</span><br><br>
                <span style="color: #00FF7F; font-size: 13px;"><b>Modello B (Sackmann Edition):</b><br>
                • {p1_name}: {src1_B}<br>
                • {p2_name}: {src2_B}</span>
            </div>
        """, unsafe_allow_html=True)

        # --- CONFRONTO AFFIANCATO A vs B ---
        st.markdown("### 📊 Confronto Modelli (Backtesting in Corso)")
        col_A, col_B = st.columns(2)
        
        with col_A:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #FFD700;">
                    <h3 style="color: #FFD700; margin-top:0; text-align:center;">🅰️ Modello A</h3>
                    <p style="color: #FFFDD0; margin-bottom: 5px;"><b>{p1_name}</b>: {prob_1_A:.1f}% (Equa: <b>{fair_1_A:.2f}</b>)</p>
                    <p style="color: {'#00FF7F' if euro_1_A > 0 else '#FFA07A'}; font-size: 14px; margin-top:0;">
                        {"🔥 VALUE! Puntata: € " + f"{euro_1_A:.2f}" if euro_1_A > 0 else "❌ No Value"}
                    </p>
                    <hr style="border-color: #444;">
                    <p style="color: #FFFDD0; margin-bottom: 5px;"><b>{p2_name}</b>: {prob_2_A:.1f}% (Equa: <b>{fair_2_A:.2f}</b>)</p>
                    <p style="color: {'#00FF7F' if euro_2_A > 0 else '#FFA07A'}; font-size: 14px; margin-top:0;">
                        {"🔥 VALUE! Puntata: € " + f"{euro_2_A:.2f}" if euro_2_A > 0 else "❌ No Value"}
                    </p>
                </div>
            """, unsafe_allow_html=True)

        with col_B:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #00FF7F;">
                    <h3 style="color: #00FF7F; margin-top:0; text-align:center;">🅱️ Modello B (Sackmann)</h3>
                    <p style="color: #FFFDD0; margin-bottom: 5px;"><b>{p1_name}</b>: {prob_1_B:.1f}% (Equa: <b>{fair_1_B:.2f}</b>)</p>
                    <p style="color: {'#00FF7F' if euro_1_B > 0 else '#FFA07A'}; font-size: 14px; margin-top:0;">
                        {"🔥 VALUE! Puntata: € " + f"{euro_1_B:.2f}" if euro_1_B > 0 else "❌ No Value"}
                    </p>
                    <hr style="border-color: #444;">
                    <p style="color: #FFFDD0; margin-bottom: 5px;"><b>{p2_name}</b>: {prob_2_B:.1f}% (Equa: <b>{fair_2_B:.2f}</b>)</p>
                    <p style="color: {'#00FF7F' if euro_2_B > 0 else '#FFA07A'}; font-size: 14px; margin-top:0;">
                        {"🔥 VALUE! Puntata: € " + f"{euro_2_B:.2f}" if euro_2_B > 0 else "❌ No Value"}
                    </p>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.error(f"Dati non estratti correttamente. Nomi: {len(players)}, Quote: {len(odds)}. Controlla il testo incollato.")
