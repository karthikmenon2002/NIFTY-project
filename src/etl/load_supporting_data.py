from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)

PEER_GROUPS_FILE = (
    PROJECT_ROOT
    / "data"
    / "supporting"
    / "peer_groups.xlsx"
)

SECTORS_FILE = (
    PROJECT_ROOT
    / "data"
    / "supporting"
    / "sectors.xlsx"
)


# ============================================================
# CLEANING HELPERS
# ============================================================

def clean_company_id(value):
    """
    Standardize company IDs.
    Example:
        ' hdfcbank ' -> 'HDFCBANK'
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if value in {
        "",
        "NAN",
        "NONE",
        "NULL",
    }:
        return None

    return value


def clean_text(value):
    """
    Clean text values safely.
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in {
        "",
        "nan",
        "none",
        "null",
    }:
        return None

    return value


def clean_boolean(value):
    """
    Convert Excel boolean-like values to SQLite integers.

    True  -> 1
    False -> 0
    """

    if pd.isna(value):
        return 0

    if isinstance(value, bool):
        return int(value)

    value = str(value).strip().lower()

    if value in {
        "true",
        "1",
        "yes",
        "y",
    }:
        return 1

    return 0


def clean_number(value):
    """
    Convert a value to float safely.
    """

    if pd.isna(value):
        return None

    try:
        return float(value)

    except (ValueError, TypeError):
        return None


# ============================================================
# READ PEER GROUPS EXCEL
# ============================================================

def read_peer_groups():

    print()
    print("=" * 70)
    print("READING PEER GROUPS")
    print("=" * 70)

    if not PEER_GROUPS_FILE.exists():
        raise FileNotFoundError(
            f"Peer groups file not found:\n"
            f"{PEER_GROUPS_FILE}"
        )

    df = pd.read_excel(
        PEER_GROUPS_FILE,
        sheet_name="Sheet1",
    )

    # Clean column names
    df.columns = [
        str(column)
        .strip()
        .lower()
        for column in df.columns
    ]

    print(
        f"Source columns: {df.columns.tolist()}"
    )

    print(
        f"Source rows:    {len(df)}"
    )

    required_columns = [
        "peer_group_name",
        "company_id",
        "is_benchmark",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required peer-group columns: "
            + ", ".join(missing_columns)
        )

    # Clean values
    df["company_id"] = (
        df["company_id"]
        .apply(clean_company_id)
    )

    df["peer_group_name"] = (
        df["peer_group_name"]
        .apply(clean_text)
    )

    df["is_benchmark"] = (
        df["is_benchmark"]
        .apply(clean_boolean)
    )

    # Remove invalid rows
    before_cleaning = len(df)

    df = df.dropna(
        subset=[
            "company_id",
            "peer_group_name",
        ]
    ).copy()

    invalid_rows = (
        before_cleaning
        - len(df)
    )

    # Remove duplicate company/group rows
    duplicate_count = int(
        df.duplicated(
            subset=[
                "company_id",
                "peer_group_name",
            ],
            keep="last",
        ).sum()
    )

    df = df.drop_duplicates(
        subset=[
            "company_id",
            "peer_group_name",
        ],
        keep="last",
    )

    print()
    print("PEER GROUP SOURCE SUMMARY")
    print("-" * 70)

    print(
        f"Valid rows:             {len(df)}"
    )

    print(
        f"Invalid rows removed:   {invalid_rows}"
    )

    print(
        f"Duplicates removed:     {duplicate_count}"
    )

    print(
        f"Distinct peer groups:   "
        f"{df['peer_group_name'].nunique()}"
    )

    return df


# ============================================================
# READ SECTORS EXCEL
# ============================================================

