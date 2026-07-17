from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUT_DIR = PROJECT_ROOT / "reports" / "radar_charts"

AXES = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
    "composite_quality_score",
]


def _scale_series(s):
    numeric = pd.to_numeric(s, errors='coerce')
    vals = numeric.dropna()
    if vals.empty:
        return pd.Series([50.0] * len(s), index=s.index)
    lo = vals.quantile(0.10)
    hi = vals.quantile(0.90)
    if lo == hi:
        return pd.Series(50.0, index=s.index)
    capped = numeric.clip(lo, hi).fillna((lo+hi)/2)
    scaled = (capped - lo) / (hi - lo) * 100.0
    return scaled


def run():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        ratios = pd.read_sql_query(
            "SELECT fr.* FROM financial_ratios fr INNER JOIN (SELECT company_id, MAX(year) AS latest_year FROM financial_ratios GROUP BY company_id) latest ON fr.company_id = latest.company_id AND fr.year = latest.latest_year",
            conn,
        )

        peer_groups = pd.read_sql_query("SELECT company_id, peer_group_name FROM peer_groups", conn)
        merged = ratios.merge(peer_groups, on='company_id', how='left')

        # compute scaled values per axis across peer group
        for group, gdf in merged.groupby('peer_group_name'):
            if pd.isna(group):
                continue
            # compute group averages
            group_avg = {}
            scaled = {}
            for axis in AXES:
                if axis not in gdf.columns:
                    scaled_series = pd.Series(50.0, index=gdf.index)
                else:
                    scaled_series = _scale_series(gdf[axis])
                scaled[axis] = scaled_series
                group_avg[axis] = scaled_series.mean()

            # draw charts for each company in group
            for idx, row in gdf.iterrows():
                company = row['company_id']
                values = [scaled[a].loc[idx] if idx in scaled[a].index else 50.0 for a in AXES]
                avg_values = [group_avg[a] for a in AXES]

                angles = np.linspace(0, 2 * np.pi, len(AXES), endpoint=False).tolist()
                values += values[:1]
                avg_values += avg_values[:1]
                angles += angles[:1]

                fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
                ax.plot(angles, values, color='tab:blue')
                ax.fill(angles, values, color='tab:blue', alpha=0.25)
                ax.plot(angles, avg_values, color='tab:orange', linestyle='--')
                ax.set_thetagrids(np.degrees(angles[:-1]), AXES)
                ax.set_ylim(0,100)
                ax.set_title(f"{company} - {group}")

                out_file = OUT_DIR / f"{company}_radar.png"
                fig.tight_layout()
                fig.savefig(out_file, dpi=150)
                plt.close(fig)

        print(f"Radar charts generated: {OUT_DIR}")

    finally:
        conn.close()


if __name__ == '__main__':
    run()
