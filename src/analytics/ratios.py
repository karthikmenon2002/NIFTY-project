"""
NIFTY 100 Financial Ratio Engine
Sprint 2 - Days 08 and 09

Implements:
- Net Profit Margin
- Operating Profit Margin
- Return on Equity (ROE)
- Return on Capital Employed (ROCE)
- Return on Assets (ROA)
- Debt-to-Equity
- Interest Coverage Ratio
- Net Debt
- Asset Turnover
- Financial-sector leverage exception
- Warning flags
"""

from typing import Optional


# ============================================================
# HELPERS
# ============================================================

def _to_float(value) -> Optional[float]:
    """
    Convert a value to float.

    Returns None when the value is missing or cannot
    be converted to a numeric value.
    """
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value, digits=4):
    """Round a numeric result while preserving None."""
    if value is None:
        return None

    return round(value, digits)


# ============================================================
# DAY 08 - PROFITABILITY RATIOS
# ============================================================

def net_profit_margin(
    net_profit,
    sales
) -> Optional[float]:
    """
    Net Profit Margin (%) =
        net_profit / sales * 100

    Returns None when sales = 0 or data is missing.
    """

    net_profit = _to_float(net_profit)
    sales = _to_float(sales)

    if (
        net_profit is None
        or sales is None
        or sales == 0
    ):
        return None

    return _round(
        (net_profit / sales) * 100
    )


def operating_profit_margin(
    operating_profit,
    sales
) -> Optional[float]:
    """
    Operating Profit Margin (%) =
        operating_profit / sales * 100

    Returns None when sales = 0 or data is missing.
    """

    operating_profit = _to_float(
        operating_profit
    )

    sales = _to_float(sales)

    if (
        operating_profit is None
        or sales is None
        or sales == 0
    ):
        return None

    return _round(
        (operating_profit / sales) * 100
    )


