import streamlit as st
import numpy as np

st.set_page_config(page_title="Motore Tennis V1", layout="centered")
st.markdown("""<style>[data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
.stApp div, .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }</style>""", unsafe_allow_html=True)

st.title("🎾 Motore Tennis V1")
budget = st.sidebar.number_input("Budget (€)", value=200.0)

# Recupera dati dal fetcher
if 'tennis_data' in st.session_state:
    w1, w2 = st.session_state['tennis_data']['w1'], st.session_state['tennis_data']['w2']
    st.write(f"Dati caricati: G1={w1:.2%}, G2={w2:.2%}")
    prob_a = w1 / (w1 + w2)
else:
    st.warning("Nessun dato trovato. Vai prima su 'Data Fetcher' e estrai i dati.")
    prob_a = 0.5

q1 = st.number_input("Quota Giocatore 1", value=1.50)

if st.button("🚀 SIMULA MATCH"):
    if 'tennis_data' in st.session_state:
        n_sim = 200000
        rng = np.random.default_rng()
        risultati = rng.random(n_sim) < prob_a
        
        prob_simulata = np.sum(risultati) / n_sim
        roi = (prob_simulata * q1) - 1
        
        if roi > 0:
            puntata = min(np.floor((roi / (q1 - 1)) * budget * 0.5), 10.0)
            if puntata >= 2: st.success(f"**PUNTA**: {int(puntata)}€ (ROI {roi:.1%})")
            else: st.warning("Valore basso, puntata sotto minimo.")
        else: st.error("Nessun valore.")
    else:
        st.error("Dati mancanti.")
