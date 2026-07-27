from pathlib import Path
import sqlite3

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / ".." / "db" / "nifty100.db"
DB_PATH = DB_PATH.resolve()
MARKET_CAP_PATH = PROJECT_ROOT / ".." / "data" / "supporting" / "market_cap.xlsx"
MARKET_CAP_PATH = MARKET_CAP_PATH.resolve()


def _connect():
    return sqlite3.connect(DB_PATH)


def run(output_dir: str | Path | None = None):
    output_dir = Path(output_dir or PROJECT_ROOT / ".." / "output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    try:
        companies = pd.read_sql_query("SELECT id, company_name FROM companies ORDER BY company_name", conn)
        sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
        ratios = pd.read_sql_query("SELECT company_id, year, return_on_equity_pct, debt_to_equity, free_cash_flow_cr, net_profit_margin_pct, operating_profit_margin_pct, composite_quality_score FROM financial_ratios", conn)
        market_cap = pd.read_excel(MARKET_CAP_PATH)
        market_cap = market_cap[["company_id", "year", "market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"]].copy()
    finally:
        conn.close()

    ratios = ratios.merge(companies, left_on="company_id", right_on="id", how="left")
    ratios = ratios.merge(sectors, on="company_id", how="left")
    ratios = ratios.merge(market_cap, on=["company_id", "year"], how="left")
    ratios = ratios.rename(columns={"company_name": "company_name"})

    latest_year = ratios["year"].dropna().max()
    latest = ratios[ratios["year"] == latest_year].copy()
    latest = latest[latest["company_id"].notna()].copy()

    sector_medians = latest.groupby("broad_sector")["pe_ratio"].median().to_dict()
    five_year_medians = (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id")
        .apply(lambda g: g.tail(5)["pe_ratio"].median())
        .rename("5yr_median_PE")
    )
    latest["5yr_median_PE"] = latest["company_id"].map(five_year_medians)
    latest["PE_vs_sector_median_pct"] = latest.apply(
        lambda row: ((row["pe_ratio"] / sector_medians.get(row["broad_sector"], row["pe_ratio"])) * 100) if pd.notna(row["pe_ratio"]) and pd.notna(row["broad_sector"]) and sector_medians.get(row["broad_sector"], 0) not in (None, 0) else None,
        axis=1,
    )
    latest["FCF_yield_pct"] = latest["free_cash_flow_cr"] / latest["market_cap_crore"] * 100
    latest["flag"] = latest.apply(lambda row: "Caution" if pd.notna(row["pe_ratio"]) and pd.notna(row["broad_sector"]) and row["pe_ratio"] > sector_medians.get(row["broad_sector"], 0) * 1.5 else "Discount" if pd.notna(row["pe_ratio"]) and pd.notna(row["broad_sector"]) and row["pe_ratio"] < sector_medians.get(row["broad_sector"], 0) * 0.7 else "Fair", axis=1)

    summary = latest[["company_id", "company_name", "broad_sector", "pe_ratio", "pb_ratio", "ev_ebitda", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"]].copy()
    summary.columns = ["company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"]
    summary = summary.sort_values("company_name").reset_index(drop=True)

    summary_path = output_dir / "valuation_summary.xlsx"
    flags_path = output_dir / "valuation_flags.csv"
    summary.to_excel(summary_path, index=False)
    flags = summary[summary["flag"].isin(["Caution", "Discount"])].copy()
    flags.to_csv(flags_path, index=False)
    return summary_path, flags_path


if __name__ == "__main__":
    run()
