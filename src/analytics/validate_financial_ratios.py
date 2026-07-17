"""
NIFTY 100 PROJECT
SPRINT 2 - FINANCIAL RATIO ENGINE
DAY 13 - VALIDATE FINANCIAL_RATIOS

Validates:
1. Database and required tables
2. Source and target row counts
3. Eligible company-year completeness
4. NULL company IDs
5. Invalid foreign keys
6. Duplicate company-year rows
7. Missing company-year records
8. Extra company-year records
9. Year validity
10. Numeric ratio sanity
11. CAGR flag validity
12. Capital-allocation classification validity
13. Company coverage
14. Overall validation status
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable


# ======================================================================
# PATHS
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

VALIDATION_REPORT = OUTPUT_DIR / "financial_ratios_validation.txt"


# ======================================================================
# CONFIGURATION
# ======================================================================

REQUIRED_TABLES = {
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
}

SOURCE_TABLES = (
    "profitandloss",
    "balancesheet",
    "cashflow",
)

KEY_COLUMNS = {
    "company_id",
    "year",
}

VALID_CAGR_FLAGS = {
    None,
    "",
    "NONE",
    "NORMAL",
    "DECLINE_TO_LOSS",
    "TURNAROUND",
    "BOTH_NEGATIVE",
    "ZERO_BASE",
    "INSUFFICIENT_DATA",
}

VALID_CAPITAL_ALLOCATION_PATTERNS = {
    None,
    "",
    "Reinvestor",
    "Shareholder Returns",
    "Liquidating Assets",
    "Distress Signal",
    "Growth Funded by Debt",
    "Cash Accumulator",
    "Pre-Revenue",
    "Mixed",
    "Unknown",
}

CAGR_FLAG_COLUMNS = (
    "revenue_cagr_3yr_flag",
    "revenue_cagr_5yr_flag",
    "revenue_cagr_10yr_flag",
    "pat_cagr_3yr_flag",
    "pat_cagr_5yr_flag",
    "pat_cagr_10yr_flag",
    "eps_cagr_3yr_flag",
    "eps_cagr_5yr_flag",
    "eps_cagr_10yr_flag",
)

CRITICAL_RATIO_COLUMNS = (
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "cfo_pat_ratio",
    "capex_intensity_pct",
    "fcf_conversion_rate_pct",
)

EXTREME_RATIO_LIMITS = {
    "net_profit_margin_pct": (-10000, 10000),
    "operating_profit_margin_pct": (-10000, 10000),
    "return_on_equity_pct": (-10000, 10000),
    "return_on_capital_employed_pct": (-10000, 10000),
    "return_on_assets_pct": (-10000, 10000),
    "debt_to_equity": (-10000, 10000),
    "interest_coverage": (-100000, 100000),
    "asset_turnover": (-10000, 10000),
    "cfo_pat_ratio": (-100000, 100000),
    "capex_intensity_pct": (-100000, 100000),
    "fcf_conversion_rate_pct": (-100000, 100000),
}


# ======================================================================
# OUTPUT HELPERS
# ======================================================================

REPORT_LINES: list[str] = []


def emit(message: str = "") -> None:
    """
    Print a message and also store it for the validation report.
    """

    text = str(message)

    print(text)

    REPORT_LINES.append(text)


def separator(
    character: str = "=",
    width: int = 70,
) -> None:
    emit(character * width)


def section(title: str) -> None:
    emit()
    separator("=")
    emit(title)
    separator("=")


def subsection(title: str) -> None:
    emit()
    emit(title)
    emit("-" * 70)


# ======================================================================
# GENERAL HELPERS
# ======================================================================

def quote_identifier(identifier: str) -> str:
    """
    Safely quote a SQLite identifier.
    """

    return '"' + identifier.replace('"', '""') + '"'


def normalize_company_id(value: Any) -> str | None:
    """
    Normalize company IDs for comparison.

    Examples:
        " ABB " -> "ABB"
        "abb"   -> "ABB"
        None    -> None
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text.upper()


