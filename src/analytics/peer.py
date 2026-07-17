from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


METRICS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "fcf",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
    "eps_cagr_5yr",
    "interest_coverage",
    "asset_turnover",
]


def percent_rank(series, higher_is_better=True):
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return pd.Series(np.nan, index=series.index)
    # percent rank from 0 to 100
    if higher_is_better:
        return numeric.rank(pct=True, method="average", ascending=True) * 100
    return numeric.rank(pct=True, method="average", ascending=False) * 100


def run():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        # load latest ratios
        ratios = pd.read_sql_query(
            """
            SELECT fr.*
            FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) AS latest_year
                FROM financial_ratios
                GROUP BY company_id
            ) latest
            ON fr.company_id = latest.company_id AND fr.year = latest.latest_year
            """,
            conn,
        )

        # load peer groups table
        peer_groups = pd.read_sql_query("SELECT company_id, peer_group_name, is_benchmark FROM peer_groups", conn)

        merged = ratios.merge(peer_groups, on="company_id", how="left")

        rows = []

        for group_name, group in merged.groupby("peer_group_name"):
            if pd.isna(group_name):
                continue
            for metric in METRICS:
                if metric not in group.columns:
                    continue
                higher_better = metric != "debt_to_equity"
                pr = percent_rank(group[metric], higher_is_better=higher_better)
                if metric == "debt_to_equity":
                    pr = 100.0 - pr

                for idx, row in group.iterrows():
                    rows.append(
                        (
                            row.get("company_id"),
                            group_name,
                            metric,
                            row.get(metric),
                            float(pr.loc[idx]) if not pd.isna(pr.loc[idx]) else None,
                            int(row.get("year")) if not pd.isna(row.get("year")) else None,
                        )
                    )

        # create table peer_percentiles and insert
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS peer_percentiles (
                company_id TEXT,
                peer_group_name TEXT,
                metric TEXT,
                value REAL,
                percentile_rank REAL,
                year INTEGER
            )
            """
        )
        cur.execute("DELETE FROM peer_percentiles")
        conn.commit()

        insert_sql = "INSERT INTO peer_percentiles (company_id, peer_group_name, metric, value, percentile_rank, year) VALUES (?, ?, ?, ?, ?, ?)"
        cur.executemany(insert_sql, rows)
        conn.commit()

        # report
        print(f"Inserted {len(rows)} peer percentile rows into peer_percentiles")

    finally:
        conn.close()


if __name__ == "__main__":
    run()
