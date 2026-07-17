from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPANIES_FILE = PROJECT_ROOT / "data" / "raw" / "companies.xlsx"

# Missing company IDs found in your validation
MISSING_COMPANIES = [
    "AGTL",
    "ULTRACEMCO",
    "UNIONBANK",
    "UNITDSPR",
    "VBL",
    "VEDL",
    "WIPRO",
    "ZOMATO",
    "ZYDUSLIFE",
]

# Read the companies file
df = pd.read_excel(COMPANIES_FILE, header=1)

# Clean column names
df.columns = [
    str(col).strip().lower().replace(" ", "_")
    for col in df.columns
]

# Clean existing IDs
df["id"] = (
    df["id"]
    .astype(str)
    .str.strip()
    .str.upper()
)

existing_ids = set(df["id"])

print("Existing companies:", len(df))

# Add missing IDs
new_rows = []

for company_id in MISSING_COMPANIES:
    if company_id not in existing_ids:
        new_row = {col: None for col in df.columns}
        new_row["id"] = company_id
        new_rows.append(new_row)
        print(f"Adding: {company_id}")

if new_rows:
    new_df = pd.DataFrame(new_rows)
    df = pd.concat([df, new_df], ignore_index=True)

# Save a cleaned master file
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "companies_complete.xlsx"

df.to_excel(OUTPUT_FILE, index=False)

print("\nDONE")
print("Total companies:", len(df))
print("Saved to:", OUTPUT_FILE)