def normalize_year(value: Any) -> int | None:
    """
    Convert different year representations into an integer year.

    Handles values such as:
        2024
        "2024"
        "Mar 2024"
        "Dec 2012"
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        if 1800 <= value <= 2200:
            return value

    if isinstance(value, float):
        if math.isnan(value):
            return None

        integer_value = int(value)

        if (
            value == integer_value
            and 1800 <= integer_value <= 2200
        ):
            return integer_value

    text = str(value).strip()

    if not text:
        return None

    # Direct integer-like string.
    try:
        numeric = float(text)

        integer_value = int(numeric)

        if (
            numeric == integer_value
            and 1800 <= integer_value <= 2200
        ):
            return integer_value

    except (TypeError, ValueError):
        pass

    # Extract a four-digit year from strings such as "Mar 2024".
    for token in text.replace("-", " ").replace("/", " ").split():
        token = token.strip()

        if (
            len(token) == 4
            and token.isdigit()
        ):
            year = int(token)

            if 1800 <= year <= 2200:
                return year

    return None


def is_finite_number(value: Any) -> bool:
    """
    Return True when value is a finite numeric value.
    """

    if value is None:
        return False

    try:
        number = float(value)

    except (TypeError, ValueError):
        return False

    return math.isfinite(number)


# ======================================================================
# DATABASE HELPERS
# ======================================================================

def connect_database() -> sqlite3.Connection:
    """
    Open the project SQLite database.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def get_table_names(
    conn: sqlite3.Connection,
) -> set[str]:
    """
    Return all non-system table names.
    """

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return {
        row["name"]
        for row in rows
    }


def get_table_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[str]:
    """
    Return column names for a table.
    """

    quoted_table = quote_identifier(table_name)

    rows = conn.execute(
        f"PRAGMA table_info({quoted_table})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def count_rows(
    conn: sqlite3.Connection,
    table_name: str,
) -> int:
    """
    Count rows in a table.
    """

    quoted_table = quote_identifier(table_name)

    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table}"
        ).fetchone()[0]
    )


# ======================================================================
# COMPANY-YEAR SET BUILDERS
# ======================================================================

def fetch_company_ids(
    conn: sqlite3.Connection,
) -> set[str]:
    """
    Return normalized valid company IDs from companies.
    """

    rows = conn.execute(
        """
        SELECT id
        FROM companies
        WHERE id IS NOT NULL
        """
    ).fetchall()

    result: set[str] = set()

    for row in rows:
        company_id = normalize_company_id(
            row["id"]
        )

        if company_id is not None:
            result.add(company_id)

    return result


def fetch_source_company_years(
    conn: sqlite3.Connection,
) -> set[tuple[str, int]]:
    """
    Build the union of valid company-year combinations from:
        profitandloss
        balancesheet
        cashflow

    Only company IDs that exist in companies are included.

    This mirrors the population strategy where all available valid
    company-year combinations are eligible for financial_ratios.
    """

    valid_company_ids = fetch_company_ids(conn)

    combinations: set[tuple[str, int]] = set()

    for table_name in SOURCE_TABLES:

        columns = set(
            get_table_columns(
                conn,
                table_name,
            )
        )

        if not {
            "company_id",
            "year",
        }.issubset(columns):
            continue

        quoted_table = quote_identifier(
            table_name
        )

        rows = conn.execute(
            f"""
            SELECT company_id, year
            FROM {quoted_table}
            WHERE company_id IS NOT NULL
              AND year IS NOT NULL
            """
        ).fetchall()

        for row in rows:

            company_id = normalize_company_id(
                row["company_id"]
            )

            year = normalize_year(
                row["year"]
            )

            if company_id is None:
                continue

            if year is None:
                continue

            if company_id not in valid_company_ids:
                continue

            combinations.add(
                (
                    company_id,
                    year,
                )
            )

    return combinations


