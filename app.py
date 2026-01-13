import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime

# =====================================================
# LOGIN SYSTEM
# =====================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

def login():
    st.title("🔐 MIS Secure Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.session_state.role = "Admin"
        elif username == "viewer" and password == "viewer123":
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
st.set_page_config(page_title="MIS Executive Dashboard", layout="wide")
st.title("📊 MIS Executive Dashboard")
st.caption(f"Logged in as **{st.session_state.role}**")

# =====================================================
# LOAD DATA (SAFE)
# =====================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"

df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip().str.lower()

df.rename(columns={
    "bank name": "bank",
    "model": "model",
    "predicted": "predicted",
    "confirmed": "confirmed",
    "accuracy": "accuracy",
    "date": "date"
}, inplace=True)

# Ensure date exists
if "date" not in df.columns:
    df["date"] = pd.to_datetime(date.today())

df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted", "confirmed", "accuracy"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df.dropna(subset=["bank", "accuracy", "date"], inplace=True)

# =====================================================
# DATE FILTER + MONTH-OVER-MONTH
# =====================================================
st.sidebar.header("📅 Date Selection")

dates = sorted(df["date"].dt.date.unique(), reverse=True)

current_date = st.sidebar.selectbox("Current Date", dates)
previous_date = (
    st.sidebar.selectbox("Compare With (MoM)", dates[1:])
    if len(dates) > 1 else current_date
)

curr = df[df["date"].dt.date == current_date]
prev = df[df["date"].dt.date == previous_date]

# =====================================================
# KPI + MoM TREND
# =====================================================
def arrow(c, p):
    return "🔺" if c > p else "🔻" if c < p else "⏸"

k1, k2, k3 = st.columns(3)

k1.metric(
    "Average Accuracy",
    f"{curr['accuracy'].mean():.2f}%",
    arrow(curr["accuracy"].mean(), prev["accuracy"].mean())
)

k2.metric(
    "Predicted Accounts",
    int(curr["predicted"].sum()),
    arrow(curr["predicted"].sum(), prev["predicted"].sum())
)

k3.metric(
    "Confirmed Accounts",
    int(curr["confirmed"].sum()),
    arrow(curr["confirmed"].sum(), prev["confirmed"].sum())
)

# =====================================================
# EMAIL ALERT CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

SENDER_EMAIL = st.secrets["EMAIL_ADDRESS"]
SENDER_PASS = st.secrets["EMAIL_PASSWORD"]

# Email cooldown (1 email per bank per day)
if "email_log" not in st.session_state:
    st.session_state.email_log = {}

def email_sent_today(bank):
    return st.session_state.email_log.get(bank) == date.today()

def mark_email_sent(bank):
    st.session_state.email_log[bank] = date.today()

def send_email(bank, acc):
    bank_key = bank.lower()
    if bank_key not in EMAIL_MAP:
        return False
    if email_sent_today(bank_key):
        return False

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = EMAIL_MAP[bank_key]
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

    mark_email_sent(bank_key)
    return True

# =====================================================
# 🚨 ALERT BANNERS + EMAIL SEND
# =====================================================
st.subheader("🚨 Critical Performance Alerts (Accuracy < 40%)")

alerts = curr.groupby("bank")["accuracy"].mean().reset_index()
critical = alerts[alerts["accuracy"] < 40]

if critical.empty:
    st.success("✅ No banks below 40% accuracy")
else:
    for _, r in critical.iterrows():
        st.error(f"{r['bank']} accuracy dropped to {r['accuracy']:.2f}%")
        if send_email(r["bank"], r["accuracy"]):
            st.info(f"📧 Email sent to {r['bank']} SPOC")

# =====================================================
# VISUALS
# =====================================================
st.subheader("🏦 Predicted vs Confirmed (Bank-wise)")

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
# DATA TABLE
# =====================================================
st.subheader("📋 MIS Data")
st.dataframe(curr, use_container_width=True)
