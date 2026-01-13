import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="MIS Reporting Dashboard", layout="wide")

st.title("📊 MIS Reporting Dashboard")
st.caption("Enterprise MIS & Risk Monitoring for Mule Account Detection")

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
# BANK-LEVEL RISK CALCULATION
# ----------------------------
risk_df = (
    filtered_df
    .groupby("bank_name")[["predicted_mules", "confirmed_mules"]]
    .sum()
    .reset_index()
)

risk_df["conversion_rate"] = (
    risk_df["confirmed_mules"] / risk_df["predicted_mules"] * 100
)

def assign_risk(rate):
    if rate >= 70:
        return "🚨 High Risk"
    elif rate >= 40:
        return "⚠️ Medium Risk"
    else:
        return "✅ Low Risk"

risk_df["risk_level"] = risk_df["conversion_rate"].apply(assign_risk)

# ----------------------------
# RISK DISTRIBUTION CHART
# ----------------------------
st.subheader("🚦 Bank Risk Distribution")

risk_count = risk_df["risk_level"].value_counts().reset_index()
risk_count.columns = ["Risk Level", "Number of Banks"]

risk_fig = px.bar(
    risk_count,
    x="Risk Level",
    y="Number of Banks",
    color="Risk Level",
    color_discrete_map={
        "🚨 High Risk": "red",
        "⚠️ Medium Risk": "orange",
        "✅ Low Risk": "green"
    }
)

st.plotly_chart(risk_fig, use_container_width=True)

# ----------------------------
# BANK-WISE RISK TABLE
# ----------------------------
st.subheader("🏦 Bank-wise Risk Assessment")

risk_display = risk_df.sort_values(
    by="conversion_rate", ascending=False
)

st.dataframe(
    risk_display[[
        "bank_name",
        "predicted_mules",
        "confirmed_mules",
        "conversion_rate",
        "risk_level"
    ]],
    use_container_width=True
)

# ----------------------------
# MANAGEMENT INSIGHTS
# ----------------------------
st.subheader("🧠 Risk Insights for Management")

high_risk_banks = risk_df[risk_df["risk_level"] == "🚨 High Risk"]

st.markdown(
    f"""
- **{len(high_risk_banks)} bank(s)** fall under **High Risk**, requiring immediate attention.
- High-risk banks show **very high confirmation rates**, indicating strong mule concentration.
- Medium-risk banks may benefit from **model threshold tuning**.
- Low-risk banks indicate **healthy detection-to-confirmation balance**.
"""
)

# ----------------------------
# DOWNLOAD
# ----------------------------
st.subheader("📥 Download Risk Assessment")

csv = risk_display.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download Risk Report (CSV)",
    csv,
    "bank_risk_assessment.csv",
    "text/csv"
)
