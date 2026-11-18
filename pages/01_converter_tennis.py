import streamlit as st
import numpy as np
import pandas as pd
import requests
import csv
import io
from datetime import datetime

st.set_page_config(page_title="Pro Value Betting - Batch Scanner", layout="centered")

# Stile grafico blindato e pulito
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #B20000 !important; }
    .stApp div[data-testid="stMarkdownContainer"] h1, 
    .stApp div[data-testid="stMarkdownContainer"] h2, 
    .stApp div[data-testid="stMarkdownContainer"] h3, 
    .stApp div[data-testid="stMarkdownContainer"] p,
    .stApp label { color: #FFFDD0 !important; }
    .stButton button, .stButton button p, [data-testid="stDownloadButton"] button, [data-testid="stDownloadButton"] button p { 
        color: #000000 !important; 
        background-color: #FFFDD0 !important; 
        font-weight: bold !important; 
    }
    [data-testid="stTextArea"] textarea, [data-testid="stNumberInput"] input { 
        color: #000000 !important; 
        background-color: #FFFFFF !important; 
        -webkit-text-fill-color: #000000 !important; 
    }
    code { color: #B20000 !important; background-color: #FFFDD0 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a { color: #FFFDD0 !important; font-weight: bold; }
    div[role="radiogroup"] label div p { color: #FFFDD0 !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎾 Pro Value Betting - Batch Scanner")

# --- PANNELLO CONFIGURAZIONE RAPIDA ---
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    bankroll = st.number_input("💰 Il tuo Bankroll (€):", min_value=10.0, value=1000.0, step=50.0)
with col_cfg2:
    superficie = st.radio("🏟️ Superficie del torneo:", ["Cemento", "Terra Battuta", "Erba"], horizontal=True)

raw_text = st.text_area(
    "Incolla l'intero blocco match SNAI del torneo:", 
    height=200, 
    placeholder="Incolla qui tutte le partite copiate dal palinsesto SNAI..."
)

# --- 📚 DATABASE LOCALE DI SUPPORTO (ATP & WTA) ---
DATABASE_TENNISTI = {
    "sinner": {"serv": 0.70, "ret": 0.43, "bonus": {"Cemento": 0.015, "Terra Battuta": 0.00, "Erba": 0.01}},
    "alcaraz": {"serv": 0.69, "ret": 0.44, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": 0.015}},
    "djokovic": {"serv": 0.69, "ret": 0.42, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.005, "Erba": 0.015}},
    "medvedev": {"serv": 0.68, "ret": 0.41, "bonus": {"Cemento": 0.02, "Terra Battuta": -0.02, "Erba": 0.00}},
    "zverev": {"serv": 0.71, "ret": 0.36, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.01, "Erba": -0.01}},
    "musetti": {"serv": 0.64, "ret": 0.39, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": 0.01}},
    "cobolli": {"serv": 0.63, "ret": 0.39, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.015, "Erba": -0.01}},
    "berrettini": {"serv": 0.72, "ret": 0.33, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.005, "Erba": 0.025}},
    "arnaldi": {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "sonego": {"serv": 0.67, "ret": 0.35, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.005, "Erba": 0.01}},
    "darderi": {"serv": 0.64, "ret": 0.39, "bonus": {"Cemento": -0.015, "Terra Battuta": 0.025, "Erba": -0.02}},
    "tiafoe": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.015, "Erba": 0.005}},
    "prizmic": {"serv": 0.65, "ret": 0.38, "bonus": {"Cemento": 0.005, "Terra Battuta": 0.01, "Erba": -0.01}},
    "moroni": {"serv": 0.60, "ret": 0.35, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.015, "Erba": -0.015}},
    "passaro": {"serv": 0.64, "ret": 0.37, "bonus": {"Cemento": -0.005, "Terra Battuta": 0.015, "Erba": -0.01}},
    "basilashvili": {"serv": 0.68, "ret": 0.35, "bonus": {"Cemento": 0.01, "Terra Battuta": -0.005, "Erba": 0.01}},
    "masarova": {"serv": 0.62, "ret": 0.38, "bonus": {"Cemento": 0.01, "Terra Battuta": 0.01, "Erba": -0.01}},
    "hercog": {"serv": 0.61, "ret": 0.38, "bonus": {"Cemento": 0.00, "Terra Battuta": 0.015, "Erba": -0.01}},
    "podoroska": {"serv": 0.60, "ret": 0.40, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": -0.02}},
    "romero gormaz": {"serv": 0.59, "ret": 0.40, "bonus": {"Cemento": -0.01, "Terra Battuta": 0.02, "Erba": -0.02}},
    "samsonova": {"serv": 0.66, "ret": 0.37, "bonus": {"Cemento": 0.015, "Terra Battuta": -0.01, "Erba": 0.015}}
}

