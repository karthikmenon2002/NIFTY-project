import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, get_sectors

st.set_page_config(page_title="Home", layout="wide")

companies = get_companies()
ratios = get_ratios()
sectors = get_sectors()

selected_year = st.sidebar.selectbox("Year", [2019, 2020, 2021, 2022, 2023, 2024], index=5)

latest = ratios[ratios["year"] == selected_year].copy()
merged = latest.merge(companies[["company_id", "company_name"]], on="company_id", how="left")
merged = merged.merge(sectors[["company_id", "broad_sector"]], on="company_id", how="left")

col1, col2, col3, col4, col5, col6 = st.columns(6)
metrics = [
    ("Average ROE", "return_on_equity_pct"),
    ("Median P/E", "pe_ratio"),
    ("Median D/E", "debt_to_equity"),
    ("Total Companies", "company_id"),
    ("Median Revenue CAGR 5yr", "revenue_cagr_5yr"),
    ("Debt-Free Companies", "debt_free"),
]

for col, (label, key) in zip([col1, col2, col3, col4, col5, col6], metrics):
    if key == "company_id":
        value = len(merged)
    elif key == "debt_free":
        value = int((merged["debt_to_equity"].fillna(float("inf")) == 0).sum())
    elif key == "pe_ratio":
        value = merged["pe_ratio"].median() if "pe_ratio" in merged.columns else None
    else:
        value = merged[key].mean() if key in merged.columns else None
    if pd.isna(value):
        display_value = "N/A"
    elif isinstance(value, float):
        display_value = f"{value:.2f}"
    else:
        display_value = value
    col.metric(label, display_value)

sector_counts = merged["broad_sector"].fillna("Unknown").value_counts().reset_index()
sector_counts.columns = ["sector", "companies"]
fig = px.pie(sector_counts, values="companies", names="sector", hole=0.45)
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

quality = merged[["company_name", "composite_quality_score"]].sort_values("composite_quality_score", ascending=False).head(5)
st.dataframe(quality, use_container_width=True)
