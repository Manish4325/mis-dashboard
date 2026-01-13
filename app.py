import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="RBIH MIS Reporting Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

FILE_PATH = "MIS_REPORTING_CHART.xlsx"
ALERT_THRESHOLD = 40.0

# =====================================================
# LOGIN SYSTEM
# =====================================================
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "bank": {"password": "bank123", "role": "Bank"}
}

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 Secure Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in USERS and USERS[u]["password"] == p:
            st.session_state.login = True
            st.session_state.role = USERS[u]["role"]
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state.role}")

# =====================================================
# LOAD DATA SAFELY
# =====================================================
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.lower().str.strip()

def find_col(keys):
    for c in df.columns:
        for k in keys:
            if k in c:
                return c
    return None

df = df.rename(columns={
    find_col(["bank"]): "bank",
    find_col(["model"]): "model",
    find_col(["predicted"]): "predicted",
    find_col(["confirmed"]): "confirmed",
    find_col(["accuracy"]): "accuracy",
    find_col(["date"]): "date"
})

# =====================================================
# FORCE CREATE REQUIRED COLUMNS (🔥 FIX)
# =====================================================
REQUIRED_COLUMNS = {
    "predicted": 0,
    "confirmed": 0,
    "accuracy": 0.0,
    "status": "Active",
    "alert_date": pd.NaT
}

for col, default in REQUIRED_COLUMNS.items():
    if col not in df.columns:
        df[col] = default

# Convert types safely
df["predicted"] = pd.to_numeric(df["predicted"], errors="coerce").fillna(0)
df["confirmed"] = pd.to_numeric(df["confirmed"], errors="coerce").fillna(0)
df["accuracy"] = pd.to_numeric(df["accuracy"], errors="coerce").fillna(0)
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =====================================================
# SLA CALCULATION (SAFE)
# =====================================================
today = pd.to_datetime(date.today())
df["sla_days"] = (today - pd.to_datetime(df["alert_date"], errors="coerce")).dt.days
df["sla_days"] = df["sla_days"].fillna(0).astype(int)

# =====================================================
# ADMIN – ADD / UPDATE BANK
# =====================================================
if st.session_state.role == "Admin":
    st.sidebar.markdown("## ➕ Add / Update Bank")
    with st.sidebar.form("add_bank"):
        b = st.text_input("Bank Name")
        m = st.text_input("Model Name")
        p = st.number_input("Predicted", 0)
        c = st.number_input("Confirmed", 0)
        a = st.number_input("Accuracy %", 0.0, 100.0)
        d = st.date_input("Date", datetime.today())
        status = st.selectbox("Model Status", ["Active", "Retrained", "Resolved"])

        submit = st.form_submit_button("Save")
        if submit:
            new_row = {
                "bank": b,
                "model": m,
                "predicted": p,
                "confirmed": c,
                "accuracy": a,
                "date": d,
                "status": status,
                "alert_date": d if a < ALERT_THRESHOLD else pd.NaT
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(FILE_PATH, index=False)
            st.success("Data saved successfully")
            st.rerun()

# =====================================================
# DATE FILTER
# =====================================================
st.sidebar.markdown("## 📅 Date Filter")
dates = sorted(df["date"].dropna().dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)
filtered_df = df[df["date"].dt.date == selected_date]

# =====================================================
# KPIs
# =====================================================
st.title("📊 RBIH MIS Dashboard")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Predicted", int(filtered_df["predicted"].sum()))
k2.metric("Total Confirmed", int(filtered_df["confirmed"].sum()))
k3.metric("Avg Accuracy", f"{filtered_df['accuracy'].mean():.2f}%")
k4.metric("Critical Models", int((filtered_df["accuracy"] < ALERT_THRESHOLD).sum()))

# =====================================================
# EMAIL CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

def normalize_bank(b):
    return b.lower().replace("bank", "").strip()

def send_alert(row):
    key = normalize_bank(row["bank"])
    if key not in EMAIL_MAP:
        return f"No email mapping for {row['bank']}"

    sender = st.secrets["EMAIL_ADDRESS"]
    password = st.secrets["EMAIL_PASSWORD"]
    receiver = EMAIL_MAP[key]
    spoc = st.secrets.get("RBIH_SPOC_EMAIL", "")

    subject = f"⚠️ Model Performance Alert – Accuracy Below Threshold | {row['bank']}"

    body = f"""
Dear {row['bank']} Analytics Team,

As part of RBIH’s continuous model performance monitoring under the MuleHunter.AI program,
we have observed a decline in the performance of one of your deployed models.

📌 Bank Name       : {row['bank']}
📌 Model Name      : {row['model']}
📌 Current Accuracy: {row['accuracy']:.2f}%
📌 Reporting Date  : {row['date'].date()}

⚠️ Observation:
The model accuracy has fallen below the acceptable operational threshold of 40%.
This indicates a degradation in prediction quality and may impact risk detection effectiveness.

🔍 Recommended Actions:
1. Analyze data drift and recent feature distribution changes.
2. Initiate model retraining using the latest validated datasets.
3. Perform post-retraining validation prior to redeployment.
4. Coordinate with your RBIH SPOC for governance guidance and approvals.

📎 Next Steps:
Please acknowledge this alert and share a tentative retraining or remediation plan.

Warm regards,  
RBIH Analytics Governance Team  
Reserve Bank Innovation Hub (RBIH)
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    if spoc:
        msg["Cc"] = spoc
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()

    return f"✅ Alert email sent successfully to {receiver}"


# =====================================================
# ALERTS (🔥 FIXED)
# =====================================================
st.markdown("## 🚨 Critical Alerts & SLA Tracking")

alerts = filtered_df[filtered_df["accuracy"] < ALERT_THRESHOLD]

DISPLAY_COLS = ["bank", "model", "accuracy", "status", "sla_days"]

for col in DISPLAY_COLS:
    if col not in alerts.columns:
        alerts[col] = "N/A"

if alerts.empty:
    st.success("No critical alerts 🎉")
else:
    st.dataframe(alerts[DISPLAY_COLS], use_container_width=True)

    if st.button("📧 Send Alert Emails"):
        for _, r in alerts.iterrows():
            st.success(send_alert(r))

# =====================================================
# VISUALS
# =====================================================
st.markdown("## 🏦 Predicted vs Confirmed")
st.plotly_chart(
    px.bar(
        filtered_df.groupby("bank")[["predicted", "confirmed"]].sum().reset_index(),
        x="bank",
        y=["predicted", "confirmed"],
        barmode="group"
    ),
    use_container_width=True
)

st.markdown("## 🎯 Performance Bands")
filtered_df["band"] = filtered_df["accuracy"].apply(
    lambda x: "High" if x >= 70 else "Medium" if x >= 50 else "Low"
)

st.plotly_chart(px.pie(filtered_df, names="band", hole=0.5),
                use_container_width=True)

st.markdown("## 📉 Month-over-Month Trend")
trend = df.groupby(df["date"].dt.to_period("M"))["accuracy"].mean().reset_index()
trend["date"] = trend["date"].astype(str)
st.plotly_chart(px.line(trend, x="date", y="accuracy", markers=True),
                use_container_width=True)

# =====================================================
# TABLE
# =====================================================
st.markdown("## 📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
