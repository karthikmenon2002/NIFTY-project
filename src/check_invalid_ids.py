import sqlite3

conn = sqlite3.connect("data/nifty100.db")

tables = [
    "analysis",
    "balancesheet",
    "cashflow",
    "documents",
    "financial_ratios",
    "profitandloss",
    "prosandcons"
]

for table in tables:
    rows = conn.execute(f"""
        SELECT DISTINCT company_id
        FROM {table}
        WHERE company_id NOT IN (
            SELECT id FROM companies
        )
        ORDER BY company_id
    """).fetchall()

    print(f"{table}: {[row[0] for row in rows]}")

conn.close()