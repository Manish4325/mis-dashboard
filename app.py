import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =====================================================
# PAGE CONFIG + THEME
# =====================================================
st.set_page_config(
    page_title="RBIH MIS Reporting Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
body { background-color: #0e1117; color: white; }
</style>
""", unsafe_allow_html=True)

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
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state.role}")

# =====================================================
# LOAD & NORMALIZE DATA (NO ERRORS EVER)
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

for col in ["predicted", "confirmed", "accuracy"]:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =====================================================
# ADD / UPDATE BANK (ADMIN)
# =====================================================
if st.session_state.role == "Admin":
    st.sidebar.markdown("## ➕ Add / Update Bank Data")
    with st.sidebar.form("add_bank"):
        b = st.text_input("Bank Name")
        m = st.text_input("Model Name")
        p = st.number_input("Predicted Mule Accounts", min_value=0)
        c = st.number_input("Confirmed Mule Accounts", min_value=0)
        a = st.number_input("Accuracy (%)", min_value=0.0, max_value=100.0)
        d = st.date_input("Reporting Date", datetime.today())
        submit = st.form_submit_button("Save Data")

        if submit:
            new_row = pd.DataFrame([{
                "bank": b,
                "model": m,
                "predicted": p,
                "confirmed": c,
                "accuracy": a,
                "date": d
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel(FILE_PATH, index=False)
            st.success("Bank data saved successfully")
            st.rerun()

# =====================================================
# FILTERS
# =====================================================
st.sidebar.markdown("## 📅 Date Filter")
dates = sorted(df["date"].dropna().dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)
filtered_df = df[df["date"].dt.date == selected_date]

# =====================================================
# KPIs
# =====================================================
st.title("📊 RBIH MIS Dashboard")

k1, k2, k3 = st.columns(3)
k1.metric("Total Predicted Accounts", int(filtered_df["predicted"].sum()))
k2.metric("Total Confirmed Accounts", int(filtered_df["confirmed"].sum()))
k3.metric("Average Accuracy", f"{filtered_df['accuracy'].mean():.2f}%")

# =====================================================
# EMAIL ALERT CONFIG
# =====================================================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

def normalize_bank(name):
    return name.lower().replace("bank", "").strip()

def send_alert(bank, model, acc, date):
    key = normalize_bank(bank)
    if key not in EMAIL_MAP:
        return f"No email mapping for {bank}"

    sender = st.secrets["EMAIL_ADDRESS"]
    password = st.secrets["EMAIL_PASSWORD"]
    receiver = EMAIL_MAP[key]

    subject = f"⚠️ Model Performance Alert – Accuracy Below Threshold | {bank}"

    body = f"""
Dear {bank} Analytics Team,

As part of RBIH’s continuous model performance monitoring under the MuleHunter.AI program,
we have observed a decline in the performance of one of your deployed models.

📌 Bank Name       : {bank}
📌 Model Name      : {model}
📌 Current Accuracy: {acc:.2f}%
📌 Reporting Date  : {date}

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
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()

    return f"Email sent to {receiver}"

# =====================================================
# CRITICAL ALERTS + BUTTON
# =====================================================
st.markdown("## 🚨 Critical Alerts (Accuracy < 40%)")

alerts = filtered_df[filtered_df["accuracy"] < ALERT_THRESHOLD]

if alerts.empty:
    st.success("✅ No banks below critical threshold")
else:
    st.warning("⚠️ Banks requiring immediate attention")
    st.dataframe(alerts[["bank", "model", "accuracy"]], use_container_width=True)

    if st.button("📧 Send Alert Emails"):
        for _, r in alerts.iterrows():
            msg = send_alert(
                bank=r["bank"],
                model=r["model"],
                acc=r["accuracy"],
                date=r["date"].date()
            )
            st.success(msg)

# =====================================================
# VISUALS
# =====================================================
st.markdown("## 🏦 Predicted vs Confirmed Accounts")
fig1 = px.bar(
    filtered_df.groupby("bank")[["predicted", "confirmed"]].sum().reset_index(),
    x="bank",
    y=["predicted", "confirmed"],
    barmode="group",
    color_discrete_sequence=["#00B4D8", "#90DBF4"]
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("## 🎯 Model Performance Bands")
filtered_df["performance_band"] = filtered_df["accuracy"].apply(
    lambda x: "High" if x >= 70 else "Medium" if x >= 50 else "Low"
)

fig2 = px.pie(
    filtered_df,
    names="performance_band",
    hole=0.5,
    color="performance_band",
    color_discrete_map={
        "High": "#2ECC71",
        "Medium": "#F1C40F",
        "Low": "#E74C3C"
    }
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("## 📉 Month-over-Month Accuracy Trend")
trend = df.groupby(df["date"].dt.to_period("M"))["accuracy"].mean().reset_index()
trend["date"] = trend["date"].astype(str)

fig3 = px.line(trend, x="date", y="accuracy", markers=True)
st.plotly_chart(fig3, use_container_width=True)

# =====================================================
# DATA TABLE
# =====================================================
st.markdown("## 📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
