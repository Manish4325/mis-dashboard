import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MIS Reporting Dashboard",
    layout="wide"
)

st.title("📊 MIS Reporting Dashboard")
st.caption("Enterprise MIS view for Mule Account Detection & Monitoring")

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
    "Bank",
    df["bank_name"].unique(),
    default=df["bank_name"].unique()
)

model_filter = st.sidebar.multiselect(
    "Model",
    df["model"].unique(),
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
conversion_rate = (total_conf / total_pred * 100) if total_pred > 0 else 0

k1, k2, k3 = st.columns(3)
k1.metric("🔮 Predicted Mule Accounts", f"{total_pred:,}")
k2.metric("✅ Confirmed Mule Accounts", f"{total_conf:,}")
k3.metric("📈 Conversion Rate", f"{conversion_rate:.2f}%")

st.divider()

# ----------------------------
# DONUT CHART (OVERALL SPLIT)
# ----------------------------
st.subheader("🔄 Predicted vs Confirmed (Overall)")

donut_df = pd.DataFrame({
    "Category": ["Confirmed", "Unconfirmed"],
    "Count": [total_conf, total_pred - total_conf]
})

donut_fig = px.pie(
    donut_df,
    values="Count",
    names="Category",
    hole=0.55
)

st.plotly_chart(donut_fig, use_container_width=True)

# ----------------------------
# STACKED BAR: BANK-WISE
# ----------------------------
st.subheader("🏦 Bank-wise Predicted vs Confirmed Accounts")

bank_summary = (
    filtered_df
    .groupby("bank_name")[["predicted_mules", "confirmed_mules"]]
    .sum()
    .reset_index()
)

stacked_fig = px.bar(
    bank_summary,
    x="bank_name",
    y=["predicted_mules", "confirmed_mules"],
    barmode="group",
    labels={"value": "Accounts", "bank_name": "Bank"}
)

st.plotly_chart(stacked_fig, use_container_width=True)

# ----------------------------
# AI-STYLE INSIGHTS
# ----------------------------
st.subheader("🧠 Key Insights")

top_bank = (
    filtered_df
    .groupby("bank_name")["confirmed_mules"]
    .sum()
    .idxmax()
)

st.markdown(
    f"""
- **{total_pred:,} mule accounts** were predicted across selected filters.
- **{total_conf:,} accounts** were confirmed, resulting in a **conversion rate of {conversion_rate:.2f}%**.
- **{top_bank}** has the **highest number of confirmed mule accounts**.
- Conversion efficiency varies significantly across banks and models, indicating scope for **model fine-tuning**.
"""
)

# ----------------------------
# DOWNLOAD FILTERED DATA
# ----------------------------
st.subheader("📥 Download Filtered Data")

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download CSV",
    data=csv,
    file_name="filtered_mis_data.csv",
    mime="text/csv"
)

# ----------------------------
# DATA TABLE
# ----------------------------
st.subheader("📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
