import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =================================================
# PAGE CONFIG + DARK THEME
# =================================================
st.set_page_config(
    page_title="MIS Executive Dashboard",
    layout="wide"
)

st.markdown("""
<style>
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

st.title("📊 MIS Executive Dashboard")
st.caption("Date-wise • Bank-wise • Model-wise MIS Performance View")

# =================================================
# LOAD DATA (ROBUST & SAFE)
# =================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.astype(str).str.strip()

# ---------- SMART COLUMN DETECTION ----------
def find_column(keywords):
    for col in df.columns:
        for key in keywords:
            if key.lower() in col.lower():
                return col
    return None

bank_col = find_column(["bank"])
model_col = find_column(["model"])
predicted_col = find_column(["predicted"])
confirmed_col = find_column(["confirmed"])
accuracy_col = find_column(["accuracy"])
date_col = find_column(["date"])

column_map = {}
if bank_col: column_map[bank_col] = "bank_name"
if model_col: column_map[model_col] = "model"
if predicted_col: column_map[predicted_col] = "predicted_mules"
if confirmed_col: column_map[confirmed_col] = "confirmed_mules"
if accuracy_col: column_map[accuracy_col] = "accuracy"
if date_col: column_map[date_col] = "accuracy_date"

df = df.rename(columns=column_map)

# ---------- VALIDATION ----------
required_cols = ["bank_name", "accuracy"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Missing required columns in Excel: {missing}")
    st.stop()

# ---------- CLEANING ----------
df["bank_name"] = df["bank_name"].ffill()

if "accuracy_date" in df.columns:
    df["accuracy_date"] = pd.to_datetime(df["accuracy_date"], errors="coerce")

for col in ["predicted_mules", "confirmed_mules", "accuracy"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["accuracy"])

# =================================================
# PERFORMANCE BAND LOGIC
# =================================================
def performance_band(acc):
    if acc >= 70:
        return "🟢 Good (≥70%)"
    elif acc >= 50:
        return "🟡 Medium (50–70%)"
    else:
        return "🔴 Poor (<50%)"

df["performance_band"] = df["accuracy"].apply(performance_band)

# =================================================
# SIDEBAR FILTERS (DATE → BANK)
# =================================================
st.sidebar.header("📅 Date Filter")

if "accuracy_date" in df.columns:
    available_dates = sorted(df["accuracy_date"].dt.date.dropna().unique(), reverse=True)
    selected_date = st.sidebar.selectbox("Select Reporting Date", available_dates)
    filtered_df = df[df["accuracy_date"].dt.date == selected_date]
else:
    filtered_df = df.copy()
    selected_date = "All Dates"

st.sidebar.header("🏦 Bank Filter")
banks = sorted(filtered_df["bank_name"].unique())
selected_bank = st.sidebar.selectbox("Select Bank", ["All Banks"] + banks)

if selected_bank != "All Banks":
    filtered_df = filtered_df[filtered_df["bank_name"] == selected_bank]

# =================================================
# KPI CARDS
# =================================================
total_pred = int(filtered_df["predicted_mules"].sum()) if "predicted_mules" in filtered_df else 0
total_conf = int(filtered_df["confirmed_mules"].sum()) if "confirmed_mules" in filtered_df else 0
avg_acc = filtered_df["accuracy"].mean()

k1, k2, k3 = st.columns(3)
k1.metric("🔮 Predicted Accounts", f"{total_pred:,}")
k2.metric("✅ Confirmed Accounts", f"{total_conf:,}")
k3.metric("🎯 Avg Accuracy", f"{avg_acc:.2f}%")

st.divider()

# =================================================
# BANK → MODEL DRILL-DOWN
# =================================================
st.subheader("🏦 Bank → Model Drill-Down")

group_cols = ["bank_name", "model"]
agg_dict = {"accuracy": "mean"}

if "predicted_mules" in filtered_df:
    agg_dict["predicted_mules"] = "sum"
if "confirmed_mules" in filtered_df:
    agg_dict["confirmed_mules"] = "sum"

model_df = filtered_df.groupby(group_cols).agg(agg_dict).reset_index()

if "predicted_mules" in model_df and "confirmed_mules" in model_df:
    drill_fig = px.bar(
        model_df,
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
st.subheader("🎯 Accuracy Health")

gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=avg_acc,
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

if "model" in filtered_df.columns:
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

# =================================================
# DETAILED DATE-WISE TABLE
# =================================================
st.subheader("📋 Detailed MIS Data")

st.dataframe(
    filtered_df[
        [c for c in [
            "bank_name",
            "model",
            "predicted_mules",
            "confirmed_mules",
            "accuracy",
            "performance_band",
            "accuracy_date"
        ] if c in filtered_df.columns]
    ],
    use_container_width=True
)

# =================================================
# EXECUTIVE SUMMARY
# =================================================
st.subheader("🧠 Executive MIS Summary")

st.markdown(f"""
- Reporting Date: **{selected_date}**
- **{(filtered_df['accuracy'] >= 70).sum()} models** performing well  
- **{((filtered_df['accuracy'] >= 50) & (filtered_df['accuracy'] < 70)).sum()} models** need improvement  
- **{(filtered_df['accuracy'] < 50).sum()} models** require immediate action  
""")
