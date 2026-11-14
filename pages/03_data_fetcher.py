import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Data Fetcher Tennis", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📡 Data Fetcher Tennis")

def extract_surface_stats(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo la riga che contiene "Summary:" dentro una tabella
        # E' l'unico modo per essere sicuri di prendere la riga giusta
        found_text = None
        for row in soup.find_all('tr'):
            if "Summary:" in row.text:
                found_text = row.text.replace("Summary:", "").strip()
                break
        
        if not found_text:
            return None, "Riga 'Summary:' non trovata."
            
        # I dati nel sito sono solitamente: Clay, Hard, Indoors, Grass
        # Dividiamo per spazi multipli
        parts = found_text.split()
        
        # parts[0] è il totale (465/138), parts[1] Clay, parts[2] Hard, etc.
        def get_win_rate(vp_str):
            if '/' not in vp_str: return 0.0
            v, p = map(int, vp_str.split('/'))
            return round((v / (v + p)) * 100, 2) if (v + p) > 0 else 0.0
            
        stats = {
            "Clay": get_win_rate(parts[1]),
            "Hard": get_win_rate(parts[2]),
            "Indoors": get_win_rate(parts[3]),
            "Grass": get_win_rate(parts[4])
        }
        return stats, None
        
    except Exception as e:
        return None, str(e)

url1 = st.text_input("URL Giocatore 1")
url2 = st.text_input("URL Giocatore 2")

if st.button("🚀 ESTRAI DATI"):
    if url1 and url2:
        with st.spinner("Estrazione in corso..."):
            s1, err1 = extract_surface_stats(url1)
            s2, err2 = extract_surface_stats(url2)
            
            if s1 and s2:
                df = pd.DataFrame([s1, s2], index=["G1", "G2"])
                st.write("### Win Rate su Superficie (%)")
                st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Errore G1: {err1}")
                st.error(f"Errore G2: {err2}")
    else:
        st.warning("Inserisci entrambi gli URL.")
