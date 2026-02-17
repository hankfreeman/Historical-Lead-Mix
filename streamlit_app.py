import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Lead Metrics Dashboard", layout="wide")
st.title("🛡️ Lead Metrics Dashboard")

# --- DEBUG PANEL ---
with st.expander("🔍 Debug Info (expand if app looks blank)", expanded=True):
    st.write("**Working directory:**", os.getcwd())
    st.write("**Files found:**", os.listdir("."))
    for f in ["leads_data.csv", "sales_data.csv"]:
        st.write(f"**{f} exists:**", os.path.exists(f))

# --- 1. Color Mapping ---
source_colors = {
    'Barrington': '#1f77b4',
    'Channel Edge': '#aec7e8',
    'Google': '#ff7f0e',
    'Lucent': '#ffbb78',
    'O2C': '#2ca02c',
    'Other': '#98df8a',
    'Policy Chat': '#17becf',
    'Ring 2': '#bcbd22',
    'Roku': '#d62728',
    'VOXR': '#ff9896',
    'Youtube': '#9467bd',
    'Regal': '#8c564b'
}
color_scale = alt.Scale(domain=list(source_colors.keys()), range=list(source_colors.values()))

# --- 2. Load Data ---
@st.cache_data
def load_data():
    leads = pd.read_csv("leads_data.csv", parse_dates=["PERIOD"])
    sales = pd.read_csv("sales_data.csv", parse_dates=["PERIOD"])
    return leads, sales

try:
    leads_df, sales_df = load_data()
    st.success(f"✅ Data loaded: {len(leads_df):,} lead rows, {len(sales_df):,} sales rows")
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

combined_df = pd.merge(leads_df, sales_df, on=["PERIOD", "LEAD_SOURCE"], how="outer").fillna(0)

# --- 3. Sidebar Filters ---
st.sidebar.header("Dashboard Controls")

min_cal = combined_df["PERIOD"].min()
max_cal = combined_df["PERIOD"].max()

start_date = st.sidebar.date_input("Start Date", value=min_cal)
end_date = st.sidebar.date_input("End Date", value=max_cal)

agg_level = st.sidebar.selectbox("Aggregation Level", ["Daily", "Weekly", "Monthly"], index=1)
agg_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}

mask = (combined_df["PERIOD"] >= pd.to_datetime(start_date)) & (combined_df["PERIOD"] <= pd.to_datetime(end_date))
date_filtered = combined_df[mask].copy()

all_sources_options = sorted(date_filtered["LEAD_SOURCE"].unique().tolist())

if "source_filter" not in st.session_state:
    st.session_state.source_filter = all_sources_options

col_a, col_b = st.sidebar.columns(2)
if col_a.button("Select All"):
    st.session_state.source_filter = all_sources_options
if col_b.button("Clear All"):
    st.session_state.source_filter = []

st.session_state.source_filter = [s for s in st.session_state.source_filter if s in all_sources_options]

selected_sources = st.sidebar.multiselect(
    "Filter Lead Sources",
    options=all_sources_options,
    default=st.session_state.source_filter,
    key="source_multiselect"
)
st.session_state.source_filter = selected_sources

# --- 4. Aggregation ---
filtered = date_filtered[date_filtered["LEAD_SOURCE"].isin(selected_sources)].copy()

freq = agg_map[agg_level]
filtered["PERIOD"] = filtered["PERIOD"].dt.to_period(freq).dt.to_timestamp()

filtered_combined = filtered.groupby(["PERIOD", "LEAD_SOURCE"]).agg(
    LEAD_COUNT=("LEAD_COUNT", "sum"),
    SOURCE_SALES=("SOURCE_SALES", "sum"),
    SOURCE_PREMIUM=("SOURCE_PREMIUM", "sum")
).reset_index()

filtered_combined["SOURCE_PSL"] = (
    filtered_combined["SOURCE_PREMIUM"] / filtered_combined["LEAD_COUNT"].replace(0, float("nan"))
).fillna(0)

metrics_df = filtered_combined.groupby("PERIOD").agg(
    LEAD_COUNT=("LEAD_COUNT", "sum"),
    TOTAL_SALES=("SOURCE_SALES", "sum"),
    TOTAL_PREMIUM=("SOURCE_PREMIUM", "sum")
).reset_index()

metrics_df["PSL"] = (
    metrics_df["TOTAL_PREMIUM"] / metrics_df["LEAD_COUNT"].replace(0, float("nan"))
).fillna(0)

# --- 5. Tabs ---
tab1, tab2 = st.tabs(["📊 Global Overview", "🧬 Source Breakout"])

with tab1:
    st.subheader("Aggregate Performance")
    c1, c2, c3 = st.columns(3)
    total_leads = metrics_df["LEAD_COUNT"].sum()
    total_premium = metrics_df["TOTAL_PREMIUM"].sum()
    c1.metric("Total Leads", f"{total_leads:,.0f}")
    c2.metric("Total Sales", f"{metrics_df['TOTAL_SALES'].sum():,.0f}")
    c3.metric("Total PSL", f"${(total_premium / total_leads if total_leads > 0 else 0):,.2f}")

    area = alt.Chart(filtered_combined).mark_area(
        opacity=0.7, interpolate="monotone"
    ).encode(
        x=alt.X("PERIOD:T", title="Date"),
        y=alt.Y("LEAD_COUNT:Q", stack="normalize", title="Lead Mix %", axis=alt.Axis(format="%")),
        color=alt.Color("LEAD_SOURCE:N", scale=color_scale, title="Lead Source"),
        tooltip=["PERIOD:T", "LEAD_SOURCE:N", "LEAD_COUNT:Q"]
    )

    line = alt.Chart(metrics_df).mark_line(
        color="#333333", strokeWidth=4, interpolate="monotone"
    ).encode(
        x="PERIOD:T",
        y=alt.Y("PSL:Q", title="Total PSL ($)", axis=alt.Axis(orient="right"))
    )

    st.altair_chart(
        (area + line).resolve_scale(y="independent").properties(height=450),
        use_container_width=True
    )

with tab2:
    st.subheader("PSL Trend by Individual Source")

    chart_data = filtered_combined[filtered_combined["SOURCE_PSL"] <= 400].copy()

    legend_selection = alt.selection_point(fields=["LEAD_SOURCE"], bind="legend", toggle="true")

    breakout_chart = alt.Chart(chart_data).mark_line(
        point=True, strokeWidth=3, interpolate="monotone"
    ).encode(
        x=alt.X("PERIOD:T", title="Date"),
        y=alt.Y("SOURCE_PSL:Q", title="Actual PSL ($)", scale=alt.Scale(zero=False)),
        color=alt.Color("LEAD_SOURCE:N", scale=color_scale, title="Toggle Legend"),
        tooltip=[
            alt.Tooltip("PERIOD:T", title="Date"),
            alt.Tooltip("LEAD_SOURCE:N", title="Source"),
            alt.Tooltip("SOURCE_PSL:Q", title="PSL", format="$.2f")
        ]
    ).add_params(legend_selection).transform_filter(legend_selection).properties(height=500).interactive()

    st.altair_chart(breakout_chart, use_container_width=True)
    st.dataframe(
        filtered_combined.sort_values(["PERIOD", "SOURCE_PSL"], ascending=[False, False]),
        use_container_width=True,
        hide_index=True
    )
