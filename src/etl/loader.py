from pathlib import Path
import re
import sqlite3

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_DIR = PROJECT_ROOT / "db"

DB_PATH = DB_DIR / "nifty100.db"
SCHEMA_PATH = DB_DIR / "schema.sql"

# Fallback if schema is accidentally inside db/db/schema.sql
if not SCHEMA_PATH.exists():
    fallback_schema = DB_DIR / "db" / "schema.sql"

    if fallback_schema.exists():
        SCHEMA_PATH = fallback_schema


# ============================================================
# FILE -> TABLE MAPPING
# ============================================================

# IMPORTANT:
# Do NOT map both companies.xlsx and companies_complete.xlsx
# at the same time because both files load into the same table
# and can cause:
#
# UNIQUE constraint failed: companies.id
#
# The loader will automatically choose ONE companies file.

CHILD_FILE_TABLE_MAP = {
    "profitandloss.xlsx": "profitandloss",
    "balancesheet.xlsx": "balancesheet",
    "cashflow.xlsx": "cashflow",
    "financialratios.xlsx": "financialratios",
    "shareholding.xlsx": "shareholding",
    "quarterlyresults.xlsx": "quarterlyresults",
    "annualreports.xlsx": "annualreports",
    "documents.xlsx": "documents",
    "prosandcons.xlsx": "prosandcons",
    "analysis.xlsx": "analysis",
    "market_cap.xlsx": "market_cap",
    "peer_groups.xlsx": "peer_groups",
    "sectors.xlsx": "sectors",
    "stock_prices.xlsx": "stock_prices",
}


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    # --------------------------------------------------------
    # General
    # --------------------------------------------------------
    "company": "company_id",
    "companyid": "company_id",
    "companycode": "company_id",
    "symbol": "company_id",
    "ticker": "company_id",

    # --------------------------------------------------------
    # Companies
    # --------------------------------------------------------
    "companyname": "company_name",
    "companylogo": "company_logo",
    "chartlink": "chart_link",
    "aboutcompany": "about_company",
    "nseprofile": "nse_profile",
    "bseprofile": "bse_profile",
    "facevalue": "face_value",
    "bookvalue": "book_value",
    "rocepercentage": "roce_percentage",
    "roepercentage": "roe_percentage",

    # --------------------------------------------------------
    # Profit and loss
    # --------------------------------------------------------
    "operatingprofit": "operating_profit",
    "opmpercentage": "opm_percentage",
    "opm": "opm_percentage",
    "otherincome": "other_income",
    "profitbeforetax": "profit_before_tax",
    "taxpercentage": "tax_percentage",
    "netprofit": "net_profit",
    "dividendpayout": "dividend_payout",

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------
    "equitycapital": "equity_capital",
    "otherliabilities": "other_liabilities",
    "totalliabilities": "total_liabilities",
    "fixedassets": "fixed_assets",
    "otherassets": "other_assets",
    "totalassets": "total_assets",

    # --------------------------------------------------------
    # Cash flow
    # --------------------------------------------------------
    "cashfromoperatingactivity": "cash_from_operating_activity",
    "cashfrominvestingactivity": "cash_from_investing_activity",
    "cashfromfinancingactivity": "cash_from_financing_activity",
    "netcashflow": "net_cash_flow",

    # Alternative cash flow names
    "operatingactivity": "cash_from_operating_activity",
    "investingactivity": "cash_from_investing_activity",
    "financingactivity": "cash_from_financing_activity",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalise_column_name(column):
    """
    Convert Excel column names to clean snake_case.

    Examples:
        Company Name -> company_name
        OPM %        -> opm_percentage
        Book Value   -> book_value
    """

    column = str(column).strip().lower()

    column = column.replace("%", " percentage ")
    column = column.replace("&", " and ")

    column = re.sub(r"[^a-z0-9]+", "_", column)
    column = re.sub(r"_+", "_", column)

    column = column.strip("_")

    return column


