import streamlit as st

st.set_page_config(page_title="Parser Tennis", layout="centered")

# Stile identico alla versione ippica per coerenza visiva
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    .stButton button { color: #000000 !important; background-color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Converter Quote Tennis")
raw_text = st.text_area("Incolla qui il pastone SNAI:", height=250)

if st.button("🚀 CONVERTI TENNIS"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players = []
    odds = []
    
    # Filtro grezzo per separare nomi (stringhe) da quote (numeri)
    for line in lines:
        # Ignora righe temporali o simboli inutili
        if "/" in line or ":" in line and not any(c.isalpha() for c in line): continue
        if any(c.isalpha() for c in line):
            players.append(line)
        elif any(c.isdigit() for c in line):
            odds.append(line.replace(',', '.'))

    # Costruzione stringa: a gruppi di 2 giocatori e 2 quote
    result = []
    for i in range(0, min(len(players), len(odds)), 2):
        if i+1 < len(players) and i+1 < len(odds):
            p1, p2 = players[i], players[i+1]
            q1, q2 = odds[i], odds[i+1]
            result.append(f"{p1}:{q1}, {p2}:{q2}")
    
    if result:
        st.code("\n".join(result))
    else:
        st.error("Dati non estratti. Verifica il pastone.")
