import streamlit as st
import numpy as np

st.set_page_config(page_title="Converter & Monte Carlo Tennis", layout="centered")

# Stile grafico blindato e pulito
st.markdown("""
    <style>
    /* Sfondo principale dell'app (Rosso) */
    [data-testid="stAppViewContainer"] { 
        background-color: #B20000 !important; 
    }
    
    /* Titoli e testi generali */
    .stApp div[data-testid="stMarkdownContainer"] h1, 
    .stApp div[data-testid="stMarkdownContainer"] h2, 
    .stApp div[data-testid="stMarkdownContainer"] h3, 
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp label { 
        color: #FFFDD0 !important; 
    }
    
    /* Pulsante principale */
    .stButton button, .stButton button p { 
        color: #000000 !important; 
        background-color: #FFFDD0 !important; 
        font-weight: bold !important; 
    }
    
    /* Casella di testo copia-incolla (Testo nero su sfondo bianco) */
    [data-testid="stTextArea"] textarea {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* Nomi giocatori evidenziati */
    code {
        color: #B20000 !important;
        background-color: #FFFDD0 !important;
        font-weight: bold !important;
    }

    /* Personalizzazione della Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #1E1E1E !important; 
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        color: #FFFDD0 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("✂️ Converter & Monte Carlo Tennis")
raw_text = st.text_area("Incolla blocco match SNAI:", height=150)

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
        
        # Box HTML personalizzato per il match rilevato (Perfettamente leggibile)
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 12px; border-radius: 8px; border: 2px solid #FFFDD0; margin-bottom: 15px;">
                <span style="color: #FFFDD0; font-size: 16px; font-weight: bold;">🎾 Match Rilevato: {p1_name} vs {p2_name}</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.write(f"Quote SNAI: `{p1_name}` @ **{odd_1}** | `{p2_name}` @ **{odd_2}**")
        
        with st.spinner("⚙️ Esecuzione di 200.000 simulazioni Monte Carlo in corso..."):
            # Valori di servizio di default (poi li collegheremo alle 4 variabili definitive)
            p_serv_1 = 0.65 
            p_serv_2 = 0.63 
            
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
