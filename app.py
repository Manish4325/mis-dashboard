import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config("MIS Dashboard", layout="wide")
st.title("📊 MIS Executive Dashboard")

# =====================================================
# LOGIN
# =====================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.subheader("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "admin123":
            st.session_state.logged_in = True
            st.session_state.role = "Admin"
        elif u == "viewer" and p == "viewer123":
            st.session_state.logged_in = True
            st.session_state.role = "Viewer"
        else:
            st.error("Invalid credentials")

if not st.session_state.logged_in:
    login()
    st.stop()

st.success(f"Logged in as {st.session_state.role}")

# =====================================================
# LOAD DATA (SAFE)
# =====================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip().str.lower()

# Normalize columns
COLUMN_MAP = {
    "bank": ["bank", "bank name"],
    "model": ["model"],
    "predicted": ["predicted"],
    "confirmed": ["confirmed"],
    "accuracy": ["accuracy"],
    "date": ["date"]
}

def find_col(keys):
    for c in df.columns:
        for k in keys:
            if k in c:
                return c
    return None

for std, opts in COLUMN_MAP.items():
    found = find_col(opts)
    if found:
        df.rename(columns={found: std}, inplace=True)

if "date" not in df.columns:
    df["date"] = pd.to_datetime(date.today())

df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted", "confirmed", "accuracy"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    else:
        df[c] = 0

df.dropna(subset=["bank", "accuracy", "date"], inplace=True)

# =====================================================
# DATE FILTER
# =====================================================
st.sidebar.header("📅 Date")
dates = sorted(df["date"].dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)

curr = df[df["date"].dt.date == selected_date]

# =====================================================
# KPI
# =====================================================
c1, c2, c3 = st.columns(3)
c1.metric("Predicted", int(curr["predicted"].sum()))
c2.metric("Confirmed", int(curr["confirmed"].sum()))
c3.metric("Avg Accuracy", f"{curr['accuracy'].mean():.2f}%")

# =====================================================
# EMAIL CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

SENDER_EMAIL = st.secrets["EMAIL_ADDRESS"]
SENDER_PASS = st.secrets["EMAIL_PASSWORD"]

def send_email(bank, acc):
    bank_key = bank.lower()
    if bank_key not in EMAIL_MAP:
        return False

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = EMAIL_MAP[bank_key]
    msg["Subject"] = f"Model Performance Alert – {bank.title()} Bank"

    body = f"""
Dear Team,

We have observed that the model accuracy for {bank.title()} Bank has dropped below the acceptable threshold.

Current Accuracy: {acc:.2f}%

We kindly request you to review the model performance and initiate retraining if required.
Please reach out to your RBIH SPOC for guidance on the next steps.

Warm regards,
RBIH Model Governance Team
"""
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASS)
    server.send_message(msg)
    server.quit()
    return True

# =====================================================
# 🚨 CRITICAL ALERTS + BUTTON
# =====================================================
st.subheader("🚨 Critical Alerts (Accuracy < 40%)")

alerts = curr.groupby("bank")["accuracy"].mean().reset_index()
critical = alerts[alerts["accuracy"] < 40]

if critical.empty:
    st.success("No banks below 40% accuracy")
else:
    st.warning("The following banks have crossed the risk threshold:")
    st.dataframe(critical, use_container_width=True)

    if st.button("📧 Send Alert Emails"):
        sent_any = False
        for _, r in critical.iterrows():
            if send_email(r["bank"], r["accuracy"]):
                st.success(f"Email sent to {r['bank']} SPOC")
                sent_any = True
        if not sent_any:
            st.info("No matching email mappings found.")

# =====================================================
# VISUALS
# =====================================================
st.subheader("🏦 Predicted vs Confirmed")

bank_sum = curr.groupby("bank")[["predicted", "confirmed"]].sum().reset_index()

st.plotly_chart(
    px.bar(
        bank_sum,
        x="bank",
        y=["predicted", "confirmed"],
        barmode="group"
    ),
    use_container_width=True
)

st.subheader("📊 Accuracy by Bank")

st.plotly_chart(
    px.bar(
        curr,
        x="bank",
        y="accuracy",
        color="accuracy",
        color_continuous_scale=["red", "yellow", "green"]
    ),
    use_container_width=True
)

# =====================================================
# TABLE
# =====================================================
st.subheader("📋 MIS Data")
st.dataframe(curr, use_container_width=True)
