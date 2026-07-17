from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "cashflow.xlsx"
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# ============================================================
# HELPERS
# ============================================================

def normalize_company_id(value):
    """Clean company IDs."""
    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if value in {"", "NAN", "NONE", "NULL"}:
        return None

    return value


def normalize_year(value):
    """
    Convert:
        Mar-13 -> 2013
        Mar-24 -> 2024
        2024   -> 2024
    """
    if pd.isna(value):
        return None

    # Handle numeric years
    if isinstance(value, (int, float)):
        try:
            year = int(value)

            if 1900 <= year <= 2100:
                return year
        except (ValueError, TypeError):
            pass

    value = str(value).strip()

    if not value:
        return None

    # Four-digit year
    if value.isdigit() and len(value) == 4:
        year = int(value)

        if 1900 <= year <= 2100:
            return year

    # Explicit Mar-13 style
    try:
        parsed = pd.to_datetime(
            value,
            format="%b-%y",
            errors="raise"
        )
        return int(parsed.year)

    except (ValueError, TypeError):
        pass

    # General fallback
    try:
        parsed = pd.to_datetime(
            value,
            errors="raise"
        )
        return int(parsed.year)

    except (ValueError, TypeError):
        return None


def to_number(value):
    """Convert Excel values safely to float."""
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()

        if value in {
            "",
            "-",
            "--",
            "NA",
            "N/A",
            "None",
            "null",
        }:
            return None

        value = value.replace(",", "")

        # Handle accounting negative format: (123) -> -123
        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]

    try:
        return float(value)

    except (ValueError, TypeError):
        return None


# ============================================================
# MAIN
# ============================================================

