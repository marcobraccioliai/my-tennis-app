import streamlit as st
import numpy as np

st.set_page_config(page_title="Motore Tennis", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    .stButton button { color: #000000 !important; background-color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Motore Tennis V1")

# Configurazioni
budget = st.sidebar.number_input("Budget (€)", value=200.0)
kelly_fraction = st.sidebar.slider("Frazione Kelly", 0.1, 1.0, 0.5)

# Input
input_match = st.text_input("Incolla stringa (es: Djokovic:1.50, Sinner:2.60)")
st.write("Inserisci la tua probabilità stimata per il Giocatore 1 (0-1):")
prob_stimata = st.slider("Tua Probabilità stimata", 0.0, 1.0, 0.5)

if st.button("🚀 SIMULA MATCH"):
    try:
        # Usiamo il punto e virgola per separare i giocatori
        parts = input_match.split(';') 
        
        # Estraiamo nome e quota separando dall'ultima occorrenza di ':'
        p1_name, p1_quota = parts[0].rsplit(':', 1)
        p2_name, p2_quota = parts[1].rsplit(':', 1)
        
        q1, q2 = float(p1_quota), float(p2_quota)
                
        # Simulazione Monte Carlo (Bernoulliana)
        n_sim = 200000
        rng = np.random.default_rng()
        risultati = rng.random(n_sim) < prob_stimata
        
        vinte = np.sum(risultati)
        prob_simulata = vinte / n_sim
        
        # Calcolo Kelly per il Giocatore 1
        roi = (prob_simulata * q1) - 1
        if roi > 0:
            puntata = min(np.floor((roi / (q1 - 1)) * budget * kelly_fraction), 10.0)
            if puntata >= 2:
                st.success(f"**PUNTA su {p1_name}**: {int(puntata)}€ (ROI {roi:.1%})")
            else:
                st.warning("Valore trovato ma puntata sotto il minimo.")
        else:
            st.error("Nessun valore trovato.")
            
    except Exception as e:
        st.error(f"Errore input: {e}")