def fetch_target_company_years(
    conn: sqlite3.Connection,
) -> set[tuple[str, int]]:
    """
    Return valid normalized company-year combinations from
    financial_ratios.
    """

    rows = conn.execute(
        """
        SELECT company_id, year
        FROM financial_ratios
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        """
    ).fetchall()

    combinations: set[tuple[str, int]] = set()

    for row in rows:

        company_id = normalize_company_id(
            row["company_id"]
        )

        year = normalize_year(
            row["year"]
        )

        if (
            company_id is not None
            and year is not None
        ):
            combinations.add(
                (
                    company_id,
                    year,
                )
            )

    return combinations


# ======================================================================
# VALIDATION RESULT TRACKING
# ======================================================================

class ValidationResults:
    """
    Track passed checks, warnings and failures.
    """

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failed: list[str] = []

    def pass_check(
        self,
        message: str,
    ) -> None:
        self.passed.append(message)

        emit(
            f"PASS: {message}"
        )

    def warn(
        self,
        message: str,
    ) -> None:
        self.warnings.append(message)

        emit(
            f"WARNING: {message}"
        )

    def fail(
        self,
        message: str,
    ) -> None:
        self.failed.append(message)

        emit(
            f"FAIL: {message}"
        )


# ======================================================================
# VALIDATION CHECKS
# ======================================================================

