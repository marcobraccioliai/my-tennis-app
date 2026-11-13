import requests
from bs4 import BeautifulSoup
import time

def fetch_player_stats(player_url):
    # 1. Simulazione comportamento umano
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 2. Pausa di sicurezza (sempre necessaria per non essere bannati)
    time.sleep(3) 
    
    try:
        response = requests.get(player_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Esempio di estrazione (va adattato alla struttura HTML specifica di TennisExplorer)
        # Qui dobbiamo poi definire i tag precisi (es: classe 'stats-table')
        # Per ora verifichiamo solo la connessione
        return f"Connessione riuscita. Titolo pagina: {soup.title.string}"
        
    except Exception as e:
        return f"Errore: {e}"

# Esempio di utilizzo:
# url = "https://www.tennisexplorer.com/player/nome-giocatore/"
# print(fetch_player_stats(url))
