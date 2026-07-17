import sqlite3

conn = sqlite3.connect("data/nifty100.db")

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("TABLES IN DATABASE:")
for table in tables:
    print(table[0])

print("\nROW COUNTS:")
for table in tables:
    table_name = table[0]
    count = conn.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()[0]
    print(f"{table_name}: {count} rows")

conn.close()