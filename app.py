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


from datetime import datetime, date, time, timedelta
from collections import Counter
from email.utils import parseaddr
import streamlit as st
import pandas as pd
import plotly.express as px


def top_senders_tool(service):
    st.subheader("📊 Top Senders — Setup")

    # --- Initialize session state ---
    if "analysis_params" not in st.session_state:
        st.session_state.analysis_params = None

    current_year = datetime.now().year
    default_start = date(current_year, 1, 1)
    default_end = date.today()

    # --- Input fields ---
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input(
            "Start date",
            value=st.session_state.get("start_date", default_start),
            key="ts_start",
        )
    with c2:
        end_date = st.date_input(
            "End date",
            value=st.session_state.get("end_date", default_end),
            key="ts_end",
        )

    email_limit = st.number_input(
        "Maximum emails to analyze",
        min_value=100,
        max_value=10000,
        step=100,
        value=st.session_state.get("email_limit", 2000),
        help="How many emails to scan for analysis.",
        key="ts_limit",
    )

    top_n = st.number_input(
        "Number of top senders to display",
        min_value=5,
        max_value=50,
        step=1,
        value=st.session_state.get("top_n", 10),
        help="Choose how many top senders to display in the results.",
        key="ts_topn",
    )

    # --- Save user choices ---
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date
    st.session_state.email_limit = email_limit
    st.session_state.top_n = top_n

    st.divider()
    st.write(f"🗓️ **Selected Range:** {start_date} → {end_date}")
    st.write(f"📬 **Email Limit:** {email_limit:,}")
    st.write(f"🏆 **Top Senders to Show:** {top_n}")

    # --- Run analysis ---
    if st.button("▶️ Run Analysis"):
        start_ts = int(datetime.combine(start_date, time.min).timestamp())
        end_ts = int((datetime.combine(end_date, time.min) + timedelta(days=1)).timestamp())
        query = f"in:inbox after:{start_ts} before:{end_ts} -in:spam -in:trash"

        st.info("⏳ Fetching emails... Please wait.")
        progress = st.progress(0)
        status = st.empty()

        # --- Step 1: Fetch message IDs ---
        messages = []
        results = service.users().messages().list(userId="me", q=query, maxResults=500).execute()
        messages.extend(results.get("messages", []))

        while "nextPageToken" in results and len(messages) < email_limit:
            results = service.users().messages().list(
                userId="me",
                q=query,
                pageToken=results["nextPageToken"],
                maxResults=500,
            ).execute()
            messages.extend(results.get("messages", []))
            progress.progress(min(len(messages) / email_limit, 1.0))
            status.text(f"📬 Loaded {len(messages)} messages...")

        if len(messages) > email_limit:
            messages = messages[:email_limit]
            st.warning(f"⚠️ Limiting to first {email_limit} messages for performance.")

        total = len(messages)
        if total == 0:
            st.warning("No messages found in this range.")
            return

        st.success(f"✅ Found {total} emails in your inbox during this period.")
        progress.progress(0)
        status.text("Analyzing senders...")

        # --- Step 2: Analyze sender emails ---
        senders = []
        for i, msg in enumerate(messages):
            try:
                data = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From"],
                ).execute()
                headers = data["payload"]["headers"]
                sender_val = next((h["value"] for h in headers if h["name"] == "From"), None)
                if sender_val:
                    senders.append(parseaddr(sender_val)[1].lower())
            except Exception:
                continue

            if (i + 1) % 10 == 0 or (i + 1) == total:
                progress.progress((i + 1) / total)
                status.text(f"📊 Analyzed {i + 1}/{total} emails...")

        # --- Step 3: Display results ---
        status.text("✅ Analysis complete!")
        progress.empty()

        counts = Counter(senders).most_common(top_n)

        if not counts:
            st.warning("No senders found.")
            return

        df = pd.DataFrame(counts, columns=["Sender", "Count"])

        # Save for later deletion functionality
        st.session_state["top_senders"] = df

        # --- Step 4: Chart ---
        fig = px.bar(
            df.sort_values("Count"),
            x="Count",
            y="Sender",
            orientation="h",
            text="Count",
            title=f"Top {top_n} Senders by Email Count",
            color="Count",
            color_continuous_scale="Aggrnyl",
        )
        fig.update_layout(
            xaxis_title="Number of Emails",
            yaxis_title="Sender",
            template="plotly_dark",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)







from datetime import datetime, time, timedelta

def delete_top_senders(service):
    st.subheader("🗑️ Clean Up by Sender")

    if "top_senders" not in st.session_state:
        st.warning("⚠️ Run the analysis first to identify top senders.")
        return

    # ✅ Safely retrieve date range if available
    params = st.session_state.get("analysis_params")
    if not params or not isinstance(params, dict) or "start" not in params or "end" not in params:
        st.info("📅 No date range found — using all emails.")
        start_ts, end_ts = None, None
    else:
        start_date = params.get("start")
        end_date = params.get("end")
        start_ts = int(datetime.combine(start_date, time.min).timestamp())
        end_ts = int((datetime.combine(end_date, time.min) + timedelta(days=1)).timestamp())
        st.info(f"📅 Deleting only emails between {start_date} and {end_date}")

    # ✅ Reset checkboxes when entering delete mode
    if "delete_tab_initialized" not in st.session_state:
        for key in list(st.session_state.keys()):
            if key.startswith("sender_"):
                del st.session_state[key]
        st.session_state.delete_tab_initialized = True

    df = st.session_state["top_senders"]
    st.write("Select the senders you want to delete emails from:")

    selected = []
    for i, row in df.iterrows():
        if st.checkbox(f"{row['Sender']} — {row['Count']} emails", key=f"sender_{i}"):
            selected.append(row["Sender"])

    if not selected:
        st.info("No senders selected yet.")
        return

    st.success(f"✅ Selected {len(selected)} sender(s): {', '.join(selected)}")

    if st.button("🚮 Move selected emails to Trash"):
        total_deleted = 0
        progress = st.progress(0)
        status = st.empty()

        for idx, sender in enumerate(selected):
            # ✅ Apply date filter if present
            if start_ts and end_ts:
                query = f"from:{sender} after:{start_ts} before:{end_ts}"
            else:
                query = f"from:{sender}"

            try:
                results = service.users().messages().list(userId="me", q=query, maxResults=500).execute()
                messages = results.get("messages", [])
                for msg in messages:
                    service.users().messages().trash(userId="me", id=msg["id"]).execute()
                    total_deleted += 1
            except Exception as e:
                st.error(f"Error deleting emails from {sender}: {e}")

            progress.progress((idx + 1) / len(selected))
            status.text(f"Processed {idx + 1}/{len(selected)} senders...")

        st.success(f"✅ Moved {total_deleted} emails to Trash.")
        progress.empty()
        status.empty()

        # ✅ Reset all sender checkboxes for safety
        for key in list(st.session_state.keys()):
            if key.startswith("sender_"):
                del st.session_state[key]
        st.session_state.delete_tab_initialized = False






# ---------- Gmail Management ----------
def gmail_manager():
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

    # ---------- Tabs for Analysis & Cleanup ----------
    tab1, tab2 = st.tabs(["📊 Analyze Inbox", "🗑️ Clean Up Senders"])

    with tab1:
        top_senders_tool(service)   # your existing analysis tool

    with tab2:
        delete_top_senders(service)  # the new cleanup section


        
        
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
