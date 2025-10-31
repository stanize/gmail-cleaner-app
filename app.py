import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

st.set_page_config(page_title="📬 Gmail Inbox Analyzer", page_icon="📨")

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
APP_URL = st.secrets.get("app_url", "https://gmail-cleaner-app-cloud9.streamlit.app")

st.title("📬 Gmail Inbox Analyzer")
st.write("Analyze and clean your Gmail inbox safely — directly from your browser.")

# ---------- Gmail Authorization ----------
def authorize_gmail():
    client_config = {
        "web": {
            "client_id": st.secrets["google"]["client_id"],
            "project_id": "gmail-cleaner",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": st.secrets["google"]["client_secret"],
            "redirect_uris": [APP_URL],
        }
    }

    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = APP_URL

    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )

    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 30px;">
            <a href="{auth_url}" target="_blank" style="text-decoration: none;">
                <div style="
                    display: inline-flex;
                    align-items: center;
                    background-color: #fff;
                    color: #555;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 10px 16px;
                    font-size: 15px;
                    font-family: 'Roboto', sans-serif;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                ">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/4/4e/Gmail_Icon.png" 
                         style="width:22px; height:22px; margin-right:10px;">
                    <strong>Connect with Gmail</strong>
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------- Authorized Section ----------
def gmail_manager():
    st.subheader("📧 Manage Emails by Sender")

    creds = Credentials.from_authorized_user_info(st.session_state.get("credentials"), scopes=SCOPES)
    service = build("gmail", "v1", credentials=creds)

    sender_email = st.text_input("Enter sender email to search", placeholder="e.g. no-reply@company.com")

    if sender_email:
        query = f"from:{sender_email}"
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        total = len(messages)

        if total == 0:
            st.info(f"No emails found from {sender_email}")
        else:
            st.success(f"Found {total} email(s) from {sender_email}")

            if st.button("🗑️ Move these emails to Trash"):
                progress = st.progress(0)
                for i, msg in enumerate(messages):
                    service.users().messages().trash(userId="me", id=msg["id"]).execute()
                    progress.progress((i + 1) / total)
                st.success(f"✅ Moved {total} email(s) from {sender_email} to Trash!")



#  Check if connected to Gmail
query_params = st.query_params
if "code" in query_params:
    try:
        client_config = {
            "web": {
                "client_id": st.secrets["google"]["client_id"],
                "project_id": "gmail-cleaner",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_secret": st.secrets["google"]["client_secret"],
                "redirect_uris": [APP_URL],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = APP_URL
        flow.fetch_token(code=query_params["code"])

        creds = flow.credentials
        st.session_state["credentials"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        st.session_state["authorized"] = True
# DEBUG: uncomment this line to show success message
#        st.success("✅ Gmail authorization successful! You can now manage your inbox.")
    except Exception as e:
        st.error(f"Authorization failed: {e}")


# ---------- App Flow ----------
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.info("Please authorize Gmail to continue.")
    authorize_gmail()
else:
    gmail_manager()
