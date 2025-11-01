import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from collections import Counter
from datetime import datetime
from email.utils import parseaddr


# ---------- Constants ----------
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
APP_URL = st.secrets.get("app_url", "https://gmail-cleaner-app-cloud9.streamlit.app")


# ---------- Initialize Page ----------
def init():
    st.set_page_config(page_title="📬 Gmail Inbox Analyzer", page_icon="📨")
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

def delete_emails_from_sender(service):
    result = st.session_state["search_results"]
    sender = result["sender"]
    messages = result["messages"]
    total = result["total"]

    st.success(f"Found {total} email(s) from {sender}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🗑️ Move these emails to Trash"):
            progress = st.progress(0)
            for i, msg in enumerate(messages):
                service.users().messages().trash(userId="me", id=msg["id"]).execute()
                progress.progress((i + 1) / total)
            st.success(f"✅ Moved {total} email(s) from {sender} to Trash!")

    with col2:
        if st.button("🔄 Clear & Start Over"):
            st.session_state.pop("search_results")
            st.rerun()



def search_by_sender(service):
    sender_email = st.text_input("Enter sender email to search", placeholder="e.g. no-reply@company.com")

    if sender_email:
        query = f"from:{sender_email}"
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        total = len(messages)

        if total == 0:
            st.info(f"No emails found from {sender_email}")
        else:
            st.session_state["search_results"] = {
                "sender": sender_email,
                "messages": messages,
                "total": total,
            }
            st.success(f"Found {total} email(s) from {sender_email}")
            st.rerun()   # 👈 ADD THIS LINE



from collections import Counter
from datetime import datetime, date, time, timedelta
from email.utils import parseaddr


from collections import Counter
from datetime import datetime, date, time, timedelta
from email.utils import parseaddr

def top_senders_tool(service):
    st.subheader("📊 Top Senders")

    # --- Initialize session state once ---
    if "top_senders_ui" not in st.session_state:
        st.session_state.top_senders_ui = {
            "show_form": False,
            "ran": False,
            "params": {}
        }

    ui = st.session_state.top_senders_ui

    # ---------- STEP 0: ENTRY BUTTON ----------
    if not ui["show_form"] and not ui["ran"]:
        if st.button("🧭 Choose date range & limit"):
            st.session_state.top_senders_ui["show_form"] = True
            st.rerun()
        return

    # ---------- STEP 1: CONFIG FORM ----------
    if ui["show_form"] and not ui["ran"]:
        with st.form("top_senders_form"):
            c1, c2 = st.columns(2)
            with c1:
                start_d = st.date_input(
                    "Start date", value=date(datetime.now().year, 1, 1)
                )
            with c2:
                end_d = st.date_input("End date", value=date.today())

            limit = st.number_input(
                "Max emails to analyze",
                min_value=100,
                max_value=10000,
                step=100,
                value=2000,
                help="Higher = more accurate, slower.",
            )

            run = st.form_submit_button("▶️ Run analysis")

        # We handle cancel *outside* the form
        if st.button("✖️ Cancel"):
            st.session_state.top_senders_ui = {"show_form": False, "ran": False, "params": {}}
            st.rerun()

        if run:
            st.session_state.top_senders_ui["params"] = {
                "start": start_d,
                "end": end_d,
                "limit": int(limit),
            }
            st.session_state.top_senders_ui["show_form"] = False
            st.session_state.top_senders_ui["ran"] = True
            st.rerun()

        return  # stay on the form screen until "Run" is clicked

    # ---------- STEP 2: ANALYSIS ----------
    if ui["ran"]:
        p = ui["params"]
        start_ts = int(datetime.combine(p["start"], time.min).timestamp())
        before_ts = int(
            (datetime.combine(p["end"], time.min) + timedelta(days=1)).timestamp()
        )
        query = f"in:inbox after:{start_ts} before:{before_ts} -in:spam -in:trash"

        status_area = st.empty()
        status_area.info("Fetching email list... ⏳")

        # --- Fetch all message IDs (with pagination) ---
        messages = []
        results = service.users().messages().list(
            userId="me", q=query, maxResults=500
        ).execute()
        messages.extend(results.get("messages", []))

        while "nextPageToken" in results and len(messages) < p["limit"]:
            results = service.users().messages().list(
                userId="me",
                q=query,
                pageToken=results["nextPageToken"],
                maxResults=500,
            ).execute()
            messages.extend(results.get("messages", []))
            if len(messages) % 500 == 0:
                status_area.info(f"📬 Loaded {len(messages)} messages so far...")

        if len(messages) > p["limit"]:
            messages = messages[: p["limit"]]
            st.warning(
                f"⚠️ Showing only the first {p['limit']} emails for performance."
            )

        total = len(messages)
        if total == 0:
            status_area.warning("No messages found for the selected range.")
            st.session_state.top_senders_ui = {"show_form": False, "ran": False, "params": {}}
            return

        status_area.empty()
        st.success(f"Found {total} emails in the selected range.")

        # --- Analyze with progress ---
        progress = st.progress(0)
        status_text = st.empty()
        senders = []

        for i, m in enumerate(messages):
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=m["id"],
                    format="metadata",
                    metadataHeaders=["From"],
                ).execute()
                headers = msg["payload"]["headers"]
                sender_val = next(
                    (h["value"] for h in headers if h["name"] == "From"), None
                )
                if sender_val:
                    senders.append(parseaddr(sender_val)[1].lower())
            except Exception:
                pass

            if (i + 1) % 10 == 0 or (i + 1) == total:
                progress.progress((i + 1) / total)
                status_text.text(f"Analyzed {i + 1}/{total} emails...")

        status_text.text("✅ Analysis complete!")

        # --- Results ---
        counts = Counter(senders).most_common(10)
        st.divider()
        st.success("Top 10 senders:")
        st.table({"Sender": [s for s, _ in counts], "Count": [c for _, c in counts]})

        # --- Reset button ---
        if st.button("🔁 New analysis"):
            st.session_state.top_senders_ui = {"show_form": False, "ran": False, "params": {}}
            st.rerun()



# ---------- Gmail Management ----------
def gmail_manager():
    # st.subheader("📧 Gmail Inbox Analysis")

    creds_info = st.session_state.get("credentials")
    if creds_info:
        creds = Credentials.from_authorized_user_info(creds_info, scopes=SCOPES)
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                st.session_state["credentials"] = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }
            except Exception as e:
                st.error(f"⚠️ Token refresh failed: {e}")
                st.session_state["authorized"] = False
                st.stop()
    else:
        st.error("⚠️ No valid Gmail credentials found.")
        st.stop()

    # ✅ Create Gmail service
    service = build("gmail", "v1", credentials=creds)

    # ✅ Display only analysis feature for now
    st.info("This version is running in analysis-only mode (delete disabled).")

    st.divider()
    if st.button("📊 Show Top Senders "):
        top_senders_tool(service)
        
        
# ---------- Handle Gmail OAuth Callback ----------
def handle_auth_callback():
    query_params = st.query_params
    if "code" in query_params and not st.session_state.get("authorized"):
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
            st.query_params.clear()  # Clean the URL
        except Exception as e:
            if not st.session_state.get("credentials"):
                st.error(f"Gmail Authorization failed: {e}")


# ---------- Main App ----------
def main():
    init()
    handle_auth_callback()

    if "authorized" not in st.session_state:
        st.session_state.authorized = False

    if not st.session_state.authorized:
        st.info("Please authorize Gmail to continue.")
        authorize_gmail()
    else:
        gmail_manager()


if __name__ == "__main__":
    main()
