import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, date
import os

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

for c in ["predicted", "confirmed", "accuracy"]:
    if c not in df.columns:
        df[c] = 0
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =====================================================
# ADD STATUS + SLA TRACKING
# =====================================================
if "status" not in df.columns:
    df["status"] = "Active"

if "alert_date" not in df.columns:
    df["alert_date"] = pd.NaT

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
            new = pd.DataFrame([{
                "bank": b,
                "model": m,
                "predicted": p,
                "confirmed": c,
                "accuracy": a,
                "date": d,
                "status": status,
                "alert_date": d if a < ALERT_THRESHOLD else pd.NaT
            }])
            df = pd.concat([df, new], ignore_index=True)
            df.to_excel(FILE_PATH, index=False)
            st.success("Data saved")
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
# SLA CALCULATION
# =====================================================
today = pd.to_datetime(date.today())
df["sla_days"] = (today - df["alert_date"]).dt.days

# =====================================================
# EMAIL CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

def normalize_bank(b):
    return b.lower().replace("bank", "").strip()

def generate_pdf(row):
    file_name = f"MIS_{row['bank']}_{row['model']}.pdf"
    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()
    content = []

    for k, v in row.items():
        content.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    doc.build(content)
    return file_name

def send_alert(row):
    key = normalize_bank(row["bank"])
    if key not in EMAIL_MAP:
        return f"No email mapping for {row['bank']}"

    pdf_file = generate_pdf(row)

    msg = MIMEMultipart()
    msg["From"] = st.secrets["EMAIL_ADDRESS"]
    msg["To"] = EMAIL_MAP[key]
    msg["Cc"] = st.secrets["RBIH_SPOC_EMAIL"]
    msg["Subject"] = f"⚠️ Model Performance Alert | {row['bank']}"

    body = f"""
Dear {row['bank']} Analytics Team,

We observed that the following model is underperforming:

Bank        : {row['bank']}
Model       : {row['model']}
Accuracy    : {row['accuracy']}%
Status      : {row['status']}
SLA Days    : {row['sla_days']}

Recommended Actions:
• Analyze data drift
• Retrain model
• Validate performance
• Coordinate with RBIH SPOC

Regards,
RBIH Analytics Governance Team
"""
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
    server.send_message(msg)
    server.quit()

    os.remove(pdf_file)
    return f"Email + PDF sent for {row['bank']}"

# =====================================================
# ALERTS
# =====================================================
st.markdown("## 🚨 Critical Alerts & SLA Tracking")

alerts = filtered_df[filtered_df["accuracy"] < ALERT_THRESHOLD]

if alerts.empty:
    st.success("No critical alerts 🎉")
else:
    st.dataframe(
        alerts[["bank", "model", "accuracy", "status", "sla_days"]],
        use_container_width=True
    )

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

st.plotly_chart(
    px.pie(filtered_df, names="band", hole=0.5),
    use_container_width=True
)

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
