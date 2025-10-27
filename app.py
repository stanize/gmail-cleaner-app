import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from collections import Counter
import pandas as pd
import pickle, os, re

st.set_page_config(page_title="📬 Gmail Inbox Analyzer", page_icon="📨")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

st.title("📬 Gmail Inbox Analyzer")
st.write("Analyze your Gmail inbox for repetitive senders — all data stays private on your Google account.")

# File upload for credentials.json (so users can provide their own)
uploaded_file = st.file_uploader("Upload your Google credentials.json", type=["json"])

def extract_sender(header_list):
    for h in header_list:
        if h['name'].lower() == 'from':
            match = re.search(r'<(.*?)>', h['value'])
            return match.group(1).lower() if match else h['value'].strip().lower()
    return None

def gmail_service(creds_json):
    # Save uploaded credentials to a temp file
    with open("temp_credentials.json", "wb") as f:
        f.write(creds_json.read())

    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('temp_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
            
    return build('gmail', 'v1', credentials=creds)

def analyze_inbox(service, max_messages):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_messages).execute()
    messages = results.get('messages', [])
    total = len(messages)
    sender_counts = Counter()

    progress = st.progress(0)
    for i, m in enumerate(messages, start=1):
        msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From']).execute()
        sender = extract_sender(msg['payload'].get('headers', []))
        if sender:
            sender_counts[sender] += 1
        progress.progress(i / total)

    df = pd.DataFrame(sender_counts.most_common(20), columns=['Sender', 'Count'])
    return df

if uploaded_file:
    st.success("Credentials file uploaded successfully ✅")

    num = st.number_input("Number of emails to scan", min_value=100, max_value=2000, value=500, step=100)

    if st.button("Run Analysis"):
        with st.spinner("Connecting to Gmail and scanning emails..."):
            service = gmail_service(uploaded_file)
            df = analyze_inbox(service, num)
        st.success("✅ Analysis complete!")
        st.dataframe(df)
        st.download_button("Download as CSV", data=df.to_csv(index=False), file_name="inbox_report.csv")
else:
    st.info("👆 Please upload your `credentials.json` file to begin.")
