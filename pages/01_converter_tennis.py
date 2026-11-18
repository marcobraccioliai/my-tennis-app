import streamlit as st
import numpy as np

st.set_page_config(page_title="Pro Value Betting & Monte Carlo", layout="centered")

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
    
    /* Radio button (Superficie) */
    div[role="radiogroup"] label div p { color: #FFFDD0 !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Pro Value Betting & Monte Carlo")

# --- PANNELLO CONFIGURAZIONE RAPIDA (Bankroll e Superficie) ---
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    bankroll = st.number_input("💰 Il tuo Bankroll (€):", min_value=10.0, value=1000.0, step=50.0)
with col_cfg2:
    superficie = st.radio("🏟️ Superficie del match:", ["Cemento", "Terra Battuta", "Erba"], horizontal=True)

raw_text = st.text_area("Incolla blocco match SNAI:", height=140)

# --- 📚 DATABASE TENNISTI AMPLIATO (Servizio %, Risposta %, Bonus Superficie) ---
# Bonus superficie: valore aggiunto/sottratto alla probabilità di punto in base alla specializzazione
DATABASE_TENNISTI = {
    "sinner": {"serv": 0.70, "ret": 0.43, "bonus": {"Cemento": 0.015, "Terra Battuta": 0.00, "Erba": 0.01}},
    "alcaraz": {"serv": 0.69, "ret": 0.44, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": 0.015}},
    "djokovic": {"serv": 0.69, "ret": 0.42, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.005, "Erba": 0.015}},
    "medvedev": {"serv": 0.68, "ret": 0.41, "bonus": {"Cemento": 0.02, "Terra Battuta": -0.02, "Erba": 0.00}},
    "zverev": {"serv": 0.71, "ret": 0.36, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.01, "Erba": -0.01}},
    "rublev": {"serv": 0.68, "ret": 0.38, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.005, "Erba": -0.01}},
    "ruud": {"serv": 0.66, "ret": 0.39, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.025, "Erba": -0.025}},
    "tsitsipas": {"serv": 0.69, "ret": 0.37, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.02, "Erba": -0.015}},
    "fritz": {"serv": 0.71, "ret": 0.35, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.015, "Erba": 0.01}},
    "hurkacz": {"serv": 0.73, "ret": 0.32, "bonus": {"Cemento": 0.01, "Terra Battuta": -0.02, "Erba": 0.025}},
    "de minaur": {"serv": 0.65, "ret": 0.42, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.01}},
    "paul": {"serv": 0.67, "ret": 0.39, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.01}},
    "tiafoe": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.015, "Erba": 0.005}},
    "musetti": {"serv": 0.64, "ret": 0.39, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": 0.01}},
    "cobolli": {"serv": 0.63, "ret": 0.39, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": -0.01}},
    "berrettini": {"serv": 0.72, "ret": 0.33, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.005, "Erba": 0.025}},
    "arnaldi": {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "sonego": {"serv": 0.67, "ret": 0.35, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.005, "Erba": 0.01}},
    "bublik": {"serv": 0.68, "ret": 0.33, "bonus": {"Cemento": 0.005, "Terra Battuta": -0.03, "Erba": 0.025}},
    "prizmic": {"serv": 0.65, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "shelton": {"serv": 0.72, "ret": 0.34, "bonus": {"Cemento": 0.02, "Terra Battuta": -0.02, "Erba": 0.005}},
    "draper": {"serv": 0.70, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.015, "Erba": 0.02}},
    "rune": {"serv": 0.67, "ret": 0.39, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": 0.00}},
    "auger-aliassime": {"serv": 0.70, "ret": 0.35, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.01}},
    "dimitrov": {"serv": 0.69, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.005, "Erba": 0.01}}
}

