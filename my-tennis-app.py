import streamlit as st

st.set_page_config(page_title="Tennis Hub", layout="centered")

# Stile grafico coerente
st.markdown("""
    <style>
    /* Sfondo pagina */
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    
    /* Titoli e testo principale */
    .stApp div[data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 { color: #FFFDD0 !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    
    /* TESTO SIDEBAR (Qui stava il problema) */
    [data-testid="stSidebar"] div, [data-testid="stSidebar"] span, [data-testid="stSidebar"] a {
        color: #000000 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis Betting Hub")
st.write("Benvenuto nel centro di controllo.")
st.write("Usa il menu a sinistra per selezionare il convertitore.")
