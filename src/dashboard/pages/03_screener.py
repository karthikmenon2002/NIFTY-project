import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, get_sectors

st.set_page_config(page_title="Screener", layout="wide")

companies = get_companies()
ratios = get_ratios()
sectors = get_sectors()

merged = ratios.merge(companies[["company_id", "company_name"]], on="company_id", how="left")
merged = merged.merge(sectors[["company_id", "broad_sector", "sub_sector"]], on="company_id", how="left")
merged = merged[merged["year"] == 2024].copy()

preset_map = {
    "Quality": {"roe": 15, "de": 0.5, "fcf": 100, "rev_cagr": 8, "pat_cagr": 8, "opm": 15, "pe": 25, "pb": 5, "dy": 1, "icr": 5},
    "Value": {"roe": 5, "de": 1.0, "fcf": 0, "rev_cagr": 0, "pat_cagr": 0, "opm": 5, "pe": 30, "pb": 5, "dy": 0.5, "icr": 2},
    "Growth": {"roe": 10, "de": 1.5, "fcf": 50, "rev_cagr": 10, "pat_cagr": 10, "opm": 10, "pe": 35, "pb": 6, "dy": 0.2, "icr": 3},
    "Dividend": {"roe": 8, "de": 0.8, "fcf": 50, "rev_cagr": 4, "pat_cagr": 4, "opm": 10, "pe": 20, "pb": 4, "dy": 1.5, "icr": 4},
    "Debt-Free": {"roe": 6, "de": 0.0, "fcf": 0, "rev_cagr": 0, "pat_cagr": 0, "opm": 5, "pe": 40, "pb": 6, "dy": 0.0, "icr": 2},
    "Turnaround": {"roe": 8, "de": 1.2, "fcf": 20, "rev_cagr": 6, "pat_cagr": 6, "opm": 8, "pe": 28, "pb": 5, "icr": 3, "dy": 0.0},
}

with st.sidebar:
    st.header("Filters")
    filters = {}
    filters["roe"] = st.slider("ROE min (%)", 0.0, 40.0, 0.0, 0.5)
    filters["de"] = st.slider("D/E max", 0.0, 3.0, 3.0, 0.1)
    filters["fcf"] = st.slider("FCF min", -5000.0, 5000.0, -5000.0, 50.0)
    filters["rev_cagr"] = st.slider("Revenue CAGR min (%)", -50.0, 50.0, -50.0, 1.0)
    filters["pat_cagr"] = st.slider("PAT CAGR min (%)", -50.0, 50.0, -50.0, 1.0)
    filters["opm"] = st.slider("OPM min (%)", -50.0, 100.0, -50.0, 1.0)
    filters["pe"] = st.slider("P/E max", 0.0, 200.0, 200.0, 1.0)
    filters["pb"] = st.slider("P/B max", 0.0, 50.0, 50.0, 0.5)
    filters["dy"] = st.slider("Dividend Yield min (%)", 0.0, 10.0, 0.0, 0.1)
    filters["icr"] = st.slider("ICR min", 0.0, 20.0, 0.0, 0.5)

    st.subheader("Presets")
    for name in preset_map:
        if st.button(name):
            for key, value in preset_map[name].items():
                filters[key] = value
            st.experimental_rerun()

masked = merged.copy()
for key, value in filters.items():
    if key == "roe":
        masked = masked[masked["return_on_equity_pct"].fillna(-999) >= value]
    elif key == "de":
        masked = masked[masked["debt_to_equity"].fillna(999) <= value]
    elif key == "fcf":
        masked = masked[masked["free_cash_flow_cr"].fillna(-999999) >= value]
    elif key == "rev_cagr":
        masked = masked[masked["revenue_cagr_5yr"].fillna(-999) >= value]
    elif key == "pat_cagr":
        masked = masked[masked["pat_cagr_5yr"].fillna(-999) >= value]
    elif key == "opm":
        masked = masked[masked["operating_profit_margin_pct"].fillna(-999) >= value]
    elif key == "pe":
        masked = masked[masked["pe_ratio"].fillna(999) <= value]
    elif key == "pb":
        masked = masked[masked["pb_ratio"].fillna(999) <= value]
    elif key == "dy":
        masked = masked[masked["dividend_yield_pct"].fillna(-999) >= value]
    elif key == "icr":
        masked = masked[masked["interest_coverage"].fillna(-999) >= value]

masked = masked[["company_id", "company_name", "broad_sector", "sub_sector", "composite_quality_score", "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr", "revenue_cagr_5yr", "pat_cagr_5yr", "operating_profit_margin_pct", "pe_ratio", "pb_ratio", "dividend_yield_pct", "interest_coverage"]]
masked.columns = ["company_id", "name", "sector", "sub_sector", "composite_score", "ROE", "D/E", "FCF", "Revenue CAGR", "PAT CAGR", "OPM", "P/E", "P/B", "Dividend Yield", "ICR"]

st.subheader(f"{len(masked)} companies match your filters")
if not masked.empty:
    csv = masked.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, file_name="screener_results.csv", mime="text/csv")
st.dataframe(masked, use_container_width=True)
