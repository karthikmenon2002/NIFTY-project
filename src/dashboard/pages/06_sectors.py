import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_ratios, get_sectors, get_companies

st.set_page_config(page_title="Sector Analysis", layout="wide")

ratios = get_ratios()
sectors = get_sectors()
companies = get_companies()

latest = ratios[ratios["year"] == 2024].copy()
merged = latest.merge(sectors[["company_id", "broad_sector", "sub_sector"]], on="company_id", how="left")
merged = merged.merge(companies[["company_id", "company_name"]], on="company_id", how="left")

sector = st.selectbox("Sector", sorted(merged["broad_sector"].dropna().unique()))
filtered = merged[merged["broad_sector"] == sector]

fig = px.scatter(
    filtered,
    x="revenue_cagr_5yr",
    y="return_on_equity_pct",
    size="market_cap_crore",
    color="sub_sector",
    hover_data=["company_name"],
)
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

summary = filtered[["sub_sector", "return_on_equity_pct", "net_profit_margin_pct", "debt_to_equity"]].groupby("sub_sector").median().reset_index()
st.dataframe(summary, use_container_width=True)
