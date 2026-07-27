import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_peers, get_companies, get_ratios

st.set_page_config(page_title="Peer Comparison", layout="wide")

companies = get_companies()
peer_groups = sorted({row.peer_group_name for _, row in get_peers().iterrows() if pd.notna(row.peer_group_name)})
selected_group = st.selectbox("Peer group", peer_groups)

peer_df = get_peers(selected_group)
peer_ids = peer_df[peer_df["company_id"].notna()]["company_id"].tolist()
selected_company = st.selectbox("Benchmark company", companies[companies["company_id"].isin(peer_ids)]["company_name"].tolist())
selected_company_id = companies.loc[companies["company_name"] == selected_company, "company_id"].iloc[0]

metrics = ["return_on_equity_pct", "net_profit_margin_pct", "return_on_capital_employed_pct", "debt_to_equity", "interest_coverage", "revenue_cagr_5yr", "pat_cagr_5yr", "composite_quality_score"]
metric_names = ["ROE", "Net Margin", "ROCE", "D/E", "ICR", "Revenue CAGR", "PAT CAGR", "Composite Score"]

latest = get_ratios().groupby("company_id").tail(1).reset_index(drop=True)
latest = latest[latest["company_id"].isin(peer_ids)]

benchmark = latest[latest["company_id"] == selected_company_id].iloc[0]
peer_avg = latest[metrics].mean()
values = [benchmark[m] for m in metrics]
avg_values = [peer_avg[m] for m in metrics]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(r=values, theta=metric_names, fill="toself", name=selected_company))
fig.add_trace(go.Scatterpolar(r=avg_values, theta=metric_names, fill="toself", name="Peer Avg"))
fig.update_layout(polar=dict(radialaxis=dict(visible=True)))
st.plotly_chart(fig, use_container_width=True)

peer_table = latest[["company_id"] + metrics].copy()
peer_table = peer_table.merge(companies[["company_id", "company_name"]], on="company_id", how="left")
peer_table["benchmark"] = peer_table["company_id"] == selected_company_id

def style_benchmark(row):
    return ["background: #FFF3CD" if row["company_id"] == selected_company_id else "" for _ in row]

st.dataframe(peer_table.style.apply(style_benchmark, axis=1), use_container_width=True)
