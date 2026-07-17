"""
SPRINT 2 - DAY 12
Populate the financial_ratios table.

Reads:
    companies
    profitandloss
    balancesheet
    cashflow

Writes:
    financial_ratios
    output/capital_allocation.csv
    output/ratio_edge_cases.log

Run from project root:
    python src/analytics/populate_financial_ratios.py
"""

from __future__ import annotations

import csv
import math
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

CAPITAL_ALLOCATION_FILE = OUTPUT_DIR / "capital_allocation.csv"
EDGE_CASE_LOG = OUTPUT_DIR / "ratio_edge_cases.log"


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(value: Any) -> Optional[float]:
    """Convert a value to float safely."""
    if value is None:
        return None

    try:
        result = float(value)

        if math.isnan(result) or math.isinf(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def safe_divide(
    numerator: Any,
    denominator: Any,
    multiplier: float = 1.0,
) -> Optional[float]:
    """Safely divide two values."""
    numerator = safe_float(numerator)
    denominator = safe_float(denominator)

    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return (numerator / denominator) * multiplier


def round_value(
    value: Any,
    digits: int = 4,
) -> Optional[float]:
    """Round numeric values safely."""
    value = safe_float(value)

    if value is None:
        return None

    return round(value, digits)


def sign_label(value: Any) -> str:
    """Return +, -, or 0 for a cash-flow value."""
    value = safe_float(value)

    if value is None or value == 0:
        return "0"

    return "+" if value > 0 else "-"


# ============================================================
# RATIO CALCULATIONS
# ============================================================

def net_profit_margin(
    net_profit: Any,
    sales: Any,
) -> Optional[float]:
    return safe_divide(net_profit, sales, 100)


def operating_profit_margin(
    operating_profit: Any,
    sales: Any,
) -> Optional[float]:
    return safe_divide(operating_profit, sales, 100)


def return_on_equity(
    net_profit: Any,
    equity_capital: Any,
    reserves: Any,
) -> Optional[float]:

    net_profit = safe_float(net_profit)
    equity_capital = safe_float(equity_capital)
    reserves = safe_float(reserves)

    if (
        net_profit is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    equity = equity_capital + reserves

    # Sprint requirement:
    # return None for zero or negative equity
    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    operating_profit: Any,
    other_income: Any,
    equity_capital: Any,
    reserves: Any,
    borrowings: Any,
) -> Optional[float]:

    operating_profit = safe_float(operating_profit)
    other_income = safe_float(other_income)
    equity_capital = safe_float(equity_capital)
    reserves = safe_float(reserves)
    borrowings = safe_float(borrowings)

    if (
        operating_profit is None
        or equity_capital is None
        or reserves is None
        or borrowings is None
    ):
        return None

    if other_income is None:
        other_income = 0.0

    # Approximate EBIT from available source fields
    ebit = operating_profit + other_income

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit: Any,
    total_assets: Any,
) -> Optional[float]:
    return safe_divide(
        net_profit,
        total_assets,
        100,
    )