def fix_cashflow():

    print("=" * 70)
    print("FIX CASHFLOW DATA - FULL RELOAD")
    print("=" * 70)

    print(f"Excel:    {EXCEL_PATH}")
    print(f"Database: {DB_PATH}")
    print()

    # --------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"Cash-flow Excel file not found:\n{EXCEL_PATH}"
        )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found:\n{DB_PATH}"
        )

    # --------------------------------------------------------
    # 1. LOAD EXCEL
    #
    # First Excel row is the Bluestock title.
    # Second row contains actual headers.
    # --------------------------------------------------------

    df = pd.read_excel(
        EXCEL_PATH,
        sheet_name="Cash Flow",
        header=1,
    )

    print("RAW SOURCE COLUMNS")
    print("-" * 70)
    print(df.columns.tolist())
    print()

    # --------------------------------------------------------
    # 2. NORMALIZE COLUMN NAMES
    # --------------------------------------------------------

    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in df.columns
    ]

    # --------------------------------------------------------
    # 3. RENAME SOURCE COLUMNS TO DATABASE COLUMNS
    # --------------------------------------------------------

    df = df.rename(
        columns={
            "operating_activity":
                "operating_cash_flow",

            "investing_activity":
                "investing_cash_flow",

            "financing_activity":
                "financing_cash_flow",
        }
    )

    required_columns = [
        "company_id",
        "year",
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "net_cash_flow",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required Excel columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # 4. CLEAN DATA
    # --------------------------------------------------------

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year"] = (
        df["year"]
        .apply(normalize_year)
    )

    numeric_columns = [
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "net_cash_flow",
    ]

    for column in numeric_columns:
        df[column] = (
            df[column]
            .apply(to_number)
        )

    # --------------------------------------------------------
    # 5. REMOVE INVALID COMPANY/YEAR ROWS
    # --------------------------------------------------------

    source_count = len(df)

    invalid_company_year = df[
        df["company_id"].isna()
        | df["year"].isna()
    ].copy()

    df = df.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    df["year"] = df["year"].astype(int)

    print("SOURCE CLEANING SUMMARY")
    print("-" * 70)

    print(
        f"Rows read:                     "
        f"{source_count}"
    )

    print(
        f"Invalid company/year rows:     "
        f"{len(invalid_company_year)}"
    )

    print(
        f"Valid rows:                    "
        f"{len(df)}"
    )

    print()

    # --------------------------------------------------------
    # 6. REMOVE EXACT DUPLICATE COMPANY-YEAR ROWS
    # --------------------------------------------------------

    duplicate_count = int(
        df.duplicated(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        ).sum()
    )

    if duplicate_count > 0:

        print(
            f"Duplicate company-year rows:   "
            f"{duplicate_count}"
        )

        print(
            "Keeping the last source row for "
            "each duplicate company-year."
        )

        df = df.drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )

        print()

    # --------------------------------------------------------
    # 7. SOURCE VALUE COUNTS
    # --------------------------------------------------------

    print("NON-NULL SOURCE VALUES")
    print("-" * 70)

    for column in numeric_columns:

        print(
            f"{column:<30}"
            f"{df[column].notna().sum()}"
        )

    print()

    # --------------------------------------------------------
    # 8. CONNECT TO DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:

        cursor = conn.cursor()

        # ----------------------------------------------------
        # 9. CHECK CASHFLOW TABLE
        # ----------------------------------------------------

        table_exists = cursor.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'cashflow'
            """
        ).fetchone()[0]

        if not table_exists:

            raise RuntimeError(
                "cashflow table does not exist."
            )

        # ----------------------------------------------------
        # 10. CHECK VALID COMPANY IDs
        # ----------------------------------------------------

        valid_companies = {
            str(row[0]).strip().upper()
            for row in cursor.execute(
                """
                SELECT id
                FROM companies
                WHERE id IS NOT NULL
                """
            ).fetchall()
        }

        print("COMPANY ID VALIDATION")
        print("-" * 70)

        print(
            f"Companies in database:         "
            f"{len(valid_companies)}"
        )

        # Split valid and invalid company IDs
        valid_mask = (
            df["company_id"]
            .isin(valid_companies)
        )

        valid_df = (
            df[valid_mask]
            .copy()
        )

        invalid_df = (
            df[~valid_mask]
            .copy()
        )

        print(
            f"Cashflow rows with valid IDs:  "
            f"{len(valid_df)}"
        )

        print(
            f"Rows with unknown company IDs: "
            f"{len(invalid_df)}"
        )

        if not invalid_df.empty:

            unknown_ids = sorted(
                invalid_df[
                    "company_id"
                ]
                .dropna()
                .unique()
                .tolist()
            )

            print()
            print(
                "Unknown company IDs:"
            )

            print(
                unknown_ids
            )

        print()

        if valid_df.empty:

            raise RuntimeError(
                "No cash-flow rows have company IDs "
                "matching the companies table."
            )

        # ----------------------------------------------------
        # 11. BACKUP OLD CASHFLOW TABLE DATA
        # ----------------------------------------------------

        old_count = cursor.execute(
            """
            SELECT COUNT(*)
            FROM cashflow
            """
        ).fetchone()[0]

        print("DATABASE RELOAD")
        print("-" * 70)

        print(
            f"Existing cashflow rows:         "
            f"{old_count}"
        )

        # ----------------------------------------------------
        # 12. DELETE OLD INCORRECT CASHFLOW DATA
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM cashflow
            """
        )

        # ----------------------------------------------------
        # 13. INSERT CLEAN SOURCE DATA
        # ----------------------------------------------------

        inserted = 0
        insert_errors = 0

        for row in valid_df.itertuples(
            index=False
        ):

            try:

                cursor.execute(
                    """
                    INSERT INTO cashflow
                    (
                        company_id,
                        year,
                        operating_cash_flow,
                        investing_cash_flow,
                        financing_cash_flow,
                        net_cash_flow
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.company_id,
                        int(row.year),

                        row.operating_cash_flow,
                        row.investing_cash_flow,
                        row.financing_cash_flow,
                        row.net_cash_flow,
                    ),
                )

                inserted += 1

            except sqlite3.IntegrityError as error:

                insert_errors += 1

                print(
                    "INSERT ERROR:",
                    row.company_id,
                    row.year,
                    error,
                )

        # ----------------------------------------------------
        # 14. COMMIT
        # ----------------------------------------------------

        conn.commit()

        # ----------------------------------------------------
        # 15. DATABASE VALIDATION
        # ----------------------------------------------------

        total_rows = cursor.execute(
            """
            SELECT COUNT(*)
            FROM cashflow
            """
        ).fetchone()[0]

        distinct_companies = cursor.execute(
            """
            SELECT COUNT(
                DISTINCT company_id
            )
            FROM cashflow
            """
        ).fetchone()[0]

        non_null_ocf = cursor.execute(
            """
            SELECT COUNT(
                operating_cash_flow
            )
            FROM cashflow
            """
        ).fetchone()[0]

        non_null_icf = cursor.execute(
            """
            SELECT COUNT(
                investing_cash_flow
            )
            FROM cashflow
            """
        ).fetchone()[0]

        non_null_financing = cursor.execute(
            """
            SELECT COUNT(
                financing_cash_flow
            )
            FROM cashflow
            """
        ).fetchone()[0]

        non_null_net = cursor.execute(
            """
            SELECT COUNT(
                net_cash_flow
            )
            FROM cashflow
            """
        ).fetchone()[0]

        null_company_ids = cursor.execute(
            """
            SELECT COUNT(*)
            FROM cashflow
            WHERE company_id IS NULL
               OR TRIM(company_id) = ''
            """
        ).fetchone()[0]

        duplicate_company_years = (
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM
                (
                    SELECT
                        company_id,
                        year,
                        COUNT(*) AS row_count
                    FROM cashflow
                    GROUP BY
                        company_id,
                        year
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )

        # ----------------------------------------------------
        # 16. PRINT RESULTS
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print(
            "CASHFLOW FULL RELOAD COMPLETE"
        )
        print("=" * 70)

        print(
            f"Rows inserted:                 "
            f"{inserted}"
        )

        print(
            f"Insert errors:                 "
            f"{insert_errors}"
        )

        print(
            f"Final cashflow rows:           "
            f"{total_rows}"
        )

        print(
            f"Distinct companies:            "
            f"{distinct_companies}"
        )

        print(
            f"NULL company IDs:              "
            f"{null_company_ids}"
        )

        print(
            f"Duplicate company-year rows:   "
            f"{duplicate_company_years}"
        )

        print()

        print("NON-NULL DATABASE VALUES")
        print("-" * 70)

        print(
            f"Operating cash flow:           "
            f"{non_null_ocf}"
        )

        print(
            f"Investing cash flow:           "
            f"{non_null_icf}"
        )

        print(
            f"Financing cash flow:           "
            f"{non_null_financing}"
        )

        print(
            f"Net cash flow:                 "
            f"{non_null_net}"
        )

        # ----------------------------------------------------
        # 17. SAMPLE ROWS
        # ----------------------------------------------------

        samples = cursor.execute(
            """
            SELECT
                company_id,
                year,
                operating_cash_flow,
                investing_cash_flow,
                financing_cash_flow,
                net_cash_flow
            FROM cashflow
            ORDER BY
                company_id,
                year
            LIMIT 10
            """
        ).fetchall()

        print()
        print("SAMPLE CASHFLOW ROWS")
        print("-" * 70)

        for sample in samples:
            print(sample)

        # ----------------------------------------------------
        # 18. FINAL STATUS
        # ----------------------------------------------------

        print()
        print("=" * 70)

        if (
            total_rows > 0
            and non_null_ocf > 0
            and non_null_icf > 0
            and non_null_financing > 0
            and null_company_ids == 0
            and duplicate_company_years == 0
        ):

            print(
                "PASS: Cash-flow data successfully "
                "reloaded."
            )

        else:

            print(
                "WARNING: Cash-flow reload completed "
                "with validation issues."
            )

        print("=" * 70)

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    fix_cashflow()