import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
from slugify import slugify

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Universal UTM Manager", layout="wide")

# --- CSS CUSTOM (STILE GRAFICO) ---
st.markdown("""
<style>
    /* 1. Stile per le TAB (Bottoni grandi) */
    div[data-baseweb="tab-list"] { gap: 8px; }
    button[data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px;
        padding: 10px 24px;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }

    /* 2. Stile per la tabella Audit */
    .status-ok { background-color: #d4edda; color: #155724; }
    .status-warning { background-color: #fff3cd; color: #856404; }
    .status-error { background-color: #f8d7da; color: #721c24; }
    
    /* 3. Stile compatto per la tabella Guida */
    div[data-testid="stTable"] {
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- UTILS ---
def normalize_text(text):
    if not text: return ""
    return slugify(text, separator="_")

def apply_status_style(val):
    if "✅" in val: return 'background-color: #d4edda; color: #155724'
    elif "⚠️" in val: return 'background-color: #fff3cd; color: #856404'
    elif "❌" in val: return 'background-color: #f8d7da; color: #721c24'
    return ''

def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

# --- CONFIGURAZIONE ---

# 1. Mapping Logico (Cosa succede quando selezioni nel dropdown)
CHANNEL_MAPPING = {
    "Paid Search": "cpc",
    "Paid Social": "social_paid",
    "Display": "cpm",
    "Video": "cpv",
    "Programmatic": "cpm",
    "Email": "email",
    "Affiliate": "affiliate",
    "Organic Social": "social_org",
    "Offline / SMS": "offline",
    "App Traffic": "app_traffic", # placeholder
    "Altro": "other"
}

# 2. Dati per la Tabella Guida (Copia fedele dell'immagine)
GUIDE_TABLE_DATA = [
    {"Traffic type": "Organic", "utm_medium": "organic", "utm_source": "google, bing, yahoo..."},
    {"Traffic type": "Referral", "utm_medium": "referral", "utm_source": "[website domain]"},
    {"Traffic type": "Direct", "utm_medium": "(none)", "utm_source": "(direct)"},
    {"Traffic type": "Paid campaign", "utm_medium": "cpc", "utm_source": "google, bing..."},
    {"Traffic type": "Affiliate campaign", "utm_medium": "affiliate", "utm_source": "tradetracker..."},
    {"Traffic type": "Display campaign", "utm_medium": "cpm", "utm_source": "reservation, display..."},
    {"Traffic type": "Video campaign", "utm_medium": "cpv", "utm_source": "youtube..."},
    {"Traffic type": "Programmatic", "utm_medium": "cpm", "utm_source": "rcs, mediamond, rai..."},
    {"Traffic type": "Organic email", "utm_medium": "email", "utm_source": "newsletter, email, crm"},
    {"Traffic type": "Social organic", "utm_medium": "social_org", "utm_source": "facebook, instagram..."},
    {"Traffic type": "Social paid", "utm_medium": "social_paid", "utm_source": "facebook, instagram..."},
    {"Traffic type": "App traffic", "utm_medium": "-", "utm_source": "app"},
    {"Traffic type": "Offline", "utm_medium": "offline", "utm_source": "brochure, qr_code, sms"},
]

# --- FUNZIONI MOCK ---
def get_mock_audit_post_campaign():
    data = [
        {"Campagna": "Saldi inverno jeans donna", "Periodo": "10-31/01/2026", "UTM (source/medium)": "meta / paid_social", "Sessions": 532, "Canale Atteso": "Paid Social", "Canale Osservato": "Paid Social", "Stato Tracking": "✅ OK - Tracking corretto"},
        {"Campagna": "DEM Welcome Firenze", "Periodo": "01-31/01/2026", "UTM (source/medium)": "sfmc / email", "Sessions": 0, "Canale Atteso": "Email", "Canale Osservato": "-", "Stato Tracking": "❌ Nessun traffico rilevato"},
        {"Campagna": "Remarketing carrello IT", "Periodo": "10-31/01/2026", "UTM (source/medium)": "meta / paid_social", "Sessions": 120, "Canale Atteso": "Paid Social", "Canale Osservato": "Unassigned", "Stato Tracking": "⚠️ Canale errato (Unassigned)"}
    ]
    return pd.DataFrame(data)

# --- INTERFACCIA UTENTE ---

# 1. SIDEBAR
st.sidebar.header("1. Configurazione Campagna")
st.sidebar.markdown("---")

destination_url = st.sidebar.text_input(
    "URL di destinazione", 
    value="https://www.site.com/",
    help="Dove atterrerà l’utente quando clicca sulla CTA? (Deve iniziare con http:// o https://)"
)

campaign_name_internal = st.sidebar.text_input(
    "Nome Campagna (Interno)", 
    placeholder="es. promo_saldi",
    help="Come chiameresti questa campagna internamente? Serve per identificarla in fase di analisi."
)

selected_grouping = st.sidebar.selectbox(
    "Channel Grouping (GA4)", 
    list(CHANNEL_MAPPING.keys()),
    help="In quale channel grouping vuoi che venga raccolto il traffico di questa campagna?"
)

platform_source = st.sidebar.text_input(
    "Piattaforma / Source", 
    placeholder="es. google, meta, newsletter",
    help="Su quale piattaforma o canale stai attivando questa campagna? (google, youtube, newsletter...)"
)

start_date = st.sidebar.date_input(
    "Data Inizio Campagna", 
    datetime.today(),
    help="Quando partirà la campagna?"
)

extra_details = st.sidebar.text_input(
    "Dettagli Extra (es. Paese)", 
    value="it",
    help="Qual è il paese principale target della campagna?"
)

cta_creative = st.sidebar.text_input(
    "CTA / Creatività (Opzionale)", 
    placeholder="es. shop_now",
    help="Qual è la CTA o il nome della creatività che vuoi tracciare?"
)

# 2. MAIN TITLE
st.title("🌐 UTM Manager & Audit Tool")

# 3. TABS
tab_builder, tab_audit = st.tabs(["🛠️ Builder (Crea Link)", "📊 Audit (Controlla Dati)"])

# === TAB 1: BUILDER ===
with tab_builder:
    # Layout colonne: aumentato spazio per la guida (60% risultati, 40% guida)
    col_results, col_guide = st.columns([0.60, 0.40], gap="large")

    with col_results:
        st.subheader("Generazione Link")
        st.caption("Compila il form a sinistra e premi il bottone per generare.")
        
        btn_generate = st.button("Genera Link UTM", type="primary")

        if btn_generate:
            if not is_valid_url(destination_url):
                st.error("⛔ **Errore URL**: L'URL di destinazione non è valido. Assicurati che inizi con `http://` o `https://`.")
            else:
                st.divider()
                
                # 1. Logica
                p_medium = CHANNEL_MAPPING.get(selected_grouping, "other")
                p_source = normalize_text(platform_source) or "not_specified"
                date_str = start_date.strftime("%Y%m%d")
                clean_name = normalize_text(campaign_name_internal)
                clean_extra = normalize_text(extra_details)
                p_campaign = f"{clean_extra}_{clean_name}_{date_str}"
                p_content = normalize_text(cta_creative)

                separator = "&" if "?" in destination_url else "?"
                final_url = f"{destination_url}{separator}utm_source={p_source}&utm_medium={p_medium}&utm_campaign={p_campaign}"
                if p_content: final_url += f"&utm_content={p_content}"

                # 2. Output
                st.success("✅ Link generato")
                st.markdown("**URL Finale:**")
                st.code(final_url, language="text")
                
                st.markdown("**Parametri:**")
                st.json({
                    "utm_source": p_source,
                    "utm_medium": p_medium, 
                    "utm_campaign": p_campaign,
                    "utm_content": p_content
                })

    with col_guide:
        st.markdown("### 📖 Guida Naming")
        st.info("Riferimento standard per Source e Medium")
        
        # Creazione Tabella dalla struttura dati definita sopra
        df_guide = pd.DataFrame(GUIDE_TABLE_DATA)
        # Visualizzazione tabella statica
        st.table(df_guide)

# === TAB 2: AUDIT ===
with tab_audit:
    st.header("Audit Campagne Attive")
    st.markdown("Controllo coerenza dati post-lancio (Simulazione GA4/BigQuery)")
    
    col_filters, col_action = st.columns([3, 1])
    with col_filters:
        audit_period = st.date_input("Periodo di analisi", (datetime.today() - timedelta(days=30), datetime.today()))
    with col_action:
        st.write("") 
        st.write("") 
        btn_run_audit = st.button("Aggiorna Dati", type="primary")

    if btn_run_audit:
        st.write("---")
        df_audit = get_mock_audit_post_campaign()
        st.dataframe(df_audit.style.applymap(apply_status_style, subset=['Stato Tracking']), use_container_width=True, hide_index=True)