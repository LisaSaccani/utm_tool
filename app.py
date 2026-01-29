import streamlit as st
import pandas as pd
import re
from datetime import datetime
from slugify import slugify

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Universal UTM Governance", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PRO (DESIGN & UX FIX) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* 1. Reset Spazi Vuoti in Alto */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    header { visibility: hidden; } /* Nasconde la barra colorata in alto di Streamlit */

    /* 2. Stile Generale */
    .stApp {
        background-color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    /* 3. Card Input */
    .css-card {
        background-color: #f8f9fa;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
    }

    /* 4. Chips (Etichette Parametri) - STILE NUOVO */
    .chip-container { 
        display: flex; 
        flex-wrap: wrap; 
        gap: 8px; 
        margin-bottom: 12px; 
    }
    .chip {
        background-color: #EFF6FF; /* Azzurro Ghiaccio */
        color: #1E40AF; /* Blu Scuro */
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        border: 1px solid #BFDBFE;
        display: flex;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .chip span { 
        color: #1f2937; /* Testo Label Scuro */
        margin-right: 6px; 
        font-weight: 700; 
        text-transform: uppercase;
        font-size: 0.7rem;
        opacity: 0.7;
    }

    /* 5. Messaggi Validazione Discreti */
    .validation-msg { font-size: 0.8rem; margin-top: -10px; margin-bottom: 12px; font-weight: 500; }
    .err { color: #dc3545; }
    .warn { color: #d63384; }

    /* 6. Header Titolo */
    .main-header {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 15px;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER VISIVO ---
st.markdown("""
<div class="main-header">
    <h2 style="margin:0; color:#111827; font-weight: 700;">🛡️ Universal UTM Governance</h2>
    <p style="margin:0; color:#6b7280; font-size: 0.9rem;">Configura, valida e genera i tuoi link di tracciamento.</p>
</div>
""", unsafe_allow_html=True)

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

GUIDE_TABLE_DATA = [
    {"Traffic type": "Organic", "utm_medium": "organic", "utm_source": "google, bing, yahoo"},
    {"Traffic type": "Referral", "utm_medium": "referral", "utm_source": "(domain)"},
    {"Traffic type": "Paid Search", "utm_medium": "cpc", "utm_source": "google, bing"},
    {"Traffic type": "Display", "utm_medium": "cpm", "utm_source": "google, dv360"},
    {"Traffic type": "Email", "utm_medium": "email", "utm_source": "newsletter, sfmc"},
    {"Traffic type": "Social Paid", "utm_medium": "social_paid", "utm_source": "meta, tiktok"},
    {"Traffic type": "Social Org", "utm_medium": "social_org", "utm_source": "meta, tiktok"},
]

# --- UTILS ---
def get_source_options():
    sources = set()
    for row in GUIDE_TABLE_DATA:
        parts = row["utm_source"].split(",")
        for p in parts:
            clean = p.strip().replace("...", "")
            if clean and "(" not in clean: sources.add(clean)
    return [""] + sorted(list(sources)) + ["Altro (Inserisci manuale)"]

SOURCE_OPTIONS = get_source_options()

def get_compatible_channels(selected_source, all_client_channels):
    if not selected_source or selected_source == "Altro (Inserisci manuale)": return [""] + all_client_channels
    norm_source = selected_source.strip().lower()
    compatible = set()
    for row in GUIDE_TABLE_DATA:
        row_srcs = [s.strip().lower() for s in row["utm_source"].split(",")]
        if norm_source in row_srcs: compatible.add(row["Traffic type"])
    if not compatible: return [""] + all_client_channels
    filtered = [c for c in all_client_channels if c in compatible]
    return [""] + sorted(filtered) if filtered else [""] + all_client_channels

def normalize_token(text):
    if not text: return ""
    return slugify(text, separator="-", lowercase=True)

def is_valid_url(url):
    return re.match(r'^https?://', url, re.IGNORECASE) is not None

# --- UI SPLIT SCREEN ---
col_left, col_right = st.columns([0.45, 0.55], gap="large")

# ================= COLONNA INPUT =================
with col_left:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    
    # 1. SETUP
    st.caption("SETUP")
    selected_prop_name = st.selectbox("Property GA4", list(MOCK_CLIENT_DB.keys()))
    prop_config = MOCK_CLIENT_DB[selected_prop_name]
    st.markdown("---")

    # 2. SORGENTE
    st.caption("CANALI")
    selected_source_option = st.selectbox("Piattaforma / Source *", SOURCE_OPTIONS)
    final_input_source = st.text_input("Manuale", placeholder="es. nuova-piattaforma") if selected_source_option == "Altro (Inserisci manuale)" else selected_source_option
    
    # Check Source
    src_valid = bool(final_input_source)
    if not src_valid: st.markdown('<div class="validation-msg err">⭕ Campo obbligatorio</div>', unsafe_allow_html=True)
    
    # Canale
    available_channels = get_compatible_channels(final_input_source, prop_config["channels"])
    label_channel = "Channel Grouping ✅" if final_input_source and len(available_channels) == 2 else "Channel Grouping" # Logica semplice per spunta
    
    sel_channel = st.selectbox(label_channel, available_channels, help="Sorgente ambigua? Specifica il canale.")
    
    real_opts = [c for c in available_channels if c]
    if len(real_opts) > 1 and not sel_channel:
        st.markdown('<div class="validation-msg err">⭕ Specifica il canale (Ambiguo)</div>', unsafe_allow_html=True)

    st.write("")

    # 3. DESTINAZIONE
    st.caption("DESTINAZIONE")
    domain_hint = prop_config.get('expected_domain', '')
    
    # Validazione URL per Label
    url_val = "https://"
    url_status_icon = ""
    if "dest_url_input" in st.session_state:
        u = st.session_state.dest_url_input
        if is_valid_url(u) and (not domain_hint or domain_hint in u):
            url_status_icon = " ✅"
    
    destination_url = st.text_input(f"URL Atterraggio{url_status_icon} *", value="https://", key="dest_url_input", help=f"Atteso: {domain_hint}")
    
    if not is_valid_url(destination_url):
         st.markdown('<div class="validation-msg err">⭕ Manca https://</div>', unsafe_allow_html=True)
    elif domain_hint and domain_hint not in destination_url:
         st.markdown(f'<div class="validation-msg warn">⚠️ Dominio diverso da {domain_hint}</div>', unsafe_allow_html=True)

    st.write("")

    # 4. NAMING
    st.caption("NAMING CAMPAGNA")
    
    # Country
    c_label = "Country"
    if "country_in" in st.session_state and st.session_state.country_in: c_label += " ✅"
    inp_country = st.text_input(f"{c_label} *", value=prop_config["default_country"], key="country_in")
    
    # Type & Name
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        inp_type = st.text_input("Type", placeholder="es. promo")
    with c2:
        n_label = "Nome Campagna"
        if "name_in" in st.session_state and st.session_state.name_in: n_label += " ✅"
        inp_name = st.text_input(f"{n_label} *", placeholder="es. saldi", key="name_in")

    # Date & CTA
    c3, c4 = st.columns([0.4, 0.6])
    with c3:
        inp_date = st.date_input("Start Date ✅", datetime.today())
    with c4:
        inp_cta = st.text_input("CTA / Content", placeholder="es. banner")

    st.markdown('</div>', unsafe_allow_html=True)

# ================= COLONNA OUTPUT =================
with col_right:
    
    st.write("") # Spacer per allineare visivamente al box grigio a sinistra
    st.write("") 

    # 1. CALCOLO DATI
    p_src = normalize_token(final_input_source)
    p_med = normalize_token(sel_channel)
    p_cmp_parts = [
        normalize_token(inp_country),
        normalize_token(inp_type),
        normalize_token(inp_name),
        inp_date.strftime("%Y%m%d"),
        normalize_token(inp_cta)
    ]
    final_campaign = "_".join([p for p in p_cmp_parts if p])
    p_cnt = normalize_token(inp_cta)

    # Costruzione URL
    sep = "&" if "?" in destination_url else "?"
    full_url = f"{destination_url}{sep}utm_source={p_src}&utm_medium={p_med}&utm_campaign={final_campaign}"
    if p_cnt: full_url += f"&utm_content={p_cnt}"

    # Check Errori
    has_errors = False
    if not is_valid_url(destination_url): has_errors = True
    if not p_src or not inp_country or not inp_name: has_errors = True
    if len(real_opts) > 1 and not sel_channel: has_errors = True

    # 2. SUPER BOX (Chips + Codice)
    st.markdown("### 🚀 Link Finale")
    
    if has_errors:
        st.info("👈 Compila i campi obbligatori a sinistra per generare il link.")
    else:
        # Chips
        st.markdown(f"""
        <div class="chip-container">
            <div class="chip"><span>SOURCE</span> {p_src}</div>
            <div class="chip"><span>MEDIUM</span> {p_med}</div>
            <div class="chip"><span>CAMPAIGN</span> {final_campaign}</div>
            {f'<div class="chip"><span>CONTENT</span> {p_cnt}</div>' if p_cnt else ''}
        </div>
        """, unsafe_allow_html=True)
        
        # Tasto Copia Nativo
        st.code(full_url, language="text")
        
        st.success("Link valido e pronto all'uso.")

    st.markdown("---")
    
    # 3. GUIDA
    with st.expander("📘 Guida ai Canali"):
        st.table(pd.DataFrame(GUIDE_TABLE_DATA))