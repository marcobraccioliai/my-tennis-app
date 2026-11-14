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
    
    # Cerchiamo la tabella che contiene "Year Summary"
    target_table = None
    for table in soup.find_all('table'):
        if "Year Summary" in table.text:
            target_table = table
            break
            
    if not target_table: return None
    
    # Cerchiamo la riga che inizia con "Summary:"
    rows = target_table.find_all('tr')
    for row in rows:
        if "Summary:" in row.text:
            # Puliamo la stringa: "Summary: 465/138 119/46 183/51 111/27 40/13 12/1"
            raw = row.text.replace("Summary:", "").strip()
            parts = raw.split() # Separa i blocchi V/P
            
            # parts[0] è il totale, parts[1] Clay, parts[2] Hard, etc.
            # Convertiamo in Win Rate %: Vinte / (Vinte + Perse)
            def calc_win_rate(vp_str):
                v, p = map(int, vp_str.split('/'))
                return (v / (v + p)) * 100 if (v + p) > 0 else 0
            
            return {
                "Clay": calc_win_rate(parts[1]),
                "Hard": calc_win_rate(parts[2]),
                "Indoors": calc_win_rate(parts[3]),
                "Grass": calc_win_rate(parts[4])
            }
    return None

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
