import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# =================================================
# LOGIN SYSTEM (ROLE BASED)
# =================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

def login_screen():
    st.title("🔐 MIS Secure Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.session_state.role = "Admin"
        elif username == "viewer" and password == "viewer123":
            st.session_state.logged_in = True
            st.session_state.role = "Viewer"
        else:
            st.error("Invalid credentials")

if not st.session_state.logged_in:
    login_screen()
    st.stop()

# =================================================
# PAGE CONFIG + DARK THEME
# =================================================
st.set_page_config(page_title="MIS Executive Dashboard", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0b1220; }
[data-testid="stSidebar"] { background-color: #111827; }
h1,h2,h3,h4,h5,h6,p,label { color:#e5e7eb; }
.stButton>button { background-color:#2563eb; color:white; }
</style>
""", unsafe_allow_html=True)

st.title("📊 MIS Executive Dashboard")
st.caption(f"Logged in as **{st.session_state.role}**")

# =================================================
# LOAD DATA (ROBUST)
# =================================================
df = pd.read_excel("MIS_REPORTING_CHART.xlsx")
df.columns = df.columns.astype(str).str.strip()

def find_col(keys):
    for c in df.columns:
        for k in keys:
            if k.lower() in c.lower():
                return c
    return None

df = df.rename(columns={
    find_col(["bank"]): "bank",
    find_col(["model"]): "model",
    find_col(["predicted"]): "predicted",
    find_col(["confirmed"]): "confirmed",
    find_col(["accuracy"]): "accuracy",
    find_col(["date"]): "date"
})

df["bank"] = df["bank"].ffill()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

for c in ["predicted","confirmed","accuracy"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["bank","accuracy","date"])

# =================================================
# SESSION STATE (LIVE EDITING)
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

data["band"] = data["accuracy"].apply(band)

# =================================================
# DATE FILTER + COMPARISON
# =================================================
st.sidebar.header("📅 Date Selection")

dates = sorted(data["date"].dt.date.unique(), reverse=True)
current_date = st.sidebar.selectbox("Current Date", dates)
previous_date = st.sidebar.selectbox("Compare With", dates[1:] if len(dates)>1 else dates)

curr = data[data["date"].dt.date == current_date]
prev = data[data["date"].dt.date == previous_date]

# =================================================
# 🚨 ALERT BANNERS + EMAIL
# =================================================
EMAIL_MAP = {
    "Bandhan": "manishroyalkondeti@gmail.com",
    "HDFC": "manishroyalkondeti43@gmail.com"
}

def send_email(bank, acc, to_email):
    msg = MIMEMultipart()
    msg["From"] = st.secrets["EMAIL_ADDRESS"]
    msg["To"] = to_email
    msg["Subject"] = f"Model Performance Alert – {bank}"

    body = f"""
Dear Team,

We have observed that the model accuracy for {bank} has dropped below the acceptable threshold.

Current Accuracy: {acc:.2f}%

We kindly request you to review the model performance and initiate retraining if required.
Please reach out to your RBIH SPOC for guidance on next steps.

Warm regards,
RBIH Model Governance Team
"""
    msg.attach(MIMEText(body,"plain"))

    server = smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
    server.send_message(msg)
    server.quit()

alert_df = curr.groupby("bank")["accuracy"].mean().reset_index()
critical = alert_df[alert_df["accuracy"] < 40]

if not critical.empty:
    for _, r in critical.iterrows():
        st.error(f"🚨 {r['bank']} accuracy dropped to {r['accuracy']:.2f}%")
        if r["bank"] in EMAIL_MAP:
            send_email(r["bank"], r["accuracy"], EMAIL_MAP[r["bank"]])
else:
    st.success("✅ No critical alerts for selected date")

# =================================================
# ADMIN-ONLY ADD / UPDATE DATA
# =================================================
if st.session_state.role == "Admin":
    st.sidebar.header("➕ Add / Update Bank Data")
    with st.sidebar.form("add"):
        b = st.text_input("Bank")
        m = st.text_input("Model")
        p = st.number_input("Predicted",0)
        c = st.number_input("Confirmed",0)
        a = st.number_input("Accuracy %",0.0,100.0)
        d = st.date_input("Date",date.today())
        if st.form_submit_button("Add"):
            new = {
                "bank": b, "model": m,
                "predicted": p, "confirmed": c,
                "accuracy": a, "date": pd.to_datetime(d),
                "band": band(a)
            }
            st.session_state.data = pd.concat(
                [st.session_state.data, pd.DataFrame([new])],
                ignore_index=True
            )
            st.success("Data added (session)")

# =================================================
# KPI CARDS WITH TREND ARROWS
# =================================================
def arrow(c,p):
    return "🔺" if c>p else "🔻" if c<p else "⏸"

k1,k2,k3,k4 = st.columns(4)

k1.metric("Avg Accuracy",
          f"{curr['accuracy'].mean():.2f}%",
          arrow(curr['accuracy'].mean(), prev['accuracy'].mean()))

k2.metric("Predicted",
          int(curr["predicted"].sum()),
          arrow(curr["predicted"].sum(), prev["predicted"].sum()))

k3.metric("Confirmed",
          int(curr["confirmed"].sum()),
          arrow(curr["confirmed"].sum(), prev["confirmed"].sum()))

k4.metric("Banks", curr["bank"].nunique())

st.divider()

# =================================================
# VISUALS (ALL PREVIOUS KEPT)
# =================================================
st.subheader("🏦 Predicted vs Confirmed (Bank-wise)")
bank_sum = curr.groupby("bank")[["predicted","confirmed"]].sum().reset_index()

st.plotly_chart(
    px.bar(
        bank_sum,
        x="bank",
        y=["predicted","confirmed"],
        barmode="group",
        color_discrete_map={
            "predicted":"#3b82f6",
            "confirmed":"#22c55e"
        }
    ),
    use_container_width=True
)

st.subheader("📊 Performance Band Distribution")
band_df = curr["band"].value_counts().reset_index()
band_df.columns=["Band","Count"]

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

st.subheader("🔥 Bank × Model Accuracy Heatmap")
heat = curr.pivot_table(index="bank",columns="model",values="accuracy",aggfunc="mean")
st.plotly_chart(px.imshow(heat,color_continuous_scale=["red","yellow","green"]),
                use_container_width=True)

# =================================================
# AI-STYLE INSIGHTS
# =================================================
st.subheader("🤖 AI-Driven Insights")
for _, r in alert_df.iterrows():
    if r["accuracy"] < 40:
        st.write(f"🔴 {r['bank']}: Immediate retraining required.")
    elif r["accuracy"] < 60:
        st.write(f"🟡 {r['bank']}: Monitor closely.")
    else:
        st.write(f"🟢 {r['bank']}: Stable performance.")

# =================================================
# DATA TABLE
# =================================================
st.subheader("📋 Live MIS Data")
st.dataframe(curr, use_container_width=True)
