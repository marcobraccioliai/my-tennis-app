import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Data Fetcher", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📡 Data Fetcher Tennis")

def extract_surface_stats(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # DEBUG: Stampiamo a video le tabelle trovate
    st.write("Debug: Analizzo le tabelle trovate...")
    tables = soup.find_all('table')
    
    # Mostriamo i primi 200 caratteri di ogni tabella per capire quale sia quella giusta
    for i, table in enumerate(tables):
        st.write(f"Tabella {i}: {table.text[:100]}...")
        
    return None # Per ora non restituiamo nulla

url1 = st.text_input("URL Giocatore 1")
url2 = st.text_input("URL Giocatore 2")

if st.button("🚀 ESTRAI DATI"):
    if url1 and url2:
        with st.spinner("Estrazione in corso..."):
            s1 = extract_surface_stats(url1)
            s2 = extract_surface_stats(url2)
            
            if s1 and s2:
                df = pd.DataFrame([s1, s2], index=["G1", "G2"])
                st.write("### Win Rate su Superficie (%)")
                st.dataframe(df)
            else:
                st.error("Errore nell'estrazione. Verifica i link.")
    else:
        st.warning("Inserisci entrambi gli URL.")
