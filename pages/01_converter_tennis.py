import streamlit as st

st.set_page_config(page_title="Parser Tennis", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    .stButton button { color: #000000 !important; background-color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Converter Quote Tennis")
raw_text = st.text_area("Incolla blocco match SNAI:", height=200)

if st.button("🚀 CONVERTI MATCH"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players = []
    odds = []
    
    for line in lines:
        # 1. Ignora righe con date o orari (contengono / o : e sono brevi)
        if any(char in line for char in ["/", ":"]):
            continue
            
        # 2. Se ha un punto è una quota
        if "." in line:
            try:
                odds.append(float(line.replace(',', '.')))
            except:
                pass
        # 3. Se ha lettere è un giocatore
        elif any(c.isalpha() for c in line):
            players.append(line)
            
    # Prendiamo solo i primi 2 nomi e le prime 2 quote
    if len(players) >= 2 and len(odds) >= 2:
        output = f"{players[0]}:{odds[0]}, {players[1]}:{odds[1]}"
        st.code(output)
    else:
        st.error(f"Dati non estratti. Nomi: {len(players)}, Quote: {len(odds)}. Verifica input.")
