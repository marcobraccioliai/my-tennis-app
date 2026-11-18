import streamlit as st

st.set_page_config(page_title="Tennis Hub", layout="centered")

# Stile grafico corretto e pulito
st.markdown("""
    <style>
    /* Sfondo principale dell'app */
    [data-testid="stAppViewContainer"] { 
        background-color: #B20000 !important; 
    }
    
    /* Titoli e testo principale nel corpo della pagina */
    .stApp div[data-testid="stMarkdownContainer"] h1, 
    .stApp div[data-testid="stMarkdownContainer"] h2, 
    .stApp div[data-testid="stMarkdownContainer"] h3, 
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp label { 
        color: #FFFDD0 !important; 
    }
    
    /* Personalizzazione della Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #1E1E1E !important; /* Sfondo scuro per la sidebar, fa risaltare i link */
    }
    
    /* Testo e link di navigazione nella sidebar (colore bianco/crema ben leggibile) */
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        color: #FFFDD0 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis Betting Hub")
st.write("Benvenuto nel centro di controllo.")
st.write("Usa il menu a sinistra per selezionare il convertitore e avviare le tue analisi.")
