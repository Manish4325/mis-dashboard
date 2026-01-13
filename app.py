import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =================================================
# PAGE CONFIG + DARK THEME
# =================================================
st.set_page_config(
    page_title="MIS Model Performance Dashboard",
    layout="wide"
)

st.markdown("""
<style>
body {
    background-color: #0b1220;
}
[data-testid="stAppViewContainer"] {
    background-color: #0b1220;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
h1, h2, h3, h4, h5, h6, p, label {
    color: #e5e7eb;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 MIS Model Performance Dashboard")
st.caption("Date-wise | Bank-wise | Model-wise MIS Performance View")

# =================================================
# LOAD DATA
# =================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"

df = pd.read_excel(FILE_PATH)
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
df["accuracy_date"] = pd.to_datetime(df["accuracy_date"], errors="coerce")

for col in ["predicted_mules", "confirmed_mules", "accuracy"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["accuracy", "accuracy_date"])

# =================================================
# PERFORMANCE BAND
# =================================================
def band(acc):
    if acc >= 70:
        return "🟢 Good (≥70%)"
    elif acc >= 50:
        return "🟡 Medium (50–70%)"
    else:
        return "🔴 Poor (<50%)"

df["performance_band"] = df["accuracy"].apply(band)

# =================================================
# SIDEBAR – DATE & BANK CONTROLS
# =================================================
st.sidebar.header("📅 Date Filter")

selected_date = st.sidebar.selectbox(
    "Select Reporting Date",
    sorted(df["accuracy_date"].dt.date.unique(), reverse=True)
)

date_df = df[df["accuracy_date"].dt.date == selected_date]

st.sidebar.header("🏦 Bank Filter")

selected_bank = st.sidebar.selectbox(
    "Select Bank",
    ["All Banks"] + sorted(date_df["bank_name"].unique())
)

if selected_bank != "All Banks":
    date_df = date_df[date_df["bank_name"] == selected_bank]

# =================================================
# KPI CARDS (DATE AWARE)
# =================================================
k1, k2, k3 = st.columns(3)

k1.metric(
    "🔮 Predicted Mule Accounts",
    f"{int(date_df['predicted_mules'].sum()):,}"
)

k2.metric(
    "✅ Confirmed Mule Accounts",
    f"{int(date_df['confirmed_mules'].sum()):,}"
)

k3.metric(
    "📈 Avg Accuracy",
    f"{date_df['accuracy'].mean():.2f}%"
)

st.divider()

# =================================================
# BANK / MODEL DRILL-DOWN VIEW
# =================================================
st.subheader("🏦 Bank → Model Drill-Down")

model_summary = (
    date_df
    .groupby(["bank_name", "model"])
    .agg({
        "predicted_mules": "sum",
        "confirmed_mules": "sum",
        "accuracy": "mean"
    })
    .reset_index()
)

drill_fig = px.bar(
    model_summary,
    x="model",
    y=["predicted_mules", "confirmed_mules"],
    barmode="group",
    color_discrete_map={
        "predicted_mules": "#3b82f6",
        "confirmed_mules": "#22c55e"
    }
)

st.plotly_chart(drill_fig, use_container_width=True)

# =================================================
# ACCURACY GAUGE
# =================================================
st.subheader("🎯 Accuracy Health (Selected Date)")

gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=date_df["accuracy"].mean(),
    number={"suffix": "%"},
    gauge={
        "axis": {"range": [0, 100]},
        "steps": [
            {"range": [0, 50], "color": "#ef4444"},
            {"range": [50, 70], "color": "#facc15"},
            {"range": [70, 100], "color": "#22c55e"}
        ],
        "bar": {"color": "white"}
    }
))

st.plotly_chart(gauge, use_container_width=True)

# =================================================
# PERFORMANCE BAND DISTRIBUTION
# =================================================
st.subheader("📊 Performance Band Distribution")

band_df = (
    date_df["performance_band"]
    .value_counts()
    .reset_index()
)
band_df.columns = ["Performance Band", "Count"]

band_fig = px.bar(
    band_df,
    x="Performance Band",
    y="Count",
    color="Performance Band",
    text="Count",
    color_discrete_map={
        "🟢 Good (≥70%)": "#22c55e",
        "🟡 Medium (50–70%)": "#facc15",
        "🔴 Poor (<50%)": "#ef4444"
    }
)

st.plotly_chart(band_fig, use_container_width=True)

# =================================================
# HEATMAP (BANK × MODEL)
# =================================================
st.subheader("🔥 Bank × Model Accuracy Heatmap")

heatmap_df = date_df.pivot_table(
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

# =================================================
# DETAILED DATE-WISE TABLE
# =================================================
st.subheader("📋 Date-wise Detailed MIS")

st.dataframe(
    date_df[[
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

# =================================================
# EXECUTIVE SUMMARY
# =================================================
st.subheader("🧠 Executive MIS Summary")

st.markdown(f"""
- Reporting Date: **{selected_date}**
- **{(date_df['accuracy'] >= 70).sum()} models** performing well  
- **{((date_df['accuracy'] >= 50) & (date_df['accuracy'] < 70)).sum()} models** need improvement  
- **{(date_df['accuracy'] < 50).sum()} models** require immediate action  
""")
