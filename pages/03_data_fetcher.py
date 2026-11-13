import streamlit as st

st.set_page_config(page_title="Data Fetcher", layout="centered")

# Stile (va inserito in ogni pagina per ora)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📡 Data Fetcher")
st.write("Questa pagina è attiva.")

# Test di presenza
if st.button("Verifica connessione"):
    st.write("Il modulo è attivo e pronto a ricevere le funzioni di scraping.")
