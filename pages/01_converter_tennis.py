import streamlit as st

st.set_page_config(page_title="Parser Tennis", layout="centered")

st.title("🎾 Converter Quote Tennis")
raw_text = st.text_area("Incolla blocco match SNAI:", height=200)

if st.button("🚀 CONVERTI MATCH"):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    players = []
    odds = []
    
    for line in lines:
        # SALVAGUARDIA: Ignora date (es: 12/11) o orari
        if "/" in line and any(c.isdigit() for c in line.split('/')[0]): continue
        if ":" in line and any(c.isdigit() for c in line.split(':')[0]): continue
        
        # Estrai nomi (righe che contengono lettere e slash, es: Frantzen C / Stevens B)
        if "/" in line and any(c.isalpha() for c in line):
            players.append(line)
        # Estrai quote (righe con numeri e punto decimale)
        elif "." in line:
            odds.append(line.replace(',', '.'))
            
    # Prendiamo solo i primi 2 nomi e le prime 2 quote
    if len(players) >= 2 and len(odds) >= 2:
        output = f"{players[0]}:{odds[0]}, {players[1]}:{odds[1]}"
        st.code(output)
    else:
        st.error(f"Dati non estratti. Nomi: {len(players)}, Quote: {len(odds)}")
