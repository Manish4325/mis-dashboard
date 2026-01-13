import streamlit as st
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date as dt_date

# =================================================
# LOGIN SYSTEM
# =================================================
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

# =================================================
# PAGE CONFIG + DARK THEME
# =================================================
st.set_page_config(page_title="MIS Executive Dashboard", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0b1220; }
[data-testid="stSidebar"] { background-color: #111827; }
h1,h2,h3,h4,h5,h6,p,label { color:#e5e7eb; }
</style>
""", unsafe_allow_html=True)

st.title("📊 MIS Executive Dashboard")
st.caption(f"Logged in as **{st.session_state.role}**")

# =================================================
# LOAD EXCEL (SAFE)
# =================================================
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.astype(str).str.strip()

def find_col(keys):
    for col in df.columns:
        for k in keys:
            if k.lower() in col.lower():
                return col
    return None

# ---- DETECT COLUMNS ----
bank_col = find_col(["bank"])
model_col = find_col(["model"])
pred_col = find_col(["predicted"])
conf_col = find_col(["confirmed"])
acc_col = find_col(["accuracy"])
date_col = find_col(["date"])

# ---- VALIDATE DATE ----
if date_col is None:
    st.error("❌ Date column not found in Excel. Please add a reporting date column.")
    st.stop()

# ---- RENAME ----
df = df.rename(columns={
    bank_col: "bank",
    model_col: "model",
    pred_col: "predicted",
    conf_col: "confirmed",
    acc_col: "accuracy",
    date_col: "date"
})

# ---- CLEAN ----
df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted", "confirmed", "accuracy"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["bank", "accuracy", "date"])

# =================================================
# SESSION STATE (AFTER DATE IS GUARANTEED)
# =================================================
if "data" not in st.session_state:
    st.session_state.data = df.copy()

data = st.session_state.data

# =================================================
# PERFORMANCE BAND
# =================================================
def band(acc):
    if acc >= 70: return "🟢 Good"
    if acc >= 50: return "🟡 Medium"
    return "🔴 Poor"

data["band"] = data["accuracy"].apply(band)

# =================================================
# DATE FILTER (NO KEYERROR POSSIBLE)
# =================================================
st.sidebar.header("📅 Reporting Date")

available_dates = sorted(
    data["date"].dt.date.unique(),
    reverse=True
)

current_date = st.sidebar.selectbox("Select Date", available_dates)
view_df = data[data["date"].dt.date == current_date]

# =================================================
# 🚨 ALERT BANNERS (<40%)
# =================================================
alerts = view_df.groupby("bank")["accuracy"].mean().reset_index()
critical = alerts[alerts["accuracy"] < 40]

if not critical.empty:
    for _, r in critical.iterrows():
        st.error(f"🚨 {r['bank']} accuracy dropped to {r['accuracy']:.2f}%")
else:
    st.success("✅ No critical alerts for this date")

# =================================================
# KPI CARDS
# =================================================
k1, k2, k3 = st.columns(3)
k1.metric("Predicted", int(view_df["predicted"].sum()))
k2.metric("Confirmed", int(view_df["confirmed"].sum()))
k3.metric("Avg Accuracy", f"{view_df['accuracy'].mean():.2f}%")

st.divider()

# =================================================
# VISUALS
# =================================================
st.subheader("🏦 Predicted vs Confirmed")

bank_sum = view_df.groupby("bank")[["predicted","confirmed"]].sum().reset_index()

st.plotly_chart(
    px.bar(
        bank_sum,
        x="bank",
        y=["predicted","confirmed"],
        barmode="group"
    ),
    use_container_width=True
)

st.subheader("📊 Performance Distribution")

band_df = view_df["band"].value_counts().reset_index()
band_df.columns = ["Band","Count"]

st.plotly_chart(
    px.bar(band_df, x="Band", y="Count", color="Band"),
    use_container_width=True
)

st.subheader("🔥 Bank × Model Accuracy Heatmap")

heat = view_df.pivot_table(
    index="bank",
    columns="model",
    values="accuracy",
    aggfunc="mean"
)

st.plotly_chart(px.imshow(heat, aspect="auto"), use_container_width=True)

# =================================================
# ADMIN ADD DATA
# =================================================
if st.session_state.role == "Admin":
    st.sidebar.header("➕ Add Bank Data")

    with st.sidebar.form("add"):
        b = st.text_input("Bank")
        m = st.text_input("Model")
        p = st.number_input("Predicted", 0)
        c = st.number_input("Confirmed", 0)
        a = st.number_input("Accuracy", 0.0, 100.0)
        d = st.date_input("Date", dt_date.today())

        if st.form_submit_button("Add"):
            st.session_state.data = pd.concat([
                st.session_state.data,
                pd.DataFrame([{
                    "bank": b,
                    "model": m,
                    "predicted": p,
                    "confirmed": c,
                    "accuracy": a,
                    "date": pd.to_datetime(d),
                    "band": band(a)
                }])
            ], ignore_index=True)
            st.success("Data added (session only)")

# =================================================
# TABLE
# =================================================
st.subheader("📋 MIS Data")
st.dataframe(view_df, use_container_width=True)
