import streamlit as st
import pandas as pd

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="MIS Dashboard", layout="wide")
st.title("📊 MIS Reporting Dashboard")

# -----------------------------
# LOAD EXCEL
# -----------------------------
FILE_PATH = "/content/MIS_REPORTING_CHART.xlsx"

df = pd.read_excel(FILE_PATH, sheet_name=0)

# -----------------------------
# CLEAN COLUMN NAMES
# -----------------------------
df.columns = df.columns.astype(str).str.strip()

# -----------------------------
# RENAME USING EXACT EXCEL HEADERS
# -----------------------------
COLUMN_MAP = {
    "Bank name": "bank_name",
    "Model": "model",
    "Cummulative number of mule accounts predicted by the model": "predicted_mules",
    "No. of Account confirmed as Mule (Post Review/ Frozen Debit Freez)": "confirmed_mules",
    "Latest accuracy": "latest_accuracy",
    "Date of latest available accuracy": "accuracy_date"
}

for old, new in COLUMN_MAP.items():
    if old in df.columns:
        df = df.rename(columns={old: new})

# -----------------------------
# VALIDATE REQUIRED COLUMNS
# -----------------------------
required_cols = ["bank_name", "predicted_mules", "confirmed_mules"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error("❌ Required columns missing in Excel:")
    for m in missing:
        st.write("-", m)
    st.stop()

# -----------------------------
# FIX BANK NAME NULLS
# -----------------------------
df["bank_name"] = df["bank_name"].ffill()

# -----------------------------
# FORCE NUMERIC CONVERSION (NO TYPE ERROR)
# -----------------------------
for col in ["predicted_mules", "confirmed_mules"]:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove bad rows
df = df.dropna(subset=["predicted_mules", "confirmed_mules"])

# -----------------------------
# KPIs
# -----------------------------
total_predicted = int(df["predicted_mules"].sum())
total_confirmed = int(df["confirmed_mules"].sum())

# -----------------------------
# KPI DISPLAY
# -----------------------------
c1, c2 = st.columns(2)
c1.metric("🔮 Total Predicted Mule Accounts", total_predicted)
c2.metric("✅ Total Confirmed Mule Accounts", total_confirmed)

# -----------------------------
# BANK-WISE CHART
# -----------------------------
st.subheader("🏦 Bank-wise Predicted Mule Accounts")

bank_chart = (
    df.groupby("bank_name", as_index=False)["predicted_mules"]
    .sum()
    .sort_values(by="predicted_mules", ascending=False)
)

st.bar_chart(bank_chart.set_index("bank_name"))

# -----------------------------
# DATA TABLE
# -----------------------------
st.subheader("📋 Detailed MIS Data")
st.dataframe(df)
