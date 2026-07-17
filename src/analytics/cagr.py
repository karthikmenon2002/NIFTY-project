"""
CAGR Engine
===========

Calculates Compound Annual Growth Rate (CAGR) and handles
the edge cases required for Sprint 2.

Formula:
    CAGR = ((end / start) ** (1 / years) - 1) * 100

Edge-case flags:
    DECLINE_TO_LOSS
    TURNAROUND
    BOTH_NEGATIVE
    ZERO_BASE
    INSUFFICIENT_DATA
"""

from typing import Optional, Tuple, Dict, Any


# ============================================================
# CAGR FLAGS
# ============================================================

DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ============================================================
# CORE CAGR FUNCTION
# ============================================================

def calculate_cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    years: int,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate CAGR and return:

        (cagr_value, flag)

    Normal example:
        calculate_cagr(100, 150, 5)
        -> (8.4472, None)

    Edge cases:
        positive -> negative = DECLINE_TO_LOSS
        negative -> positive = TURNAROUND
        negative -> negative = BOTH_NEGATIVE
        zero start          = ZERO_BASE
        missing/invalid     = INSUFFICIENT_DATA
    """

    # Missing values
    if start_value is None or end_value is None:
        return None, INSUFFICIENT_DATA

    # Invalid year period
    if years is None or years <= 0:
        return None, INSUFFICIENT_DATA

    try:
        start = float(start_value)
        end = float(end_value)
    except (TypeError, ValueError):
        return None, INSUFFICIENT_DATA

    # Zero base
    if start == 0:
        return None, ZERO_BASE

    # Positive start -> negative end
    if start > 0 and end < 0:
        return None, DECLINE_TO_LOSS

    # Negative start -> positive end
    if start < 0 and end > 0:
        return None, TURNAROUND

    # Negative start -> negative end
    if start < 0 and end < 0:
        return None, BOTH_NEGATIVE

    # End value zero cannot produce a meaningful normal CAGR
    if end == 0:
        return None, DECLINE_TO_LOSS

    # Normal positive-to-positive CAGR
    cagr = ((end / start) ** (1 / years) - 1) * 100

    return round(cagr, 4), None


# ============================================================
# WINDOW CAGR
# ============================================================

def calculate_window_cagr(
    yearly_values: Dict[int, Optional[float]],
    end_year: int,
    window: int,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate CAGR for a specific window.

    Example:
        For a 5-year CAGR ending in 2025:
            start year = 2020
            end year   = 2025

    Requires both endpoint years.
    """

    if not yearly_values:
        return None, INSUFFICIENT_DATA

    start_year = end_year - window

    if start_year not in yearly_values:
        return None, INSUFFICIENT_DATA

    if end_year not in yearly_values:
        return None, INSUFFICIENT_DATA

    start_value = yearly_values.get(start_year)
    end_value = yearly_values.get(end_year)

    return calculate_cagr(
        start_value=start_value,
        end_value=end_value,
        years=window,
    )


# ============================================================
# CALCULATE 3Y, 5Y AND 10Y CAGR
# ============================================================

