import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ===============================
# PAGE CONFIG (DARK THEME FEEL)
# ===============================
st.set_page_config(
    page_title="MIS Model Performance Dashboard",
    layout="wide"
)

st.markdown(
    """
    <style>
    body { background-color: #0E1117; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 MIS Model Performance Dashboard")
st.caption("Executive MIS view – Model Prediction, Accuracy & Performance Quality")

# ===============================
# LOAD DATA
# ===============================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"

df = pd.read_excel(FILE_PATH, sheet_name=0)
df.columns = df.columns.astype(str).str.strip()

# Rename columns safely
df = df.rename(columns={
    "Bank name": "bank_name",
    "Model": "model",
    "Cummulative number of mule accounts predicted by the model": "predicted_mules",
    "No. of Account confirmed as Mule (Post Review/ Frozen Debit Freez)": "confirmed_mules",
    "Latest accuracy": "accuracy",
    "Date of latest available accuracy": "accuracy_date"
})

# Fix missing bank names
df["bank_name"] = df["bank_name"].ffill()

# Convert numeric columns
for col in ["predicted_mules", "confirmed_mules", "accuracy"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["accuracy_date"] = pd.to_datetime(df["accuracy_date"], errors="coerce")

df = df.dropna(subset=["accuracy"])

# ===============================
# PERFORMANCE BAND LOGIC
# ===============================
def performance_band(acc):
    if acc >= 70:
        return "Good (≥70%)"
    elif acc >= 50:
        return "Medium (50–70%)"
    else:
        return "Poor (<50%)"

df["performance_band"] = df["accuracy"].apply(performance_band)

# ===============================
# SIDEBAR FILTERS
# ===============================
st.sidebar.header("🔎 Filters")

bank_filter = st.sidebar.multiselect(
    "Select Banks",
    df["bank_name"].unique(),
    default=df["bank_name"].unique()
)

filtered_df = df[df["bank_name"].isin(bank_filter)]

# ===============================
# KPI SECTION
# ===============================
total_predicted = int(filtered_df["predicted_mules"].sum())
total_confirmed = int(filtered_df["confirmed_mules"].sum())
avg_accuracy = filtered_df["accuracy"].mean()

k1, k2, k3 = st.columns(3)
k1.metric("🔮 Total Predicted Mule Accounts", f"{total_predicted:,}")
k2.metric("✅ Total Confirmed Mule Accounts", f"{total_confirmed:,}")
k3.metric("📈 Average Model Accuracy", f"{avg_accuracy:.2f}%")

st.divider()

# ===============================
# 1️⃣ PREDICTED vs CONFIRMED (BANK-WISE)
# ===============================
st.subheader("🏦 Bank-wise Predicted vs Confirmed Mule Accounts")

bank_summary = (
    filtered_df
    .groupby("bank_name")[["predicted_mules", "confirmed_mules"]]
    .sum()
    .reset_index()
)

bar_fig = px.bar(
    bank_summary,
    x="bank_name",
    y=["predicted_mules", "confirmed_mules"],
    barmode="group",
    color_discrete_map={
        "predicted_mules": "#1f77b4",
        "confirmed_mules": "#2ca02c"
    }
)

bar_fig.update_layout(
    xaxis_title="Bank",
    yaxis_title="Number of Accounts",
    legend_title="Legend"
)

st.plotly_chart(bar_fig, use_container_width=True)

# ===============================
# 2️⃣ ACCURACY PERFORMANCE GAUGE
# ===============================
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
        ],
        "bar": {"color": "white"}
    }
))

st.plotly_chart(gauge, use_container_width=True)

# ===============================
# 3️⃣ PERFORMANCE BAND DISTRIBUTION (FIXED)
# ===============================
st.subheader("📊 Performance Band Distribution")

band_df = (
    filtered_df["performance_band"]
    .value_counts()
    .reset_index()
)

band_df.columns = ["Performance Band", "Count"]

band_fig = px.bar(
    band_df,
    x="Performance Band",
    y="Count",
    color="Performance Band",
    color_discrete_map={
        "Good (≥70%)": "#2ca02c",
        "Medium (50–70%)": "#ffcc00",
        "Poor (<50%)": "#ff4d4d"
    },
    text="Count"
)

band_fig.update_traces(textposition="outside")
band_fig.update_layout(showlegend=False)

st.plotly_chart(band_fig, use_container_width=True)

# ===============================
# 4️⃣ ACCURACY TREND (TIME)
# ===============================
st.subheader("📉 Accuracy Trend Over Time")

trend_df = (
    filtered_df
    .sort_values("accuracy_date")
    .groupby("accuracy_date")["accuracy"]
    .mean()
    .reset_index()
)

trend_fig = px.line(
    trend_df,
    x="accuracy_date",
    y="accuracy",
    markers=True
)

trend_fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Average Accuracy (%)"
)

st.plotly_chart(trend_fig, use_container_width=True)

# ===============================
# 5️⃣ HEATMAP (BANK × MODEL)
# ===============================
st.subheader("🔥 Bank × Model Accuracy Heatmap")

heatmap_df = filtered_df.pivot_table(
    index="bank_name",
    columns="model",
    values="accuracy",
    aggfunc="mean"
)

heatmap_fig = px.imshow(
    heatmap_df,
    color_continuous_scale=["red", "yellow", "green"],
    aspect="auto"
)

st.plotly_chart(heatmap_fig, use_container_width=True)

# ===============================
# 6️⃣ DETAILED MIS TABLE
# ===============================
st.subheader("📋 Detailed MIS Data")

st.dataframe(
    filtered_df[[
        "bank_name",
        "model",
        "predicted_mules",
        "confirmed_mules",
        "accuracy",
        "performance_band",
        "accuracy_date"
    ]],
    use_container_width=True
)

# ===============================
# EXECUTIVE INSIGHTS
# ===============================
st.subheader("🧠 MIS Insights")

st.markdown(f"""
- **{(filtered_df['accuracy'] >= 70).sum()} models** are performing **well (≥70%)**  
- **{((filtered_df['accuracy'] >= 50) & (filtered_df['accuracy'] < 70)).sum()} models** need **improvement**  
- **{(filtered_df['accuracy'] < 50).sum()} models** are **underperforming**  
- Overall accuracy trend helps track **month-on-month model health**
""")
