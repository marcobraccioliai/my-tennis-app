import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Data Fetcher Tennis", layout="centered")

st.markdown("""<style>[data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
.stApp div, .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }</style>""", unsafe_allow_html=True)

st.title("📡 Data Fetcher Tennis")
url1 = st.text_input("URL Giocatore 1")
url2 = st.text_input("URL Giocatore 2")

def get_winrate(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        for row in soup.find_all('tr'):
            if "Summary:" in row.text:
                parts = row.text.replace("Summary:", "").strip().split()
                v, p = map(int, parts[2].split('/')) # parts[2] è Hard, la superficie standard
                return (v / (v + p))
        return None
    except: return None

if st.button("🚀 ESTRAI E MEMORIZZA"):
    w1, w2 = get_winrate(url1), get_winrate(url2)
    if w1 and w2:
        st.session_state['tennis_data'] = {'w1': w1, 'w2': w2}
        st.success(f"Dati acquisiti! G1: {w1:.2%}, G2: {w2:.2%}")
    else:
        st.error("Errore estrazione.")
