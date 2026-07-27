import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios

st.set_page_config(page_title="Trend Analysis", layout="wide")

companies = get_companies()
company_ids = companies["company_id"].tolist()
selected = st.selectbox("Company", company_ids)
metric_options = ["return_on_equity_pct", "return_on_capital_employed_pct", "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr"]
selected_metrics = st.multiselect("Metrics", metric_options, default=["return_on_equity_pct"], max_selections=3)

ratios = get_ratios(selected)
plot_df = ratios[["year"] + selected_metrics].copy()

fig = go.Figure()
for metric in selected_metrics:
    fig.add_trace(go.Scatter(x=plot_df["year"], y=plot_df[metric], mode="lines+markers", name=metric))
    if plot_df[metric].notna().sum() > 1:
        yoy = plot_df[metric].pct_change() * 100
        for x, y, change in zip(plot_df["year"], plot_df[metric], yoy):
            if pd.notna(change):
                fig.add_annotation(x=x, y=y, text=f"{change:.1f}%", showarrow=False, yshift=10)

fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)
