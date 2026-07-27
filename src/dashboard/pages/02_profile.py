import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, get_pl, get_bs, get_cf

st.set_page_config(page_title="Company Profile", layout="wide")

companies = get_companies()
company_lookup = {c.company_name.lower(): c.company_id for _, c in companies.iterrows()}
company_lookup.update({c.company_id.lower(): c.company_id for _, c in companies.iterrows()})

search = st.text_input("Search company", placeholder="Type company name or ticker")
selected = None
if search:
    matches = [k for k in company_lookup if search.lower() in k]
    if matches:
        selected = company_lookup[matches[0]]

if selected is None:
    options = companies["company_name"].tolist()
    selected = st.selectbox("Select company", options)
    selected = companies.loc[companies["company_name"] == selected, "company_id"].iloc[0]

company = companies[companies["company_id"] == selected].iloc[0]
ratios = get_ratios(selected)
if ratios.empty:
    st.error("Ticker not found — please try another")
    st.stop()

latest = ratios.sort_values("year").iloc[-1]

st.subheader(f"{company.company_name} ({selected})")
st.caption(f"Sector: {company.broad_sector if pd.notna(company.broad_sector) else 'N/A'} | Sub-sector: {company.sub_sector if pd.notna(company.sub_sector) else 'N/A'}")
st.write(company.about_company if pd.notna(company.about_company) else "No summary available for this company yet.")

col1, col2, col3, col4, col5, col6 = st.columns(6)
for col, label, value in [
    (col1, "ROE", latest.get("return_on_equity_pct")),
    (col2, "ROCE", latest.get("return_on_capital_employed_pct")),
    (col3, "Net Profit Margin", latest.get("net_profit_margin_pct")),
    (col4, "D/E", latest.get("debt_to_equity")),
    (col5, "Revenue CAGR 5yr", latest.get("revenue_cagr_5yr")),
    (col6, "FCF", latest.get("free_cash_flow_cr")),
]:
    display_value = "N/A" if pd.isna(value) else f"{value:.2f}"
    col.metric(label, display_value)

pl = get_pl(selected)
bs = get_bs(selected)
cf = get_cf(selected)

plot_df = pd.DataFrame({"year": ratios["year"], "Revenue": pl.get("sales"), "Net Profit": pl.get("net_profit")})
fig = px.bar(plot_df, x="year", y=["Revenue", "Net Profit"], barmode="group")
st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=ratios["year"], y=ratios["return_on_equity_pct"], mode="lines+markers", name="ROE"))
fig2.add_trace(go.Scatter(x=ratios["year"], y=ratios["return_on_capital_employed_pct"], mode="lines+markers", name="ROCE", yaxis="y2"))
fig2.update_layout(yaxis2=dict(overlaying="y", side="right"), margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig2, use_container_width=True)

st.write("Pros")
st.write("- ✓ Strong operating discipline")
st.write("- ✓ Stable cash generation")
st.write("Cons")
st.write("- ✗ High leverage in some years")