def cerca_statistiche(nome_giocatore):
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], True
    return {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, False

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

def esegui_monte_carlo(p_serv_1, p_serv_2, n_sim=200000):
    vittorie_1 = 0
    for _ in range(n_sim):
        s1, s2 = 0, 0
        while s1 < 2 and s2 < 2:
            if simula_set(p_serv_1, p_serv_2): s1 += 1
            else: s2 += 1
        if s1 == 2: vittorie_1 += 1
    return (vittorie_1 / n_sim) * 100

def calcola_kelly(prob_percentuale, quota_bookmaker, bankroll, frazione=0.25):
    """Calcola la puntata consigliata con il Criterio di Kelly Frazionario (Quarter Kelly)"""
    p = prob_percentuale / 100.0
    q = 1.0 - p
    b = quota_bookmaker - 1.0
    if b <= 0: return 0.0, 0.0
    
    kelly_pieno = (b * p - q) / b
    if kelly_pieno <= 0:
        return 0.0, 0.0
        
    kelly_frazionario = kelly_pieno * frazione
    stake_euro = bankroll * kelly_frazionario
    return kelly_frazionario * 100, stake_euro
# ----------------------------------------

if st.button("🚀 ANALIZZA MATCH & CALCOLA STAKE"):
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
        
        stats_1, trovato_1 = cerca_statistiche(p1_name)
        stats_2, trovato_2 = cerca_statistiche(p2_name)
        
        # Applicazione del bonus/malus superficie sulle probabilità di servizio
        bonus_1 = stats_1["bonus"][superficie]
        bonus_2 = stats_2["bonus"][superficie]
        
        p_serv_1 = ((stats_1["serv"] + (1 - stats_2["ret"])) / 2) + bonus_1
        p_serv_2 = ((stats_2["serv"] + (1 - stats_1["ret"])) / 2) + bonus_2
        
        # --- DIAGNOSTICA VERBOSA ---
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 2px solid #FFFDD0; margin-bottom: 15px;">
                <span style="color: #FFFDD0; font-size: 16px; font-weight: bold;">🎾 {p1_name} vs {p2_name} ({superficie})</span><br><br>
                <span style="color: {'#00FF7F' if trovato_1 else '#FFA500'}; font-size: 14px;"><b>{p1_name}:</b> {"✅ Trovato in DB (Bonus " + superficie + f": {bonus_1*100:+.1f}%)" if trovato_1 else "⚠️ NON in DB -> Valori default applicati"}</span><br>
                <span style="color: {'#00FF7F' if trovato_2 else '#FFA500'}; font-size: 14px;"><b>{p2_name}:</b> {"✅ Trovato in DB (Bonus " + superficie + f": {bonus_2*100:+.1f}%)" if trovato_2 else "⚠️ NON in DB -> Valori default applicati"}</span><br><br>
                <span style="color: #FFD700; font-size: 13px;">⚙️ Input Monte Carlo (Prob. punto al servizio): <b>{p1_name} {p_serv_1*100:.1f}%</b> | <b>{p2_name} {p_serv_2*100:.1f}%</b></span>
            </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("⚙️ Esecuzione di 200.000 simulazioni Monte Carlo..."):
            prob_1 = esegui_monte_carlo(p_serv_1, p_serv_2, n_sim=200000)
            prob_2 = 100 - prob_1
            
            fair_odd_1 = 100 / prob_1 if prob_1 > 0 else 0
            fair_odd_2 = 100 / prob_2 if prob_2 > 0 else 0
            
            perc_k1, euro_k1 = calcola_kelly(prob_1, odd_1, bankroll)
            perc_k2, euro_k2 = calcola_kelly(prob_2, odd_2, bankroll)
            
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #FFFDD0;">
                    <p style="color: #FFFDD0; margin: 0; font-size: 14px;">Prob. {p1_name}</p>
                    <h2 style="color: #FFFDD0; margin: 5px 0; font-size: 32px;">{prob_1:.1f}%</h2>
                    <p style="color: #00FF7F; margin: 0; font-weight: bold;">Quota Equa: {fair_odd_1:.2f}</p>
                    <p style="color: #A0A0A0; margin: 5px 0 0 0; font-size: 13px;">Quota SNAI: <b style="color: #FFFDD0;">{odd_1}</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            if odd_1 > fair_odd_1 and euro_k1 > 0:
                st.markdown(f"""
                    <div style="background-color: #093d1e; padding: 10px; border-radius: 8px; border: 1px solid #00FF7F; margin-top: 10px; text-align: center;">
                        <span style="color: #00FF7F; font-weight: bold; font-size: 16px;">🔥 VALUE BET!</span><br>
                        <span style="color: #FFFDD0; font-size: 14px;">Puntata (Quarter Kelly): <b>€ {euro_k1:.2f}</b> ({perc_k1:.2f}%)</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #FFA07A; font-weight: bold; text-align: center; margin-top: 10px;">❌ No Value - Non scommettere</p>', unsafe_allow_html=True)
                
        with col2:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #FFFDD0;">
                    <p style="color: #FFFDD0; margin: 0; font-size: 14px;">Prob. {p2_name}</p>
                    <h2 style="color: #FFFDD0; margin: 5px 0; font-size: 32px;">{prob_2:.1f}%</h2>
                    <p style="color: #00FF7F; margin: 0; font-weight: bold;">Quota Equa: {fair_odd_2:.2f}</p>
                    <p style="color: #A0A0A0; margin: 5px 0 0 0; font-size: 13px;">Quota SNAI: <b style="color: #FFFDD0;">{odd_2}</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            if odd_2 > fair_odd_2 and euro_k2 > 0:
                st.markdown(f"""
                    <div style="background-color: #093d1e; padding: 10px; border-radius: 8px; border: 1px solid #00FF7F; margin-top: 10px; text-align: center;">
                        <span style="color: #00FF7F; font-weight: bold; font-size: 16px;">🔥 VALUE BET!</span><br>
                        <span style="color: #FFFDD0; font-size: 14px;">Puntata (Quarter Kelly): <b>€ {euro_k2:.2f}</b> ({perc_k2:.2f}%)</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #FFA07A; font-weight: bold; text-align: center; margin-top: 10px;">❌ No Value - Non scommettere</p>', unsafe_allow_html=True)
                
    else:
        st.error(f"Dati non estratti correttamente. Nomi: {len(players)}, Quote: {len(odds)}. Controlla il testo incollato.")