def return_on_equity(
    net_profit,
    equity_capital,
    reserves
) -> Optional[float]:
    """
    ROE (%) =
        net_profit /
        (equity_capital + reserves)
        * 100

    Sprint rule:
    Return None when equity + reserves <= 0.
    """

    net_profit = _to_float(net_profit)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if (
        net_profit is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    equity = (
        equity_capital
        + reserves
    )

    if equity <= 0:
        return None

    return _round(
        (net_profit / equity) * 100
    )


def return_on_capital_employed(
    operating_profit,
    equity_capital,
    reserves,
    borrowings
) -> Optional[float]:
    """
    ROCE (%) =
        EBIT /
        (equity + reserves + borrowings)
        * 100

    The available source field operating_profit
    is used as the EBIT proxy.
    """

    operating_profit = _to_float(
        operating_profit
    )

    equity_capital = _to_float(
        equity_capital
    )

    reserves = _to_float(reserves)
    borrowings = _to_float(borrowings)

    if any(
        value is None
        for value in (
            operating_profit,
            equity_capital,
            reserves,
            borrowings,
        )
    ):
        return None

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    return _round(
        (
            operating_profit
            / capital_employed
        )
        * 100
    )


def return_on_assets(
    net_profit,
    total_assets
) -> Optional[float]:
    """
    ROA (%) =
        net_profit / total_assets * 100

    Returns None when total_assets = 0.
    """

    net_profit = _to_float(net_profit)
    total_assets = _to_float(total_assets)

    if (
        net_profit is None
        or total_assets is None
        or total_assets == 0
    ):
        return None

    return _round(
        (net_profit / total_assets) * 100
    )


# ============================================================
# OPM CROSS-CHECK
# ============================================================

def opm_difference(
    calculated_opm,
    source_opm
) -> Optional[float]:
    """
    Absolute difference between calculated OPM
    and source OPM percentage.
    """

    calculated_opm = _to_float(
        calculated_opm
    )

    source_opm = _to_float(
        source_opm
    )

    if (
        calculated_opm is None
        or source_opm is None
    ):
        return None

    return _round(
        abs(
            calculated_opm
            - source_opm
        )
    )


def opm_mismatch(
    calculated_opm,
    source_opm,
    threshold=1.0
) -> bool:
    """
    Return True when OPM difference exceeds
    the Sprint 2 threshold of 1 percentage point.
    """

    difference = opm_difference(
        calculated_opm,
        source_opm
    )

    if difference is None:
        return False

    return difference > threshold


# ============================================================
# DAY 09 - LEVERAGE RATIOS
# ============================================================

def debt_to_equity(
    borrowings,
    equity_capital,
    reserves
) -> Optional[float]:
    """
    Debt-to-Equity =
        borrowings /
        (equity_capital + reserves)

    Sprint rules:
    - Return 0 when borrowings = 0.
    - Return None when equity <= 0.
    """

    borrowings = _to_float(borrowings)
    equity_capital = _to_float(equity_capital)
    reserves = _to_float(reserves)

    if (
        borrowings is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    if borrowings == 0:
        return 0.0

    equity = (
        equity_capital
        + reserves
    )

    if equity <= 0:
        return None

    return _round(
        borrowings / equity
    )


def high_leverage_flag(
    debt_equity,
    broad_sector=None,
    threshold=5.0
) -> bool:
    """
    High leverage flag.

    Sprint rule:
    D/E > 5 is flagged unless the company
    belongs to the Financials broad sector.
    """

    debt_equity = _to_float(
        debt_equity
    )

    if debt_equity is None:
        return False

    sector = (
        str(broad_sector)
        .strip()
        .lower()
        if broad_sector is not None
        else ""
    )

    if sector == "financials":
        return False

    return debt_equity > threshold


def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest
) -> Optional[float]:
    """
    Interest Coverage Ratio =
        (operating_profit + other_income)
        / interest

    Returns None when interest = 0,
    representing a debt-free/no-interest case.
    """

    operating_profit = _to_float(
        operating_profit
    )

    other_income = _to_float(
        other_income
    )

    interest = _to_float(interest)

    if (
        operating_profit is None
        or other_income is None
        or interest is None
    ):
        return None

    if interest == 0:
        return None

    return _round(
        (
            operating_profit
            + other_income
        )
        / interest
    )


def interest_coverage_label(
    interest_coverage
) -> Optional[str]:
    """
    Display label for debt-free companies.
    """

    if interest_coverage is None:
        return "Debt Free"

    return None


def icr_warning_flag(
    interest_coverage,
    threshold=1.5
) -> bool:
    """
    Flag companies at risk of not covering
    interest payments.

    ICR < 1.5 -> True
    """

    interest_coverage = _to_float(
        interest_coverage
    )

    if interest_coverage is None:
        return False

    return interest_coverage < threshold


def net_debt(
    borrowings,
    investments
) -> Optional[float]:
    """
    Net Debt =
        borrowings - investments

    Investments are used as the liquid-asset proxy
    according to the Sprint 2 specification.
    """

    borrowings = _to_float(borrowings)
    investments = _to_float(investments)

    if (
        borrowings is None
        or investments is None
    ):
        return None

    return _round(
        borrowings - investments
    )


# ============================================================
# EFFICIENCY RATIOS
# ============================================================

def asset_turnover(
    sales,
    total_assets
) -> Optional[float]:
    """
    Asset Turnover =
        sales / total_assets

    Returns None when total_assets = 0.
    """

    sales = _to_float(sales)
    total_assets = _to_float(total_assets)

    if (
        sales is None
        or total_assets is None
        or total_assets == 0
    ):
        return None

    return _round(
        sales / total_assets
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def calculate_core_ratios(
    *,
    sales,
    operating_profit,
    other_income,
    interest,
    net_profit,
    equity_capital,
    reserves,
    borrowings,
    investments,
    total_assets,
    broad_sector=None,
):
    """
    Calculate all Day 08 and Day 09 core ratios
    for one company-year record.
    """

    npm = net_profit_margin(
        net_profit,
        sales
    )

    opm = operating_profit_margin(
        operating_profit,
        sales
    )

    roe = return_on_equity(
        net_profit,
        equity_capital,
        reserves
    )

    roce = return_on_capital_employed(
        operating_profit,
        equity_capital,
        reserves,
        borrowings
    )

    roa = return_on_assets(
        net_profit,
        total_assets
    )

    de = debt_to_equity(
        borrowings,
        equity_capital,
        reserves
    )

    icr = interest_coverage_ratio(
        operating_profit,
        other_income,
        interest
    )

    return {
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm,
        "return_on_equity_pct": roe,
        "return_on_capital_employed_pct": roce,
        "return_on_assets_pct": roa,
        "debt_to_equity": de,
        "high_leverage_flag": high_leverage_flag(
            de,
            broad_sector
        ),
        "interest_coverage": icr,
        "icr_label": interest_coverage_label(
            icr
        ),
        "icr_warning_flag": icr_warning_flag(
            icr
        ),
        "net_debt": net_debt(
            borrowings,
            investments
        ),
        "asset_turnover": asset_turnover(
            sales,
            total_assets
        ),
    }


# ============================================================
# QUICK SELF-CHECK
# ============================================================

if __name__ == "__main__":

    result = calculate_core_ratios(
        sales=1000,
        operating_profit=200,
        other_income=20,
        interest=50,
        net_profit=120,
        equity_capital=200,
        reserves=300,
        borrowings=250,
        investments=100,
        total_assets=1200,
        broad_sector="Industrials",
    )

    print(
        "RATIO ENGINE SELF-CHECK"
    )

    print(
        "=" * 50
    )

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )