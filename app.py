import streamlit as st
import pandas as pd

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MIS Reporting Dashboard",
    layout="wide"
)

st.title("📊 MIS Reporting Dashboard")
st.caption("Interactive MIS view for Mule Account Detection")

# ----------------------------
# LOAD DATA
# ----------------------------
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.astype(str).str.strip()

df = df.rename(columns={
    "Bank name": "bank_name",
    "Model": "model",
    "Cummulative number of mule accounts predicted by the model": "predicted_mules",
    "No. of Account confirmed as Mule (Post Review/ Frozen Debit Freez)": "confirmed_mules",
    "Latest accuracy": "accuracy",
    "Date of latest available accuracy": "accuracy_date"
})

df["bank_name"] = df["bank_name"].ffill()

for col in ["predicted_mules", "confirmed_mules", "accuracy"]:
    df[col] = (
        df[col].astype(str)
        .str.replace(",", "", regex=False)
    )
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["accuracy_date"] = pd.to_datetime(df["accuracy_date"], errors="coerce")

df = df.dropna(subset=["predicted_mules", "confirmed_mules"])

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔎 Filters")

bank_filter = st.sidebar.multiselect(
    "Select Bank(s)",
    options=df["bank_name"].unique(),
    default=df["bank_name"].unique()
)

model_filter = st.sidebar.multiselect(
    "Select Model(s)",
    options=df["model"].unique(),
    default=df["model"].unique()
)

filtered_df = df[
    (df["bank_name"].isin(bank_filter)) &
    (df["model"].isin(model_filter))
]

# ----------------------------
# KPIs
# ----------------------------
total_pred = int(filtered_df["predicted_mules"].sum())
total_conf = int(filtered_df["confirmed_mules"].sum())

conversion_rate = (
    (total_conf / total_pred) * 100
    if total_pred > 0 else 0
)

k1, k2, k3 = st.columns(3)

k1.metric("🔮 Predicted Mule Accounts", total_pred)
k2.metric("✅ Confirmed Mule Accounts", total_conf)
k3.metric("📈 Conversion Rate", f"{conversion_rate:.2f}%")

st.divider()

# ----------------------------
# CHART 1: BANK-WISE COMPARISON
# ----------------------------
st.subheader("🏦 Bank-wise Predicted vs Confirmed Accounts")

bank_summary = (
    filtered_df
    .groupby("bank_name")[["predicted_mules", "confirmed_mules"]]
    .sum()
    .sort_values(by="predicted_mules", ascending=False)
)

st.bar_chart(bank_summary)

# ----------------------------
# CHART 2: MODEL PERFORMANCE
# ----------------------------
st.subheader("🤖 Model-wise Performance")

model_summary = (
    filtered_df
    .groupby("model")[["predicted_mules", "confirmed_mules"]]
    .sum()
)

st.bar_chart(model_summary)

# ----------------------------
# CHART 3: ACCURACY TREND
# ----------------------------
st.subheader("📅 Accuracy Trend Over Time")

accuracy_trend = (
    filtered_df
    .dropna(subset=["accuracy_date", "accuracy"])
    .sort_values("accuracy_date")
)

if not accuracy_trend.empty:
    st.line_chart(
        accuracy_trend.set_index("accuracy_date")["accuracy"]
    )
else:
    st.info("No accuracy trend data available for selected filters.")

# ----------------------------
# TOP BANKS
# ----------------------------
st.subheader("🏆 Top 5 Banks by Confirmed Mule Accounts")

top_banks = (
    filtered_df
    .groupby("bank_name")["confirmed_mules"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)

st.table(top_banks)

# ----------------------------
# DATA TABLE
# ----------------------------
st.subheader("📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