def read_sectors():

    print()
    print("=" * 70)
    print("READING SECTORS")
    print("=" * 70)

    if not SECTORS_FILE.exists():
        raise FileNotFoundError(
            f"Sectors file not found:\n"
            f"{SECTORS_FILE}"
        )

    df = pd.read_excel(
        SECTORS_FILE,
        sheet_name="Sheet1",
    )

    # Clean column names
    df.columns = [
        str(column)
        .strip()
        .lower()
        for column in df.columns
    ]

    print(
        f"Source columns: {df.columns.tolist()}"
    )

    print(
        f"Source rows:    {len(df)}"
    )

    required_columns = [
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required sector columns: "
            + ", ".join(missing_columns)
        )

    # Clean company IDs
    df["company_id"] = (
        df["company_id"]
        .apply(clean_company_id)
    )

    # Clean text fields
    for column in [
        "broad_sector",
        "sub_sector",
        "market_cap_category",
    ]:

        df[column] = (
            df[column]
            .apply(clean_text)
        )

    # Clean index weight
    df["index_weight_pct"] = (
        df["index_weight_pct"]
        .apply(clean_number)
    )

    # Remove invalid company IDs
    before_cleaning = len(df)

    df = df.dropna(
        subset=["company_id"]
    ).copy()

    invalid_rows = (
        before_cleaning
        - len(df)
    )

    # One sector record per company
    duplicate_count = int(
        df.duplicated(
            subset=["company_id"],
            keep="last",
        ).sum()
    )

    df = df.drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    print()
    print("SECTOR SOURCE SUMMARY")
    print("-" * 70)

    print(
        f"Valid rows:             {len(df)}"
    )

    print(
        f"Invalid rows removed:   {invalid_rows}"
    )

    print(
        f"Duplicates removed:     {duplicate_count}"
    )

    print(
        f"Distinct broad sectors: "
        f"{df['broad_sector'].nunique()}"
    )

    print(
        f"Distinct sub sectors:   "
        f"{df['sub_sector'].nunique()}"
    )

    return df


# ============================================================
# GET VALID COMPANY IDs
# ============================================================

def get_valid_company_ids(conn):

    rows = conn.execute(
        """
        SELECT id
        FROM companies
        WHERE id IS NOT NULL
          AND TRIM(id) != ''
        """
    ).fetchall()

    return {
        str(row[0])
        .strip()
        .upper()
        for row in rows
    }


# ============================================================
# FILTER UNKNOWN COMPANY IDs
# ============================================================

def filter_valid_companies(
    df,
    valid_company_ids,
    label,
):

    valid_mask = (
        df["company_id"]
        .isin(valid_company_ids)
    )

    valid_df = (
        df[valid_mask]
        .copy()
    )

    invalid_df = (
        df[~valid_mask]
        .copy()
    )

    print()
    print(
        f"{label} COMPANY ID VALIDATION"
    )

    print("-" * 70)

    print(
        f"Valid rows:              "
        f"{len(valid_df)}"
    )

    print(
        f"Unknown company IDs:     "
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
            "Unknown IDs:"
        )

        print(
            unknown_ids
        )

    return valid_df


# ============================================================
# REBUILD PEER_GROUPS TABLE
# ============================================================

