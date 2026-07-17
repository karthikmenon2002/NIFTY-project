from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"

# Load master companies file
companies_path = RAW_DIR / "companies.xlsx"
companies_df = pd.read_excel(companies_path, header=1)

# First column is the real company ID/ticker
master_ids = set(
    companies_df.iloc[:, 0]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
)

print(f"MASTER COMPANY IDs: {len(master_ids)}")
print("Sample:", sorted(master_ids)[:10])

files = [
    RAW_DIR / "profitandloss.xlsx",
    RAW_DIR / "balancesheet.xlsx",
    RAW_DIR / "cashflow.xlsx",
    RAW_DIR / "analysis.xlsx",
    RAW_DIR / "documents.xlsx",
    RAW_DIR / "prosandcons.xlsx",
    SUPPORTING_DIR / "financial_ratios.xlsx",
    SUPPORTING_DIR / "market_cap.xlsx",
    SUPPORTING_DIR / "peer_groups.xlsx",
    SUPPORTING_DIR / "sectors.xlsx",
    SUPPORTING_DIR / "stock_prices.xlsx",
]

print("\nCOMPANY IDs NOT IN MASTER:")

for file_path in files:
    if not file_path.exists():
        print(f"{file_path.name}: FILE NOT FOUND")
        continue

    # Core files have header on Excel row 2
    if file_path.parent == RAW_DIR:
        df = pd.read_excel(file_path, header=1)
    else:
        df = pd.read_excel(file_path)

    # Standardize column names
    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    if "company_id" in df.columns:
        ids = set(
            df["company_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )
    elif "id" in df.columns:
        ids = set(
            df["id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )
    else:
        print(f"{file_path.name}: NO company_id/id COLUMN")
        continue

    missing = sorted(ids - master_ids)

    if missing:
        print(f"{file_path.name}: {missing}")
    else:
        print(f"{file_path.name}: OK")