def calculate_all_cagrs(
    yearly_values: Dict[int, Optional[float]],
    end_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate 3-year, 5-year and 10-year CAGR.

    Returns:
        {
            "cagr_3yr": value,
            "cagr_3yr_flag": flag,
            "cagr_5yr": value,
            "cagr_5yr_flag": flag,
            "cagr_10yr": value,
            "cagr_10yr_flag": flag,
        }
    """

    if not yearly_values:
        return {
            "cagr_3yr": None,
            "cagr_3yr_flag": INSUFFICIENT_DATA,
            "cagr_5yr": None,
            "cagr_5yr_flag": INSUFFICIENT_DATA,
            "cagr_10yr": None,
            "cagr_10yr_flag": INSUFFICIENT_DATA,
        }

    # Use latest available year if end_year is not supplied
    if end_year is None:
        end_year = max(yearly_values.keys())

    cagr_3yr, flag_3yr = calculate_window_cagr(
        yearly_values,
        end_year,
        3,
    )

    cagr_5yr, flag_5yr = calculate_window_cagr(
        yearly_values,
        end_year,
        5,
    )

    cagr_10yr, flag_10yr = calculate_window_cagr(
        yearly_values,
        end_year,
        10,
    )

    return {
        "cagr_3yr": cagr_3yr,
        "cagr_3yr_flag": flag_3yr,
        "cagr_5yr": cagr_5yr,
        "cagr_5yr_flag": flag_5yr,
        "cagr_10yr": cagr_10yr,
        "cagr_10yr_flag": flag_10yr,
    }


# ============================================================
# REVENUE CAGR
# ============================================================

def calculate_revenue_cagrs(
    yearly_revenue: Dict[int, Optional[float]],
    end_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate Revenue CAGR for 3, 5 and 10 years."""

    result = calculate_all_cagrs(
        yearly_values=yearly_revenue,
        end_year=end_year,
    )

    return {
        "revenue_cagr_3yr": result["cagr_3yr"],
        "revenue_cagr_3yr_flag": result["cagr_3yr_flag"],

        "revenue_cagr_5yr": result["cagr_5yr"],
        "revenue_cagr_5yr_flag": result["cagr_5yr_flag"],

        "revenue_cagr_10yr": result["cagr_10yr"],
        "revenue_cagr_10yr_flag": result["cagr_10yr_flag"],
    }


# ============================================================
# PAT / NET PROFIT CAGR
# ============================================================

def calculate_pat_cagrs(
    yearly_pat: Dict[int, Optional[float]],
    end_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate PAT / Net Profit CAGR for 3, 5 and 10 years."""

    result = calculate_all_cagrs(
        yearly_values=yearly_pat,
        end_year=end_year,
    )

    return {
        "pat_cagr_3yr": result["cagr_3yr"],
        "pat_cagr_3yr_flag": result["cagr_3yr_flag"],

        "pat_cagr_5yr": result["cagr_5yr"],
        "pat_cagr_5yr_flag": result["cagr_5yr_flag"],

        "pat_cagr_10yr": result["cagr_10yr"],
        "pat_cagr_10yr_flag": result["cagr_10yr_flag"],
    }


# ============================================================
# EPS CAGR
# ============================================================

def calculate_eps_cagrs(
    yearly_eps: Dict[int, Optional[float]],
    end_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate EPS CAGR for 3, 5 and 10 years."""

    result = calculate_all_cagrs(
        yearly_values=yearly_eps,
        end_year=end_year,
    )

    return {
        "eps_cagr_3yr": result["cagr_3yr"],
        "eps_cagr_3yr_flag": result["cagr_3yr_flag"],

        "eps_cagr_5yr": result["cagr_5yr"],
        "eps_cagr_5yr_flag": result["cagr_5yr_flag"],

        "eps_cagr_10yr": result["cagr_10yr"],
        "eps_cagr_10yr_flag": result["cagr_10yr_flag"],
    }


# ============================================================
# SELF-CHECK
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("CAGR ENGINE SELF-CHECK")
    print("=" * 70)

    test_cases = {
        "Normal CAGR": calculate_cagr(
            100,
            200,
            5,
        ),

        "Decline to Loss": calculate_cagr(
            100,
            -50,
            5,
        ),

        "Turnaround": calculate_cagr(
            -100,
            50,
            5,
        ),

        "Both Negative": calculate_cagr(
            -100,
            -50,
            5,
        ),

        "Zero Base": calculate_cagr(
            0,
            100,
            5,
        ),

        "Insufficient Data": calculate_cagr(
            None,
            100,
            5,
        ),
    }

    for name, result in test_cases.items():
        print(
            f"{name:20} "
            f"Value: {str(result[0]):12} "
            f"Flag: {result[1]}"
        )

    print("\n" + "=" * 70)
    print("3Y / 5Y / 10Y WINDOW TEST")
    print("=" * 70)

    sample_revenue = {
        2015: 100,
        2016: 110,
        2017: 120,
        2018: 130,
        2019: 145,
        2020: 160,
        2021: 180,
        2022: 200,
        2023: 230,
        2024: 260,
        2025: 300,
    }

    revenue_result = calculate_revenue_cagrs(
        sample_revenue,
        end_year=2025,
    )

    for key, value in revenue_result.items():
        print(f"{key}: {value}")