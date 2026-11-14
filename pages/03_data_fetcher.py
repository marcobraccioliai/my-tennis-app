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
    
    # Cerchiamo la tabella che contiene le statistiche per superficie
    # In TennisExplorer solitamente è una tabella con header 'Surface'
    stats = {"Hard": 0.0, "Clay": 0.0, "Grass": 0.0, "Carpet": 0.0}
    
    try:
        tables = soup.find_all('table', {'class': 'table-bordered'})
        for table in tables:
            if 'Surface' in table.text:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        surface = cells[0].text.strip()
                        if surface in stats:
                            # Estrae la percentuale dalla cella (es: 75%)
                            pct_text = cells[1].text.strip().replace('%', '')
                            stats[surface] = float(pct_text)
        return stats
    except:
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