def debt_to_equity(
    borrowings: Any,
    equity_capital: Any,
    reserves: Any,
) -> Optional[float]:

    borrowings = safe_float(borrowings)
    equity_capital = safe_float(equity_capital)
    reserves = safe_float(reserves)

    if (
        borrowings is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    # Sprint requirement:
    # debt-free company returns 0
    if borrowings == 0:
        return 0.0

    return borrowings / equity


def interest_coverage_ratio(
    operating_profit: Any,
    other_income: Any,
    interest: Any,
) -> Optional[float]:

    operating_profit = safe_float(operating_profit)
    other_income = safe_float(other_income)
    interest = safe_float(interest)

    if operating_profit is None:
        return None

    if other_income is None:
        other_income = 0.0

    # Debt-free / no interest case
    if interest is None or interest == 0:
        return None

    return (
        operating_profit + other_income
    ) / interest


def calculate_net_debt(
    borrowings: Any,
    investments: Any,
) -> Optional[float]:

    borrowings = safe_float(borrowings)
    investments = safe_float(investments)

    if borrowings is None:
        return None

    if investments is None:
        investments = 0.0

    return borrowings - investments


def asset_turnover(
    sales: Any,
    total_assets: Any,
) -> Optional[float]:
    return safe_divide(
        sales,
        total_assets,
    )


# ============================================================
# CASH-FLOW KPIs
# ============================================================

def free_cash_flow(
    operating_cash_flow: Any,
    investing_cash_flow: Any,
) -> Optional[float]:

    operating_cash_flow = safe_float(
        operating_cash_flow
    )

    investing_cash_flow = safe_float(
        investing_cash_flow
    )

    if (
        operating_cash_flow is None
        or investing_cash_flow is None
    ):
        return None

    # Sprint formula
    return (
        operating_cash_flow
        + investing_cash_flow
    )


def cfo_pat_ratio(
    operating_cash_flow: Any,
    net_profit: Any,
) -> Optional[float]:

    return safe_divide(
        operating_cash_flow,
        net_profit,
    )


def cfo_quality_label(
    ratio: Any,
) -> Optional[str]:

    ratio = safe_float(ratio)

    if ratio is None:
        return None

    if ratio > 1.0:
        return "High Quality"

    if ratio >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(
    investing_cash_flow: Any,
    sales: Any,
) -> Optional[float]:

    investing_cash_flow = safe_float(
        investing_cash_flow
    )

    sales = safe_float(sales)

    if (
        investing_cash_flow is None
        or sales is None
        or sales == 0
    ):
        return None

    return (
        abs(investing_cash_flow)
        / sales
    ) * 100


def capex_intensity_label(
    value: Any,
) -> Optional[str]:

    value = safe_float(value)

    if value is None:
        return None

    if value < 3:
        return "Asset Light"

    if value <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: Any,
    operating_profit: Any,
) -> Optional[float]:

    return safe_divide(
        fcf,
        operating_profit,
        100,
    )


# ============================================================
# CAPITAL ALLOCATION CLASSIFICATION
# ============================================================

def classify_capital_allocation(
    cfo: Any,
    cfi: Any,
    cff: Any,
    cfo_pat: Any,
) -> str:

    cfo_sign = sign_label(cfo)
    cfi_sign = sign_label(cfi)
    cff_sign = sign_label(cff)

    pattern = (
        cfo_sign,
        cfi_sign,
        cff_sign,
    )

    if pattern == ("+", "-", "-"):
        return "Reinvestor"

    if pattern == ("+", "-", "+"):
        ratio = safe_float(cfo_pat)

        if ratio is not None and ratio > 1:
            return "Shareholder Returns"

        return "Mixed"

    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    return "Mixed"


# ============================================================
# CAGR ENGINE
# ============================================================

def calculate_cagr(
    start_value: Any,
    end_value: Any,
    years: int,
) -> tuple[Optional[float], Optional[str]]:

    start_value = safe_float(start_value)
    end_value = safe_float(end_value)

    if (
        start_value is None
        or end_value is None
        or years <= 0
    ):
        return None, "INSUFFICIENT_DATA"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value > 0:
        value = (
            (
                end_value / start_value
            ) ** (1 / years)
            - 1
        ) * 100

        return round_value(value), None

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    return None, "INSUFFICIENT_DATA"


def get_cagr_for_window(
    history: dict[int, Any],
    current_year: int,
    window: int,
) -> tuple[Optional[float], Optional[str]]:

    start_year = current_year - window

    if (
        start_year not in history
        or current_year not in history
    ):
        return None, "INSUFFICIENT_DATA"

    return calculate_cagr(
        history[start_year],
        history[current_year],
        window,
    )


# ============================================================
# COMPOSITE QUALITY SCORE
# ============================================================