# --- 🌐 INTEGRAZIONE ARCHIVIO JEFF SACKMANN (ATP + WTA) ---
@st.cache_data(ttl=86400)
def scarica_archivio_sackmann():
    urls = [
        "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_players.csv",
        "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_players.csv"
    ]
    giocatori_web = {}
    for url in urls:
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    cognome = row.get("name_last", "").strip().lower()
                    if cognome and len(cognome) > 3:
                        giocatori_web[cognome] = {
                            "nome_completo": f"{row.get('name_first', '')} {row.get('name_last', '')}".strip(),
                            "paese": row.get("ioc", "")
                        }
        except Exception:
            continue
    return giocatori_web

def estrai_dati_modello_A(nome_giocatore):
    """Modello A: Solo DB locale oppure Default puro"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale"
    return {"serv": 0.64, "ret": 0.38, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, "Default"

def estrai_dati_modello_B(nome_giocatore, quota_giocatore, quota_avversario, archivio_sackmann):
    """Modello B: DB locale -> Archivio Sackmann (ATP/WTA) + Calibrazione Bayesiana"""
    nome_pulito = nome_giocatore.lower()
    for key in DATABASE_TENNISTI:
        if key in nome_pulito:
            return DATABASE_TENNISTI[key], "DB Locale"
            
    trovato_sackmann = False
    info_player = ""
    for cognome_ws, dati in archivio_sackmann.items():
        if cognome_ws in nome_pulito:
            trovato_sackmann = True
            info_player = f"{dati['nome_completo']} ({dati['paese']})"
            break
            
    prob_mercato = (1 / quota_giocatore) / ((1 / quota_giocatore) + (1 / quota_avversario))
    correzione = (prob_mercato - 0.50) * 0.08
    serv_stimato = np.clip(0.61 + correzione, 0.53, 0.68)
    ret_stimato = np.clip(0.37 + correzione, 0.30, 0.44)
    
    etichetta = f"Sackmann ({info_player})" if trovato_sackmann else "Stima Circuito (Market)"
    return {"serv": serv_stimato, "ret": ret_stimato, "bonus": {"Cemento": 0.0, "Terra Battuta": 0.0, "Erba": 0.0}}, etichetta

# --- MOTORE MONTE CARLO ISOLATO ---
def simula_punto(p_serv):
    return np.random.random() < p_serv

def simula_game(p_serv):
    punti_serv, punti_risp = 0, 0
    while True:
        if punti_serv >= 3 and punti_risp >= 3:
            p1, p2 = simula_punto(p_serv), simula_punto(p_serv)
            if p1 and p2: return True
            if not p1 and not p2: return False
        else:
            if simula_punto(p_serv): punti_serv += 1
            else: punti_risp += 1
            if punti_serv >= 4 and punti_serv - punti_risp >= 2: return True
            if punti_risp >= 4 and punti_risp - punti_serv >= 2: return False

def simula_tiebreak(p_serv_1, p_serv_2):
    p1_pts, p2_pts = 0, 0
    while True:
        serv_1 = ((p1_pts + p2_pts) // 1) % 2 == 0
        p_curr = p_serv_1 if serv_1 else (1 - p_serv_2)
        if simula_punto(p_curr): p1_pts += 1
        else: p2_pts += 1
        if (p1_pts >= 7 or p2_pts >= 7) and abs(p1_pts - p2_pts) >= 2:
            return p1_pts > p2_pts

def simula_set(p_serv_1, p_serv_2):
    g1, g2 = 0, 0
    while True:
        t1 = (g1 + g2) % 2 == 0
        p_curr = p_serv_1 if t1 else (1 - p_serv_2)
        vince_g1 = simula_game(p_curr) if t1 else not simula_game(1 - p_serv_2)
        if t1 and vince_g1: g1 += 1
        elif t1 and not vince_g1: g2 += 1
        elif not t1 and not vince_g1: g1 += 1
        else: g2 += 1
        if g1 == 6 and g2 == 6: return simula_tiebreak(p_serv_1, p_serv_2)
        if (g1 >= 6 or g2 >= 6) and abs(g1 - g2) >= 2: return g1 > g2

def esegui_monte_carlo(p_serv_1, p_serv_2, n_sim=100000):
    vittorie_1 = 0
    for _ in range(n_sim):
        s1, s2 = 0, 0
        while s1 < 2 and s2 < 2:
            if simula_set(p_serv_1, p_serv_2): s1 += 1
            else: s2 += 1
        if s1 == 2: vittorie_1 += 1
    return (vittorie_1 / n_sim) * 100

def arrotonda_per_snai(importo_euro):
    """Vincoli SNAI: puntata minima 1.00€, incrementi di 0.05€"""
    if importo_euro < 1.0:
        return 0.0
    return max(1.0, round(importo_euro / 0.05) * 0.05)

def valuta_scommessa(prob_percentuale, quota_bookmaker, bankroll, frazione=0.25, edge_minimo=0.05):
    """Calcola Edge, Kelly Frazionario e applica il blocco 'Stai Fermo' sotto soglia"""
    p = prob_percentuale / 100.0
    q = 1.0 - p
    b = quota_bookmaker - 1.0
    if b <= 0:
        return 0.0, 0.0, "No Value"
        
    edge = (p * quota_bookmaker) - 1.0
    
    if edge <= 0:
        return edge * 100, 0.0, "❌ No Value"
    if edge < edge_minimo:
        return edge * 100, 0.0, "🛑 STAI FERMO (Edge < 5%)"
        
    kelly_pieno = (b * p - q) / b
    stake_euro_snai = arrotonda_per_snai(bankroll * (kelly_pieno * frazione))
    
    if stake_euro_snai <= 0:
        return edge * 100, 0.0, "🛑 STAI FERMO (< 1.00€)"
        
    return edge * 100, stake_euro_snai, "🔥 VALUE BET"

# --- PARSER SEQUENZIALE CON SEGREGATION & FILTRO DOPPI ---
def estrai_blocchi_match(testo_grezzo):
    linee = [l.strip() for l in testo_grezzo.split('\n') if l.strip()]
    match_estratti = []
    doppi_scartati = 0
    
    i = 0
    while i < len(linee):
        riga_corr = linee[i]
        # Identifica data (es. 18/11) o orario (es. 17:00)
        if ("/" in riga_corr and len(riga_corr) <= 6) or (":" in riga_corr and len(riga_corr) <= 5):
            i += 1
            continue
            
        # Verifica due righe consecutive di nomi giocatori
        if i + 1 < len(linee) and any(c.isalpha() for c in linee[i]) and any(c.isalpha() for c in linee[i+1]):
            p1 = linee[i]
            p2 = linee[i+1]
            i += 2
            
            # Raccoglie le quote del blocco corrente fino al separatore successivo
            quote_blocco = []
            while i < len(linee):
                item = linee[i]
                # Stop se incontra data, orario o nuovi nomi
                if ("/" in item and len(item) <= 6) or (":" in item and len(item) <= 5) or any(c.isalpha() for c in item):
                    break
                if item != "-":
                    try:
                        val = float(item.replace(',', '.'))
                        if 1.01 <= val <= 50.0:
                            quote_blocco.append(val)
                    except ValueError:
                        pass
                i += 1
                
            # Filtra i match di doppio (contengono '/' nel nome della coppia)
            if "/" in p1 or "/" in p2:
                doppi_scartati += 1
                continue
                
            if len(quote_blocco) >= 2:
                match_estratti.append({
                    "p1": p1,
                    "p2": p2,
                    "odd_1": quote_blocco[0],
                    "odd_2": quote_blocco[1]
                })
        else:
            i += 1
            
    return match_estratti, doppi_scartati

# ----------------------------------------

if st.button("🚀 AVVIA ELABORAZIONE SEQUENZIALE TORNEO"):
    if not raw_text.strip():
        st.warning("Incolla prima il blocco di testo con i match!")
    else:
        archivio_sackmann = scarica_archivio_sackmann()
        lista_match, n_doppi = estrai_blocchi_match(raw_text)
        
        if n_doppi > 0:
            st.info(f"ℹ️ Esclusi automaticamente **{n_doppi} match di doppio** (il modello Monte Carlo simula esclusivamente il singolare).")
            
        if not lista_match:
            st.error("Nessun match di singolare valido individuato. Controlla il testo incollato.")
        else:
            st.success(f"Individuati **{len(lista_match)} match di singolare**. Avvio elaborazione isolata...")
            
            report_esportazione = []
            
            # --- CICLO SEQUENZIALE ISOLATO (DATA SEGREGATION) ---
            for idx, match_data in enumerate(lista_match, 1):
                # Variabili locali strict-scoped per evitare sovrapposizioni
                curr_p1 = str(match_data["p1"])
                curr_p2 = str(match_data["p2"])
                curr_odd1 = float(match_data["odd_1"])
                curr_odd2 = float(match_data["odd_2"])
                
                with st.spinner(f"⚙️ Elaborazione Match {idx}/{len(lista_match)}: {curr_p1} vs {curr_p2}..."):
                    # 1. Estrazione Modello A
                    s1_A, src1_A = estrai_dati_modello_A(curr_p1)
                    s2_A, src2_A = estrai_dati_modello_A(curr_p2)
                    p_serv_1_A = ((s1_A["serv"] + (1 - s2_A["ret"])) / 2) + s1_A["bonus"][superficie]
                    p_serv_2_A = ((s2_A["serv"] + (1 - s1_A["ret"])) / 2) + s2_A["bonus"][superficie]
                    prob_1_A = esegui_monte_carlo(p_serv_1_A, p_serv_2_A, n_sim=100000)
                    prob_2_A = 100.0 - prob_1_A
                    fair_1_A = 100.0 / prob_1_A if prob_1_A > 0 else 0.0
                    fair_2_A = 100.0 / prob_2_A if prob_2_A > 0 else 0.0
                    edge_1_A, stake_1_A, verdetto_1_A = valuta_scommessa(prob_1_A, curr_odd1, bankroll)
                    edge_2_A, stake_2_A, verdetto_2_A = valuta_scommessa(prob_2_A, curr_odd2, bankroll)
                    
                    # 2. Estrazione Modello B (Sackmann + Calibrazione)
                    s1_B, src1_B = estrai_dati_modello_B(curr_p1, curr_odd1, curr_odd2, archivio_sackmann)
                    s2_B, src2_B = estrai_dati_modello_B(curr_p2, curr_odd2, curr_odd1, archivio_sackmann)
                    p_serv_1_B = ((s1_B["serv"] + (1 - s2_B["ret"])) / 2) + s1_B["bonus"][superficie]
                    p_serv_2_B = ((s2_B["serv"] + (1 - s1_B["ret"])) / 2) + s2_B["bonus"][superficie]
                    prob_1_B = esegui_monte_carlo(p_serv_1_B, p_serv_2_B, n_sim=100000)
                    prob_2_B = 100.0 - prob_1_B
                    fair_1_B = 100.0 / prob_1_B if prob_1_B > 0 else 0.0
                    fair_2_B = 100.0 / prob_2_B if prob_2_B > 0 else 0.0
                    edge_1_B, stake_1_B, verdetto_1_B = valuta_scommessa(prob_1_B, curr_odd1, bankroll)
                    edge_2_B, stake_2_B, verdetto_2_B = valuta_scommessa(prob_2_B, curr_odd2, bankroll)

                # --- OUTPUT IMMEDIATO DEL SINGOLO MATCH ---
                st.markdown(f"""
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 2px solid #FFFDD0; margin-top: 15px;">
                        <h3 style="color: #FFFDD0; margin-top:0;">Match #{idx}: {curr_p1} (@{curr_odd1}) vs {curr_p2} (@{curr_odd2})</h3>
                        <span style="color: #A0A0A0; font-size: 12px;">Fonti Modello B: {curr_p1} [{src1_B}] | {curr_p2} [{src2_B}]</span>
                    </div>
                """, unsafe_allow_html=True)
                
                c_modA, c_modB = st.columns(2)
                with c_modA:
                    st.markdown(f"""
                        <div style="background-color: #262626; padding: 12px; border-radius: 8px; border: 1px solid #FFD700; margin-top: 5px;">
                            <p style="color: #FFD700; font-weight: bold; text-align: center; margin-top: 0;">🅰️ Modello A (Interno)</p>
                            <p style="color: #FFFDD0; font-size: 13px; margin-bottom: 2px;"><b>{curr_p1}</b>: {prob_1_A:.1f}% (Equa {fair_1_A:.2f})</p>
                            <p style="color: {'#00FF7F' if stake_1_A > 0 else '#FFA07A'}; font-size: 12px; font-weight: bold; margin-top: 0;">
                                {verdetto_1_A} {f'| Puntata: € {stake_1_A:.2f}' if stake_1_A > 0 else ''}
                            </p>
                            <hr style="border-color: #444; margin: 6px 0;">
                            <p style="color: #FFFDD0; font-size: 13px; margin-bottom: 2px;"><b>{curr_p2}</b>: {prob_2_A:.1f}% (Equa {fair_2_A:.2f})</p>
                            <p style="color: {'#00FF7F' if stake_2_A > 0 else '#FFA07A'}; font-size: 12px; font-weight: bold; margin-top: 0;">
                                {verdetto_2_A} {f'| Puntata: € {stake_2_A:.2f}' if stake_2_A > 0 else ''}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with c_modB:
                    st.markdown(f"""
                        <div style="background-color: #262626; padding: 12px; border-radius: 8px; border: 1px solid #00FF7F; margin-top: 5px;">
                            <p style="color: #00FF7F; font-weight: bold; text-align: center; margin-top: 0;">🅱️ Modello B (Sackmann)</p>
                            <p style="color: #FFFDD0; font-size: 13px; margin-bottom: 2px;"><b>{curr_p1}</b>: {prob_1_B:.1f}% (Equa {fair_1_B:.2f})</p>
                            <p style="color: {'#00FF7F' if stake_1_B > 0 else '#FFA07A'}; font-size: 12px; font-weight: bold; margin-top: 0;">
                                {verdetto_1_B} {f'| Puntata: € {stake_1_B:.2f}' if stake_1_B > 0 else ''}
                            </p>
                            <hr style="border-color: #444; margin: 6px 0;">
                            <p style="color: #FFFDD0; font-size: 13px; margin-bottom: 2px;"><b>{curr_p2}</b>: {prob_2_B:.1f}% (Equa {fair_2_B:.2f})</p>
                            <p style="color: {'#00FF7F' if stake_2_B > 0 else '#FFA07A'}; font-size: 12px; font-weight: bold; margin-top: 0;">
                                {verdetto_2_B} {f'| Puntata: € {stake_2_B:.2f}' if stake_2_B > 0 else ''}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

                # Registrazione riga pulita per l'esportazione finale
                report_esportazione.append({
                    "Match #": idx,
                    "Superficie": superficie,
                    "Giocatore 1": curr_p1,
                    "Quota SNAI 1": curr_odd1,
                    "Giocatore 2": curr_p2,
                    "Quota SNAI 2": curr_odd2,
                    "ModB Prob 1 (%)": round(prob_1_B, 1),
                    "ModB Equa 1": round(fair_1_B, 2),
                    "ModB Edge 1 (%)": round(edge_1_B, 1),
                    "ModB Azione 1": verdetto_1_B,
                    "ModB Puntata 1 (€)": stake_1_B,
                    "ModB Prob 2 (%)": round(prob_2_B, 1),
                    "ModB Equa 2": round(fair_2_B, 2),
                    "ModB Edge 2 (%)": round(edge_2_B, 1),
                    "ModB Azione 2": verdetto_2_B,
                    "ModB Puntata 2 (€)": stake_2_B,
                    "ModA Azione 1": verdetto_1_A,
                    "ModA Puntata 1 (€)": stake_1_A,
                    "ModA Azione 2": verdetto_2_A,
                    "ModA Puntata 2 (€)": stake_2_A
                })

            # --- RIEPILOGO TABELLARE ED ESPORTAZIONE CSV ---
            st.markdown("---")
            st.subheader("📋 Riepilogo Backtesting ed Esportazione")
            df_report = pd.DataFrame(report_esportazione)
            st.dataframe(df_report, use_container_width=True)
            
            csv_buffer = df_report.to_csv(index=False, sep=";").encode("utf-8-sig")
            nome_file = f"backtesting_tennis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            
            st.download_button(
                label="📥 Scarica Report Completo in CSV (Excel)",
                data=csv_buffer,
                file_name=nome_file,
                mime="text/csv"
            )
