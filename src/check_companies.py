from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "companies.xlsx"

df = pd.read_excel(FILE_PATH, header=1)

ids_to_check = [
    "ATGL",
    "ULTRACEMCO",
    "UNIONBANK",
    "UNITDSPR",
    "VBL",
    "VEDL",
    "WIPRO",
    "ZOMATO",
    "ZYDUSLIFE",
]

company_ids = set(
    df["id"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
)

print("===== CHECKING MASTER companies.xlsx =====")
print(f"Total master companies: {len(company_ids)}\n")

for company_id in ids_to_check:
    if company_id in company_ids:
        print(f"{company_id} -> FOUND")
    else:
        print(f"{company_id} -> MISSING")