import streamlit as st
import numpy as np

st.set_page_config(page_title="Motore Tennis V1", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    .stButton button { color: #000000 !important; background-color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Motore Tennis V1")

budget = st.sidebar.number_input("Budget (€)", value=200.0)
kelly_fraction = st.sidebar.slider("Prudenza Kelly", 0.1, 1.0, 0.5)

input_match = st.text_input("Incolla stringa (es: Giocatore:1.50; Giocatore:2.60)")
prob_stimata = st.slider("Tua Probabilità stimata (Giocatore 1)", 0.0, 1.0, 0.5)

if st.button("🚀 SIMULA MATCH"):
    try:
        # Divide per il punto e virgola
        parts = [p.strip() for p in input_match.split(';')]
        
        if len(parts) < 2:
            st.error("Errore: il formato deve essere Nome:Quota; Nome:Quota")
        else:
            # Estrazione sicura
            p1_name, p1_quota = parts[0].rsplit(':', 1)
            p2_name, p2_quota = parts[1].rsplit(':', 1)
            
            q1 = float(p1_quota.strip())
            
            # Simulazione
            n_sim = 200000
            rng = np.random.default_rng()
            risultati = rng.random(n_sim) < prob_stimata
            
            prob_simulata = np.sum(risultati) / n_sim
            roi = (prob_simulata * q1) - 1
            
            if roi > 0:
                puntata = min(np.floor((roi / (q1 - 1)) * budget * kelly_fraction), 10.0)
                if puntata >= 2:
                    st.success(f"**PUNTA su {p1_name.strip()}**: {int(puntata)}€ (ROI {roi:.1%})")
                else:
                    st.warning(f"Valore trovato (ROI {roi:.1%}), ma puntata sotto il minimo di 2€.")
            else:
                st.error("Nessun valore trovato.")
            
    except Exception as e:
        st.error(f"Errore: {e}")