def rebuild_peer_groups(
    conn,
    df,
):

    print()
    print("=" * 70)
    print("REBUILDING PEER_GROUPS TABLE")
    print("=" * 70)

    # --------------------------------------------------------
    # Remove old table
    # --------------------------------------------------------

    conn.execute(
        """
        DROP TABLE IF EXISTS peer_groups
        """
    )

    # --------------------------------------------------------
    # Create correct schema
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE peer_groups
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            peer_group_name TEXT NOT NULL,

            company_id TEXT NOT NULL,

            is_benchmark INTEGER
                NOT NULL
                DEFAULT 0,

            UNIQUE(
                company_id,
                peer_group_name
            ),

            FOREIGN KEY(company_id)
                REFERENCES companies(id)
        )
        """
    )

    # --------------------------------------------------------
    # Insert data
    # --------------------------------------------------------

    inserted = 0

    for row in df.itertuples(
        index=False
    ):

        conn.execute(
            """
            INSERT INTO peer_groups
            (
                peer_group_name,
                company_id,
                is_benchmark
            )
            VALUES (?, ?, ?)
            """,
            (
                row.peer_group_name,
                row.company_id,
                int(row.is_benchmark),
            ),
        )

        inserted += 1

    print(
        f"Rows inserted: {inserted}"
    )

    return inserted


# ============================================================
# REBUILD SECTORS TABLE
# ============================================================

def rebuild_sectors(
    conn,
    df,
):

    print()
    print("=" * 70)
    print("REBUILDING SECTORS TABLE")
    print("=" * 70)

    # --------------------------------------------------------
    # Remove old table
    # --------------------------------------------------------

    conn.execute(
        """
        DROP TABLE IF EXISTS sectors
        """
    )

    # --------------------------------------------------------
    # Create correct schema
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE sectors
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT
                NOT NULL
                UNIQUE,

            broad_sector TEXT,

            sub_sector TEXT,

            index_weight_pct REAL,

            market_cap_category TEXT,

            FOREIGN KEY(company_id)
                REFERENCES companies(id)
        )
        """
    )

    # --------------------------------------------------------
    # Insert data
    # --------------------------------------------------------

    inserted = 0

    for row in df.itertuples(
        index=False
    ):

        conn.execute(
            """
            INSERT INTO sectors
            (
                company_id,
                broad_sector,
                sub_sector,
                index_weight_pct,
                market_cap_category
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row.company_id,
                row.broad_sector,
                row.sub_sector,
                row.index_weight_pct,
                row.market_cap_category,
            ),
        )

        inserted += 1

    print(
        f"Rows inserted: {inserted}"
    )

    return inserted


# ============================================================
# VALIDATE NEW SCHEMA
# ============================================================

def validate_schema(conn):

    print()
    print("=" * 70)
    print("SCHEMA VALIDATION")
    print("=" * 70)

    peer_columns = [
        row[1]
        for row in conn.execute(
            """
            PRAGMA table_info(peer_groups)
            """
        ).fetchall()
    ]

    sector_columns = [
        row[1]
        for row in conn.execute(
            """
            PRAGMA table_info(sectors)
            """
        ).fetchall()
    ]

    expected_peer_columns = [
        "id",
        "peer_group_name",
        "company_id",
        "is_benchmark",
    ]

    expected_sector_columns = [
        "id",
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]

    print(
        "peer_groups columns:"
    )

    print(
        peer_columns
    )

    print()

    print(
        "sectors columns:"
    )

    print(
        sector_columns
    )

    print()

    peer_schema_ok = (
        peer_columns
        == expected_peer_columns
    )

    sector_schema_ok = (
        sector_columns
        == expected_sector_columns
    )

    if peer_schema_ok:
        print(
            "PASS: peer_groups schema is correct."
        )
    else:
        print(
            "FAIL: peer_groups schema is incorrect."
        )

    if sector_schema_ok:
        print(
            "PASS: sectors schema is correct."
        )
    else:
        print(
            "FAIL: sectors schema is incorrect."
        )

    return (
        peer_schema_ok
        and sector_schema_ok
    )


# ============================================================
# VALIDATE LOADED DATA
# ============================================================

def validate_data(conn):

    print()
    print("=" * 70)
    print("SUPPORTING DATA VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Peer-group counts
    # --------------------------------------------------------

    peer_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM peer_groups
        """
    ).fetchone()[0]

    named_peer_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM peer_groups
        WHERE peer_group_name IS NOT NULL
          AND TRIM(peer_group_name) != ''
        """
    ).fetchone()[0]

    distinct_peer_groups = (
        conn.execute(
            """
            SELECT COUNT(
                DISTINCT peer_group_name
            )
            FROM peer_groups
            """
        ).fetchone()[0]
    )

    benchmark_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM peer_groups
        WHERE is_benchmark = 1
        """
    ).fetchone()[0]

    # --------------------------------------------------------
    # Sector counts
    # --------------------------------------------------------

    sector_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM sectors
        """
    ).fetchone()[0]

    broad_sector_count = (
        conn.execute(
            """
            SELECT COUNT(
                DISTINCT broad_sector
            )
            FROM sectors
            WHERE broad_sector IS NOT NULL
            """
        ).fetchone()[0]
    )

    sub_sector_count = (
        conn.execute(
            """
            SELECT COUNT(
                DISTINCT sub_sector
            )
            FROM sectors
            WHERE sub_sector IS NOT NULL
            """
        ).fetchone()[0]
    )

    missing_broad_sector = (
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sectors
            WHERE broad_sector IS NULL
               OR TRIM(broad_sector) = ''
            """
        ).fetchone()[0]
    )

    missing_sub_sector = (
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sectors
            WHERE sub_sector IS NULL
               OR TRIM(sub_sector) = ''
            """
        ).fetchone()[0]
    )

    # --------------------------------------------------------
    # Foreign-key validation
    # --------------------------------------------------------

    invalid_peer_companies = (
        conn.execute(
            """
            SELECT COUNT(*)
            FROM peer_groups pg
            LEFT JOIN companies c
                ON pg.company_id = c.id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]
    )

    invalid_sector_companies = (
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sectors s
            LEFT JOIN companies c
                ON s.company_id = c.id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print(
        f"peer_groups rows:             "
        f"{peer_count}"
    )

    print(
        f"Named peer-group rows:        "
        f"{named_peer_count}"
    )

    print(
        f"Distinct peer groups:         "
        f"{distinct_peer_groups}"
    )

    print(
        f"Benchmark companies:          "
        f"{benchmark_count}"
    )

    print()

    print(
        f"sectors rows:                 "
        f"{sector_count}"
    )

    print(
        f"Distinct broad sectors:       "
        f"{broad_sector_count}"
    )

    print(
        f"Distinct sub sectors:         "
        f"{sub_sector_count}"
    )

    print(
        f"Missing broad sectors:        "
        f"{missing_broad_sector}"
    )

    print(
        f"Missing sub sectors:          "
        f"{missing_sub_sector}"
    )

    print()

    print(
        f"Invalid peer company IDs:     "
        f"{invalid_peer_companies}"
    )

    print(
        f"Invalid sector company IDs:   "
        f"{invalid_sector_companies}"
    )

    # --------------------------------------------------------
    # Sample rows
    # --------------------------------------------------------

    peer_samples = conn.execute(
        """
        SELECT
            company_id,
            peer_group_name,
            is_benchmark
        FROM peer_groups
        ORDER BY id
        LIMIT 5
        """
    ).fetchall()

    sector_samples = conn.execute(
        """
        SELECT
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category
        FROM sectors
        ORDER BY id
        LIMIT 5
        """
    ).fetchall()

    print()
    print("PEER GROUP SAMPLE")
    print("-" * 70)

    for row in peer_samples:
        print(row)

    print()
    print("SECTOR SAMPLE")
    print("-" * 70)

    for row in sector_samples:
        print(row)

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    passed = (
        peer_count > 0
        and named_peer_count == peer_count
        and sector_count > 0
        and missing_broad_sector == 0
        and missing_sub_sector == 0
        and invalid_peer_companies == 0
        and invalid_sector_companies == 0
    )

    print()
    print("=" * 70)

    if passed:

        print(
            "PASS: Supporting data loaded correctly."
        )

    else:

        print(
            "FAIL: Supporting data has validation issues."
        )

    print("=" * 70)

    return passed


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("LOAD SUPPORTING DATA")
    print("REBUILD PEER_GROUPS + SECTORS")
    print("=" * 70)

    print(
        f"Database:    {DB_PATH}"
    )

    print(
        f"Peer groups: {PEER_GROUPS_FILE}"
    )

    print(
        f"Sectors:     {SECTORS_FILE}"
    )

    # --------------------------------------------------------
    # Validate files
    # --------------------------------------------------------

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found:\n"
            f"{DB_PATH}"
        )

    # --------------------------------------------------------
    # Read Excel files BEFORE modifying database
    # --------------------------------------------------------

    peer_df = read_peer_groups()

    sector_df = read_sectors()

    # --------------------------------------------------------
    # Connect to SQLite
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        conn.execute(
            """
            PRAGMA foreign_keys = ON
            """
        )

        # ----------------------------------------------------
        # Validate companies table
        # ----------------------------------------------------

        companies_table_exists = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'companies'
                """
            ).fetchone()[0]
        )

        if not companies_table_exists:
            raise RuntimeError(
                "companies table does not exist."
            )

        valid_company_ids = (
            get_valid_company_ids(conn)
        )

        print()
        print("=" * 70)
        print("COMPANY MASTER")
        print("=" * 70)

        print(
            f"Valid companies in database: "
            f"{len(valid_company_ids)}"
        )

        # ----------------------------------------------------
        # Remove unknown company IDs
        # ----------------------------------------------------

        peer_df = filter_valid_companies(
            peer_df,
            valid_company_ids,
            "PEER GROUP",
        )

        sector_df = filter_valid_companies(
            sector_df,
            valid_company_ids,
            "SECTOR",
        )

        # ----------------------------------------------------
        # Rebuild both tables
        # ----------------------------------------------------

        rebuild_peer_groups(
            conn,
            peer_df,
        )

        rebuild_sectors(
            conn,
            sector_df,
        )

        # ----------------------------------------------------
        # Commit changes
        # ----------------------------------------------------

        conn.commit()

        # ----------------------------------------------------
        # Validate corrected schema
        # ----------------------------------------------------

        schema_passed = (
            validate_schema(conn)
        )

        # ----------------------------------------------------
        # Validate loaded data
        # ----------------------------------------------------

        data_passed = (
            validate_data(conn)
        )

        # ----------------------------------------------------
        # Final status
        # ----------------------------------------------------

        print()
        print("=" * 70)

        if (
            schema_passed
            and data_passed
        ):

            print(
                "SUPPORTING DATA LOAD STATUS: PASS"
            )

            print(
                "peer_groups and sectors are ready "
                "for peer analysis."
            )

        else:

            print(
                "SUPPORTING DATA LOAD STATUS: FAIL"
            )

            print(
                "Review the validation output above."
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
    main()