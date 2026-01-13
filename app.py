import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# =====================================================
# HARD RESET SESSION (PREVENT STALE DATA BUG)
# =====================================================
if "data" in st.session_state:
    del st.session_state["data"]

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
# LOAD EXCEL (100% SAFE)
# =====================================================
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.str.strip().str.lower()

# --- COLUMN NORMALIZATION ---
COLUMN_MAP = {
    "bank": ["bank", "bank name"],
    "model": ["model"],
    "predicted": ["predicted"],
    "confirmed": ["confirmed"],
    "accuracy": ["accuracy"],
    "date": ["date", "reporting date"]
}

def resolve(col_list):
    for c in df.columns:
        for k in col_list:
            if k in c:
                return c
    return None

resolved = {}
for key, values in COLUMN_MAP.items():
    resolved[key] = resolve(values)

# --- FORCE DATE COLUMN ---
if resolved["date"] is None:
    st.warning("⚠️ Date column missing. Using today's date.")
    df["date"] = pd.to_datetime(date.today())
else:
    df.rename(columns={resolved["date"]: "date"}, inplace=True)

# --- RENAME OTHERS ---
for k in ["bank", "model", "predicted", "confirmed", "accuracy"]:
    if resolved[k]:
        df.rename(columns={resolved[k]: k}, inplace=True
        )

# --- CLEAN ---
df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted", "confirmed", "accuracy"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df.dropna(subset=["bank", "accuracy", "date"], inplace=True)

# =====================================================
# SESSION STATE (SAFE INITIALIZATION)
# =====================================================
st.session_state.data = df.copy()
data = st.session_state.data

# =====================================================
# DATE FILTER (KEYERROR-PROOF)
# =====================================================
st.sidebar.header("📅 Reporting Date")

available_dates = sorted(
    data["date"].astype("datetime64[ns]").dt.date.unique(),
    reverse=True
)

selected_date = st.sidebar.selectbox("Select Date", available_dates)
view_df = data[data["date"].dt.date == selected_date]

# =====================================================
# KPIs
# =====================================================
c1, c2, c3 = st.columns(3)
c1.metric("Predicted Accounts", int(view_df["predicted"].sum()))
c2.metric("Confirmed Accounts", int(view_df["confirmed"].sum()))
c3.metric("Average Accuracy", f"{view_df['accuracy'].mean():.2f}%")

st.divider()

# =====================================================
# VISUALS
# =====================================================
st.subheader("🏦 Predicted vs Confirmed (Bank-wise)")

bank_summary = view_df.groupby("bank")[["predicted", "confirmed"]].sum().reset_index()

st.plotly_chart(
    px.bar(
        bank_summary,
        x="bank",
        y=["predicted", "confirmed"],
        barmode="group",
        color_discrete_map={
            "predicted": "#3b82f6",
            "confirmed": "#22c55e"
        }
    ),
    use_container_width=True
)

st.subheader("📊 Bank Accuracy Distribution")

st.plotly_chart(
    px.bar(
        view_df,
        x="bank",
        y="accuracy",
        color="accuracy",
        color_continuous_scale=["red", "yellow", "green"]
    ),
    use_container_width=True
)

# =====================================================
# ADMIN ADD DATA
# =====================================================
if st.session_state.role == "Admin":
    st.sidebar.header("➕ Add Bank Record")

    with st.sidebar.form("add"):
        b = st.text_input("Bank Name")
        m = st.text_input("Model")
        p = st.number_input("Predicted", 0)
        c = st.number_input("Confirmed", 0)
        a = st.number_input("Accuracy", 0.0, 100.0)
        d = st.date_input("Date", date.today())

        if st.form_submit_button("Add"):
            new_row = {
                "bank": b,
                "model": m,
                "predicted": p,
                "confirmed": c,
                "accuracy": a,
                "date": pd.to_datetime(d)
            }
            st.session_state.data = pd.concat(
                [st.session_state.data, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.success("Data added successfully")

# =====================================================
# DATA TABLE
# =====================================================
st.subheader("📋 MIS Data")
st.dataframe(view_df, use_container_width=True)
