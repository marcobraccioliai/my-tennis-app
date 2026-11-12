import streamlit as st

st.set_page_config(page_title="Tennis Hub", layout="centered")

# Stile grafico coerente
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis Betting Hub")
st.write("Benvenuto nel centro di controllo.")
st.write("Usa il menu a sinistra per selezionare il convertitore.")