def calculate_composite_quality_score(
    npm: Any,
    roe: Any,
    roa: Any,
    debt_equity: Any,
    interest_coverage: Any,
    cfo_quality: Optional[str],
    revenue_cagr_5yr: Any,
) -> Optional[float]:

    score = 0.0
    available = 0

    npm = safe_float(npm)

    if npm is not None:
        available += 1

        if npm >= 20:
            score += 100
        elif npm >= 10:
            score += 75
        elif npm > 0:
            score += 50

    roe = safe_float(roe)

    if roe is not None:
        available += 1

        if roe >= 20:
            score += 100
        elif roe >= 15:
            score += 75
        elif roe > 0:
            score += 50

    roa = safe_float(roa)

    if roa is not None:
        available += 1

        if roa >= 10:
            score += 100
        elif roa >= 5:
            score += 75
        elif roa > 0:
            score += 50

    debt_equity = safe_float(debt_equity)

    if debt_equity is not None:
        available += 1

        if debt_equity < 0.5:
            score += 100
        elif debt_equity < 1:
            score += 75
        elif debt_equity < 2:
            score += 50

    interest_coverage = safe_float(
        interest_coverage
    )

    if interest_coverage is not None:
        available += 1

        if interest_coverage >= 5:
            score += 100
        elif interest_coverage >= 3:
            score += 75
        elif interest_coverage >= 1.5:
            score += 50

    if cfo_quality is not None:
        available += 1

        if cfo_quality == "High Quality":
            score += 100
        elif cfo_quality == "Moderate":
            score += 60
        else:
            score += 20

    revenue_cagr_5yr = safe_float(
        revenue_cagr_5yr
    )

    if revenue_cagr_5yr is not None:
        available += 1

        if revenue_cagr_5yr >= 15:
            score += 100
        elif revenue_cagr_5yr >= 10:
            score += 75
        elif revenue_cagr_5yr > 0:
            score += 50

    if available == 0:
        return None

    return round(
        score / available,
        2,
    )


# ============================================================
# DATABASE HELPERS
# ============================================================

