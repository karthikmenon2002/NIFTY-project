"""
Cash Flow KPIs & Capital Allocation
====================================

Sprint 2 - Day 11

Implements:
1. Free Cash Flow
2. CFO Quality Score
3. CFO Quality Classification
4. CapEx Intensity
5. CapEx Intensity Classification
6. FCF Conversion Rate
7. Capital Allocation Pattern Classification
"""

from typing import Optional, Iterable, Dict, Any


# ============================================================
# HELPER
# ============================================================

def safe_float(value) -> Optional[float]:
    """Convert a value to float safely."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ============================================================
# FREE CASH FLOW
# ============================================================

def calculate_free_cash_flow(
    operating_cash_flow: Optional[float],
    investing_cash_flow: Optional[float],
) -> Optional[float]:
    """
    Free Cash Flow (FCF)

    Sprint formula:
        FCF = operating_cash_flow + investing_cash_flow

    Negative FCF is allowed.
    """

    cfo = safe_float(operating_cash_flow)
    cfi = safe_float(investing_cash_flow)

    if cfo is None or cfi is None:
        return None

    return round(cfo + cfi, 4)


# ============================================================
# CFO / PAT RATIO
# ============================================================

def calculate_cfo_pat_ratio(
    operating_cash_flow: Optional[float],
    net_profit: Optional[float],
) -> Optional[float]:
    """
    Calculate CFO / PAT for one year.

    Returns None if PAT = 0.
    """

    cfo = safe_float(operating_cash_flow)
    pat = safe_float(net_profit)

    if cfo is None or pat is None:
        return None

    if pat == 0:
        return None

    return round(cfo / pat, 4)


# ============================================================
# CFO QUALITY SCORE - 5 YEAR AVERAGE
# ============================================================

def calculate_cfo_quality_score(
    operating_cash_flows: Iterable[Optional[float]],
    net_profits: Iterable[Optional[float]],
) -> Optional[float]:
    """
    CFO Quality Score:
        Average CFO / PAT ratio over available valid years.

    Sprint classification:
        > 1.0       = High Quality
        0.5 - 1.0   = Moderate
        < 0.5       = Accrual Risk

    Years where PAT = 0 or values are missing are ignored.
    """

    ratios = []

    for cfo, pat in zip(operating_cash_flows, net_profits):
        ratio = calculate_cfo_pat_ratio(cfo, pat)

        if ratio is not None:
            ratios.append(ratio)

    if not ratios:
        return None

    return round(sum(ratios) / len(ratios), 4)


def classify_cfo_quality(
    score: Optional[float],
) -> Optional[str]:
    """Classify CFO Quality Score."""

    score = safe_float(score)

    if score is None:
        return None

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


# ============================================================
# CAPEX INTENSITY
# ============================================================

def calculate_capex_intensity(
    investing_cash_flow: Optional[float],
    sales: Optional[float],
) -> Optional[float]:
    """
    CapEx Intensity:
        abs(investing_cash_flow) / sales * 100

    Returns None if sales = 0.
    """

    cfi = safe_float(investing_cash_flow)
    sales_value = safe_float(sales)

    if cfi is None or sales_value is None:
        return None

    if sales_value == 0:
        return None

    result = abs(cfi) / abs(sales_value) * 100

    return round(result, 4)


def classify_capex_intensity(
    capex_intensity: Optional[float],
) -> Optional[str]:
    """
    Classification:
        < 3%    = Asset Light
        3%-8%   = Moderate
        > 8%    = Capital Intensive
    """

    value = safe_float(capex_intensity)

    if value is None:
        return None

    if value < 3:
        return "Asset Light"

    if value <= 8:
        return "Moderate"

    return "Capital Intensive"


# ============================================================
# FCF CONVERSION RATE
# ============================================================

def calculate_fcf_conversion_rate(
    free_cash_flow: Optional[float],
    operating_profit: Optional[float],
) -> Optional[float]:
    """
    FCF Conversion Rate:
        FCF / operating_profit * 100

    Returns None if operating_profit = 0.
    """

    fcf = safe_float(free_cash_flow)
    op_profit = safe_float(operating_profit)

    if fcf is None or op_profit is None:
        return None

    if op_profit == 0:
        return None

    return round((fcf / op_profit) * 100, 4)


# ============================================================
# CASH FLOW SIGN
# ============================================================

def cash_flow_sign(
    value: Optional[float],
) -> str:
    """
    Convert cash flow value into:
        +
        -
        0
    """

    value = safe_float(value)

    if value is None:
        return "0"

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


# ============================================================
# CAPITAL ALLOCATION PATTERN CLASSIFIER
# ============================================================

def classify_capital_allocation(
    operating_cash_flow: Optional[float],
    investing_cash_flow: Optional[float],
    financing_cash_flow: Optional[float],
    cfo_pat_ratio: Optional[float] = None,
) -> str:
    """
    Classify company-year cash-flow pattern.

    Required Sprint patterns:

        (+,-,-) = Reinvestor

        (+,-,-) with high CFO/PAT
                = Shareholder Returns

        (+,+,-) = Liquidating Assets

        (-,+,+) = Distress Signal

        (-,-,+) = Growth Funded by Debt

        (+,+,+) = Cash Accumulator

        (-,-,-) = Pre-Revenue

        Anything else = Mixed
    """

    cfo_sign = cash_flow_sign(operating_cash_flow)
    cfi_sign = cash_flow_sign(investing_cash_flow)
    cff_sign = cash_flow_sign(financing_cash_flow)

    pattern = (
        cfo_sign,
        cfi_sign,
        cff_sign,
    )

    # Positive CFO, negative investing, negative financing
    if pattern == ("+", "-", "-"):

        ratio = safe_float(cfo_pat_ratio)

        # High cash conversion indicates capacity for
        # shareholder distributions.
        if ratio is not None and ratio > 1.0:
            return "Shareholder Returns"

        return "Reinvestor"

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
# COMPLETE CASH FLOW KPI ENGINE
# ============================================================

def calculate_cashflow_kpis(
    operating_cash_flow: Optional[float],
    investing_cash_flow: Optional[float],
    financing_cash_flow: Optional[float],
    sales: Optional[float],
    operating_profit: Optional[float],
    net_profit: Optional[float],
) -> Dict[str, Any]:
    """
    Calculate all single company-year cash-flow KPIs.
    """

    fcf = calculate_free_cash_flow(
        operating_cash_flow,
        investing_cash_flow,
    )

    cfo_pat_ratio = calculate_cfo_pat_ratio(
        operating_cash_flow,
        net_profit,
    )

    capex_intensity = calculate_capex_intensity(
        investing_cash_flow,
        sales,
    )

    fcf_conversion = calculate_fcf_conversion_rate(
        fcf,
        operating_profit,
    )

    pattern_label = classify_capital_allocation(
        operating_cash_flow,
        investing_cash_flow,
        financing_cash_flow,
        cfo_pat_ratio,
    )

    return {
        "free_cash_flow": fcf,
        "cfo_pat_ratio": cfo_pat_ratio,
        "cfo_quality_label": classify_cfo_quality(
            cfo_pat_ratio
        ),
        "capex_intensity_pct": capex_intensity,
        "capex_intensity_label": classify_capex_intensity(
            capex_intensity
        ),
        "fcf_conversion_rate_pct": fcf_conversion,
        "cfo_sign": cash_flow_sign(
            operating_cash_flow
        ),
        "cfi_sign": cash_flow_sign(
            investing_cash_flow
        ),
        "cff_sign": cash_flow_sign(
            financing_cash_flow
        ),
        "pattern_label": pattern_label,
    }


# ============================================================
# SELF-CHECK
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("CASH FLOW KPI ENGINE SELF-CHECK")
    print("=" * 70)

    result = calculate_cashflow_kpis(
        operating_cash_flow=150,
        investing_cash_flow=-60,
        financing_cash_flow=-30,
        sales=1000,
        operating_profit=200,
        net_profit=120,
    )

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 70)
    print("5-YEAR CFO QUALITY TEST")
    print("=" * 70)

    score = calculate_cfo_quality_score(
        operating_cash_flows=[
            100,
            120,
            140,
            160,
            180,
        ],
        net_profits=[
            80,
            100,
            110,
            130,
            150,
        ],
    )

    print(f"CFO Quality Score: {score}")
    print(
        f"CFO Quality Classification: "
        f"{classify_cfo_quality(score)}"
    )

    print("\n" + "=" * 70)
    print("CAPITAL ALLOCATION PATTERN TESTS")
    print("=" * 70)

    test_patterns = [
        (
            "Reinvestor",
            100,
            -50,
            -20,
            0.8,
        ),
        (
            "Shareholder Returns",
            100,
            -50,
            -20,
            1.5,
        ),
        (
            "Liquidating Assets",
            100,
            50,
            -20,
            0.8,
        ),
        (
            "Distress Signal",
            -100,
            50,
            20,
            0.8,
        ),
        (
            "Growth Funded by Debt",
            -100,
            -50,
            20,
            0.8,
        ),
        (
            "Cash Accumulator",
            100,
            50,
            20,
            0.8,
        ),
        (
            "Pre-Revenue",
            -100,
            -50,
            -20,
            0.8,
        ),
    ]

    for (
        expected,
        cfo,
        cfi,
        cff,
        ratio,
    ) in test_patterns:

        actual = classify_capital_allocation(
            cfo,
            cfi,
            cff,
            ratio,
        )

        status = (
            "PASS"
            if actual == expected
            else "FAIL"
        )

        print(
            f"{status}: "
            f"Expected={expected}, "
            f"Actual={actual}"
        )