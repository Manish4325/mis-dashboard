import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="MIS Reporting Dashboard",
    layout="wide",
)

FILE_PATH = "MIS_REPORTING_CHART.xlsx"
ALERT_THRESHOLD = 40.0

# =====================
# EMAIL CONFIG
# =====================
EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

SENDER_EMAIL = st.secrets["EMAIL_ADDRESS"]
SENDER_PASS = st.secrets["EMAIL_PASSWORD"]

# =====================
# LOAD DATA (SAFE)
# =====================
df = pd.read_excel(FILE_PATH)
df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
)

# ---- column detection ----
def find_col(keywords):
    for col in df.columns:
        for k in keywords:
            if k in col:
                return col
    return None

bank_col = find_col(["bank"])
model_col = find_col(["model"])
predicted_col = find_col(["predicted"])
confirmed_col = find_col(["confirmed", "post review"])
accuracy_col = find_col(["accuracy"])
date_col = find_col(["date"])

# ---- rename safely ----
df = df.rename(columns={
    bank_col: "bank",
    model_col: "model",
    predicted_col: "predicted",
    confirmed_col: "confirmed",
    accuracy_col: "accuracy",
    date_col: "date"
})

# ---- fill missing columns safely ----
for c in ["predicted", "confirmed", "accuracy"]:
    if c not in df.columns:
        df[c] = 0
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =====================
# SIDEBAR FILTER
# =====================
st.sidebar.title("📅 Filters")

dates = sorted(df["date"].dropna().dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)

filtered_df = df[df["date"].dt.date == selected_date]

# =====================
# KPIs (NO CRASH)
# =====================
st.title("📊 MIS Reporting Dashboard")

c1, c2, c3 = st.columns(3)

total_pred = int(filtered_df["predicted"].sum())
total_conf = int(filtered_df["confirmed"].sum())
avg_acc = filtered_df["accuracy"].mean()

c1.metric("Total Predicted Accounts", total_pred)
c2.metric("Total Confirmed Accounts", total_conf)
c3.metric("Average Accuracy", f"{avg_acc:.2f}%")

# =====================
# CRITICAL ALERTS
# =====================
st.markdown("## 🚨 Critical Alerts (Accuracy < 40%)")

alerts = filtered_df[filtered_df["accuracy"] < ALERT_THRESHOLD]

def normalize(bank):
    return bank.lower().replace("bank", "").strip()

def send_email(bank, accuracy):
    key = normalize(bank)
    if key not in EMAIL_MAP:
        return f"No email mapping for {bank}"

    receiver = EMAIL_MAP[key]

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver
    msg["Subject"] = f"Model Performance Alert – {bank}"

    body = f"""
Dear Team,

We have observed that the model accuracy for {bank} has dropped below the acceptable threshold.

Current Accuracy: {accuracy:.2f}%

We request you to review the model performance and initiate retraining if required.
Please reach out to your RBIH SPOC for further guidance.

Regards,
RBIH Model Governance Team
"""
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASS)
    server.send_message(msg)
    server.quit()

    return f"Email sent to {receiver}"

if alerts.empty:
    st.success("✅ No banks below critical threshold")
else:
    st.warning("⚠️ Banks below threshold:")
    st.dataframe(alerts[["bank", "accuracy"]])

    if st.button("📧 Send Alert Emails"):
        for _, r in alerts.iterrows():
            st.write(send_email(r["bank"], r["accuracy"]))

# =====================
# PREDICTED VS CONFIRMED
# =====================
st.markdown("## 🏦 Predicted vs Confirmed Accounts")

bar_df = (
    filtered_df
    .groupby("bank")[["predicted", "confirmed"]]
    .sum()
    .reset_index()
)

fig = px.bar(
    bar_df,
    x="bank",
    y=["predicted", "confirmed"],
    barmode="group",
    color_discrete_sequence=["#00B4D8", "#90DBF4"]
)

st.plotly_chart(fig, use_container_width=True)

# =====================
# PERFORMANCE BANDS
# =====================
st.markdown("## 🎯 Performance Bands")

def band(a):
    if a >= 70: return "High"
    if a >= 50: return "Medium"
    return "Low"

filtered_df["band"] = filtered_df["accuracy"].apply(band)

band_fig = px.pie(
    filtered_df,
    names="band",
    hole=0.5,
    color="band",
    color_discrete_map={
        "High": "#2ECC71",
        "Medium": "#F1C40F",
        "Low": "#E74C3C"
    }
)

st.plotly_chart(band_fig, use_container_width=True)

# =====================
# TREND
# =====================
st.markdown("## 📉 Month-over-Month Accuracy Trend")

trend = (
    df.groupby(df["date"].dt.to_period("M"))["accuracy"]
    .mean()
    .reset_index()
)

trend["date"] = trend["date"].astype(str)

trend_fig = px.line(trend, x="date", y="accuracy", markers=True)
st.plotly_chart(trend_fig, use_container_width=True)

# =====================
# TABLE
# =====================
st.markdown("## 📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
