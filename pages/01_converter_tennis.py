import streamlit as st
import numpy as np

st.set_page_config(page_title="Converter & Monte Carlo Tennis", layout="centered")

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
    [data-testid="stTextArea"] textarea { color: #000000 !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #000000 !important; }
    code { color: #B20000 !important; background-color: #FFFDD0 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a { color: #FFFDD0 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("✂️ Converter & Monte Carlo Tennis")
raw_text = st.text_area("Incolla blocco match SNAI:", height=150)

# --- 📚 DATABASE LOCALE AMPLIATO (Con flag di controllo) ---
DATABASE_TENNISTI = {
    "cobolli": {"serv": 0.63, "ret": 0.39},
    "tiafoe": {"serv": 0.66, "ret": 0.37},
    "sinner": {"serv": 0.70, "ret": 0.43},
    "alcaraz": {"serv": 0.69, "ret": 0.44},
    "medvedev": {"serv": 0.68, "ret": 0.41},
    "djokovic": {"serv": 0.69, "ret": 0.42},
    "zverev": {"serv": 0.71, "ret": 0.36},
    "bublik": {"serv": 0.67, "ret": 0.33},
    "prizmic": {"serv": 0.65, "ret": 0.38}
}

def cerca_statistiche(nome_giocatore):
    """Cerca il tennista nel database locale e restituisce le stats e lo stato di origine"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], True # Trovato nel DB
    # Valori di default se il tennista non è censito
    return {"serv": 0.64, "ret": 0.38}, False # Non trovato, usato default

# --- MOTORE DI SIMULAZIONE MONTE CARLO ---
def simula_punto(p_serv):
    return np.random.random() < p_serv

def simula_game(p_serv):
    punti_serv = 0
    punti_risp = 0
    while True:
        if punti_serv >= 3 and punti_risp >= 3:
            p1 = simula_punto(p_serv)
            p2 = simula_punto(p_serv)
            if p1 and p2: return True
            if not p1 and not p2: return False
        else:
            if simula_punto(p_serv): punti_serv += 1
            else: punti_risp += 1
            if punti_serv >= 4 and punti_serv - punti_risp >= 2: return True
            if punti_risp >= 4 and punti_risp - punti_serv >= 2: return False

def simula_tiebreak(p_serv_1, p_serv_2):
    p1_pts = 0
    p2_pts = 0
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
# ----------------------------------------

if st.button("🚀 CONVERTI & SIMULA MATCH"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players = []
    odds = []
    
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
        p1_name = players[0]
        p2_name = players[1]
        odd_1 = float(odds[0])
        odd_2 = float(odds[1])
        
        # Interroghiamo il database con il sistema di controllo verboso
        stats_1, trovato_1 = cerca_statistiche(p1_name)
        stats_2, trovato_2 = cerca_statistiche(p2_name)
        
        # Calcolo combinato
        p_serv_1 = (stats_1["serv"] + (1 - stats_2["ret"])) / 2
        p_serv_2 = (stats_2["serv"] + (1 - stats_1["ret"])) / 2
        
        # --- BLOCCO DI TRASPARENZA E VERBOSITÀ ---
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 2px solid #FFFDD0; margin-bottom: 15px;">
                <span style="color: #FFFDD0; font-size: 16px; font-weight: bold;">🎾 Match Rilevato: {p1_name} vs {p2_name}</span><br><br>
                <span style="color: #00FF7F; font-size: 14px;"><b>{p1_name}:</b> {"✅ Trovato nel Database" if trovato_1 else "⚠️ NON trovato -> Usati valori di default (Serv: 64%, Ret: 38%"}</span><br>
                <span style="color: #00FF7F; font-size: 14px;"><b>{p2_name}:</b> {"✅ Trovato nel Database" if trovato_2 else "⚠️ NON trovato -> Usati valori di default (Serv: 64%, Ret: 38%"}</span><br><br>
                <span style="color: #FFD700; font-size: 13px;">⚙️ Parametri passati al Monte Carlo (Prob. punto al servizio stimata):<br>
                • {p1_name}: {p_serv_1*100:.1f}%<br>
                • {p2_name}: {p_serv_2*100:.1f}%</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.write(f"Quote SNAI: `{p1_name}` @ **{odd_1}** | `{p2_name}` @ **{odd_2}**")
        
        with st.spinner("⚙️ Esecuzione di 200.000 simulazioni Monte Carlo in corso..."):
            prob_1 = esegui_monte_carlo(p_serv_1, p_serv_2, n_sim=200000)
            prob_2 = 100 - prob_1
            
            fair_odd_1 = 100 / prob_1 if prob_1 > 0 else 0
            fair_odd_2 = 100 / prob_2 if prob_2 > 0 else 0
            
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #FFFDD0;">
                    <p style="color: #FFFDD0; margin: 0; font-size: 14px;">Prob. {p1_name}</p>
                    <h2 style="color: #FFFDD0; margin: 5px 0; font-size: 32px;">{prob_1:.1f}%</h2>
                    <p style="color: #00FF7F; margin: 0; font-weight: bold;">Quota Equa: {fair_odd_1:.2f}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write(f"Quota SNAI: **{odd_1}**")
            if odd_1 > fair_odd_1:
                st.markdown('<p style="color: #00FF7F; font-weight: bold; font-size: 18px;">🔥 VALUE BET TROVATA!</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #FFA07A; font-weight: bold;">❌ No Value</p>', unsafe_allow_html=True)
                
        with col2:
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #FFFDD0;">
                    <p style="color: #FFFDD0; margin: 0; font-size: 14px;">Prob. {p2_name}</p>
                    <h2 style="color: #FFFDD0; margin: 5px 0; font-size: 32px;">{prob_2:.1f}%</h2>
                    <p style="color: #00FF7F; margin: 0; font-weight: bold;">Quota Equa: {fair_odd_2:.2f}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write(f"Quota SNAI: **{odd_2}**")
            if odd_2 > fair_odd_2:
                st.markdown('<p style="color: #00FF7F; font-weight: bold; font-size: 18px;">🔥 VALUE BET TROVATA!</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #FFA07A; font-weight: bold;">❌ No Value</p>', unsafe_allow_html=True)
                
    else:
        st.error(f"Dati non estratti correttamente. Nomi: {len(players)}, Quote: {len(odds)}. Controlla il testo incollato.")
