import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from collections import Counter
import pandas as pd
import os, re

APP_URL = st.secrets.get("app_url", "https://gmail-cleaner-app-cloud9.streamlit.app")

# Streamlit page setup
st.set_page_config(page_title="📬 Gmail Inbox Analyzer", page_icon="📨")

st.title("📬 Gmail Inbox Analyzer")
st.write("Analyze your Gmail inbox for repetitive senders — all data stays private on your Google account.")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def extract_sender(header_list):
    for h in header_list:
        if h['name'].lower() == 'from':
            match = re.search(r'<(.*?)>', h['value'])
            return match.group(1).lower() if match else h['value'].strip().lower()
    return None

def authorize_gmail():
    client_config = {
        "web": {
            "client_id": st.secrets["google"]["client_id"],
            "project_id": "gmail-cleaner",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": st.secrets["google"]["client_secret"],
            "redirect_uris": [st.secrets.get("app_url", "https://yourusername.streamlit.app")],

        }
    }

    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = APP_URL

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.markdown(f"[🔑 Click here to authorize Gmail access]({auth_url})")

def analyze_inbox(service, max_messages):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_messages).execute()
    messages = results.get('messages', [])
    sender_counts = Counter()

    progress = st.progress(0)
    total = len(messages)

    for i, m in enumerate(messages, start=1):
        msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From']).execute()
        sender = extract_sender(msg['payload'].get('headers', []))
        if sender:
            sender_counts[sender] += 1
        progress.progress(i / total)

    df = pd.DataFrame(sender_counts.most_common(20), columns=['Sender', 'Count'])
    return df

# App main flow
try:
    client_id = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
except Exception:
    st.error("Missing Google credentials in Streamlit Secrets. Please add them in Settings → Secrets.")
    st.stop()

st.write("")

if "authorized" not in st.session_state:
    authorize_gmail()
    st.stop()

num = st.number_input("Number of emails to scan", min_value=100, max_value=2000, value=500, step=100)

if st.button("Run Inbox Analysis"):
    st.info("This demo version stops before connecting to Gmail (to avoid exposing tokens).")
    # Once OAuth redirect is complete, you’ll use the Gmail API here to analyze inboxes.
