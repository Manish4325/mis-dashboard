import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# =================================================
# PAGE CONFIG + DARK LOVE THEME
# =================================================
st.set_page_config(page_title="MIS Executive Dashboard", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0b1220; }
[data-testid="stSidebar"] { background-color: #111827; }
h1, h2, h3, h4, h5, h6, p, label { color: #e5e7eb; }
.stButton>button { background-color:#2563eb; color:white; }
</style>
""", unsafe_allow_html=True)

st.title("📊 MIS Executive Dashboard")
st.caption("A living MIS system – Monitor • Edit • Improve • Decide")

# =================================================
# LOAD DATA (ROBUST)
# =================================================
FILE_PATH = "MIS_REPORTING_CHART.xlsx"
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.astype(str).str.strip()

def find_column(keys):
    for c in df.columns:
        for k in keys:
            if k.lower() in c.lower():
                return c
    return None

df = df.rename(columns={
    find_column(["bank"]): "bank_name",
    find_column(["model"]): "model",
    find_column(["predicted"]): "predicted_mules",
    find_column(["confirmed"]): "confirmed_mules",
    find_column(["accuracy"]): "accuracy",
    find_column(["date"]): "accuracy_date"
})

df["bank_name"] = df["bank_name"].ffill()
df["accuracy_date"] = pd.to_datetime(df["accuracy_date"], errors="coerce")

for c in ["predicted_mules", "confirmed_mules", "accuracy"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["bank_name", "accuracy"])

# =================================================
# SESSION STATE (FOR EDITING / ADDING DATA)
# =================================================
if "data" not in st.session_state:
    st.session_state.data = df.copy()

data = st.session_state.data

# =================================================
# PERFORMANCE BAND
# =================================================
def band(acc):
    if acc >= 70: return "🟢 Good"
    if acc >= 50: return "🟡 Medium"
    return "🔴 Poor"

data["performance_band"] = data["accuracy"].apply(band)

# =================================================
# SIDEBAR – DATE FILTER
# =================================================
st.sidebar.header("📅 Reporting Date")

dates = sorted(data["accuracy_date"].dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Select Date", dates)

view_df = data[data["accuracy_date"].dt.date == selected_date]

# =================================================
# ❤️ ADD / UPDATE BANK DATA (FORM)
# =================================================
st.sidebar.header("➕ Add / Update Bank Data")

with st.sidebar.form("add_bank"):
    new_bank = st.text_input("Bank Name")
    new_model = st.text_input("Model")
    new_pred = st.number_input("Predicted Mule Accounts", min_value=0)
    new_conf = st.number_input("Confirmed Mule Accounts", min_value=0)
    new_acc = st.number_input("Accuracy (%)", min_value=0.0, max_value=100.0)
    new_date = st.date_input("Reporting Date", value=date.today())

    submit = st.form_submit_button("Add / Update")

    if submit:
        new_row = {
            "bank_name": new_bank,
            "model": new_model,
            "predicted_mules": new_pred,
            "confirmed_mules": new_conf,
            "accuracy": new_acc,
            "accuracy_date": pd.to_datetime(new_date),
            "performance_band": band(new_acc)
        }
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame([new_row])],
            ignore_index=True
        )
        st.success("✅ Bank data added to dashboard (session)")

# =================================================
# KPIs
# =================================================
k1, k2, k3, k4 = st.columns(4)

k1.metric("🔮 Predicted", int(view_df["predicted_mules"].sum()))
k2.metric("✅ Confirmed", int(view_df["confirmed_mules"].sum()))
k3.metric("📈 Avg Accuracy", f"{view_df['accuracy'].mean():.2f}%")
k4.metric("🏦 Banks", view_df["bank_name"].nunique())

st.divider()

# =================================================
# VISUALS – KEEP EVERYTHING
# =================================================
st.subheader("🏦 Predicted vs Confirmed (Bank-wise)")
bank_sum = view_df.groupby("bank_name")[["predicted_mules","confirmed_mules"]].sum().reset_index()

st.plotly_chart(
    px.bar(
        bank_sum,
        x="bank_name",
        y=["predicted_mules","confirmed_mules"],
        barmode="group",
        color_discrete_map={
            "predicted_mules":"#3b82f6",
            "confirmed_mules":"#22c55e"
        }
    ),
    use_container_width=True
)

st.subheader("📊 Performance Band Distribution")
band_df = view_df["performance_band"].value_counts().reset_index()
band_df.columns = ["Band","Count"]

st.plotly_chart(
    px.bar(
        band_df,
        x="Band",
        y="Count",
        color="Band",
        color_discrete_map={
            "🟢 Good":"#22c55e",
            "🟡 Medium":"#facc15",
            "🔴 Poor":"#ef4444"
        }
    ),
    use_container_width=True
)

# =================================================
# 🧠 AUTO EXECUTIVE COMMENTARY (AI-STYLE)
# =================================================
st.subheader("🧠 Executive Commentary")

best = view_df.groupby("bank_name")["accuracy"].mean().idxmax()
worst = view_df.groupby("bank_name")["accuracy"].mean().idxmin()

st.markdown(f"""
- Overall average accuracy for **{selected_date}** is **{view_df['accuracy'].mean():.2f}%**
- **{best}** is currently the **best performing bank**
- **{worst}** requires **immediate attention**
- Majority of models fall under **{view_df['performance_band'].mode()[0]}** category
- This MIS suggests targeted **model tuning & operational focus**
""")

# =================================================
# FINAL TABLE
# =================================================
st.subheader("📋 Live MIS Data (Editable Session View)")
st.dataframe(view_df, use_container_width=True)