def validate_required_tables(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Verify all required tables exist.
    """

    subsection(
        "1. REQUIRED TABLE CHECK"
    )

    existing_tables = get_table_names(conn)

    missing_tables = (
        REQUIRED_TABLES
        - existing_tables
    )

    if not missing_tables:
        results.pass_check(
            "All required tables exist."
        )

    else:
        results.fail(
            "Missing required tables: "
            + ", ".join(
                sorted(missing_tables)
            )
        )


def validate_required_columns(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Verify required financial_ratios key columns.
    """

    subsection(
        "2. REQUIRED COLUMN CHECK"
    )

    columns = set(
        get_table_columns(
            conn,
            "financial_ratios",
        )
    )

    missing_columns = (
        KEY_COLUMNS
        - columns
    )

    if not missing_columns:
        results.pass_check(
            "financial_ratios contains company_id and year."
        )

    else:
        results.fail(
            "financial_ratios is missing columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )


def validate_row_counts(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> tuple[
    int,
    int,
    set[tuple[str, int]],
    set[tuple[str, int]],
]:
    """
    Compare actual target rows with eligible source combinations.
    """

    subsection(
        "3. ROW COUNT AND COMPLETENESS CHECK"
    )

    source_combinations = (
        fetch_source_company_years(conn)
    )

    target_combinations = (
        fetch_target_company_years(conn)
    )

    eligible_count = len(
        source_combinations
    )

    final_count = count_rows(
        conn,
        "financial_ratios",
    )

    unique_target_count = len(
        target_combinations
    )

    completeness = (
        (
            unique_target_count
            / eligible_count
        )
        * 100
        if eligible_count
        else 0.0
    )

    emit(
        f"Eligible company-year combinations: {eligible_count}"
    )

    emit(
        f"financial_ratios rows:              {final_count}"
    )

    emit(
        f"Unique target company-years:        {unique_target_count}"
    )

    emit(
        f"Completeness:                       {completeness:.2f}%"
    )

    if (
        final_count == eligible_count
        and unique_target_count == eligible_count
    ):
        results.pass_check(
            "Row completeness is 100%."
        )

    else:
        results.fail(
            "Row completeness mismatch: "
            f"eligible={eligible_count}, "
            f"rows={final_count}, "
            f"unique_target={unique_target_count}."
        )

    # Informational sprint target only.
    if final_count < 1100:
        results.warn(
            f"Row count is {final_count}, below the nominal "
            "Sprint target of 1,100; however, the actual "
            f"eligible source population is {eligible_count}."
        )

    return (
        eligible_count,
        final_count,
        source_combinations,
        target_combinations,
    )


def validate_null_company_ids(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check for NULL or blank company IDs.
    """

    subsection(
        "4. NULL COMPANY ID CHECK"
    )

    null_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios
        WHERE company_id IS NULL
           OR TRIM(company_id) = ''
        """
    ).fetchone()[0]

    emit(
        f"NULL/blank company IDs: {null_count}"
    )

    if null_count == 0:
        results.pass_check(
            "No NULL or blank company IDs."
        )

    else:
        results.fail(
            f"Found {null_count} NULL or blank company IDs."
        )


def validate_foreign_keys(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check invalid company IDs and SQLite FK violations.
    """

    subsection(
        "5. FOREIGN KEY CHECK"
    )

    invalid_rows = conn.execute(
        """
        SELECT
            fr.company_id,
            fr.year
        FROM financial_ratios AS fr
        LEFT JOIN companies AS c
            ON UPPER(TRIM(fr.company_id))
             = UPPER(TRIM(c.id))
        WHERE c.id IS NULL
        ORDER BY
            fr.company_id,
            fr.year
        """
    ).fetchall()

    emit(
        f"Invalid company references: {len(invalid_rows)}"
    )

    fk_violations = conn.execute(
        """
        PRAGMA foreign_key_check
        """
    ).fetchall()

    emit(
        f"SQLite foreign-key violations: {len(fk_violations)}"
    )

    if (
        not invalid_rows
        and not fk_violations
    ):
        results.pass_check(
            "All company IDs are valid and no foreign-key "
            "violations were found."
        )

    else:
        results.fail(
            "Foreign-key validation failed."
        )

        for row in invalid_rows[:10]:
            emit(
                "  Invalid company-year: "
                f"{row['company_id']} | "
                f"{row['year']}"
            )

        for row in fk_violations[:10]:
            emit(
                f"  FK violation: {tuple(row)}"
            )


def validate_duplicates(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check duplicate company-year rows.
    """

    subsection(
        "6. DUPLICATE COMPANY-YEAR CHECK"
    )

    duplicates = conn.execute(
        """
        SELECT
            company_id,
            year,
            COUNT(*) AS duplicate_count
        FROM financial_ratios
        GROUP BY
            company_id,
            year
        HAVING COUNT(*) > 1
        ORDER BY
            duplicate_count DESC,
            company_id,
            year
        """
    ).fetchall()

    emit(
        f"Duplicate company-year groups: {len(duplicates)}"
    )

    if not duplicates:
        results.pass_check(
            "No duplicate company-year rows."
        )

    else:
        results.fail(
            f"Found {len(duplicates)} duplicate "
            "company-year groups."
        )

        for row in duplicates[:20]:
            emit(
                "  "
                f"{row['company_id']} | "
                f"{row['year']} | "
                f"count={row['duplicate_count']}"
            )


def validate_missing_and_extra_rows(
    source_combinations: set[tuple[str, int]],
    target_combinations: set[tuple[str, int]],
    results: ValidationResults,
) -> None:
    """
    Compare eligible source combinations with target combinations.
    """

    subsection(
        "7. SOURCE-TARGET COVERAGE CHECK"
    )

    missing = sorted(
        source_combinations
        - target_combinations
    )

    extra = sorted(
        target_combinations
        - source_combinations
    )

    emit(
        f"Missing eligible company-year rows: {len(missing)}"
    )

    emit(
        f"Unexpected extra company-year rows: {len(extra)}"
    )

    if not missing:
        results.pass_check(
            "No eligible company-year combinations are missing."
        )

    else:
        results.fail(
            f"{len(missing)} eligible company-year "
            "combinations are missing."
        )

        emit(
            "First missing records:"
        )

        for company_id, year in missing[:20]:
            emit(
                f"  {company_id} | {year}"
            )

    if not extra:
        results.pass_check(
            "No unexpected extra company-year combinations."
        )

    else:
        results.warn(
            f"Found {len(extra)} target company-year "
            "combinations not present in the eligible source union."
        )

        emit(
            "First extra records:"
        )

        for company_id, year in extra[:20]:
            emit(
                f"  {company_id} | {year}"
            )


def validate_years(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check NULL and unreasonable years.
    """

    subsection(
        "8. YEAR VALIDATION"
    )

    rows = conn.execute(
        """
        SELECT
            company_id,
            year
        FROM financial_ratios
        """
    ).fetchall()

    invalid_years: list[
        tuple[Any, Any]
    ] = []

    normalized_years: list[int] = []

    for row in rows:

        year = normalize_year(
            row["year"]
        )

        if year is None:
            invalid_years.append(
                (
                    row["company_id"],
                    row["year"],
                )
            )

        else:
            normalized_years.append(
                year
            )

    emit(
        f"Invalid years: {len(invalid_years)}"
    )

    if normalized_years:
        emit(
            f"Minimum year: {min(normalized_years)}"
        )

        emit(
            f"Maximum year: {max(normalized_years)}"
        )

    if not invalid_years:
        results.pass_check(
            "All target years are valid."
        )

    else:
        results.fail(
            f"Found {len(invalid_years)} invalid years."
        )

        for company_id, year in invalid_years[:20]:
            emit(
                f"  {company_id} | {year}"
            )


def validate_company_coverage(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Compare company coverage between companies and financial_ratios.
    """

    subsection(
        "9. COMPANY COVERAGE CHECK"
    )

    all_companies = fetch_company_ids(conn)

    target_rows = conn.execute(
        """
        SELECT DISTINCT company_id
        FROM financial_ratios
        WHERE company_id IS NOT NULL
        """
    ).fetchall()

    target_companies = {
        company_id
        for row in target_rows
        if (
            company_id := normalize_company_id(
                row["company_id"]
            )
        )
        is not None
    }

    missing_companies = sorted(
        all_companies
        - target_companies
    )

    emit(
        f"Companies table:                  {len(all_companies)}"
    )

    emit(
        f"Companies in financial_ratios:    {len(target_companies)}"
    )

    emit(
        f"Companies without ratio records:  {len(missing_companies)}"
    )

    if not missing_companies:
        results.pass_check(
            "All companies have at least one financial-ratio record."
        )

    else:
        results.warn(
            f"{len(missing_companies)} companies have no "
            "financial-ratio records."
        )

        for company_id in missing_companies[:20]:
            emit(
                f"  {company_id}"
            )


def validate_numeric_values(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check numeric ratio columns for non-finite or extreme values.
    """

    subsection(
        "10. NUMERIC RATIO SANITY CHECK"
    )

    existing_columns = set(
        get_table_columns(
            conn,
            "financial_ratios",
        )
    )

    available_columns = [
        column
        for column in CRITICAL_RATIO_COLUMNS
        if column in existing_columns
    ]

    if not available_columns:
        results.warn(
            "None of the configured critical ratio columns "
            "exist in financial_ratios."
        )

        return

    selected_columns = [
        "company_id",
        "year",
        *available_columns,
    ]

    select_sql = ", ".join(
        quote_identifier(column)
        for column in selected_columns
    )

    rows = conn.execute(
        f"""
        SELECT {select_sql}
        FROM financial_ratios
        """
    ).fetchall()

    non_finite_values: list[
        tuple[str, Any, str, Any]
    ] = []

    extreme_values: list[
        tuple[str, Any, str, Any]
    ] = []

    for row in rows:

        company_id = row["company_id"]

        year = row["year"]

        for column in available_columns:

            value = row[column]

            if value is None:
                continue

            if not is_finite_number(value):

                non_finite_values.append(
                    (
                        company_id,
                        year,
                        column,
                        value,
                    )
                )

                continue

            number = float(value)

            lower_limit, upper_limit = (
                EXTREME_RATIO_LIMITS[column]
            )

            if (
                number < lower_limit
                or number > upper_limit
            ):
                extreme_values.append(
                    (
                        company_id,
                        year,
                        column,
                        value,
                    )
                )

    emit(
        f"Non-finite numeric values: {len(non_finite_values)}"
    )

    emit(
        f"Extreme numeric values:    {len(extreme_values)}"
    )

    if not non_finite_values:
        results.pass_check(
            "No NaN or infinite values detected in "
            "critical ratio columns."
        )

    else:
        results.fail(
            f"Found {len(non_finite_values)} non-finite "
            "numeric values."
        )

        for item in non_finite_values[:20]:
            emit(
                "  "
                f"{item[0]} | "
                f"{item[1]} | "
                f"{item[2]} = "
                f"{item[3]}"
            )

    if not extreme_values:
        results.pass_check(
            "No extreme values exceeded configured sanity limits."
        )

    else:
        results.warn(
            f"Found {len(extreme_values)} values outside "
            "configured sanity limits."
        )

        for item in extreme_values[:20]:
            emit(
                "  "
                f"{item[0]} | "
                f"{item[1]} | "
                f"{item[2]} = "
                f"{item[3]}"
            )


def validate_cagr_flags(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Check CAGR flags against known edge-case values.
    """

    subsection(
        "11. CAGR FLAG VALIDATION"
    )

    existing_columns = set(
        get_table_columns(
            conn,
            "financial_ratios",
        )
    )

    available_flag_columns = [
        column
        for column in CAGR_FLAG_COLUMNS
        if column in existing_columns
    ]

    if not available_flag_columns:
        results.warn(
            "No CAGR flag columns were found."
        )

        return

    invalid_flags: list[
        tuple[str, Any, str, Any]
    ] = []

    for column in available_flag_columns:

        quoted_column = quote_identifier(
            column
        )

        rows = conn.execute(
            f"""
            SELECT
                company_id,
                year,
                {quoted_column} AS flag_value
            FROM financial_ratios
            WHERE {quoted_column} IS NOT NULL
            """
        ).fetchall()

        for row in rows:

            raw_flag = row["flag_value"]

            normalized_flag = (
                str(raw_flag).strip().upper()
                if raw_flag is not None
                else None
            )

            if normalized_flag not in VALID_CAGR_FLAGS:

                invalid_flags.append(
                    (
                        row["company_id"],
                        row["year"],
                        column,
                        raw_flag,
                    )
                )

    emit(
        f"Invalid CAGR flags: {len(invalid_flags)}"
    )

    if not invalid_flags:
        results.pass_check(
            "All CAGR flags use recognized values."
        )

    else:
        results.fail(
            f"Found {len(invalid_flags)} invalid CAGR flags."
        )

        for item in invalid_flags[:20]:
            emit(
                "  "
                f"{item[0]} | "
                f"{item[1]} | "
                f"{item[2]} = "
                f"{item[3]}"
            )


def validate_capital_allocation(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Validate capital-allocation classifications.
    """

    subsection(
        "12. CAPITAL ALLOCATION VALIDATION"
    )

    columns = set(
        get_table_columns(
            conn,
            "financial_ratios",
        )
    )

    column_name = (
        "capital_allocation_pattern"
    )

    if column_name not in columns:

        results.warn(
            "capital_allocation_pattern column does not exist."
        )

        return

    rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            capital_allocation_pattern
        FROM financial_ratios
        """
    ).fetchall()

    invalid_patterns: list[
        tuple[Any, Any, Any]
    ] = []

    pattern_counts: dict[str, int] = {}

    for row in rows:

        raw_pattern = (
            row["capital_allocation_pattern"]
        )

        if raw_pattern is None:
            normalized_pattern = None

        else:
            normalized_pattern = str(
                raw_pattern
            ).strip()

        if (
            normalized_pattern
            not in VALID_CAPITAL_ALLOCATION_PATTERNS
        ):
            invalid_patterns.append(
                (
                    row["company_id"],
                    row["year"],
                    raw_pattern,
                )
            )

        display_pattern = (
            normalized_pattern
            if normalized_pattern
            else "NULL/BLANK"
        )

        pattern_counts[display_pattern] = (
            pattern_counts.get(
                display_pattern,
                0,
            )
            + 1
        )

    emit(
        "Capital allocation distribution:"
    )

    for pattern, count in sorted(
        pattern_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        emit(
            f"  {pattern}: {count}"
        )

    emit(
        f"Invalid capital-allocation patterns: "
        f"{len(invalid_patterns)}"
    )

    if not invalid_patterns:
        results.pass_check(
            "All capital-allocation patterns are recognized."
        )

    else:
        results.fail(
            f"Found {len(invalid_patterns)} invalid "
            "capital-allocation classifications."
        )

        for item in invalid_patterns[:20]:
            emit(
                "  "
                f"{item[0]} | "
                f"{item[1]} | "
                f"{item[2]}"
            )


def validate_null_distribution(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Report NULL percentages for financial ratio columns.

    NULL values are not automatically failures because many ratios
    legitimately cannot be calculated for every company-year.
    """

    subsection(
        "13. NULL DISTRIBUTION REPORT"
    )

    columns = get_table_columns(
        conn,
        "financial_ratios",
    )

    excluded_columns = {
        "id",
        "company_id",
        "year",
    }

    ratio_columns = [
        column
        for column in columns
        if column not in excluded_columns
    ]

    total_rows = count_rows(
        conn,
        "financial_ratios",
    )

    if total_rows == 0:

        results.fail(
            "financial_ratios is empty."
        )

        return

    null_statistics: list[
        tuple[str, int, float]
    ] = []

    for column in ratio_columns:

        quoted_column = quote_identifier(
            column
        )

        null_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM financial_ratios
            WHERE {quoted_column} IS NULL
            """
        ).fetchone()[0]

        null_pct = (
            null_count
            / total_rows
        ) * 100

        null_statistics.append(
            (
                column,
                null_count,
                null_pct,
            )
        )

    null_statistics.sort(
        key=lambda item: (
            -item[2],
            item[0],
        )
    )

    emit(
        "Columns with highest NULL percentages:"
    )

    for (
        column,
        null_count,
        null_pct,
    ) in null_statistics[:20]:

        emit(
            f"  {column:<35} "
            f"{null_count:>5} "
            f"({null_pct:>6.2f}%)"
        )

    completely_null_columns = [
        column
        for (
            column,
            _,
            null_pct,
        ) in null_statistics
        if null_pct == 100.0
    ]

    if completely_null_columns:

        results.warn(
            "Completely NULL columns: "
            + ", ".join(
                completely_null_columns
            )
        )

    else:
        results.pass_check(
            "No ratio column is completely NULL."
        )


def validate_database_integrity(
    conn: sqlite3.Connection,
    results: ValidationResults,
) -> None:
    """
    Run SQLite integrity check.
    """

    subsection(
        "14. SQLITE DATABASE INTEGRITY CHECK"
    )

    result = conn.execute(
        """
        PRAGMA integrity_check
        """
    ).fetchone()[0]

    emit(
        f"SQLite integrity result: {result}"
    )

    if str(result).lower() == "ok":

        results.pass_check(
            "SQLite database integrity check passed."
        )

    else:
        results.fail(
            f"SQLite integrity check failed: {result}"
        )


# ======================================================================
# REPORT WRITER
# ======================================================================

def write_report() -> None:
    """
    Save validation output to a text file.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    VALIDATION_REPORT.write_text(
        "\n".join(REPORT_LINES) + "\n",
        encoding="utf-8",
    )


# ======================================================================
# MAIN VALIDATION FUNCTION
# ======================================================================

def validate_financial_ratios() -> int:
    """
    Run the complete Day 13 financial-ratio validation suite.

    Returns:
        0 -> validation passed
        1 -> validation failed
    """

    REPORT_LINES.clear()

    separator("=")

    emit(
        "SPRINT 2 - FINANCIAL RATIO ENGINE"
    )

    emit(
        "DAY 13 - VALIDATE FINANCIAL_RATIOS"
    )

    separator("=")

    emit(
        f"Database: {DB_PATH}"
    )

    results = ValidationResults()

    conn: sqlite3.Connection | None = None

    try:

        conn = connect_database()

        # --------------------------------------------------------------
        # SOURCE ROW COUNTS
        # --------------------------------------------------------------

        subsection(
            "SOURCE AND TARGET ROW COUNTS"
        )

        for table_name in (
            "companies",
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
        ):

            table_count = count_rows(
                conn,
                table_name,
            )

            emit(
                f"{table_name:<20} "
                f"{table_count}"
            )

        # --------------------------------------------------------------
        # VALIDATION CHECKS
        # --------------------------------------------------------------

        validate_required_tables(
            conn,
            results,
        )

        validate_required_columns(
            conn,
            results,
        )

        (
            eligible_count,
            final_count,
            source_combinations,
            target_combinations,
        ) = validate_row_counts(
            conn,
            results,
        )

        validate_null_company_ids(
            conn,
            results,
        )

        validate_foreign_keys(
            conn,
            results,
        )

        validate_duplicates(
            conn,
            results,
        )

        validate_missing_and_extra_rows(
            source_combinations,
            target_combinations,
            results,
        )

        validate_years(
            conn,
            results,
        )

        validate_company_coverage(
            conn,
            results,
        )

        validate_numeric_values(
            conn,
            results,
        )

        validate_cagr_flags(
            conn,
            results,
        )

        validate_capital_allocation(
            conn,
            results,
        )

        validate_null_distribution(
            conn,
            results,
        )

        validate_database_integrity(
            conn,
            results,
        )

        # --------------------------------------------------------------
        # FINAL SUMMARY
        # --------------------------------------------------------------

        section(
            "DAY 13 VALIDATION SUMMARY"
        )

        emit(
            f"Eligible company-year combinations: {eligible_count}"
        )

        emit(
            f"financial_ratios rows:              {final_count}"
        )

        emit(
            f"Passed checks:                      {len(results.passed)}"
        )

        emit(
            f"Warnings:                           {len(results.warnings)}"
        )

        emit(
            f"Failed checks:                      {len(results.failed)}"
        )

        emit()

        if results.warnings:

            emit(
                "WARNINGS"
            )

            emit(
                "-" * 70
            )

            for index, warning in enumerate(
                results.warnings,
                start=1,
            ):
                emit(
                    f"{index}. {warning}"
                )

        if results.failed:

            emit()

            emit(
                "FAILED CHECKS"
            )

            emit(
                "-" * 70
            )

            for index, failure in enumerate(
                results.failed,
                start=1,
            ):
                emit(
                    f"{index}. {failure}"
                )

        emit()

        separator("=")

        if not results.failed:

            emit(
                "DAY 13 VALIDATION STATUS: PASS"
            )

            emit(
                "financial_ratios successfully represents "
                "the available eligible source data."
            )

            if (
                eligible_count == final_count
                and final_count < 1100
            ):
                emit()

                emit(
                    "NOTE: The nominal Sprint target is >= 1,100 rows, "
                    f"but the current database contains only "
                    f"{eligible_count} eligible unique company-year "
                    "combinations."
                )

                emit(
                    "No artificial rows should be created solely "
                    "to reach 1,100."
                )

            exit_code = 0

        else:

            emit(
                "DAY 13 VALIDATION STATUS: FAIL"
            )

            emit(
                "Fix the failed checks before continuing "
                "to peer analysis."
            )

            exit_code = 1

        separator("=")

        emit()

        emit(
            "Validation report:"
        )

        emit(
            str(VALIDATION_REPORT)
        )

        return exit_code

    except Exception as error:

        emit()

        separator("=")

        emit(
            "VALIDATION SCRIPT FAILED"
        )

        separator("=")

        emit(
            f"{type(error).__name__}: {error}"
        )

        return 1

    finally:

        if conn is not None:
            conn.close()

        try:
            write_report()

        except Exception as report_error:
            print(
                "WARNING: Could not write validation report:"
            )

            print(
                report_error
            )


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    sys.exit(
        validate_financial_ratios()
    )