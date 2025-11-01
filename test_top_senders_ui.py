import streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="UI Test", page_icon="🧩")

st.title("📊 Top Senders — UI Test")

# --- Persistent state initialization ---
if "start_date" not in st.session_state:
    st.session_state.start_date = date(datetime.now().year, 1, 1)
if "end_date" not in st.session_state:
    st.session_state.end_date = date.today()
if "email_limit" not in st.session_state:
    st.session_state.email_limit = 2000

# --- Inputs ---
c1, c2 = st.columns(2)
with c1:
    st.session_state.start_date = st.date_input(
        "Start date", st.session_state.start_date
    )
with c2:
    st.session_state.end_date = st.date_input(
        "End date", st.session_state.end_date
    )

st.session_state.email_limit = st.number_input(
    "Maximum emails to analyze",
    min_value=100,
    max_value=10000,
    step=100,
    value=st.session_state.email_limit,
)

# --- Display current values ---
st.divider()
st.write(f"🗓️ **Selected Range:** {st.session_state.start_date} → {st.session_state.end_date}")
st.write(f"📬 **Email Limit:** {st.session_state.email_limit:,}")
