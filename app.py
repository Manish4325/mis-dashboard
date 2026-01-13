import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =======================
# CONFIG
# =======================
st.set_page_config(
    page_title="MIS Reporting Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

FILE_PATH = "MIS_REPORTING_CHART.xlsx"
ALERT_THRESHOLD = 40.0

EMAIL_MAP = {
    "bandhan": "manishroyalkondeti@gmail.com",
    "hdfc": "manishroyalkondeti43@gmail.com"
}

SENDER_EMAIL = st.secrets["EMAIL_ADDRESS"]
SENDER_PASS = st.secrets["EMAIL_PASSWORD"]

# =======================
# UTILITIES
# =======================
def normalize_bank(name):
    return name.lower().replace("bank", "").strip()

def send_email(bank, accuracy):
    bank_key = normalize_bank(bank)

    if bank_key not in EMAIL_MAP:
        return False, f"No email mapping for {bank}"

    receiver = EMAIL_MAP[bank_key]

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver
    msg["Subject"] = f"Model Performance Alert – {bank}"

    body = f"""
Dear Team,

We have observed that the model accuracy for {bank} has dropped below the acceptable threshold.

Current Accuracy: {accuracy:.2f}%

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

    return True, f"Email sent to {receiver}"

# =======================
# LOAD DATA
# =======================
df = pd.read_excel(FILE_PATH, sheet_name=0)
df.columns = df.columns.str.strip().str.lower()

COLUMN_MAP = {
    "bank name": "bank",
    "model": "model",
    "cummulative number of mule accounts predicted by the model": "predicted",
    "no. of account confirmed as mule (post review/ frozen debit freez)": "confirmed",
    "latest accuracy": "accuracy",
    "date of latest available accuracy": "date"
}

df = df.rename(columns=COLUMN_MAP)

for col in ["predicted", "confirmed", "accuracy"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["date"] = pd.to_datetime(df["date"], errors="coerce")

# =======================
# SIDEBAR
# =======================
st.sidebar.title("📊 Filters")

selected_date = st.sidebar.selectbox(
    "Select Date",
    sorted(df["date"].dropna().dt.date.unique(), reverse=True)
)

filtered_df = df[df["date"].dt.date == selected_date]

# =======================
# HEADER KPIs
# =======================
st.title("📈 MIS Reporting Dashboard")

c1, c2, c3 = st.columns(3)
c1.metric("Total Predicted Accounts", int(filtered_df["predicted"].sum()))
c2.metric("Total Confirmed Accounts", int(filtered_df["confirmed"].sum()))
c3.metric("Avg Accuracy", f"{filtered_df['accuracy'].mean():.2f}%")

# =======================
# CRITICAL ALERTS
# =======================
st.markdown("## 🚨 Critical Alerts (Accuracy < 40%)")

alerts = filtered_df[filtered_df["accuracy"] < ALERT_THRESHOLD]

if alerts.empty:
    st.success("✅ No banks below critical threshold")
else:
    st.warning("The following banks have crossed the risk threshold:")
    st.dataframe(alerts[["bank", "accuracy"]])

    if st.button("📧 Send Alert Emails"):
        results = []
        for _, row in alerts.iterrows():
            success, msg = send_email(row["bank"], row["accuracy"])
            results.append(msg)

        st.success("Email process completed")
        for r in results:
            st.write("•", r)

# =======================
# PREDICTED VS CONFIRMED
# =======================
st.markdown("## 🏦 Predicted vs Confirmed Accounts")

bar_df = (
    filtered_df.groupby("bank")[["predicted", "confirmed"]]
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

# =======================
# ACCURACY PERFORMANCE BAND
# =======================
st.markdown("## 🎯 Model Performance Bands")

def band(acc):
    if acc >= 70:
        return "High"
    elif acc >= 50:
        return "Medium"
    return "Low"

filtered_df["performance"] = filtered_df["accuracy"].apply(band)

band_fig = px.pie(
    filtered_df,
    names="performance",
    hole=0.5,
    color="performance",
    color_discrete_map={
        "High": "#2ECC71",
        "Medium": "#F1C40F",
        "Low": "#E74C3C"
    }
)

st.plotly_chart(band_fig, use_container_width=True)

# =======================
# MONTH-OVER-MONTH TREND
# =======================
st.markdown("## 📉 Accuracy Trend (Month-over-Month)")

trend = (
    df.groupby([df["date"].dt.to_period("M")])["accuracy"]
    .mean()
    .reset_index()
)

trend["date"] = trend["date"].astype(str)

trend_fig = px.line(
    trend,
    x="date",
    y="accuracy",
    markers=True
)

st.plotly_chart(trend_fig, use_container_width=True)

# =======================
# DETAILED TABLE
# =======================
st.markdown("## 📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
