import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Lead Metrics Dashboard", layout="wide")
st.title("🛡️ Lead Metrics Dashboard")

# --- SYNTHETIC DATA GENERATOR ---
@st.cache_data
def generate_synthetic_data(start_date, end_date, agg_level):
    """Generate synthetic lead and sales data with dynamic source mix and stable PSL"""
    
    sources = ['Barrington', 'Channel Edge', 'Google', 'Lucent', 'O2C', 'Other', 
               'Policy Chat', 'Ring 2', 'Roku', 'VOXR', 'Youtube', 'Regal']
    
    # Base PSL for each source (relatively stable)
    base_psl = {
        'Barrington': 185, 'Channel Edge': 165, 'Google': 195, 'Lucent': 175,
        'O2C': 205, 'Other': 155, 'Policy Chat': 190, 'Ring 2': 170,
        'Roku': 180, 'VOXR': 160, 'Youtube': 200, 'Regal': 188
    }
    
    # Generate date range
    if agg_level == "Daily":
        periods = pd.date_range(start=start_date, end=end_date, freq='D')
    elif agg_level == "Weekly":
        periods = pd.date_range(start=start_date, end=end_date, freq='W')
    else:  # Monthly
        periods = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    data = []
    
    # Create evolving source weights that change dramatically over time
    np.random.seed(42)
    time_steps = len(periods)
    
    for i, period in enumerate(periods):
        # Create time-varying source distribution using sine waves with different phases
        # This creates natural shifts in lead source popularity
        weights = {}
        for j, source in enumerate(sources):
            # Each source has different trend patterns
            phase = j * np.pi / 6  # Different phase for each source
            trend = np.sin(2 * np.pi * i / time_steps * 3 + phase) ** 2
            seasonal = np.sin(2 * np.pi * i / time_steps * 12 + phase * 2)
            random_shock = np.random.normal(0, 0.3)
            
            weights[source] = max(0.1, trend + seasonal * 0.3 + random_shock)
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}
        
        # Total leads for this period (300-800 range with variance)
        total_leads = int(np.random.normal(550, 100))
        
        # Distribute leads across sources based on weights
        for source in sources:
            lead_count = int(total_leads * weights[source] * np.random.uniform(0.8, 1.2))
            lead_count = max(5, lead_count)  # Minimum 5 leads per source
            
            # Conversion rate (20-35% with some variance by source)
            base_conversion = 0.27
            source_modifier = np.random.normal(0, 0.03)
            conversion_rate = np.clip(base_conversion + source_modifier, 0.15, 0.40)
            
            sales_count = int(lead_count * conversion_rate)
            
            # PSL is stable with small random variation (±5%)
            source_psl = base_psl[source] * np.random.uniform(0.95, 1.05)
            
            premium = sales_count * source_psl
            
            data.append({
                'PERIOD': period,
                'LEAD_SOURCE': source,
                'LEAD_COUNT': lead_count,
                'SOURCE_SALES': sales_count,
                'SOURCE_PREMIUM': premium
            })
    
    return pd.DataFrame(data)

# --- 1. Color Mapping Configuration ---
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

# --- 2. Sidebar Filters ---
st.sidebar.header("Dashboard Controls")

# Date Range
min_cal = datetime(2023, 1, 1)
max_cal = datetime(2024, 12, 31)

start_date = st.sidebar.date_input("Start Date", value=min_cal)
end_date = st.sidebar.date_input("End Date", value=max_cal)

agg_level = st.sidebar.selectbox("Aggregation Level", options=["Daily", "Weekly", "Monthly"], index=1)

# --- 3. Generate Data ---
combined_df = generate_synthetic_data(start_date, end_date, agg_level)

# Lead Source Sidebar Multi-select
all_sources_options = sorted(combined_df['LEAD_SOURCE'].unique().tolist())

if 'source_filter' not in st.session_state:
    st.session_state.source_filter = all_sources_options

col_a, col_b = st.sidebar.columns(2)
if col_a.button("Select All"):
    st.session_state.source_filter = all_sources_options
if col_b.button("Clear All"):
    st.session_state.source_filter = []

