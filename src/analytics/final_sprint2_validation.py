"""
NIFTY 100 PROJECT
SPRINT 2 - FINANCIAL RATIO ENGINE
FINAL SPRINT 2 VALIDATION

Validates:
1. Database file
2. Required Sprint 2 tables
3. Source and target row counts
4. Company coverage
5. Financial-ratios schema
6. Financial-ratios completeness
7. Duplicate company-year rows
8. NULL company IDs
9. Foreign keys
10. Cash-flow source data
11. Cash-flow derived ratios
12. Capital allocation
13. Peer-group and sector data
14. Peer-analysis output
15. Peer-group summary
16. Financial-ratio validation report
17. SQLite database integrity
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path
from typing import Any


# ======================================================================
# PATHS
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"

FINANCIAL_VALIDATION_REPORT = (
    OUTPUT_DIR / "financial_ratios_validation.txt"
)

FINAL_VALIDATION_REPORT = (
    OUTPUT_DIR / "sprint2_final_validation.txt"
)

PEER_ANALYSIS_CSV = (
    OUTPUT_DIR / "peer_analysis.csv"
)

PEER_GROUP_SUMMARY_CSV = (
    OUTPUT_DIR / "peer_group_summary.csv"
)


# ======================================================================
# CONFIGURATION
# ======================================================================

REQUIRED_TABLES = {
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
    "peer_groups",
    "sectors",
}

SOURCE_TABLES = (
    "profitandloss",
    "balancesheet",
    "cashflow",
)

REQUIRED_FINANCIAL_RATIO_COLUMNS = {
    "company_id",
    "year",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "cash_from_operations_cr",
    "cfo_pat_ratio",
    "capex_cr",
    "fcf_conversion_rate_pct",
    "capital_allocation_pattern",
    "composite_quality_score",
}

CASHFLOW_COLUMNS = (
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "net_cash_flow",
)

CASHFLOW_DERIVED_COLUMNS = (
    "cash_from_operations_cr",
    "free_cash_flow_cr",
    "cfo_pat_ratio",
    "fcf_conversion_rate_pct",
)


# ======================================================================
# OUTPUT
# ======================================================================

REPORT_LINES: list[str] = []


def emit(message: str = "") -> None:
    text = str(message)

    print(text)

    REPORT_LINES.append(text)


def separator(
    character: str = "=",
    width: int = 70,
) -> None:
    emit(character * width)


def subsection(title: str) -> None:
    emit()
    emit(title)
    emit("-" * 70)


def write_report() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_VALIDATION_REPORT.write_text(
        "\n".join(REPORT_LINES) + "\n",
        encoding="utf-8",
    )


# ======================================================================
# RESULT TRACKING
# ======================================================================

class ValidationResults:

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
# GENERAL HELPERS
# ======================================================================

def quote_identifier(
    identifier: str,
) -> str:

    return (
        '"'
        + identifier.replace('"', '""')
        + '"'
    )


def normalize_company_id(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text.upper()


def normalize_year(
    value: Any,
) -> int | None:

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

    # Direct numeric year
    try:

        numeric = float(text)

        integer_value = int(numeric)

        if (
            numeric == integer_value
            and 1800 <= integer_value <= 2200
        ):
            return integer_value

    except (
        TypeError,
        ValueError,
    ):
        pass

    # Extract 4-digit year
    for token in (
        text
        .replace("-", " ")
        .replace("/", " ")
        .split()
    ):

        token = token.strip()

        if (
            len(token) == 4
            and token.isdigit()
        ):

            year = int(token)

            if 1800 <= year <= 2200:
                return year

    return None


# ======================================================================
# DATABASE HELPERS
# ======================================================================

def connect_database() -> sqlite3.Connection:

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def get_table_names(
    conn: sqlite3.Connection,
) -> set[str]:

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
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

    quoted_table = quote_identifier(
        table_name
    )

    rows = conn.execute(
        f"""
        PRAGMA table_info({quoted_table})
        """
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def count_rows(
    conn: sqlite3.Connection,
    table_name: str,
) -> int:

    quoted_table = quote_identifier(
        table_name
    )

    return int(
        conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {quoted_table}
            """
        ).fetchone()[0]
    )


