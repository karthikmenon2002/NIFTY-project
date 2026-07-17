import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/nifty100.db")
OUTPUT_PATH = Path("output/validation_failures.csv")

def validate_database():
    conn = sqlite3.connect(DB_PATH)
    failures = []

    tables = [
        "analysis", "balancesheet", "cashflow", "companies",
        "documents", "financial_ratios", "market_cap",
        "peer_groups", "profitandloss", "prosandcons",
        "sectors", "stock_prices"
    ]

    # Check 1: Empty tables
    for table in tables:
        count = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        if count == 0:
            failures.append({
                "table": table,
                "check": "empty_table",
                "details": "Table contains 0 rows"
            })

    # Check 2: Duplicate IDs
    for table in tables:
        duplicates = conn.execute(
            f'SELECT COUNT(*) - COUNT(DISTINCT id) FROM "{table}"'
        ).fetchone()[0]

        if duplicates > 0:
            failures.append({
                "table": table,
                "check": "duplicate_id",
                "details": f"{duplicates} duplicate IDs found"
            })

    # Check 3: Invalid company_id references
    for table in tables:
        if table == "companies":
            continue

        columns = [
            row[1] for row in
            conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        ]

        if "company_id" in columns:
            invalid = conn.execute(f"""
                SELECT COUNT(*)
                FROM "{table}"
                WHERE company_id NOT IN (
                    SELECT id FROM companies
                )
            """).fetchone()[0]

            if invalid > 0:
                failures.append({
                    "table": table,
                    "check": "invalid_company_id",
                    "details": f"{invalid} invalid company_id values"
                })

    conn.close()

    result = pd.DataFrame(
        failures,
        columns=["table", "check", "details"]
    )
    result.to_csv(OUTPUT_PATH, index=False)

    print("VALIDATION COMPLETE")
    print(f"Failures found: {len(result)}")
    print(f"Report: {OUTPUT_PATH}")

if __name__ == "__main__":
    validate_database()