def fetch_rows(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[dict[str, Any]]:
    """Fetch all rows from a SQLite table as dictionaries."""
    cursor = conn.execute(f'SELECT * FROM "{table_name}"')
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def parse_year(value: Any) -> Optional[int]:
    """
    Convert source year formats to a four-digit integer.

    Supports:
        2024
        2024.0
        "2024"
        "Dec 2012"
        "Mar 2014"
        "Mar-13"
        "Mar-99"
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        year = int(value)
        return year if 1900 <= year <= 2100 else None

    text = str(value).strip()
    if not text:
        return None

    try:
        year = int(float(text))
        if 1900 <= year <= 2100:
            return year
    except (TypeError, ValueError, OverflowError):
        pass

    match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text)
    if match:
        return int(match.group(1))

    match = re.search(r"(?<!\d)(\d{2})\s*$", text)
    if match:
        short_year = int(match.group(1))
        return 2000 + short_year if short_year <= 50 else 1900 + short_year

    return None


def normalise_company_id(value: Any) -> Optional[str]:
    """Return a clean company ID string."""
    if value is None:
        return None
    company_id = str(value).strip()
    return company_id or None


def make_lookup(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Build a (company_id, parsed_year) -> row lookup."""
    lookup = {}

    for row in rows:
        company_id = normalise_company_id(row.get("company_id"))
        year = parse_year(row.get("year"))

        if company_id is None or year is None:
            continue

        lookup[(company_id, year)] = row

    return lookup


def build_history(
    rows: list[dict[str, Any]],
    value_column: str,
) -> dict[str, dict[int, Any]]:
    """Build company -> year -> value history using parsed years."""
    history = defaultdict(dict)

    for row in rows:
        company_id = normalise_company_id(row.get("company_id"))
        year = parse_year(row.get("year"))

        if company_id is None or year is None:
            continue

        history[company_id][year] = row.get(value_column)

    return history


# ============================================================
# MAIN POPULATION ENGINE
# ============================================================

def populate_financial_ratios() -> None:

    print("=" * 70)
    print("SPRINT 2 - FINANCIAL RATIO ENGINE")
    print("DAY 12 - POPULATE FINANCIAL_RATIOS")
    print("=" * 70)

    print(f"Database: {DB_PATH}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:

        # ----------------------------------------------------
        # LOAD SOURCE DATA
        # ----------------------------------------------------

        companies = fetch_rows(
            conn,
            "companies",
        )

        profit_rows = fetch_rows(
            conn,
            "profitandloss",
        )

        balance_rows = fetch_rows(
            conn,
            "balancesheet",
        )

        cashflow_rows = fetch_rows(
            conn,
            "cashflow",
        )

        print()
        print("SOURCE ROW COUNTS")
        print("-" * 70)
        print(
            f"companies:      {len(companies)}"
        )
        print(
            f"profitandloss:  {len(profit_rows)}"
        )
        print(
            f"balancesheet:   {len(balance_rows)}"
        )
        print(
            f"cashflow:       {len(cashflow_rows)}"
        )

        # ----------------------------------------------------
        # LOOKUPS
        # ----------------------------------------------------

        company_lookup = {
            str(row["id"]): row
            for row in companies
            if row.get("id") is not None
        }

        profit_lookup = make_lookup(
            profit_rows
        )

        balance_lookup = make_lookup(
            balance_rows
        )

        cashflow_lookup = make_lookup(
            cashflow_rows
        )

        # ----------------------------------------------------
        # HISTORY FOR CAGR
        # ----------------------------------------------------

        revenue_history = build_history(
            profit_rows,
            "sales",
        )

        pat_history = build_history(
            profit_rows,
            "net_profit",
        )

        # EPS source is not available in current source tables.
        # Keep empty history so EPS CAGR fields become NULL /
        # INSUFFICIENT_DATA rather than inventing values.
        eps_history = defaultdict(dict)

        # ----------------------------------------------------
        # BASE COMPANY-YEAR UNIVERSE
        #
        # Use UNION of all source tables so that available
        # company-year records are not lost.
        # ----------------------------------------------------

        all_keys = (
            set(profit_lookup.keys())
            | set(balance_lookup.keys())
            | set(cashflow_lookup.keys())
        )

        print()
        print(
            f"Unique company-year combinations: "
            f"{len(all_keys)}"
        )

        # ----------------------------------------------------
        # CLEAR OLD GENERATED DATA
        # ----------------------------------------------------

        conn.execute(
            "DELETE FROM financial_ratios"
        )

        # ----------------------------------------------------
        # INSERT SQL
        # ----------------------------------------------------

        insert_sql = """
        INSERT INTO financial_ratios (
            company_id,
            year,

            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            return_on_capital_employed_pct,
            return_on_assets_pct,

            debt_to_equity,
            high_leverage_flag,
            interest_coverage,
            icr_label,
            icr_warning_flag,
            net_debt,
            asset_turnover,

            free_cash_flow_cr,
            cash_from_operations_cr,
            cfo_pat_ratio,
            cfo_quality_label,
            capex_cr,
            capex_intensity_pct,
            capex_intensity_label,
            fcf_conversion_rate_pct,

            earnings_per_share,
            book_value_per_share,
            dividend_payout_ratio_pct,
            total_debt_cr,

            revenue_cagr_3yr,
            revenue_cagr_3yr_flag,
            revenue_cagr_5yr,
            revenue_cagr_5yr_flag,
            revenue_cagr_10yr,
            revenue_cagr_10yr_flag,

            pat_cagr_3yr,
            pat_cagr_3yr_flag,
            pat_cagr_5yr,
            pat_cagr_5yr_flag,
            pat_cagr_10yr,
            pat_cagr_10yr_flag,

            eps_cagr_3yr,
            eps_cagr_3yr_flag,
            eps_cagr_5yr,
            eps_cagr_5yr_flag,
            eps_cagr_10yr,
            eps_cagr_10yr_flag,

            cfo_sign,
            cfi_sign,
            cff_sign,
            capital_allocation_pattern,

            composite_quality_score
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """

        inserted = 0
        skipped = 0
        errors = 0

        capital_allocation_rows = []
        edge_case_logs = []

        # ----------------------------------------------------
        # PROCESS EVERY COMPANY-YEAR
        # ----------------------------------------------------

        for company_id, year in sorted(
            all_keys,
            key=lambda x: (
                x[0],
                x[1],
            ),
        ):

            # Foreign-key safety
            if company_id not in company_lookup:

                skipped += 1

                edge_case_logs.append(
                    f"{company_id} | {year} | "
                    f"DATA_SOURCE_ISSUE | "
                    f"Company ID missing from companies table"
                )

                continue

            profit = profit_lookup.get(
                (company_id, year),
                {},
            )

            balance = balance_lookup.get(
                (company_id, year),
                {},
            )

            cashflow = cashflow_lookup.get(
                (company_id, year),
                {},
            )

            company = company_lookup.get(
                company_id,
                {},
            )

            # ------------------------------------------------
            # SOURCE VALUES
            # ------------------------------------------------

            sales = safe_float(
                profit.get("sales")
            )

            operating_profit = safe_float(
                profit.get(
                    "operating_profit"
                )
            )

            other_income = safe_float(
                profit.get("other_income")
            )

            interest = safe_float(
                profit.get("interest")
            )

            net_profit = safe_float(
                profit.get("net_profit")
            )

            equity_capital = safe_float(
                balance.get(
                    "equity_capital"
                )
            )

            reserves = safe_float(
                balance.get("reserves")
            )

            borrowings = safe_float(
                balance.get("borrowings")
            )

            investments = safe_float(
                balance.get("investments")
            )

            total_assets = safe_float(
                balance.get(
                    "total_assets"
                )
            )

            operating_cash_flow = safe_float(
                cashflow.get(
                    "operating_cash_flow"
                )
            )

            investing_cash_flow = safe_float(
                cashflow.get(
                    "investing_cash_flow"
                )
            )

            financing_cash_flow = safe_float(
                cashflow.get(
                    "financing_cash_flow"
                )
            )

            # ------------------------------------------------
            # CORE RATIOS
            # ------------------------------------------------

            npm = net_profit_margin(
                net_profit,
                sales,
            )

            opm = operating_profit_margin(
                operating_profit,
                sales,
            )

            roe = return_on_equity(
                net_profit,
                equity_capital,
                reserves,
            )

            roce = (
                return_on_capital_employed(
                    operating_profit,
                    other_income,
                    equity_capital,
                    reserves,
                    borrowings,
                )
            )

            roa = return_on_assets(
                net_profit,
                total_assets,
            )

            de = debt_to_equity(
                borrowings,
                equity_capital,
                reserves,
            )

            # broad_sector is not currently shown in companies.
            # Default to non-Financial unless the column exists.
            broad_sector = str(
                company.get(
                    "broad_sector",
                    "",
                )
                or ""
            ).strip()

            is_financial = (
                broad_sector.lower()
                == "financials"
            )

            high_leverage = (
                1
                if (
                    de is not None
                    and de > 5
                    and not is_financial
                )
                else 0
            )

            icr = interest_coverage_ratio(
                operating_profit,
                other_income,
                interest,
            )

            if (
                interest is None
                or interest == 0
            ):
                icr_label = "Debt Free"

            else:
                icr_label = None

            icr_warning = (
                1
                if (
                    icr is not None
                    and icr < 1.5
                )
                else 0
            )

            calculated_net_debt = (
                calculate_net_debt(
                    borrowings,
                    investments,
                )
            )

            turnover = asset_turnover(
                sales,
                total_assets,
            )

            # ------------------------------------------------
            # CASH-FLOW KPIs
            # ------------------------------------------------

            fcf = free_cash_flow(
                operating_cash_flow,
                investing_cash_flow,
            )

            cfo_pat = cfo_pat_ratio(
                operating_cash_flow,
                net_profit,
            )

            quality_label = (
                cfo_quality_label(
                    cfo_pat
                )
            )

            capex = (
                abs(investing_cash_flow)
                if investing_cash_flow
                is not None
                else None
            )

            capex_pct = capex_intensity(
                investing_cash_flow,
                sales,
            )

            capex_label = (
                capex_intensity_label(
                    capex_pct
                )
            )

            fcf_conversion = (
                fcf_conversion_rate(
                    fcf,
                    operating_profit,
                )
            )

            cfo_s = sign_label(
                operating_cash_flow
            )

            cfi_s = sign_label(
                investing_cash_flow
            )

            cff_s = sign_label(
                financing_cash_flow
            )

            allocation_pattern = (
                classify_capital_allocation(
                    operating_cash_flow,
                    investing_cash_flow,
                    financing_cash_flow,
                    cfo_pat,
                )
            )

            # ------------------------------------------------
            # CAGR
            # ------------------------------------------------

            company_revenue_history = (
                revenue_history.get(
                    company_id,
                    {},
                )
            )

            company_pat_history = (
                pat_history.get(
                    company_id,
                    {},
                )
            )

            company_eps_history = (
                eps_history.get(
                    company_id,
                    {},
                )
            )

            rev_3, rev_3_flag = (
                get_cagr_for_window(
                    company_revenue_history,
                    year,
                    3,
                )
            )

            rev_5, rev_5_flag = (
                get_cagr_for_window(
                    company_revenue_history,
                    year,
                    5,
                )
            )

            rev_10, rev_10_flag = (
                get_cagr_for_window(
                    company_revenue_history,
                    year,
                    10,
                )
            )

            pat_3, pat_3_flag = (
                get_cagr_for_window(
                    company_pat_history,
                    year,
                    3,
                )
            )

            pat_5, pat_5_flag = (
                get_cagr_for_window(
                    company_pat_history,
                    year,
                    5,
                )
            )

            pat_10, pat_10_flag = (
                get_cagr_for_window(
                    company_pat_history,
                    year,
                    10,
                )
            )

            eps_3, eps_3_flag = (
                get_cagr_for_window(
                    company_eps_history,
                    year,
                    3,
                )
            )

            eps_5, eps_5_flag = (
                get_cagr_for_window(
                    company_eps_history,
                    year,
                    5,
                )
            )

            eps_10, eps_10_flag = (
                get_cagr_for_window(
                    company_eps_history,
                    year,
                    10,
                )
            )

            # ------------------------------------------------
            # AVAILABLE COMPANY-LEVEL VALUES
            # ------------------------------------------------

            book_value_per_share = (
                safe_float(
                    company.get(
                        "book_value"
                    )
                )
            )

            # No reliable EPS/dividend fields were shown
            # in the currently loaded source tables.
            earnings_per_share = None

            dividend_payout_ratio_pct = None

            total_debt_cr = borrowings

            # ------------------------------------------------
            # COMPOSITE QUALITY SCORE
            # ------------------------------------------------

            composite_score = (
                calculate_composite_quality_score(
                    npm,
                    roe,
                    roa,
                    de,
                    icr,
                    quality_label,
                    rev_5,
                )
            )

            # ------------------------------------------------
            # EDGE CASE LOGGING
            # ------------------------------------------------

            source_roce = safe_float(
                company.get(
                    "roce_percentage"
                )
            )

            if (
                source_roce is not None
                and roce is not None
                and abs(
                    source_roce - roce
                ) > 5
            ):
                edge_case_logs.append(
                    f"{company_id} | {year} | "
                    f"VERSION_DIFFERENCE | "
                    f"ROCE source={source_roce:.4f}, "
                    f"calculated={roce:.4f}, "
                    f"difference="
                    f"{abs(source_roce - roce):.4f}"
                )

            source_roe = safe_float(
                company.get(
                    "roe_percentage"
                )
            )

            if (
                source_roe is not None
                and roe is not None
                and abs(
                    source_roe - roe
                ) > 5
            ):
                edge_case_logs.append(
                    f"{company_id} | {year} | "
                    f"VERSION_DIFFERENCE | "
                    f"ROE source={source_roe:.4f}, "
                    f"calculated={roe:.4f}, "
                    f"difference="
                    f"{abs(source_roe - roe):.4f}"
                )

            if (
                equity_capital is not None
                and reserves is not None
                and (
                    equity_capital
                    + reserves
                ) <= 0
            ):
                edge_case_logs.append(
                    f"{company_id} | {year} | "
                    f"FORMULA_DISCREPANCY | "
                    f"Non-positive equity; "
                    f"ROE and D/E returned NULL"
                )

            # ------------------------------------------------
            # INSERT
            # ------------------------------------------------

            values = (
                company_id,
                year,

                round_value(npm),
                round_value(opm),
                round_value(roe),
                round_value(roce),
                round_value(roa),

                round_value(de),
                high_leverage,
                round_value(icr),
                icr_label,
                icr_warning,
                round_value(
                    calculated_net_debt
                ),
                round_value(turnover),

                round_value(fcf),
                round_value(
                    operating_cash_flow
                ),
                round_value(cfo_pat),
                quality_label,
                round_value(capex),
                round_value(capex_pct),
                capex_label,
                round_value(
                    fcf_conversion
                ),

                earnings_per_share,
                round_value(
                    book_value_per_share
                ),
                dividend_payout_ratio_pct,
                round_value(
                    total_debt_cr
                ),

                rev_3,
                rev_3_flag,
                rev_5,
                rev_5_flag,
                rev_10,
                rev_10_flag,

                pat_3,
                pat_3_flag,
                pat_5,
                pat_5_flag,
                pat_10,
                pat_10_flag,

                eps_3,
                eps_3_flag,
                eps_5,
                eps_5_flag,
                eps_10,
                eps_10_flag,

                cfo_s,
                cfi_s,
                cff_s,
                allocation_pattern,

                composite_score,
            )

            try:

                conn.execute(
                    insert_sql,
                    values,
                )

                inserted += 1

                capital_allocation_rows.append(
                    {
                        "company_id":
                            company_id,

                        "year":
                            year,

                        "cfo_sign":
                            cfo_s,

                        "cfi_sign":
                            cfi_s,

                        "cff_sign":
                            cff_s,

                        "pattern_label":
                            allocation_pattern,
                    }
                )

            except sqlite3.Error as error:

                errors += 1

                edge_case_logs.append(
                    f"{company_id} | {year} | "
                    f"DATA_SOURCE_ISSUE | "
                    f"Database insert error: "
                    f"{error}"
                )

                print(
                    f"ERROR inserting "
                    f"{company_id} {year}: "
                    f"{error}"
                )

        # ----------------------------------------------------
        # COMMIT DATABASE
        # ----------------------------------------------------

        conn.commit()

        # ----------------------------------------------------
        # CAPITAL ALLOCATION CSV
        # ----------------------------------------------------

        with open(
            CAPITAL_ALLOCATION_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "company_id",
                    "year",
                    "cfo_sign",
                    "cfi_sign",
                    "cff_sign",
                    "pattern_label",
                ],
            )

            writer.writeheader()

            writer.writerows(
                capital_allocation_rows
            )

        # ----------------------------------------------------
        # EDGE CASE LOG
        # ----------------------------------------------------

        with open(
            EDGE_CASE_LOG,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                "SPRINT 2 - RATIO EDGE CASE LOG\n"
            )

            file.write(
                "=" * 70 + "\n"
            )

            if edge_case_logs:

                for log_entry in edge_case_logs:
                    file.write(
                        log_entry + "\n"
                    )

            else:

                file.write(
                    "No edge cases detected.\n"
                )

        # ----------------------------------------------------
        # FINAL VALIDATION
        # ----------------------------------------------------

        final_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM financial_ratios
            """
        ).fetchone()[0]

        distinct_companies = (
            conn.execute(
                """
                SELECT COUNT(
                    DISTINCT company_id
                )
                FROM financial_ratios
                """
            ).fetchone()[0]
        )

        null_company_ids = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM financial_ratios
                WHERE company_id IS NULL
                """
            ).fetchone()[0]
        )

        duplicate_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        company_id,
                        year,
                        COUNT(*) AS cnt
                    FROM financial_ratios
                    GROUP BY
                        company_id,
                        year
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )

        print()
        print("=" * 70)
        print("DAY 12 POPULATION COMPLETE")
        print("=" * 70)

        print(
            f"Rows inserted:       "
            f"{inserted}"
        )

        print(
            f"Rows skipped:        "
            f"{skipped}"
        )

        print(
            f"Insert errors:       "
            f"{errors}"
        )

        print(
            f"Final row count:     "
            f"{final_count}"
        )

        print(
            f"Distinct companies:  "
            f"{distinct_companies}"
        )

        print(
            f"NULL company IDs:    "
            f"{null_company_ids}"
        )

        print(
            f"Duplicate company-year rows: "
            f"{duplicate_count}"
        )

        print()
        print(
            f"Capital allocation CSV:"
        )

        print(
            CAPITAL_ALLOCATION_FILE
        )

        print()
        print(
            f"Edge-case log:"
        )

        print(
            EDGE_CASE_LOG
        )

        print("=" * 70)

        if final_count >= 1100:
            print(
                f"PASS: financial_ratios contains {final_count} rows; "
                "Sprint target is >= 1,100."
            )
        else:
            print(
                f"WARNING: financial_ratios contains {final_count} rows; "
                "Sprint target is >= 1,100."
            )

        print("=" * 70)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    populate_financial_ratios()