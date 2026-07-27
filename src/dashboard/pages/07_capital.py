import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_ratios, get_companies

st.set_page_config(page_title="Capital Allocation", layout="wide")

ratios = get_ratios()
latest = ratios[ratios["year"] == 2024].copy()
companies = get_companies()
latest = latest.merge(companies[["company_id", "company_name"]], on="company_id", how="left")

fig = px.treemap(latest, path=[px.Constant("All"), "capital_allocation_pattern"], values="composite_quality_score", hover_data=["company_name"])
st.plotly_chart(fig, use_container_width=True)

pattern = st.selectbox("Pattern", sorted(latest["capital_allocation_pattern"].dropna().unique()))
filtered = latest[latest["capital_allocation_pattern"] == pattern]
st.dataframe(filtered[["company_name", "capital_allocation_pattern", "composite_quality_score"]], use_container_width=True)