def normalise_id_value(value):
    """
    Standardise company IDs and other text IDs.

    Examples:
        " wipro "  -> "WIPRO"
        "Wipro"    -> "WIPRO"
        "nan"      -> None
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in {
        "",
        "nan",
        "none",
        "null",
        "na",
        "n/a",
    }:
        return None

    return value.upper()


def clean_column_names(df):
    """
    Clean all DataFrame column names and apply aliases.
    """

    cleaned_columns = []

    for column in df.columns:

        cleaned = normalise_column_name(column)

        compact = cleaned.replace("_", "")

        if compact in COLUMN_ALIASES:
            cleaned = COLUMN_ALIASES[compact]

        elif cleaned in COLUMN_ALIASES:
            cleaned = COLUMN_ALIASES[cleaned]

        cleaned_columns.append(cleaned)

    df.columns = cleaned_columns

    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    return df


def get_sql_table_columns(conn, table_name):
    """
    Get column names from an SQLite table.
    """

    cursor = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    return [
        row[1]
        for row in cursor.fetchall()
    ]


def get_table_info(conn, table_name):
    """
    Return PRAGMA table_info data.
    """

    cursor = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    return cursor.fetchall()


def get_database_tables(conn):
    """
    Return all user-created SQLite tables.
    """

    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )

    return [
        row[0]
        for row in cursor.fetchall()
    ]


def find_header_row(file_path, sql_columns, max_rows=20):
    """
    Automatically detect the real Excel header row.
    """

    preview = pd.read_excel(
        file_path,
        header=None,
        nrows=max_rows
    )

    sql_normalised = {
        normalise_column_name(column)
        for column in sql_columns
    }

    best_row = 0
    best_score = -1

    for row_index in range(len(preview)):

        row_values = preview.iloc[row_index].tolist()

        score = 0

        for value in row_values:

            if pd.isna(value):
                continue

            value_clean = normalise_column_name(value)
            value_compact = value_clean.replace("_", "")

            # Direct SQL column match
            if value_clean in sql_normalised:
                score += 3

            # Alias match
            if value_compact in COLUMN_ALIASES:

                alias_column = COLUMN_ALIASES[value_compact]

                if alias_column in sql_normalised:
                    score += 3

            # Common useful headers
            if value_clean in {
                "id",
                "company_id",
                "company_name",
                "year",
                "sales",
                "revenue",
                "expenses",
                "eps",
            }:
                score += 1

        if score > best_score:
            best_score = score
            best_row = row_index

    return best_row


def read_excel_safely(file_path, sql_columns):
    """
    Detect the correct header row and read the Excel file.
    """

    header_row = find_header_row(
        file_path,
        sql_columns
    )

    print(f"Reading with header={header_row}")

    df = pd.read_excel(
        file_path,
        header=header_row
    )

    print(f"Raw shape: {df.shape}")

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove completely empty columns
    df = df.dropna(
        axis=1,
        how="all"
    )

    # Clean column names
    df = clean_column_names(df)

    print(f"Cleaned shape: {df.shape}")
    print(f"Excel columns: {df.columns.tolist()}")

    return df


def clean_dataframe_values(df):
    """
    Clean values before inserting into SQLite.
    """

    df = df.copy()

    # Convert common empty values to None
    df = df.replace(
        {
            "": None,
            "-": None,
            "--": None,
            "NA": None,
            "N/A": None,
            "nan": None,
            "None": None,
            "NULL": None,
            "null": None,
        }
    )

    # Strip whitespace from text
    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = df[column].apply(
                lambda value:
                value.strip()
                if isinstance(value, str)
                else value
            )

    # Standardise ID columns
    for id_column in [
        "id",
        "company_id",
    ]:

        if id_column in df.columns:

            df[id_column] = df[id_column].apply(
                normalise_id_value
            )

    return df


def match_dataframe_to_table(
    df,
    conn,
    table_name
):
    """
    Match Excel columns with SQLite table columns.

    Extra Excel columns are ignored.
    """

    sql_columns = get_sql_table_columns(
        conn,
        table_name
    )

    print(
        f"SQL columns: {sql_columns}"
    )

    rename_map = {}

    for excel_column in df.columns:

        normalised = normalise_column_name(
            excel_column
        )

        compact = normalised.replace(
            "_",
            ""
        )

        if normalised in sql_columns:

            rename_map[excel_column] = normalised

        elif compact in COLUMN_ALIASES:

            alias_column = COLUMN_ALIASES[
                compact
            ]

            if alias_column in sql_columns:

                rename_map[
                    excel_column
                ] = alias_column

    df = df.rename(
        columns=rename_map
    )

    # Remove duplicate columns after renaming
    df = df.loc[
        :,
        ~df.columns.duplicated()
    ]

    matching_columns = [
        column
        for column in df.columns
        if column in sql_columns
    ]

    ignored_columns = [
        column
        for column in df.columns
        if column not in sql_columns
    ]

    if ignored_columns:

        print(
            "Ignoring columns not in schema:",
            ignored_columns
        )

    if not matching_columns:

        raise ValueError(
            f"\nNo matching columns found for table "
            f"'{table_name}'.\n"
            f"Excel columns: {df.columns.tolist()}\n"
            f"SQL columns: {sql_columns}"
        )

    df = df[
        matching_columns
    ].copy()

    print(
        f"Columns being loaded: "
        f"{df.columns.tolist()}"
    )

    return df


# ============================================================
# REQUIRED COLUMN VALIDATION
# ============================================================

def validate_required_columns(
    conn,
    table_name,
    df
):
    """
    Check required NOT NULL columns before inserting.
    """

    table_info = get_table_info(
        conn,
        table_name
    )

    missing_required = []

    for column_info in table_info:

        column_name = column_info[1]
        not_null = column_info[3]
        default_value = column_info[4]
        primary_key = column_info[5]

        # Skip auto-generated INTEGER primary keys
        if primary_key:
            continue

        if (
            not_null == 1
            and default_value is None
            and column_name not in df.columns
        ):

            missing_required.append(
                column_name
            )

    if missing_required:

        raise ValueError(
            f"Missing required columns for "
            f"'{table_name}': "
            f"{missing_required}"
        )


def remove_invalid_rows(
    df,
    conn,
    table_name
):
    """
    Remove rows where required NOT NULL fields are empty.
    """

    table_info = get_table_info(
        conn,
        table_name
    )

    required_columns = []

    for column_info in table_info:

        column_name = column_info[1]
        not_null = column_info[3]
        primary_key = column_info[5]

        if (
            not_null == 1
            and not primary_key
            and column_name in df.columns
        ):

            required_columns.append(
                column_name
            )

    for column in required_columns:

        before = len(df)

        df = df[
            df[column].notna()
        ].copy()

        if df[column].dtype == "object":

            df = df[
                df[column]
                .astype(str)
                .str.strip()
                != ""
            ].copy()

        removed = before - len(df)

        if removed > 0:

            print(
                f"Removed {removed} rows with "
                f"missing '{column}'"
            )

    return df


# ============================================================
# PRIMARY KEY HANDLING
# ============================================================

def get_primary_key_columns(
    conn,
    table_name
):
    """
    Return primary key columns for a table.
    """

    table_info = get_table_info(
        conn,
        table_name
    )

    primary_keys = []

    for column_info in table_info:

        column_name = column_info[1]
        primary_key_position = column_info[5]

        if primary_key_position > 0:

            primary_keys.append(
                (
                    primary_key_position,
                    column_name
                )
            )

    primary_keys.sort()

    return [
        column_name
        for _, column_name in primary_keys
    ]


def remove_duplicate_primary_keys(
    df,
    conn,
    table_name
):
    """
    Remove duplicate primary-key rows from the DataFrame.

    This prevents errors such as:

        UNIQUE constraint failed: companies.id
    """

    primary_keys = get_primary_key_columns(
        conn,
        table_name
    )

    available_primary_keys = [
        column
        for column in primary_keys
        if column in df.columns
    ]

    if not available_primary_keys:
        return df

    before = len(df)

    df = df.drop_duplicates(
        subset=available_primary_keys,
        keep="first"
    ).copy()

    removed = before - len(df)

    if removed > 0:

        print(
            f"Removed {removed} duplicate rows "
            f"using primary key(s): "
            f"{available_primary_keys}"
        )

    return df


# ============================================================
# FOREIGN KEY HANDLING
# ============================================================

def get_foreign_keys(
    conn,
    table_name
):
    """
    Return foreign key information for a table.
    """

    cursor = conn.execute(
        f'PRAGMA foreign_key_list("{table_name}")'
    )

    return cursor.fetchall()


def filter_invalid_foreign_keys(
    df,
    conn,
    table_name
):
    """
    Remove rows whose foreign-key value does not exist
    in the parent table.

    This prevents:

        FOREIGN KEY constraint failed
    """

    foreign_keys = get_foreign_keys(
        conn,
        table_name
    )

    if not foreign_keys:
        return df

    for fk in foreign_keys:

        parent_table = fk[2]
        child_column = fk[3]
        parent_column = fk[4]

        if child_column not in df.columns:
            continue

        # Standardise company IDs
        if child_column == "company_id":

            df[child_column] = df[child_column].apply(
                normalise_id_value
            )

        try:

            parent_rows = conn.execute(
                f'''
                SELECT "{parent_column}"
                FROM "{parent_table}"
                WHERE "{parent_column}" IS NOT NULL
                '''
            ).fetchall()

        except sqlite3.Error as error:

            print(
                f"WARNING: Could not validate foreign key "
                f"{table_name}.{child_column}: {error}"
            )

            continue

        valid_parent_values = {
            normalise_id_value(row[0])
            if child_column == "company_id"
            else row[0]
            for row in parent_rows
        }

        before = len(df)

        invalid_mask = (
            df[child_column].notna()
            &
            ~df[child_column].isin(
                valid_parent_values
            )
        )

        invalid_values = sorted(
            {
                str(value)
                for value in df.loc[
                    invalid_mask,
                    child_column
                ].dropna().unique()
            }
        )

        invalid_count = int(
            invalid_mask.sum()
        )

        if invalid_count > 0:

            print()
            print(
                f"WARNING: {invalid_count} rows in "
                f"'{table_name}' have invalid "
                f"{child_column} values."
            )

            print(
                f"Missing parent IDs: "
                f"{invalid_values[:30]}"
            )

            if len(invalid_values) > 30:

                print(
                    f"... and "
                    f"{len(invalid_values) - 30} more."
                )

            # Remove orphan rows
            df = df[
                ~invalid_mask
            ].copy()

            print(
                f"Removed {before - len(df)} orphan rows."
            )

    return df


# ============================================================
# SPECIAL COMPANY TABLE CLEANING
# ============================================================

def prepare_companies_dataframe(df):
    """
    Prepare companies data before loading.

    Ensures:
    - id exists
    - IDs are uppercase
    - duplicate company IDs are removed
    - missing IDs are removed
    """

    if "id" not in df.columns:

        if "company_id" in df.columns:

            df = df.rename(
                columns={
                    "company_id": "id"
                }
            )

        else:

            raise ValueError(
                "Companies file does not contain "
                "'id' or 'company_id'."
            )

    df["id"] = df["id"].apply(
        normalise_id_value
    )

    before = len(df)

    df = df[
        df["id"].notna()
    ].copy()

    removed_missing = before - len(df)

    if removed_missing > 0:

        print(
            f"Removed {removed_missing} companies "
            f"with missing IDs."
        )

    before = len(df)

    df = df.drop_duplicates(
        subset=["id"],
        keep="first"
    ).copy()

    removed_duplicates = before - len(df)

    if removed_duplicates > 0:

        print(
            f"Removed {removed_duplicates} duplicate "
            f"company IDs."
        )

    return df


# ============================================================
# INSERT DATA
# ============================================================

def insert_dataframe(
    conn,
    df,
    table_name
):
    """
    Insert a DataFrame into SQLite using sqlite3.executemany().

    pandas.DataFrame.to_sql() may commit a raw sqlite3 connection
    internally, which destroys an active SQLite SAVEPOINT and causes:

        sqlite3.OperationalError: no such savepoint: load_companies

    executemany() keeps transaction control entirely inside sqlite3.
    """

    if df.empty:
        return

    columns = list(df.columns)

    quoted_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    placeholders = ", ".join(
        "?"
        for _ in columns
    )

    insert_sql = (
        f'INSERT INTO "{table_name}" '
        f'({quoted_columns}) '
        f'VALUES ({placeholders})'
    )

    clean_df = df.astype(object).where(
        pd.notna(df),
        None
    )

    rows = [
        tuple(row)
        for row in clean_df.itertuples(
            index=False,
            name=None
        )
    ]

    savepoint_name = (
        "load_"
        + re.sub(
            r"[^a-zA-Z0-9_]",
            "_",
            table_name
        )
    )

    conn.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:

        chunk_size = 500

        for start in range(
            0,
            len(rows),
            chunk_size
        ):

            conn.executemany(
                insert_sql,
                rows[start:start + chunk_size]
            )

        conn.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )

    except Exception:

        try:
            conn.execute(
                f"ROLLBACK TO SAVEPOINT {savepoint_name}"
            )
        finally:
            conn.execute(
                f"RELEASE SAVEPOINT {savepoint_name}"
            )

        raise


# ============================================================
# LOAD ONE FILE
# ============================================================

def load_single_file(
    conn,
    table_name,
    filename
):
    """
    Load one Excel file into one SQLite table.
    """

    file_path = DATA_RAW_DIR / filename

    print()
    print("=" * 70)
    print(f"Loading {filename}")
    print(f"Target table: {table_name}")
    print("=" * 70)

    if not file_path.exists():

        print(
            f"SKIPPED: File not found: "
            f"{file_path}"
        )

        return {
            "file": filename,
            "table": table_name,
            "status": "SKIPPED",
            "rows": 0,
            "message": "File not found",
        }

    sql_columns = get_sql_table_columns(
        conn,
        table_name
    )

    if not sql_columns:

        print(
            f"SKIPPED: Table '{table_name}' "
            f"does not exist."
        )

        return {
            "file": filename,
            "table": table_name,
            "status": "SKIPPED",
            "rows": 0,
            "message": "Table not found",
        }

    # --------------------------------------------------------
    # Read Excel
    # --------------------------------------------------------

    df = read_excel_safely(
        file_path,
        sql_columns
    )

    # --------------------------------------------------------
    # Clean values
    # --------------------------------------------------------

    df = clean_dataframe_values(
        df
    )

    # --------------------------------------------------------
    # Match Excel columns to SQL schema
    # --------------------------------------------------------

    df = match_dataframe_to_table(
        df,
        conn,
        table_name
    )

    # --------------------------------------------------------
    # Special company cleaning
    # --------------------------------------------------------

    if table_name == "companies":

        df = prepare_companies_dataframe(
            df
        )

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    validate_required_columns(
        conn,
        table_name,
        df
    )

    # --------------------------------------------------------
    # Remove rows missing required values
    # --------------------------------------------------------

    df = remove_invalid_rows(
        df,
        conn,
        table_name
    )

    # --------------------------------------------------------
    # Remove duplicate primary keys
    # --------------------------------------------------------

    df = remove_duplicate_primary_keys(
        df,
        conn,
        table_name
    )

    # --------------------------------------------------------
    # Remove invalid foreign-key rows
    # --------------------------------------------------------

    if table_name != "companies":

        df = filter_invalid_foreign_keys(
            df,
            conn,
            table_name
        )

    # --------------------------------------------------------
    # Stop if nothing remains
    # --------------------------------------------------------

    if df.empty:

        print(
            f"WARNING: No valid rows found "
            f"for {filename}"
        )

        return {
            "file": filename,
            "table": table_name,
            "status": "EMPTY",
            "rows": 0,
            "message": "No valid rows",
        }

    # --------------------------------------------------------
    # Insert
    # --------------------------------------------------------

    insert_dataframe(
        conn,
        df,
        table_name
    )

    conn.commit()

    row_count = len(df)

    print(
        f"SUCCESS: {row_count:,} rows loaded."
    )

    return {
        "file": filename,
        "table": table_name,
        "status": "SUCCESS",
        "rows": row_count,
        "message": "",
    }


# ============================================================
# DATABASE CREATION
# ============================================================

def create_database():
    """
    Delete old database and create a fresh database
    using schema.sql.
    """

    DB_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if DB_PATH.exists():

        DB_PATH.unlink()

        print(
            "Old database deleted."
        )

    if not SCHEMA_PATH.exists():

        raise FileNotFoundError(
            f"schema.sql not found.\n"
            f"Expected location: {SCHEMA_PATH}"
        )

    print(
        "Creating database schema..."
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    # Enable foreign keys
    conn.execute(
        "PRAGMA foreign_keys = ON;"
    )

    schema_sql = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    conn.executescript(
        schema_sql
    )

    conn.commit()

    print(
        "Database schema created."
    )

    return conn


# ============================================================
# SELECT COMPANIES FILE
# ============================================================

def get_companies_file():
    """
    Select exactly ONE companies file.

    Priority:
        1. companies_complete.xlsx
        2. companies.xlsx

    This prevents loading the companies table twice.
    """

    preferred_files = [
        "companies_complete.xlsx",
        "companies.xlsx",
    ]

    for filename in preferred_files:

        file_path = DATA_RAW_DIR / filename

        if file_path.exists():

            return filename

    return None


# ============================================================
# FIND FILES TO LOAD
# ============================================================

def get_files_to_load(conn):
    """
    Build the load order.

    Parent table 'companies' is always loaded first.
    Child tables are loaded afterwards.
    """

    files_to_load = []

    database_tables = set(
        get_database_tables(conn)
    )

    # --------------------------------------------------------
    # 1. Companies MUST load first
    # --------------------------------------------------------

    companies_file = get_companies_file()

    if companies_file is not None:

        if "companies" in database_tables:

            files_to_load.append(
                (
                    companies_file,
                    "companies"
                )
            )

    # --------------------------------------------------------
    # 2. Child tables
    # --------------------------------------------------------

    for filename, table_name in CHILD_FILE_TABLE_MAP.items():

        file_path = DATA_RAW_DIR / filename

        if (
            file_path.exists()
            and table_name in database_tables
        ):

            files_to_load.append(
                (
                    filename,
                    table_name
                )
            )

    return files_to_load


# ============================================================
# FOREIGN KEY CHECK
# ============================================================

def run_foreign_key_check(conn):
    """
    Run SQLite's final foreign-key integrity check.
    """

    print()
    print("=" * 70)
    print("FOREIGN KEY CHECK")
    print("=" * 70)

    violations = conn.execute(
        "PRAGMA foreign_key_check;"
    ).fetchall()

    if not violations:

        print(
            "PASS: No foreign key violations found."
        )

        return True

    print(
        f"FAILED: {len(violations)} foreign key "
        f"violation(s) found."
    )

    for violation in violations[:50]:

        print(
            violation
        )

    if len(violations) > 50:

        print(
            f"... and "
            f"{len(violations) - 50} more."
        )

    return False


# ============================================================
# AUDIT REPORT
# ============================================================

def print_audit_report(
    conn,
    results
):
    """
    Print ETL loading summary.
    """

    print()
    print("=" * 70)
    print("LOAD AUDIT REPORT")
    print("=" * 70)

    for result in results:

        print(
            f"{result['status']:10} | "
            f"{result['table']:20} | "
            f"{result['rows']:8,} rows | "
            f"{result['file']}"
        )

        if result["message"]:

            print(
                f"{'':10}   "
                f"Message: "
                f"{result['message']}"
            )

    print()
    print("=" * 70)
    print("DATABASE TABLE COUNTS")
    print("=" * 70)

    tables = get_database_tables(
        conn
    )

    for table_name in tables:

        try:

            count = conn.execute(
                f'''
                SELECT COUNT(*)
                FROM "{table_name}"
                '''
            ).fetchone()[0]

            print(
                f"{table_name:25} "
                f"{count:,} rows"
            )

        except sqlite3.Error as error:

            print(
                f"{table_name:25} "
                f"ERROR: {error}"
            )


# ============================================================
# MAIN LOADER
# ============================================================

def load_excel_files():

    print()
    print("=" * 70)
    print("NIFTY 100 DATABASE LOADER")
    print("=" * 70)

    print(
        f"Project root: {PROJECT_ROOT}"
    )

    print(
        f"Raw data:    {DATA_RAW_DIR}"
    )

    print(
        f"Database:    {DB_PATH}"
    )

    print(
        f"Schema:      {SCHEMA_PATH}"
    )

    conn = None

    try:

        # ----------------------------------------------------
        # Create fresh database
        # ----------------------------------------------------

        conn = create_database()

        # ----------------------------------------------------
        # Show database tables
        # ----------------------------------------------------

        database_tables = get_database_tables(
            conn
        )

        print()
        print(
            "Database tables:"
        )

        for table in database_tables:

            print(
                f"  - {table}"
            )

        # ----------------------------------------------------
        # Find files in correct order
        # ----------------------------------------------------

        files_to_load = get_files_to_load(
            conn
        )

        if not files_to_load:

            raise FileNotFoundError(
                f"No mapped Excel files found in:\n"
                f"{DATA_RAW_DIR}"
            )

        print()
        print("=" * 70)
        print("LOAD ORDER")
        print("=" * 70)

        for index, (
            filename,
            table_name
        ) in enumerate(
            files_to_load,
            start=1
        ):

            print(
                f"{index:2}. "
                f"{filename:30} "
                f"-> {table_name}"
            )

        # ----------------------------------------------------
        # Ensure companies is first
        # ----------------------------------------------------

        if files_to_load[0][1] != "companies":

            raise RuntimeError(
                "The companies table must be loaded first."
            )

        # ----------------------------------------------------
        # Load files
        # ----------------------------------------------------

        results = []

        for filename, table_name in files_to_load:

            try:

                result = load_single_file(
                    conn,
                    table_name,
                    filename
                )

                results.append(
                    result
                )

                # ------------------------------------------------
                # Companies must load successfully before children
                # ------------------------------------------------

                if (
                    table_name == "companies"
                    and result["status"] != "SUCCESS"
                ):

                    raise RuntimeError(
                        "Companies table failed to load. "
                        "Child tables cannot be loaded safely."
                    )

            except Exception as error:

                print()
                print(
                    f"FAILED: {filename}"
                )

                print(
                    f"ERROR: {error}"
                )

                results.append(
                    {
                        "file": filename,
                        "table": table_name,
                        "status": "FAILED",
                        "rows": 0,
                        "message": str(error),
                    }
                )

                # If companies fail, stop immediately.
                if table_name == "companies":

                    raise RuntimeError(
                        "Companies table failed. "
                        "Stopping loader to prevent "
                        "foreign-key failures."
                    ) from error

                # Other tables may continue
                continue

        # ----------------------------------------------------
        # Final audit
        # ----------------------------------------------------

        print_audit_report(
            conn,
            results
        )

        # ----------------------------------------------------
        # Foreign key integrity check
        # ----------------------------------------------------

        foreign_keys_ok = run_foreign_key_check(
            conn
        )

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        failed_results = [
            result
            for result in results
            if result["status"] == "FAILED"
        ]

        print()
        print("=" * 70)

        if (
            not failed_results
            and foreign_keys_ok
        ):

            print(
                "LOAD COMPLETE - SUCCESS"
            )

        else:

            print(
                "LOAD COMPLETE - WITH WARNINGS"
            )

        print("=" * 70)

        print(
            f"Database: {DB_PATH}"
        )

        print(
            f"Files processed: {len(results)}"
        )

        print(
            f"Successful: "
            f"{sum(
                result['status'] == 'SUCCESS'
                for result in results
            )}"
        )

        print(
            f"Failed: "
            f"{sum(
                result['status'] == 'FAILED'
                for result in results
            )}"
        )

        print(
            f"Empty: "
            f"{sum(
                result['status'] == 'EMPTY'
                for result in results
            )}"
        )

        print(
            f"Skipped: "
            f"{sum(
                result['status'] == 'SKIPPED'
                for result in results
            )}"
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("LOADER FAILED")
        print("=" * 70)

        print(
            f"ERROR: {error}"
        )

        raise

    finally:

        if conn is not None:

            conn.close()


# ============================================================
# RUN LOADER
# ============================================================

if __name__ == "__main__":
    load_excel_files()