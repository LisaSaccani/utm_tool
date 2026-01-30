import streamlit as st
import pandas as pd
import re
from datetime import datetime
from slugify import slugify
from urllib.parse import urlparse, parse_qs

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Universal UTM Governance", layout="wide")

# --- CSS (STILE CLEAN + CHECKER CORRETTO) ---
st.markdown("""
<style>
    /* 1. Header Sezioni */
    .section-header {
        font-size: 12px; font-weight: 700; color: #888; margin-top: 25px; margin-bottom: 10px;
        text-transform: uppercase; letter-spacing: 1px; font-family: sans-serif;
    }
    
    /* 2. Messaggi Validazione */
    .msg-error { color: #d93025; font-size: 13px; margin-top: -5px; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }
    .msg-warning { color: #e37400; font-size: 13px; margin-top: -5px; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }
    .msg-success { color: #188038; font-size: 13px; margin-top: -5px; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; font-weight: 500; }
    
    /* 3. Output Box Builder */
    .output-box-ready { background-color: #e8f0fe; color: #174ea6; padding: 15px; border-radius: 8px; border: 1px solid #d2e3fc; }
    .output-box-success { background-color: #e6f4ea; color: #137333; padding: 15px; border-radius: 8px; border: 1px solid #ceead6; }
    
    /* 4. STILE UTM CHECKER (Riproduzione Screenshot) */
    .utm-check-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        margin-top: 15px;
        overflow: hidden; /* Importante per i bordi */
    }
    
    .utm-row {
        display: flex;
        align-items: center;
        border-bottom: 1px solid #e9ecef;
        padding: 12px 15px;
    }
    
    .utm-row:last-child {
        border-bottom: none;
    }
    
    /* Colonna Etichetta (Tag) */
    .utm-label-col {
        width: 160px;
        flex-shrink: 0;
    }
    
    .utm-tag {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 4px;
        color: white;
        font-weight: 600;
        font-size: 13px;
        text-align: center;
        min-width: 110px;
    }
    
    .tag-blue { background-color: #0077c8; } 
    .tag-gray { background-color: #6c757d; } 
    
    /* Colonna Valore */
    .utm-value-col {
        flex-grow: 1;
        font-size: 15px;
        color: #333;
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    .check-icon { color: #28a745; font-weight: bold; font-size: 18px; }
    .error-icon { color: #dc3545; font-weight: bold; font-size: 18px; }
    .error-text { color: #dc3545; font-weight: 500; font-size: 14px; font-style: italic; }

    /* Padding Top */
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- HEADER PRINCIPALE ---
st.title("🛡️ Universal UTM Governance")
st.markdown("""
**Guida passo a passo nella generazione di link completi di parametri UTM.**  
Usa il **Builder** per creare nuovi link standardizzati o il **Checker** per analizzare link esistenti.
""")
st.write("---")

# --- MOCK DB ---
MOCK_CLIENT_DB = {
    "Chicco (Model 2026)": {
        "channels": ["Paid Search", "Paid Social", "Display", "Email", "Organic Social", "SMS", "Affiliate", "Video", "Altro"],
        "default_country": "it",
        "expected_domain": "chicco.it"
    },
    "Ferrarelle (Test)": {
        "channels": ["Cross-network", "Paid Search", "Display", "Social", "Email"],
        "default_country": "it",
        "expected_domain": "ferrarelle.it"
    }
}

# --- DATI GUIDA ---
GUIDE_TABLE_DATA = [
    {"Traffic type": "Organic", "utm_medium": "organic", "utm_source": "google, bing, yahoo"},
    {"Traffic type": "Referral", "utm_medium": "referral", "utm_source": "(domain)"},
    {"Traffic type": "Direct", "utm_medium": "(none)", "utm_source": "(direct)"},
    {"Traffic type": "Paid Search", "utm_medium": "cpc", "utm_source": "google, bing"},
    {"Traffic type": "Affiliate", "utm_medium": "affiliate", "utm_source": "tradetracker, awin"},
    {"Traffic type": "Display", "utm_medium": "cpm", "utm_source": "reservation, display, dv360, google"},
    {"Traffic type": "Video", "utm_medium": "cpv", "utm_source": "youtube, vimeo, google"},
    {"Traffic type": "Programmatic", "utm_medium": "cpm", "utm_source": "rcs, mediamond, rai, manzoni"},
    {"Traffic type": "Email", "utm_medium": "email|mailing_campaign", "utm_source": "newsletter, email, crm, sfmc, mailchimp"},
    {"Traffic type": "Organic Social", "utm_medium": "social_org", "utm_source": "facebook, instagram, tiktok, linkedin, pinterest"},
    {"Traffic type": "Paid Social", "utm_medium": "social_paid", "utm_source": "facebook, instagram, tiktok, linkedin, pinterest"},
    {"Traffic type": "App traffic", "utm_medium": "-", "utm_source": "app"},
    {"Traffic type": "SMS", "utm_medium": "offline", "utm_source": "sms"},
    {"Traffic type": "Altro", "utm_medium": "other", "utm_source": ""},
]

# --- UTILS ---
def get_source_options():
    sources = set()
    for row in GUIDE_TABLE_DATA:
        parts = row["utm_source"].split(",")
        for p in parts:
            clean = p.strip().replace("...", "")
            if clean and "(" not in clean and "[" not in clean:
                sources.add(clean)
    return [""] + sorted(list(sources)) + ["Altro (Inserisci manuale)"]

SOURCE_OPTIONS = get_source_options()

def get_compatible_channels(selected_source, all_client_channels):
    if not selected_source or selected_source == "Altro (Inserisci manuale)":
        return [""] + all_client_channels
    norm_source = selected_source.strip().lower()
    compatible_types = set()
    for row in GUIDE_TABLE_DATA:
        row_sources = [s.strip().lower() for s in row["utm_source"].split(",")]
        if norm_source in row_sources:
            compatible_types.add(row["Traffic type"])
    if not compatible_types:
        return [""] + all_client_channels
    filtered_channels = [c for c in all_client_channels if c in compatible_types]
    return [""] + sorted(filtered_channels) if filtered_channels else [""] + all_client_channels

def normalize_token(text):
    if not text: return ""
    return slugify(text, separator="-", lowercase=True)

def is_valid_url(url):
    regex = re.compile(r'^https?://(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

# --- TABS DI NAVIGAZIONE ---
tab_builder, tab_checker = st.tabs(["🛠️ UTM Generator", "🔍 UTM Checker"])

# --- SESSION STATE PER CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==============================================================================
# TAB 1: UTM GENERATOR (BUILDER)
# ==============================================================================
with tab_builder:
    col_left, col_right = st.columns([0.5, 0.5], gap="large")

    with col_left:
        # 1. SETUP
        st.markdown('<div class="section-header">SETUP</div>', unsafe_allow_html=True)
        selected_prop_name = st.selectbox("Property GA4", list(MOCK_CLIENT_DB.keys()))
        prop_config = MOCK_CLIENT_DB[selected_prop_name]

        # 2. CANALI
        st.markdown('<div class="section-header">CANALI</div>', unsafe_allow_html=True)
        
        selected_source_option = st.selectbox("Piattaforma / Source *", SOURCE_OPTIONS, help="Su quale piattaforma o canale stai attivando questa campagna?")
        final_input_source = ""
        if selected_source_option == "Altro (Inserisci manuale)":
            final_input_source = st.text_input("Inserisci Source Manuale", placeholder="es. nuova-piattaforma")
        else:
            final_input_source = selected_source_option
        
        if final_input_source:
            src_clean = normalize_token(final_input_source)
            if final_input_source != src_clean:
                st.markdown(f'<div class="msg-warning">⚠️ Consigliato: {src_clean}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)

        available_channels = get_compatible_channels(final_input_source, prop_config["channels"])
        sel_channel = st.selectbox("Channel Grouping", available_channels, help="In quale channel grouping vuoi che venga raccolto il traffico?")
        
        real_opts = [c for c in available_channels if c]
        if len(real_opts) > 1 and not sel_channel:
            st.markdown(f'<div class="msg-error">❌ Seleziona un canale (Sorgente ambigua)</div>', unsafe_allow_html=True)
        elif sel_channel:
            st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)

        # 3. DESTINAZIONE
        st.markdown('<div class="section-header">DESTINAZIONE</div>', unsafe_allow_html=True)
        
        domain_hint = prop_config.get('expected_domain', '')
        destination_url = st.text_input("URL Atterraggio *", value="https://", help="Dove atterrerà l’utente quando clicca sulla CTA?")
        
        if destination_url == "https://" or not destination_url:
            pass
        elif not is_valid_url(destination_url):
            st.markdown('<div class="msg-error">❌ URL non valido (es. https://sito.it)</div>', unsafe_allow_html=True)
        elif domain_hint and domain_hint not in destination_url:
            st.markdown(f'<div class="msg-warning">⚠️ Dominio diverso da {domain_hint}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="msg-success">✅ URL valido</div>', unsafe_allow_html=True)

        # 4. NAMING CAMPAGNA
        st.markdown('<div class="section-header">NAMING CAMPAGNA</div>', unsafe_allow_html=True)
        st.caption("Pattern: `Country_Type_Name_Date_CTA`")

        inp_country = st.text_input("Country *", value=prop_config["default_country"], help="In che lingua è la comunicazione?")
        if inp_country: st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            inp_type = st.text_input("Type", placeholder="es. promo", help="Che tipo di campagna è?")
            if inp_type: st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)
        with c2:
            inp_name = st.text_input("Nome Campagna *", placeholder="es. saldi", help="Come chiameresti questa campagna?")
            if inp_name:
                nm_norm = normalize_token(inp_name)
                if inp_name != nm_norm:
                    st.markdown(f'<div class="msg-warning">⚠️ Usa: {nm_norm}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            inp_date = st.date_input("Start Date", datetime.today(), help="Quando partirà la campagna?")
            st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)
        with c4:
            inp_cta = st.text_input("CTA / Content", placeholder="es. banner", help="Qual è la CTA?")
            if inp_cta: st.markdown('<div class="msg-success">✅ OK</div>', unsafe_allow_html=True)


    # COLONNA DESTRA (OUTPUT)
    with col_right:
        st.markdown("### 🚀 Link Finale")
        
        date_str = inp_date.strftime("%Y%m%d")
        p_cnt = normalize_token(inp_country)
        p_typ = normalize_token(inp_type)
        p_nam = normalize_token(inp_name)
        p_cta = normalize_token(inp_cta)
        p_src = normalize_token(final_input_source)
        p_med = normalize_token(sel_channel)

        parts = []
        if p_cnt: parts.append(p_cnt)
        if p_typ: parts.append(p_typ)
        if p_nam: parts.append(p_nam)
        parts.append(date_str)
        if p_cta: parts.append(p_cta)
        
        final_campaign = "_".join(parts)

        errors = []
        if not is_valid_url(destination_url): errors.append("URL")
        if not p_src: errors.append("Source")
        if len(real_opts) > 1 and not sel_channel: errors.append("Canale")
        if not p_cnt: errors.append("Country")
        if not p_nam: errors.append("Name")

        if errors:
            st.markdown(f"""
            <div class="output-box-ready">
                👉 <b>Compila i campi obbligatori a sinistra per generare il link.</b><br>
                <small>Mancano: {", ".join(errors)}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            sep = "&" if "?" in destination_url else "?"
            final_url = f"{destination_url}{sep}utm_source={p_src}&utm_medium={p_med}&utm_campaign={final_campaign}"
            if p_cta: final_url += f"&utm_content={p_cta}"
            
            st.markdown(f"""
            <div class="output-box-success">
                ✅ <b>Link pronto per l'uso</b>
            </div>
            """, unsafe_allow_html=True)
            
            st.code(final_url, language="text")
            
            st.write("Parametri Tecnici:")
            st.json({
                "source": p_src,
                "medium": p_med,
                "campaign": final_campaign,
                "content": p_cta
            })

        st.write("")
        st.write("")
        with st.expander("📘 Guida ai Canali"):
            st.table(pd.DataFrame(GUIDE_TABLE_DATA))

        st.markdown("---")
        st.markdown("### 💬 Costruiamolo insieme")
        st.caption("Usa questa chat per farti aiutare a definire la strategia di tracciamento (connessa a MCP)")

        # Visualizza messaggi esistenti
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input chat
        if prompt := st.chat_input("Come posso aiutarti con i tuoi UTM?"):
            # Aggiungi messaggio utente
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Risposta (Placeholder per MCP)
            with st.chat_message("assistant"):
                response = f"Ricevuto! Sto analizzando la tua richiesta: '{prompt}'. (In attesa di connessione MCP...)"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# ==============================================================================
# TAB 2: UTM CHECKER (CORRETTO E PULITO)
# ==============================================================================
with tab_checker:
    st.markdown("### UTM Checker Tool")
    st.markdown("Usa questo strumento per verificare se i parametri UTM del tuo link sono impostati correttamente.")
    
    check_url_input = st.text_input("Inserisci qui il tuo URL con UTM", placeholder="https://sito.it?utm_source=...")
    
    if st.button("Analizza URL", type="primary"):
        if not check_url_input:
            st.error("Inserisci un URL per procedere.")
        else:
            try:
                parsed = urlparse(check_url_input)
                params = parse_qs(parsed.query)
                
                # 1. URL CHECKS
                st.markdown("### URL checks")
                
                is_https = parsed.scheme == 'https'
                icon_https = "✅" if is_https else "⚠️"
                val_https = "Yes" if is_https else "No (Not Secure)"
                
                length = len(check_url_input)
                icon_len = "✅" if length < 2048 else "⚠️"
                
                has_utm = any(k.startswith('utm_') for k in params.keys())
                icon_utm = "✅" if has_utm else "❌"
                val_utm = "Yes" if has_utm else "No"

                st.markdown(f"""
                <div class="utm-check-card">
                    <div class="utm-row">
                        <div class="utm-label-col" style="font-weight:bold; color:#555;">HTTPS</div>
                        <div class="utm-value-col">{icon_https} {val_https}</div>
                    </div>
                    <div class="utm-row">
                        <div class="utm-label-col" style="font-weight:bold; color:#555;">URL length</div>
                        <div class="utm-value-col">{icon_len} {length} chars</div>
                    </div>
                    <div class="utm-row">
                        <div class="utm-label-col" style="font-weight:bold; color:#555;">Contains UTM</div>
                        <div class="utm-value-col">{icon_utm} {val_utm}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. UTM CHECKS (COSTRUZIONE STRINGA HTML UNICA)
                st.markdown("### UTM checks")
                
                # Definizione Campi e Obbligatorietà
                fields_to_check = [
                    ("UTM Source", "utm_source", "tag-blue", True),   # True = Obbligatorio
                    ("UTM Medium", "utm_medium", "tag-blue", True),
                    ("UTM Campaign", "utm_campaign", "tag-blue", True),
                    ("UTM Term", "utm_term", "tag-gray", False),
                    ("UTM Content", "utm_content", "tag-gray", False)
                ]
                
                # Inizializza la stringa HTML
                html_output = '<div class="utm-check-card">'
                
                for label, key, tag_class, is_required in fields_to_check:
                    val_list = params.get(key, [])
                    val = val_list[0] if val_list else None
                    
                    if val:
                        # Valore presente (VERDE)
                        display_val = f'{val} <span class="check-icon">✔</span>'
                    else:
                        if is_required:
                            # Valore assente e obbligatorio (ROSSO)
                            display_val = '<span class="error-text">Mancante</span> <span class="error-icon">✖</span>'
                        else:
                            # Valore assente ma opzionale (Grigio)
                            display_val = '<span style="color:#ccc">-</span>'
                    
                    # Concatena la riga HTML
                    html_output += f"""
                    <div class="utm-row">
                        <div class="utm-label-col">
                            <span class="utm-tag {tag_class}">{label}:</span>
                        </div>
                        <div class="utm-value-col">{display_val}</div>
                    </div>
                    """
                
                # Chiudi il div della card
                html_output += "</div>"
                
                # Stampa tutto l'HTML in una volta sola (SOLUZIONE AL BUG VISIVO)
                st.markdown(html_output, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Errore analisi URL: {e}")