# Ensure session state only contains valid options
st.session_state.source_filter = [s for s in st.session_state.source_filter if s in all_sources_options]

selected_sources = st.sidebar.multiselect(
    "Filter Lead Sources", 
    options=all_sources_options, 
    default=st.session_state.source_filter,
    key="source_multiselect"
)

st.session_state.source_filter = selected_sources

filtered_combined = combined_df[combined_df['LEAD_SOURCE'].isin(selected_sources)].copy()

# Aggregates for Tab 1
metrics_df = filtered_combined.groupby('PERIOD').agg({
    'LEAD_COUNT': 'sum', 'SOURCE_SALES': 'sum', 'SOURCE_PREMIUM': 'sum'
}).reset_index().rename(columns={'SOURCE_SALES': 'TOTAL_SALES', 'SOURCE_PREMIUM': 'TOTAL_PREMIUM'})

metrics_df['PSL'] = (metrics_df['TOTAL_PREMIUM'] / metrics_df['LEAD_COUNT']).fillna(0)
filtered_combined['SOURCE_PSL'] = (filtered_combined['SOURCE_PREMIUM'] / filtered_combined['LEAD_COUNT']).fillna(0)

# --- 5. Tabs ---
tab1, tab2 = st.tabs(["📊 Global Overview", "🧬 Source Breakout"])

with tab1:
    st.subheader("Aggregate Performance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Leads", f"{metrics_df['LEAD_COUNT'].sum():,.0f}")
    c2.metric("Total Sales", f"{metrics_df['TOTAL_SALES'].sum():,.0f}")
    c3.metric("Total PSL", f"${(metrics_df['TOTAL_PREMIUM'].sum()/metrics_df['LEAD_COUNT'].sum() if metrics_df['LEAD_COUNT'].sum() > 0 else 0):,.2f}")

    # Smoothed Area Chart
    area = alt.Chart(filtered_combined).mark_area(
        opacity=0.7, 
        interpolate='monotone'
    ).encode(
        x=alt.X('PERIOD:T', title='Date'),
        y=alt.Y('LEAD_COUNT:Q', stack='normalize', title='Lead Mix %', axis=alt.Axis(format='%')),
        color=alt.Color('LEAD_SOURCE:N', scale=color_scale, title="Lead Source"),
        tooltip=['PERIOD', 'LEAD_SOURCE', 'LEAD_COUNT']
    )

    line = alt.Chart(metrics_df).mark_line(color='#333333', strokeWidth=4, interpolate='monotone').encode(
        x='PERIOD:T',
        y=alt.Y('PSL:Q', title='Total PSL ($)', axis=alt.Axis(orient='right'))
    )

    st.altair_chart((area + line).resolve_scale(y='independent').properties(height=450), use_container_width=True)

with tab2:
    st.subheader("PSL Trend by Individual Source")
    
    # Apply $400 Outlier Filter
    chart_data = filtered_combined[filtered_combined['SOURCE_PSL'] <= 400].copy()
    
    legend_selection = alt.selection_point(fields=['LEAD_SOURCE'], bind='legend', toggle='true')

    breakout_chart = alt.Chart(chart_data).mark_line(
        point=True, 
        strokeWidth=3, 
        interpolate='monotone'
    ).encode(
        x=alt.X('PERIOD:T', title='Date'),
        y=alt.Y('SOURCE_PSL:Q', title='Actual PSL ($)', scale=alt.Scale(zero=False)),
        color=alt.Color('LEAD_SOURCE:N', scale=color_scale, title="Toggle Legend"),
        tooltip=[
            alt.Tooltip('PERIOD:T', title='Date'),
            alt.Tooltip('LEAD_SOURCE:N', title='Source'),
            alt.Tooltip('SOURCE_PSL:Q', title='PSL', format='$.2f')
        ]
    ).add_params(
        legend_selection
    ).transform_filter(
        legend_selection
    ).properties(height=500).interactive()

    st.altair_chart(breakout_chart, use_container_width=True)
    st.dataframe(filtered_combined.sort_values(['PERIOD', 'SOURCE_PSL'], ascending=[False, False]), use_container_width=True, hide_index=True)
