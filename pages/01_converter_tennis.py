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
        # Se c'è uno slash, è un nome giocatore/team
        if "/" in line:
            players.append(line)
        # Se è un numero (quota), lo prendiamo
        else:
            try:
                val = float(line.replace(',', '.'))
                odds.append(val)
            except ValueError:
                continue
    
    # Prendiamo solo i primi due nomi e le prime due quote (T/T Match)
    if len(players) >= 2 and len(odds) >= 2:
        output = f"{players[0]}:{odds[0]}, {players[1]}:{odds[1]}"
        st.code(output)
    else:
        st.error(f"Dati non estratti correttamente. Nomi trovati: {len(players)}, Quote trovate: {len(odds)}")
