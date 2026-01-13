import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MIS Model Performance Dashboard",
    layout="wide"
)

st.title("📊 MIS Model Performance Dashboard")
st.caption("Executive view of Model Accuracy & Performance Quality")

# ----------------------------
# LOAD DATA
# ----------------------------
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.astype(str).str.strip()

df = df.rename(columns={
    "Bank name": "bank_name",
    "Model": "model",
    "Latest accuracy": "accuracy"
})

df["bank_name"] = df["bank_name"].ffill()
df["accuracy"] = pd.to_numeric(df["accuracy"], errors="coerce")
df = df.dropna(subset=["accuracy"])

# ----------------------------
# PERFORMANCE BAND
# ----------------------------
def performance_band(acc):
    if acc >= 70:
        return "🟢 Good Performance"
    elif acc >= 50:
        return "🟡 Medium Performance"
    else:
        return "🔴 Poor Performance"

df["performance_band"] = df["accuracy"].apply(performance_band)

# ----------------------------
# SIDEBAR FILTER
# ----------------------------
st.sidebar.header("🔎 Filters")

bank_filter = st.sidebar.multiselect(
    "Select Bank(s)",
    df["bank_name"].unique(),
    default=df["bank_name"].unique()
)

filtered_df = df[df["bank_name"].isin(bank_filter)]

# ----------------------------
# KPI CARDS
# ----------------------------
avg_accuracy = filtered_df["accuracy"].mean()

k1, k2, k3 = st.columns(3)

k1.metric("📈 Average Accuracy", f"{avg_accuracy:.2f}%")
k2.metric("🟢 Good Models", (filtered_df["accuracy"] >= 70).sum())
k3.metric("🔴 Poor Models", (filtered_df["accuracy"] < 50).sum())

st.divider()

# ============================
# 1️⃣ GAUGE CHART (OVERALL HEALTH)
# ============================
st.subheader("🎯 Overall Model Performance Health")

gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=avg_accuracy,
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": "white"},
        "steps": [
            {"range": [0, 50], "color": "#ff4d4d"},
            {"range": [50, 70], "color": "#ffcc00"},
            {"range": [70, 100], "color": "#4CAF50"}
        ]
    },
    number={"suffix": "%"}
))

st.plotly_chart(gauge, use_container_width=True)

# ============================
# 2️⃣ LOLLIPOP CHART (BANK RANKING)
# ============================
st.subheader("🏦 Bank-wise Model Accuracy Ranking")

rank_df = (
    filtered_df
    .groupby("bank_name")["accuracy"]
    .mean()
    .reset_index()
    .sort_values("accuracy")
)

lollipop = px.scatter(
    rank_df,
    x="accuracy",
    y="bank_name",
    size="accuracy",
    color="accuracy",
    color_continuous_scale=["red", "yellow", "green"]
)

st.plotly_chart(lollipop, use_container_width=True)

# ============================
# 3️⃣ HEATMAP (MODEL × BANK)
# ============================
st.subheader("🔥 Model Performance Heatmap")

heatmap_df = filtered_df.pivot_table(
    index="bank_name",
    columns="model",
    values="accuracy",
    aggfunc="mean"
)

heatmap = px.imshow(
    heatmap_df,
    color_continuous_scale=["red", "yellow", "green"],
    aspect="auto"
)

st.plotly_chart(heatmap, use_container_width=True)

# ============================
# 4️⃣ RADAR CHART (PERFORMANCE SPREAD)
# ============================
st.subheader("🕸 Performance Spread (Radar View)")

radar_df = (
    filtered_df
    .groupby("bank_name")["accuracy"]
    .mean()
    .reset_index()
    .head(5)
)

radar = go.Figure()

radar.add_trace(go.Scatterpolar(
    r=radar_df["accuracy"],
    theta=radar_df["bank_name"],
    fill="toself",
    name="Accuracy"
))

radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    showlegend=False
)

st.plotly_chart(radar, use_container_width=True)

# ============================
# 5️⃣ PERFORMANCE DISTRIBUTION
# ============================
st.subheader("📊 Performance Band Distribution")

band_count = filtered_df["performance_band"].value_counts().reset_index()
band_count.columns = ["Performance Band", "Count"]

band_fig = px.bar(
    band_count,
    x="Performance Band",
    y="Count",
    color="Performance Band",
    color_discrete_map={
        "🟢 Good Performance": "green",
        "🟡 Medium Performance": "orange",
        "🔴 Poor Performance": "red"
    }
)

st.plotly_chart(band_fig, use_container_width=True)

# ============================
# MANAGEMENT INSIGHTS
# ============================
st.subheader("🧠 MIS Insights")

st.markdown(f"""
- **{(filtered_df['accuracy'] >= 70).sum()} models** are performing **well (≥70%)**.
- **{((filtered_df['accuracy'] >= 50) & (filtered_df['accuracy'] < 70)).sum()} models** need **performance tuning**.
- **{(filtered_df['accuracy'] < 50).sum()} models** are **underperforming** and require **immediate improvement**.
- Overall average accuracy stands at **{avg_accuracy:.2f}%**.
""")
