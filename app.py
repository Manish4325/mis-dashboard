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
# LOAD DATA (SAFE)
# =====================================================
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.str.strip().str.lower()

COLUMN_MAP = {
    "bank": ["bank"],
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

for k, v in COLUMN_MAP.items():
    col = find_col(v)
    if col:
        df.rename(columns={col: k}, inplace=True)

if "date" not in df.columns:
    df["date"] = pd.to_datetime(date.today())

df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted", "confirmed", "accuracy"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df.dropna(subset=["bank", "accuracy", "date"], inplace=True)

data = df.copy()

# =====================================================
# DATE FILTER + MoM COMPARISON
# =====================================================
st.sidebar.header("📅 Date Selection")
dates = sorted(data["date"].dt.date.unique(), reverse=True)

current_date = st.sidebar.selectbox("Current Date", dates)
prev_date = st.sidebar.selectbox(
    "Compare With (MoM)",
    dates[1:] if len(dates) > 1 else dates
)

curr = data[data["date"].dt.date == current_date]
prev = data[data["date"].dt.date == prev_date]

# =====================================================
# KPI + MoM CHANGE
# =====================================================
def arrow(c, p):
    return "🔺" if c > p else "🔻" if c < p else "⏸"

c1, c2, c3 = st.columns(3)

c1.metric(
    "Average Accuracy",
    f"{curr['accuracy'].mean():.2f}%",
    arrow(curr["accuracy"].mean(), prev["accuracy"].mean())
)

c2.metric(
    "Predicted Accounts",
    int(curr["predicted"].sum()),
    arrow(curr["predicted"].sum(), prev["predicted"].sum())
)

c3.metric(
    "Confirmed Accounts",
    int(curr["confirmed"].sum()),
    arrow(curr["confirmed"].sum(), prev["confirmed"].sum())
)

# =====================================================
# 🚨 ALERTS + EMAIL
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

def send_email(bank, acc, to_email):
    msg = MIMEMultipart()
    msg["From"] = st.secrets["EMAIL_ADDRESS"]
    msg["To"] = to_email
    msg["Subject"] = f"Model Performance Alert – {bank.title()}"

    body = f"""
Dear Team,

We have observed that the model accuracy for {bank.title()} Bank has dropped below the acceptable threshold.

Current Accuracy: {acc:.2f}%

We kindly request you to review the model performance and initiate retraining if required.
Please reach out to your RBIH SPOC for guidance on next steps.

Warm regards,
RBIH Model Governance Team
"""
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(
        st.secrets["EMAIL_ADDRESS"],
        st.secrets["EMAIL_PASSWORD"]
    )
    server.send_message(msg)
    server.quit()

alerts = curr.groupby("bank")["accuracy"].mean().reset_index()
critical = alerts[alerts["accuracy"] < 40]

st.subheader("🚨 Critical Performance Alerts")

if not critical.empty:
    for _, r in critical.iterrows():
        st.error(f"{r['bank']} accuracy dropped to {r['accuracy']:.2f}%")
        bank_key = r["bank"].lower()
        if bank_key in EMAIL_MAP:
            send_email(bank_key, r["accuracy"], EMAIL_MAP[bank_key])
else:
    st.success("No banks below 40% accuracy")

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
