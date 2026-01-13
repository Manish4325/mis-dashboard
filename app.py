import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# =====================================================
# LOGIN
# =====================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

def login():
    st.title("🔐 MIS Secure Login")
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

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config("MIS Dashboard", layout="wide")
st.title("📊 MIS Executive Dashboard")
st.caption(f"Logged in as **{st.session_state.role}**")

# =====================================================
# LOAD DATA (100% SAFE)
# =====================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip().str.lower()

# ---- COLUMN NORMALIZATION ----
COLUMN_MAP = {
    "bank": ["bank", "bank name"],
    "model": ["model"],
    "predicted": ["predicted"],
    "confirmed": ["confirmed"],
    "accuracy": ["accuracy"],
    "date": ["date"]
}

def find_col(possible):
    for col in df.columns:
        for p in possible:
            if p in col:
                return col
    return None

resolved = {}
for k, v in COLUMN_MAP.items():
    resolved[k] = find_col(v)

# ---- RENAME SAFELY ----
for k, v in resolved.items():
    if v:
        df.rename(columns={v: k}, inplace=True)

# ---- FORCE DATE ----
if "date" not in df.columns:
    df["date"] = pd.to_datetime(date.today())

# ---- CLEAN ----
df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# 🔥 FIX: convert only existing columns
for c in ["predicted", "confirmed", "accuracy"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    else:
        df[c] = 0   # safe default

df.dropna(subset=["bank", "accuracy", "date"], inplace=True)

# =====================================================
# DATE FILTER
# =====================================================
st.sidebar.header("📅 Date Filter")

dates = sorted(df["date"].dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)

curr = df[df["date"].dt.date == selected_date]

# =====================================================
# KPI
# =====================================================
k1, k2, k3 = st.columns(3)

k1.metric("Predicted Accounts", int(curr["predicted"].sum()))
k2.metric("Confirmed Accounts", int(curr["confirmed"].sum()))
k3.metric("Avg Accuracy", f"{curr['accuracy'].mean():.2f}%")

# =====================================================
# EMAIL ALERT CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

SENDER_EMAIL = st.secrets["EMAIL_ADDRESS"]
SENDER_PASS = st.secrets["EMAIL_PASSWORD"]

if "email_log" not in st.session_state:
    st.session_state.email_log = {}

def send_email(bank, acc):
    key = bank.lower()
    if key not in EMAIL_MAP:
        return False

    if st.session_state.email_log.get(key) == date.today():
        return False

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = EMAIL_MAP[key]
    msg["Subject"] = f"Model Performance Alert – {bank.title()}"

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

    st.session_state.email_log[key] = date.today()
    return True

# =====================================================
# ALERTS
# =====================================================
st.subheader("🚨 Critical Alerts (Accuracy < 40%)")

alerts = curr.groupby("bank")["accuracy"].mean().reset_index()
critical = alerts[alerts["accuracy"] < 40]

if critical.empty:
    st.success("No banks below 40% accuracy")
else:
    for _, r in critical.iterrows():
        st.error(f"{r['bank']} accuracy dropped to {r['accuracy']:.2f}%")
        if send_email(r["bank"], r["accuracy"]):
            st.info(f"📧 Email sent to {r['bank']} SPOC")

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
