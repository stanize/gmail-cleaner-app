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
        <div style="text-align:center; margin-top:30px;">
            <a href="{auth_url}" target="_blank">
                <button style="
                    background-color:#FF4B4B;
                    color:white;
                    border:none;
                    border-radius:8px;
                    padding:12px 24px;
                    font-size:16px;
                    cursor:pointer;
                    font-weight:bold;
                    box-shadow:0px 3px 6px rgba(0,0,0,0.3);
                ">
                    🔑 Authorize Gmail Access
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
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


# ---------- App Flow ----------
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.info("Please authorize Gmail to continue.")
    authorize_gmail()
else:
    gmail_manager()
