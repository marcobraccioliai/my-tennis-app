import streamlit as st

st.set_page_config(page_title="Parser Tennis", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    .stButton button { color: #000000 !important; background-color: #FFFDD0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("✂️ Converter Quote Tennis")
raw_text = st.text_area("Incolla blocco match SNAI:", height=200)

if st.button("🚀 CONVERTI MATCH"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players = []
    odds = []
    
    for line in lines:
        if any(char in line for char in ["/", ":"]): continue
        if any(c.isalpha() for c in line):
            players.append(line)
        elif "." in line:
            try:
                odds.append(line.replace(',', '.'))
            except:
                continue
            
    if len(players) >= 2 and len(odds) >= 2:
        # Usa il punto e virgola come separatore per essere compatibile col motore
        output = f"{players[0]}:{odds[0]}; {players[1]}:{odds[1]}"
        st.code(output)
    else:
        st.error(f"Dati non estratti. Nomi: {len(players)}, Quote: {len(odds)}.")