# ======================================================================
# COMPANY-YEAR ELIGIBILITY
#
# IMPORTANT:
# This intentionally matches validate_financial_ratios.py.
#
# Eligible rows are the UNION of valid company-year combinations from:
#
#     profitandloss
#     balancesheet
#     cashflow
#
# Only company IDs existing in companies.id are included.
# ======================================================================

def fetch_valid_company_ids(
    conn: sqlite3.Connection,
) -> set[str]:

    rows = conn.execute(
        """
        SELECT id
        FROM companies
        WHERE id IS NOT NULL
        """
    ).fetchall()

    valid_ids: set[str] = set()

    for row in rows:

        company_id = normalize_company_id(
            row["id"]
        )

        if company_id is not None:

            valid_ids.add(
                company_id
            )

    return valid_ids


def fetch_eligible_company_years(
    conn: sqlite3.Connection,
) -> set[tuple[str, int]]:

    valid_company_ids = (
        fetch_valid_company_ids(conn)
    )

    eligible: set[
        tuple[str, int]
    ] = set()

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
            SELECT
                company_id,
                year
            FROM {quoted_table}
            WHERE company_id IS NOT NULL
              AND year IS NOT NULL
            """
        ).fetchall()

        for row in rows:

            company_id = (
                normalize_company_id(
                    row["company_id"]
                )
            )

            year = normalize_year(
                row["year"]
            )

            if company_id is None:
                continue

            if year is None:
                continue

            if (
                company_id
                not in valid_company_ids
            ):
                continue

            eligible.add(
                (
                    company_id,
                    year,
                )
            )

    return eligible


def fetch_target_company_years(
    conn: sqlite3.Connection,
) -> set[tuple[str, int]]:

    rows = conn.execute(
        """
        SELECT
            company_id,
            year
        FROM financial_ratios
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        """
    ).fetchall()

    target: set[
        tuple[str, int]
    ] = set()

    for row in rows:

        company_id = (
            normalize_company_id(
                row["company_id"]
            )
        )

        year = normalize_year(
            row["year"]
        )

        if (
            company_id is not None
            and year is not None
        ):

            target.add(
                (
                    company_id,
                    year,
                )
            )

    return target


# ======================================================================
# MAIN VALIDATION
# ======================================================================

def run_validation() -> int:

    REPORT_LINES.clear()

    separator()

    emit(
        "SPRINT 2 - FINANCIAL RATIO ENGINE"
    )

    emit(
        "FINAL SPRINT 2 VALIDATION"
    )

    separator()

    emit(
        f"Database: {DB_PATH}"
    )

    results = ValidationResults()

    conn: sqlite3.Connection | None = None

    try:

        # ==============================================================
        # 1. DATABASE FILE
        # ==============================================================

        subsection(
            "1. DATABASE FILE CHECK"
        )

        if DB_PATH.exists():

            results.pass_check(
                "Database file exists."
            )

        else:

            results.fail(
                f"Database file does not exist: {DB_PATH}"
            )

            return 1

        conn = connect_database()

        # ==============================================================
        # 2. REQUIRED TABLES
        # ==============================================================

        subsection(
            "2. REQUIRED TABLE CHECK"
        )

        existing_tables = (
            get_table_names(conn)
        )

        missing_tables = (
            REQUIRED_TABLES
            - existing_tables
        )

        if not missing_tables:

            results.pass_check(
                "All required Sprint 2 tables exist."
            )

        else:

            results.fail(
                "Missing required tables: "
                + ", ".join(
                    sorted(
                        missing_tables
                    )
                )
            )

            return 1

        # ==============================================================
        # 3. SOURCE AND TARGET ROW COUNTS
        # ==============================================================

        subsection(
            "3. SOURCE AND TARGET ROW COUNTS"
        )

        table_counts: dict[
            str,
            int,
        ] = {}

        for table_name in (
            "companies",
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
            "peer_groups",
            "sectors",
        ):

            table_count = count_rows(
                conn,
                table_name,
            )

            table_counts[
                table_name
            ] = table_count

            emit(
                f"{table_name:<22} "
                f"{table_count}"
            )

        # ==============================================================
        # 4. COMPANY COVERAGE
        # ==============================================================

        subsection(
            "4. COMPANY COVERAGE CHECK"
        )

        valid_company_ids = (
            fetch_valid_company_ids(conn)
        )

        ratio_company_rows = (
            conn.execute(
                """
                SELECT DISTINCT company_id
                FROM financial_ratios
                WHERE company_id IS NOT NULL
                  AND TRIM(company_id) != ''
                """
            ).fetchall()
        )

        ratio_company_ids = {
            company_id
            for row in ratio_company_rows
            if (
                company_id
                := normalize_company_id(
                    row["company_id"]
                )
            )
            is not None
        }

        sector_company_rows = (
            conn.execute(
                """
                SELECT DISTINCT company_id
                FROM sectors
                WHERE company_id IS NOT NULL
                  AND TRIM(company_id) != ''
                """
            ).fetchall()
        )

        sector_company_ids = {
            company_id
            for row in sector_company_rows
            if (
                company_id
                := normalize_company_id(
                    row["company_id"]
                )
            )
            is not None
        }

        emit(
            f"Companies table:               "
            f"{len(valid_company_ids)}"
        )

        emit(
            f"Companies in financial ratios: "
            f"{len(ratio_company_ids)}"
        )

        emit(
            f"Companies with sector data:    "
            f"{len(sector_company_ids)}"
        )

        missing_ratio_companies = (
            valid_company_ids
            - ratio_company_ids
        )

        missing_sector_companies = (
            valid_company_ids
            - sector_company_ids
        )

        if (
            not missing_ratio_companies
            and not missing_sector_companies
        ):

            results.pass_check(
                "All companies are represented "
                "in the core Sprint 2 data."
            )

        else:

            if missing_ratio_companies:

                results.fail(
                    f"{len(missing_ratio_companies)} "
                    "companies are missing from "
                    "financial_ratios."
                )

            if missing_sector_companies:

                results.fail(
                    f"{len(missing_sector_companies)} "
                    "companies are missing sector data."
                )

        # ==============================================================
        # 5. FINANCIAL RATIOS SCHEMA
        # ==============================================================

        subsection(
            "5. FINANCIAL RATIOS SCHEMA CHECK"
        )

        ratio_columns = set(
            get_table_columns(
                conn,
                "financial_ratios",
            )
        )

        missing_ratio_columns = (
            REQUIRED_FINANCIAL_RATIO_COLUMNS
            - ratio_columns
        )

        if not missing_ratio_columns:

            results.pass_check(
                "Required financial-ratio columns are present."
            )

        else:

            results.fail(
                "Missing financial-ratio columns: "
                + ", ".join(
                    sorted(
                        missing_ratio_columns
                    )
                )
            )

        # ==============================================================
        # 6. FINANCIAL RATIOS COMPLETENESS
        #
        # FIXED:
        # Uses exact same source-union logic as Day 13 validator.
        # ==============================================================

        subsection(
            "6. FINANCIAL RATIOS COMPLETENESS CHECK"
        )

        eligible_company_years = (
            fetch_eligible_company_years(
                conn
            )
        )

        target_company_years = (
            fetch_target_company_years(
                conn
            )
        )

        eligible_count = len(
            eligible_company_years
        )

        financial_ratio_rows = (
            table_counts[
                "financial_ratios"
            ]
        )

        unique_company_years = len(
            target_company_years
        )

        matched_company_years = (
            eligible_company_years
            & target_company_years
        )

        missing_rows = sorted(
            eligible_company_years
            - target_company_years
        )

        unexpected_rows = sorted(
            target_company_years
            - eligible_company_years
        )

        completeness = (
            (
                len(
                    matched_company_years
                )
                / eligible_count
            )
            * 100
            if eligible_count
            else 0.0
        )

        emit(
            f"Eligible company-years:       "
            f"{eligible_count}"
        )

        emit(
            f"financial_ratios rows:        "
            f"{financial_ratio_rows}"
        )

        emit(
            f"Unique company-years:         "
            f"{unique_company_years}"
        )

        emit(
            f"Completeness:                 "
            f"{completeness:.2f}%"
        )

        emit(
            f"Missing eligible rows:        "
            f"{len(missing_rows)}"
        )

        emit(
            f"Unexpected extra rows:        "
            f"{len(unexpected_rows)}"
        )

        if (
            financial_ratio_rows
            == eligible_count
            and unique_company_years
            == eligible_count
            and not missing_rows
            and not unexpected_rows
        ):

            results.pass_check(
                "Financial-ratio source coverage is complete."
            )

        else:

            results.fail(
                "Financial-ratio source coverage is incomplete."
            )

            if missing_rows:

                emit()

                emit(
                    "Sample missing company-years:"
                )

                for (
                    company_id,
                    year,
                ) in missing_rows[:20]:

                    emit(
                        f"  {company_id} | {year}"
                    )

            if unexpected_rows:

                emit()

                emit(
                    "Sample unexpected company-years:"
                )

                for (
                    company_id,
                    year,
                ) in unexpected_rows[:20]:

                    emit(
                        f"  {company_id} | {year}"
                    )

        if financial_ratio_rows < 1100:

            results.warn(
                f"financial_ratios contains "
                f"{financial_ratio_rows} rows, "
                "below the nominal target of 1100; "
                "however, the actual eligible source "
                f"population is {eligible_count}."
            )

        # ==============================================================
        # 7. DUPLICATES
        # ==============================================================

        subsection(
            "7. DUPLICATE COMPANY-YEAR CHECK"
        )

        duplicate_rows = (
            conn.execute(
                """
                SELECT
                    company_id,
                    year,
                    COUNT(*) AS row_count
                FROM financial_ratios
                GROUP BY
                    company_id,
                    year
                HAVING COUNT(*) > 1
                """
            ).fetchall()
        )

        emit(
            f"Duplicate company-year groups: "
            f"{len(duplicate_rows)}"
        )

        if not duplicate_rows:

            results.pass_check(
                "No duplicate company-year rows."
            )

        else:

            results.fail(
                f"Found {len(duplicate_rows)} "
                "duplicate company-year groups."
            )

        # ==============================================================
        # 8. NULL COMPANY IDs
        # ==============================================================

        subsection(
            "8. NULL COMPANY ID CHECK"
        )

        null_company_ids = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM financial_ratios
                WHERE company_id IS NULL
                   OR TRIM(company_id) = ''
                """
            ).fetchone()[0]
        )

        emit(
            f"NULL/blank company IDs:       "
            f"{null_company_ids}"
        )

        if null_company_ids == 0:

            results.pass_check(
                "No NULL or blank company IDs."
            )

        else:

            results.fail(
                f"Found {null_company_ids} "
                "NULL or blank company IDs."
            )

        # ==============================================================
        # 9. FOREIGN KEYS
        # ==============================================================

        subsection(
            "9. FOREIGN KEY CHECK"
        )

        invalid_company_refs = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM financial_ratios AS fr
                LEFT JOIN companies AS c
                    ON UPPER(TRIM(fr.company_id))
                     = UPPER(TRIM(c.id))
                WHERE c.id IS NULL
                """
            ).fetchone()[0]
        )

        fk_violations = (
            conn.execute(
                """
                PRAGMA foreign_key_check
                """
            ).fetchall()
        )

        emit(
            f"Invalid company references:   "
            f"{invalid_company_refs}"
        )

        emit(
            f"SQLite FK violations:         "
            f"{len(fk_violations)}"
        )

        if (
            invalid_company_refs == 0
            and not fk_violations
        ):

            results.pass_check(
                "Foreign-key validation passed."
            )

        else:

            results.fail(
                "Foreign-key validation failed."
            )

        # ==============================================================
        # 10. CASH FLOW DATA
        # ==============================================================

        subsection(
            "10. CASH FLOW DATA CHECK"
        )

        cashflow_columns = set(
            get_table_columns(
                conn,
                "cashflow",
            )
        )

        emit(
            f"Cashflow rows:               "
            f"{table_counts['cashflow']}"
        )

        cashflow_data_valid = True

        for column in CASHFLOW_COLUMNS:

            if column not in cashflow_columns:

                emit(
                    f"{column:<30} MISSING"
                )

                cashflow_data_valid = False

                continue

            quoted_column = (
                quote_identifier(
                    column
                )
            )

            non_null_count = (
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM cashflow
                    WHERE {quoted_column}
                          IS NOT NULL
                    """
                ).fetchone()[0]
            )

            emit(
                f"Non-NULL {column:<24} "
                f"{non_null_count}"
            )

            if non_null_count == 0:

                cashflow_data_valid = False

        if cashflow_data_valid:

            results.pass_check(
                "Cash-flow source metrics are populated."
            )

        else:

            results.fail(
                "One or more required cash-flow "
                "source metrics are missing or empty."
            )

        # ==============================================================
        # 11. CASH-FLOW DERIVED RATIOS
        # ==============================================================

        subsection(
            "11. CASH-FLOW DERIVED RATIO CHECK"
        )

        derived_data_valid = True

        for column in CASHFLOW_DERIVED_COLUMNS:

            if column not in ratio_columns:

                emit(
                    f"{column:<35} MISSING"
                )

                derived_data_valid = False

                continue

            quoted_column = (
                quote_identifier(
                    column
                )
            )

            non_null_count = (
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM financial_ratios
                    WHERE {quoted_column}
                          IS NOT NULL
                    """
                ).fetchone()[0]
            )

            emit(
                f"{column:<35} "
                f"{non_null_count}"
            )

            if non_null_count == 0:

                derived_data_valid = False

        if derived_data_valid:

            results.pass_check(
                "Cash-flow derived metrics are populated."
            )

        else:

            results.fail(
                "One or more cash-flow derived "
                "metrics are missing or empty."
            )

        # ==============================================================
        # 12. CAPITAL ALLOCATION
        # ==============================================================

        subsection(
            "12. CAPITAL ALLOCATION CHECK"
        )

        capital_allocation_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM financial_ratios
                WHERE capital_allocation_pattern
                      IS NOT NULL
                  AND TRIM(
                      capital_allocation_pattern
                  ) != ''
                """
            ).fetchone()[0]
        )

        emit(
            "Rows with capital-allocation "
            f"classification: {capital_allocation_count}"
        )

        if (
            capital_allocation_count
            == financial_ratio_rows
        ):

            results.pass_check(
                "All financial-ratio rows have "
                "a capital-allocation pattern."
            )

        else:

            results.fail(
                f"{financial_ratio_rows - capital_allocation_count} "
                "financial-ratio rows are missing "
                "capital-allocation classifications."
            )

        # ==============================================================
        # 13. PEER GROUP AND SECTOR DATA
        # ==============================================================

        subsection(
            "13. PEER GROUP AND SECTOR DATA CHECK"
        )

        peer_group_count = (
            table_counts[
                "peer_groups"
            ]
        )

        sector_count = (
            table_counts[
                "sectors"
            ]
        )

        emit(
            f"Peer-group assignments:       "
            f"{peer_group_count}"
        )

        emit(
            f"Sector assignments:           "
            f"{sector_count}"
        )

        if (
            peer_group_count > 0
            and sector_count > 0
        ):

            results.pass_check(
                "Peer-group and sector "
                "supporting data are loaded."
            )

        else:

            results.fail(
                "Peer-group or sector "
                "supporting data is missing."
            )

        # ==============================================================
        # 14. PEER ANALYSIS OUTPUT
        # ==============================================================

        subsection(
            "14. PEER ANALYSIS OUTPUT CHECK"
        )

        if not PEER_ANALYSIS_CSV.exists():

            results.fail(
                "peer_analysis.csv does not exist."
            )

        else:

            import csv

            with PEER_ANALYSIS_CSV.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                peer_rows = list(
                    csv.DictReader(file)
                )

            peer_company_ids: list[str] = []

            missing_analysis_groups = 0

            missing_peer_scores = 0

            for row in peer_rows:

                company_id = (
                    normalize_company_id(
                        row.get(
                            "company_id"
                        )
                    )
                )

                if company_id:

                    peer_company_ids.append(
                        company_id
                    )

                analysis_group = str(
                    row.get(
                        "analysis_group",
                        "",
                    )
                    or ""
                ).strip()

                if not analysis_group:

                    missing_analysis_groups += 1

                score_value = str(
                    row.get(
                        "peer_composite_score",
                        row.get(
                            "composite_quality_score",
                            "",
                        ),
                    )
                    or ""
                ).strip()

                if not score_value:

                    missing_peer_scores += 1

            distinct_peer_companies = set(
                peer_company_ids
            )

            duplicate_peer_companies = (
                len(peer_company_ids)
                - len(
                    distinct_peer_companies
                )
            )

            emit(
                f"Peer-analysis rows:          "
                f"{len(peer_rows)}"
            )

            emit(
                f"Distinct companies:          "
                f"{len(distinct_peer_companies)}"
            )

            emit(
                f"Duplicate companies:         "
                f"{duplicate_peer_companies}"
            )

            emit(
                f"Missing analysis groups:     "
                f"{missing_analysis_groups}"
            )

            emit(
                f"Missing peer scores:         "
                f"{missing_peer_scores}"
            )

            if (
                len(distinct_peer_companies)
                == len(valid_company_ids)
                and duplicate_peer_companies == 0
                and missing_analysis_groups == 0
                and missing_peer_scores == 0
            ):

                results.pass_check(
                    "Peer-analysis output covers "
                    "all companies."
                )

            else:

                results.fail(
                    "Peer-analysis output validation failed."
                )

        # ==============================================================
        # 15. PEER GROUP SUMMARY
        # ==============================================================

        subsection(
            "15. PEER GROUP SUMMARY CHECK"
        )

        if not PEER_GROUP_SUMMARY_CSV.exists():

            results.fail(
                "peer_group_summary.csv does not exist."
            )

        else:

            import csv

            with PEER_GROUP_SUMMARY_CSV.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                summary_rows = list(
                    csv.DictReader(file)
                )

            emit(
                f"Peer-group summary rows:     "
                f"{len(summary_rows)}"
            )

            if summary_rows:

                results.pass_check(
                    "Peer-group summary was generated."
                )

            else:

                results.fail(
                    "Peer-group summary is empty."
                )

        # ==============================================================
        # 16. FINANCIAL VALIDATION REPORT
        # ==============================================================

        subsection(
            "16. FINANCIAL VALIDATION REPORT CHECK"
        )

        if (
            FINANCIAL_VALIDATION_REPORT.exists()
        ):

            results.pass_check(
                "Financial-ratio validation report exists."
            )

            emit(
                str(
                    FINANCIAL_VALIDATION_REPORT
                )
            )

        else:

            results.fail(
                "Financial-ratio validation "
                "report does not exist."
            )

        # ==============================================================
        # 17. DATABASE INTEGRITY
        # ==============================================================

        subsection(
            "17. SQLITE DATABASE INTEGRITY CHECK"
        )

        integrity_result = (
            conn.execute(
                """
                PRAGMA integrity_check
                """
            ).fetchone()[0]
        )

        emit(
            f"SQLite integrity result: "
            f"{integrity_result}"
        )

        if (
            str(
                integrity_result
            ).lower()
            == "ok"
        ):

            results.pass_check(
                "SQLite database integrity check passed."
            )

        else:

            results.fail(
                "SQLite database integrity check failed: "
                f"{integrity_result}"
            )

    except Exception as error:

        emit()

        results.fail(
            "Unexpected validation error: "
            f"{type(error).__name__}: "
            f"{error}"
        )

    finally:

        if conn is not None:

            conn.close()

    # ==================================================================
    # FINAL SUMMARY
    # ==================================================================

    emit()

    separator()

    emit(
        "SPRINT 2 FINAL VALIDATION SUMMARY"
    )

    separator()

    emit(
        f"Passed checks: {len(results.passed)}"
    )

    emit(
        f"Warnings:      {len(results.warnings)}"
    )

    emit(
        f"Failed checks: {len(results.failed)}"
    )

    if results.warnings:

        emit()

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
            "FAILURES"
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

    separator()

    if not results.failed:

        emit(
            "SPRINT 2 FINAL STATUS: PASS"
        )

        emit(
            "Sprint 2 - Financial Ratio Engine "
            "is complete."
        )

        if (
            len(
                fetch_eligible_company_years(
                    connect_database()
                )
            )
            < 1100
        ):

            emit()

            emit(
                "NOTE: The nominal target is >= 1,100 rows, "
                "but the available valid source population "
                "contains fewer eligible company-year combinations."
            )

            emit(
                "No artificial rows are required."
            )

        exit_code = 0

    else:

        emit(
            "SPRINT 2 FINAL STATUS: FAIL"
        )

        emit(
            "Resolve the failed checks "
            "before closing Sprint 2."
        )

        exit_code = 1

    separator()

    emit()

    emit(
        "Final Sprint 2 validation report:"
    )

    emit(
        str(
            FINAL_VALIDATION_REPORT
        )
    )

    try:

        write_report()

    except Exception as report_error:

        print(
            "WARNING: Could not write final report:"
        )

        print(
            report_error
        )

    return exit_code


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":

    sys.exit(
        run_validation()
    )