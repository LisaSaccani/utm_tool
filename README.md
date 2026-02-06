# 🛡️ Universal UTM Governance

A powerful Streamlit application to generate, manage, and validate UTM links with Google Analytics 4 integration and a Gemini-powered AI Assistant.

## 🚀 Features
- **UTM Generator**: Create standardized links with predefined channel mappings.
- **UTM Checker**: Validate existing links for HTTPS, length, and mandatory parameters.
- **AI Assistant**: Gemini-powered chat (Bot-style UI) to analyze GA4 data using MCP tools.
- **GA4 Integration**: Fetch real traffic sources and property data directly from your account.

## 🛠️ Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place your `client_secrets.json` from Google Cloud Console in the root directory.
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## 🔐 Security
Ensure `token.json` and `client_secrets.json` are **never** committed to Git. A `.gitignore` is provided.
