import streamlit as st
import pandas as pd
import re
from datetime import datetime
from slugify import slugify

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Universal UTM Governance", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .validation-box { padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 14px; }
    .valid { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .invalid { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    div[data-baseweb="tab-list"] { gap: 8px; }
    button[data-baseweb="tab"] { background-color: #f0f2f6; font-weight: bold; border: 1px solid #ddd; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #FF4B4B; color: white; border-color: #FF4B4B; }
    div[data-testid="stTable"] { font-size: 12px; }
</style>
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

# --- LOGICA DINAMICA ---
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
    if not filtered_channels:
        return [""] + all_client_channels
    return [""] + sorted(filtered_channels)

# --- UTILS ---
def normalize_token(text):
    if not text: return ""
    return slugify(text, separator="-", lowercase=True)

def validate_token(text, field_name, is_mandatory=True):
    if not text:
        if is_mandatory:
            return False, f'<div class="validation-box invalid">❌ <b>{field_name}</b> è obbligatorio.</div>', ""
        else:
            return True, "", "" 
    normalized = normalize_token(text)
    if text != normalized:
        return False, f'<div class="validation-box warning">⚠️ <b>{field_name}</b> formato errato.<br>Consigliato: <code>{normalized}</code></div>', normalized
    return True, f'<div class="validation-box valid">✅ <b>{field_name}</b> OK</div>', normalized

def validate_url_logic(url, expected_domain):
    regex = re.compile(r'^https?://(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not re.match(regex, url):
        return False, f'<div class="validation-box invalid">❌ <b>URL</b> non valido. (Es. https://www.chicco.it)</div>'
    if expected_domain and expected_domain not in url:
        return True, f'<div class="validation-box warning">⚠️ <b>URL</b> valido ma dominio sospetto (atteso: <b>{expected_domain}</b>).</div>'
    return True, f'<div class="validation-box valid">✅ <b>URL</b> valido e coerente</div>'

# --- UI SIDEBAR ---
st.sidebar.title("1. Configurazione")

selected_prop_name = st.sidebar.selectbox("Property GA4", list(MOCK_CLIENT_DB.keys()))
prop_config = MOCK_CLIENT_DB[selected_prop_name]

st.sidebar.markdown("---")
st.sidebar.subheader("Sorgente e Canale")

# 1. SCELTA SORGENTE
selected_source_option = st.sidebar.selectbox(
    "Piattaforma / Source (Obbligatorio)", 
    SOURCE_OPTIONS,
    help="Su quale piattaforma o canale stai attivando questa campagna?"
)
final_input_source = st.sidebar.text_input("Inserisci Source Manuale", placeholder="es. nuova-piattaforma") if selected_source_option == "Altro (Inserisci manuale)" else selected_source_option

# 2. SCELTA CANALE
available_channels_filtered = get_compatible_channels(final_input_source, prop_config["channels"])
sel_channel = st.sidebar.selectbox(
    "Channel Grouping (Opzionale)", 
    available_channels_filtered,
    help="In quale channel grouping vuoi che venga raccolto il traffico di questa campagna? Nota: se la sorgente è ambigua (es. Facebook), questo campo è obbligatorio."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Destinazione")
domain_hint = prop_config.get('expected_domain', '')
destination_url = st.sidebar.text_input(
    "URL di destinazione", 
    value="https://", 
    help=f"Dove atterrerà l’utente quando clicca sulla CTA? Inserisci l'URL completo (Atteso: {domain_hint})"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Naming Campagna")
st.sidebar.caption("Pattern: `Country_Type_Name_Date_CTA`")

inp_country = st.sidebar.text_input(
    "Country / Lingua *", 
    value=prop_config["default_country"], 
    help="In che lingua è la comunicazione principale di questa campagna?"
)

inp_type = st.sidebar.text_input(
    "Campaign Type (Goal)", 
    placeholder="es. promo", 
    help="Che tipo di campagna è? awarness (awr), conversion (cnv), ecc."
)

inp_name = st.sidebar.text_input(
    "Campaign Name *", 
    placeholder="es. saldi-invernali", 
    help="Come chiameresti questa campagna internamente?"
)

inp_date = st.sidebar.date_input(
    "Data Partenza *", 
    datetime.today(), 
    help="Quando partirà la campagna?"
)

inp_cta = st.sidebar.text_input(
    "CTA / Creatività", 
    placeholder="es. shop-now", 
    help="Qual è la CTA o il nome della creatività che vuoi tracciare?"
)


# --- MAIN PAGE ---
st.title("🛡️ Universal UTM Governance")
tab_builder, tab_audit = st.tabs(["🛠️ Builder & Validazione", "📊 Audit Storico"])

with tab_builder:
    col_results, col_guide = st.columns([0.60, 0.40], gap="large")

    with col_results:
        st.subheader("Controllo Qualità")
        
        all_valid = True
        corrections_needed = False

        # 1. URL CHECK
        url_ok, url_msg = validate_url_logic(destination_url, prop_config.get("expected_domain"))
        st.markdown(url_msg, unsafe_allow_html=True)
        if "invalid" in url_msg: all_valid = False

        # 2. SOURCE CHECK
        is_val_src, msg_src, corr_src = validate_token(final_input_source, "Source", is_mandatory=True)
        st.markdown(msg_src, unsafe_allow_html=True)
        if not is_val_src:
            if corr_src: corrections_needed = True
            else: all_valid = False

        # 3. CHANNEL CHECK (Anti-Ambiguità)
        real_channel_options = [c for c in available_channels_filtered if c]
        if len(real_channel_options) > 1 and not sel_channel:
            st.markdown(f'<div class="validation-box invalid">❌ <b>Channel Grouping</b> mancante. <br>La sorgente <b>{final_input_source}</b> è ambigua, devi specificare il canale.</div>', unsafe_allow_html=True)
            all_valid = False
        elif final_input_source and not sel_channel and not real_channel_options:
             st.markdown(f'<div class="validation-box warning">⚠️ <b>Channel Grouping</b> non specificato.</div>', unsafe_allow_html=True)
        elif sel_channel:
             st.markdown(f'<div class="validation-box valid">✅ <b>Channel</b>: {sel_channel}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Validazione Naming Campagna:**")

        # 4. CAMPAIGN TOKENS
        token_configs = [
            ("Country", inp_country, True),
            ("Type", inp_type, False),
            ("Name", inp_name, True),
            ("CTA", inp_cta, False)
        ]

        c1, c2 = st.columns(2)
        campaign_tokens_clean = []
        for i, (label, val, mandatory) in enumerate(token_configs):
            with (c1 if i % 2 == 0 else c2):
                is_val, msg, corrected = validate_token(val, label, is_mandatory=mandatory)
                if msg: st.markdown(msg, unsafe_allow_html=True)
                if not is_val:
                    if corrected: corrections_needed = True
                    else: all_valid = False
                
                final_val = corrected if corrected else val
                if final_val: campaign_tokens_clean.append(final_val)

        # Composizione
        date_str = inp_date.strftime("%Y%m%d")
        ordered_parts = [
            normalize_token(inp_country),
            normalize_token(inp_type),
            normalize_token(inp_name),
            date_str,
            normalize_token(inp_cta)
        ]
        final_campaign = "_".join([p for p in ordered_parts if p])
        final_medium = normalize_token(sel_channel) if sel_channel else "not-set"

        st.divider()

        # --- OUTPUT ---
        if not all_valid and not corrections_needed:
            st.error("⛔ Correggi errori bloccanti.")
        
        elif corrections_needed:
            st.warning("⚠️ Formattazione da correggere.")
            if st.button("Correggi e Genera", type="primary"):
                sep = "&" if "?" in destination_url else "?"
                final_url = f"{destination_url}{sep}utm_source={corr_src}&utm_medium={final_medium}&utm_campaign={final_campaign}"
                if normalize_token(inp_cta): final_url += f"&utm_content={normalize_token(inp_cta)}"

                st.success("✅ Generato (Corretto)")
                st.code(final_url)
                st.json({"source": corr_src, "medium": final_medium, "campaign": final_campaign})
        
        else:
            if st.button("Genera Link UTM", type="primary"):
                sep = "&" if "?" in destination_url else "?"
                final_url = f"{destination_url}{sep}utm_source={corr_src}&utm_medium={final_medium}&utm_campaign={final_campaign}"
                if normalize_token(inp_cta): final_url += f"&utm_content={normalize_token(inp_cta)}"
                
                st.success("✅ Link Pronto")
                st.code(final_url)
                st.json({"source": corr_src, "medium": final_medium, "campaign": final_campaign})

    with col_guide:
        st.markdown("### 📖 Guida Naming")
        st.table(pd.DataFrame(GUIDE_TABLE_DATA))

with tab_audit:
    st.header("Audit Campagne")
    st.info("Connessione GA4 in attesa.")