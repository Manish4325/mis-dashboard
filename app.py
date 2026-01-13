import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================
# PAGE CONFIG + DARK THEME
# ============================
st.set_page_config(
    page_title="MIS Executive Dashboard",
    layout="wide"
)

st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 MIS Executive Dashboard")
st.caption("Comprehensive MIS view: Volumes • Accuracy • Trends • Performance Quality")

# ============================
# LOAD DATA
# ============================
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
df = df.dropna(subset=["predicted_mules", "confirmed_mules", "accuracy"])

# ============================
# PERFORMANCE BAND
# ============================
def performance_band(acc):
    if acc >= 70:
        return "Good (≥70%)"
    elif acc >= 50:
        return "Medium (50–70%)"
    else:
        return "Poor (<50%)"

df["performance_band"] = df["accuracy"].apply(performance_band)

# ============================
# SIDEBAR FILTERS
# ============================
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

# ============================
# EXECUTIVE KPIs
# ============================
total_pred = int(filtered_df["predicted_mules"].sum())
total_conf = int(filtered_df["confirmed_mules"].sum())
conversion = (total_conf / total_pred * 100) if total_pred > 0 else 0
avg_accuracy = filtered_df["accuracy"].mean()

k1, k2, k3, k4 = st.columns(4)

k1.metric("🔵 Predicted Accounts", f"{total_pred:,}")
k2.metric("🟢 Confirmed Accounts", f"{total_conf:,}")
k3.metric("📈 Conversion Rate", f"{conversion:.2f}%")
k4.metric("🎯 Avg Accuracy", f"{avg_accuracy:.2f}%")

st.divider()

# ============================
# PREDICTED vs CONFIRMED (BANK-WISE)
# ============================
st.subheader("🏦 Bank-wise Predicted vs Confirmed Accounts")

bank_volume = (
    filtered_df
    .groupby("bank_name")[["predicted_mules", "confirmed_mules"]]
    .sum()
    .reset_index()
)

vol_fig = px.bar(
    bank_volume,
    x="bank_name",
    y=["predicted_mules", "confirmed_mules"],
    barmode="group",
    color_discrete_map={
        "predicted_mules": "#1f77b4",
        "confirmed_mules": "#2ca02c"
    }
)

st.plotly_chart(vol_fig, use_container_width=True)

# ============================
# DONUT: OVERALL SPLIT
# ============================
donut_df = pd.DataFrame({
    "Type": ["Confirmed", "Unconfirmed"],
    "Count": [total_conf, total_pred - total_conf]
})

donut_fig = px.pie(
    donut_df,
    values="Count",
    names="Type",
    hole=0.55,
    color_discrete_map={
        "Confirmed": "#2ca02c",
        "Unconfirmed": "#444"
    }
)

st.plotly_chart(donut_fig, use_container_width=True)

# ============================
# PERFORMANCE GAUGE
# ============================
st.subheader("🎯 Overall Model Performance Health")

gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=avg_accuracy,
    number={"suffix": "%"},
    gauge={
        "axis": {"range": [0, 100]},
        "steps": [
            {"range": [0, 50], "color": "#ff4d4d"},
            {"range": [50, 70], "color": "#ffcc00"},
            {"range": [70, 100], "color": "#2ca02c"}
        ]
    }
))

st.plotly_chart(gauge, use_container_width=True)

# ============================
# TREND MIS (MONTH-OVER-MONTH)
# ============================
st.subheader("📅 Month-over-Month Accuracy Trend")

trend_df = (
    filtered_df
    .dropna(subset=["accuracy_date"])
    .sort_values("accuracy_date")
)

trend_fig = px.line(
    trend_df,
    x="accuracy_date",
    y="accuracy",
    color="bank_name",
    markers=True
)

st.plotly_chart(trend_fig, use_container_width=True)

# ============================
# HEATMAP: BANK × MODEL
# ============================
st.subheader("🔥 Bank × Model Accuracy Heatmap")

heat_df = filtered_df.pivot_table(
    index="bank_name",
    columns="model",
    values="accuracy",
    aggfunc="mean"
)

heat_fig = px.imshow(
    heat_df,
    color_continuous_scale=["red", "yellow", "green"],
    aspect="auto"
)

st.plotly_chart(heat_fig, use_container_width=True)

# ============================
# PERFORMANCE BAND DISTRIBUTION
# ============================
st.subheader("📊 Performance Band Distribution")

band_fig = px.bar(
    filtered_df["performance_band"].value_counts().reset_index(),
    x="index",
    y="performance_band",
    color="index",
    color_discrete_map={
        "Good (≥70%)": "green",
        "Medium (50–70%)": "orange",
        "Poor (<50%)": "red"
    }
)

st.plotly_chart(band_fig, use_container_width=True)

# ============================
# FINAL TABLE
# ============================
st.subheader("📋 Detailed MIS Data")
st.dataframe(filtered_df, use_container_width=True)
