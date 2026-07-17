from pathlib import Path
import sqlite3

import numpy as np
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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

PEER_ANALYSIS_CSV = (
    OUTPUT_DIR
    / "peer_analysis.csv"
)

PEER_SUMMARY_CSV = (
    OUTPUT_DIR
    / "peer_group_summary.csv"
)


# ============================================================
# METRIC CONFIGURATION
# ============================================================

# For these metrics, a higher value is generally better.
HIGHER_IS_BETTER = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "interest_coverage",
    "asset_turnover",
    "cfo_pat_ratio",
    "fcf_conversion_rate_pct",
    "revenue_cagr_3yr",
    "revenue_cagr_5yr",
    "pat_cagr_3yr",
    "pat_cagr_5yr",
    "composite_quality_score",
]


# For these metrics, a lower value is generally better.
LOWER_IS_BETTER = [
    "debt_to_equity",
]


ALL_METRICS = (
    HIGHER_IS_BETTER
    + LOWER_IS_BETTER
)


# ============================================================
# DATABASE HELPERS
# ============================================================

def table_exists(
    conn,
    table_name,
):
    """
    Check whether a SQLite table exists.
    """

    result = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return result is not None


def get_table_columns(
    conn,
    table_name,
):
    """
    Return the list of columns in a SQLite table.
    """

    rows = conn.execute(
        f"""
        PRAGMA table_info({table_name})
        """
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


# ============================================================
# CLEANING HELPERS
# ============================================================

def clean_company_id(value):
    """
    Standardize company IDs.
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if value in {
        "",
        "NAN",
        "NONE",
        "NULL",
        "<NA>",
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
        "<na>",
    }:
        return None

    return value


def safe_numeric(series):
    """
    Convert a pandas Series to numeric values.
    Invalid values become NaN.
    """

    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# PEER SCORING HELPERS
# ============================================================

def percentile_score(
    series,
    higher_is_better=True,
):
    """
    Convert a metric into a percentile score from 0 to 100.

    Best values receive the highest percentile.
    Missing values remain NaN.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid_count = (
        numeric
        .notna()
        .sum()
    )

    if valid_count == 0:

        return pd.Series(
            np.nan,
            index=series.index,
            dtype=float,
        )

    if higher_is_better:

        return (
            numeric.rank(
                method="average",
                pct=True,
                ascending=True,
            )
            * 100
        )

    return (
        numeric.rank(
            method="average",
            pct=True,
            ascending=False,
        )
        * 100
    )


def rank_metric(
    series,
    higher_is_better=True,
):
    """
    Rank companies inside a peer group.

    Rank 1 = best.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    return numeric.rank(
        method="min",
        ascending=not higher_is_better,
        na_option="bottom",
    )


def classify_peer_position(
    percentile,
):
    """
    Convert overall peer percentile into
    a readable classification.
    """

    if pd.isna(percentile):
        return "Insufficient Data"

    if percentile >= 80:
        return "Peer Leader"

    if percentile >= 60:
        return "Above Average"

    if percentile >= 40:
        return "Average"

    if percentile >= 20:
        return "Below Average"

    return "Peer Laggard"


# ============================================================
# LOAD DATA
# ============================================================

def load_data(conn):

    print()
    print("=" * 70)
    print("LOADING PEER ANALYSIS DATA")
    print("=" * 70)

    required_tables = [
        "companies",
        "financial_ratios",
        "peer_groups",
        "sectors",
    ]

    missing_tables = [
        table
        for table in required_tables
        if not table_exists(
            conn,
            table,
        )
    ]

    if missing_tables:

        raise RuntimeError(
            "Missing required tables: "
            + ", ".join(
                missing_tables
            )
        )

    # --------------------------------------------------------
    # Validate supporting table schemas
    # --------------------------------------------------------

    peer_columns = get_table_columns(
        conn,
        "peer_groups",
    )

    sector_columns = get_table_columns(
        conn,
        "sectors",
    )

    required_peer_columns = {
        "company_id",
        "peer_group_name",
        "is_benchmark",
    }

    required_sector_columns = {
        "company_id",
        "broad_sector",
        "sub_sector",
    }

    missing_peer_columns = (
        required_peer_columns
        - set(peer_columns)
    )

    missing_sector_columns = (
        required_sector_columns
        - set(sector_columns)
    )

    if missing_peer_columns:

        raise RuntimeError(
            "peer_groups table is missing columns: "
            + ", ".join(
                sorted(
                    missing_peer_columns
                )
            )
            + "\nRun "
            "src/etl/load_supporting_data.py "
            "before peer analysis."
        )

    if missing_sector_columns:

        raise RuntimeError(
            "sectors table is missing columns: "
            + ", ".join(
                sorted(
                    missing_sector_columns
                )
            )
            + "\nRun "
            "src/etl/load_supporting_data.py "
            "before peer analysis."
        )

    # --------------------------------------------------------
    # Latest financial-ratio row for each company
    # --------------------------------------------------------

    ratios = pd.read_sql_query(
        """
        SELECT fr.*
        FROM financial_ratios fr

        INNER JOIN
        (
            SELECT
                company_id,
                MAX(year) AS latest_year

            FROM financial_ratios

            GROUP BY company_id
        ) latest

            ON fr.company_id =
               latest.company_id

           AND fr.year =
               latest.latest_year
        """,
        conn,
    )

    # --------------------------------------------------------
    # Companies
    # --------------------------------------------------------

    companies = pd.read_sql_query(
        """
        SELECT *
        FROM companies
        """,
        conn,
    )

    # --------------------------------------------------------
    # Peer groups
    # --------------------------------------------------------

    peer_groups = pd.read_sql_query(
        """
        SELECT
            company_id,
            peer_group_name,
            is_benchmark

        FROM peer_groups
        """,
        conn,
    )

    # --------------------------------------------------------
    # Sectors
    # --------------------------------------------------------

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category

        FROM sectors
        """,
        conn,
    )

    print(
        f"Latest financial-ratio rows: "
        f"{len(ratios)}"
    )

    print(
        f"Companies:                   "
        f"{len(companies)}"
    )

    print(
        f"Peer-group assignments:      "
        f"{len(peer_groups)}"
    )

    print(
        f"Sector assignments:          "
        f"{len(sectors)}"
    )

    return (
        ratios,
        companies,
        peer_groups,
        sectors,
    )


# ============================================================
# PREPARE PEER DATA
# ============================================================

def prepare_peer_data(
    ratios,
    companies,
    peer_groups,
    sectors,
):

    print()
    print("=" * 70)
    print("PREPARING PEER DATA")
    print("=" * 70)

    # --------------------------------------------------------
    # Clean financial-ratio company IDs
    # --------------------------------------------------------

    ratios = ratios.copy()

    ratios["company_id"] = (
        ratios["company_id"]
        .apply(clean_company_id)
    )

    # --------------------------------------------------------
    # Clean peer-group data
    # --------------------------------------------------------

    peer_groups = (
        peer_groups.copy()
    )

    peer_groups["company_id"] = (
        peer_groups["company_id"]
        .apply(clean_company_id)
    )

    peer_groups["peer_group_name"] = (
        peer_groups[
            "peer_group_name"
        ]
        .apply(clean_text)
    )

    peer_groups[
        "is_benchmark"
    ] = pd.to_numeric(
        peer_groups[
            "is_benchmark"
        ],
        errors="coerce",
    ).fillna(0)

    # If a company appears multiple times,
    # prefer a benchmark row.
    peer_groups = (
        peer_groups
        .sort_values(
            [
                "company_id",
                "is_benchmark",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "company_id"
            ],
            keep="first",
        )
    )

    # --------------------------------------------------------
    # Clean sector data
    # --------------------------------------------------------

    sectors = sectors.copy()

    sectors["company_id"] = (
        sectors["company_id"]
        .apply(clean_company_id)
    )

    for column in [
        "broad_sector",
        "sub_sector",
        "market_cap_category",
    ]:

        if column in sectors.columns:

            sectors[column] = (
                sectors[column]
                .apply(clean_text)
            )

    if (
        "index_weight_pct"
        in sectors.columns
    ):

        sectors[
            "index_weight_pct"
        ] = pd.to_numeric(
            sectors[
                "index_weight_pct"
            ],
            errors="coerce",
        )

    sectors = (
        sectors
        .drop_duplicates(
            subset=[
                "company_id"
            ],
            keep="last",
        )
    )

    # --------------------------------------------------------
    # Merge financial ratios with peer groups
    # --------------------------------------------------------

    data = ratios.merge(
        peer_groups[
            [
                "company_id",
                "peer_group_name",
                "is_benchmark",
            ]
        ],
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Merge sector data
    # --------------------------------------------------------

    data = data.merge(
        sectors[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
                "index_weight_pct",
                "market_cap_category",
            ]
        ],
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Convert financial metrics to numeric
    # --------------------------------------------------------

    for metric in ALL_METRICS:

        if metric in data.columns:

            data[metric] = (
                safe_numeric(
                    data[metric]
                )
            )

    # ========================================================
    # SMART PEER-GROUP ASSIGNMENT
    # ========================================================

    # Count membership in explicit peer groups.
    peer_group_sizes = (
        data[
            "peer_group_name"
        ]
        .dropna()
        .value_counts()
    )

    # Count membership in sub-sectors.
    sub_sector_sizes = (
        data[
            "sub_sector"
        ]
        .dropna()
        .value_counts()
    )

    # Count membership in broad sectors.
    broad_sector_sizes = (
        data[
            "broad_sector"
        ]
        .dropna()
        .value_counts()
    )

    def assign_smart_peer_group(row):

        peer_group = clean_text(
            row.get(
                "peer_group_name"
            )
        )

        sub_sector = clean_text(
            row.get(
                "sub_sector"
            )
        )

        broad_sector = clean_text(
            row.get(
                "broad_sector"
            )
        )

        # ----------------------------------------------------
        # Priority 1:
        # Explicit peer group with at least 2 companies
        # ----------------------------------------------------

        if peer_group:

            explicit_size = (
                peer_group_sizes.get(
                    peer_group,
                    0,
                )
            )

            if explicit_size >= 2:

                return pd.Series(
                    [
                        "Explicit Peer Group",
                        (
                            "Peer Group: "
                            f"{peer_group}"
                        ),
                    ]
                )

        # ----------------------------------------------------
        # Priority 2:
        # Sub-sector with at least 2 companies
        # ----------------------------------------------------

        if sub_sector:

            sub_sector_size = (
                sub_sector_sizes.get(
                    sub_sector,
                    0,
                )
            )

            if sub_sector_size >= 2:

                return pd.Series(
                    [
                        "Sub Sector",
                        (
                            "Sub Sector: "
                            f"{sub_sector}"
                        ),
                    ]
                )

        # ----------------------------------------------------
        # Priority 3:
        # Broad-sector fallback
        # ----------------------------------------------------

        if broad_sector:

            broad_sector_size = (
                broad_sector_sizes.get(
                    broad_sector,
                    0,
                )
            )

            if broad_sector_size >= 2:

                return pd.Series(
                    [
                        "Broad Sector Fallback",
                        (
                            "Broad Sector: "
                            f"{broad_sector}"
                        ),
                    ]
                )

        # ----------------------------------------------------
        # Priority 4:
        # Final fallback
        # ----------------------------------------------------

        return pd.Series(
            [
                "Unclassified",
                "Unclassified",
            ]
        )

    data[
        [
            "peer_source",
            "analysis_group",
        ]
    ] = data.apply(
        assign_smart_peer_group,
        axis=1,
    )

    # --------------------------------------------------------
    # Initial group-size calculation
    # --------------------------------------------------------

    data[
        "peer_group_size"
    ] = (
        data
        .groupby(
            "analysis_group"
        )[
            "company_id"
        ]
        .transform(
            "count"
        )
    )

    print(
        f"Companies prepared: "
        f"{len(data)}"
    )

    print()
    print(
        "PEER SOURCE DISTRIBUTION"
    )

    print("-" * 70)

    print(
        data[
            "peer_source"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "ANALYSIS GROUP COUNT"
    )

    print("-" * 70)

    print(
        f"Unique analysis groups: "
        f"{data['analysis_group'].nunique()}"
    )

    print()
    print(
        "GROUP SIZE DISTRIBUTION"
    )

    print("-" * 70)

    group_sizes = (
        data
        .groupby(
            "analysis_group"
        )[
            "company_id"
        ]
        .nunique()
        .sort_values()
    )

    print(
        group_sizes
        .value_counts()
        .sort_index()
        .to_string()
    )

    return data


# ============================================================
# CALCULATE PEER METRICS
# ============================================================

def calculate_peer_metrics(
    data,
):

    print()
    print("=" * 70)
    print(
        "CALCULATING PEER PERCENTILES AND RANKS"
    )
    print("=" * 70)

    result = data.copy()

    available_metrics = [
        metric
        for metric in ALL_METRICS
        if metric in result.columns
    ]

    print(
        f"Available metrics: "
        f"{len(available_metrics)}"
    )

    print()

    for metric in available_metrics:
        print(metric)

    # --------------------------------------------------------
    # Recalculate peer-group size
    # --------------------------------------------------------

    result[
        "peer_group_size"
    ] = (
        result
        .groupby(
            "analysis_group"
        )[
            "company_id"
        ]
        .transform(
            "count"
        )
    )

    # --------------------------------------------------------
    # Calculate percentile and rank for every metric
    # --------------------------------------------------------

    percentile_columns = []

    for metric in available_metrics:

        higher_is_better = (
            metric
            in HIGHER_IS_BETTER
        )

        percentile_column = (
            f"{metric}"
            "_peer_percentile"
        )

        rank_column = (
            f"{metric}"
            "_peer_rank"
        )

        result[
            percentile_column
        ] = (
            result
            .groupby(
                "analysis_group",
                group_keys=False,
            )[
                metric
            ]
            .transform(
                lambda series:
                percentile_score(
                    series,
                    higher_is_better,
                )
            )
        )

        result[
            rank_column
        ] = (
            result
            .groupby(
                "analysis_group",
                group_keys=False,
            )[
                metric
            ]
            .transform(
                lambda series:
                rank_metric(
                    series,
                    higher_is_better,
                )
            )
        )

        percentile_columns.append(
            percentile_column
        )

    # --------------------------------------------------------
    # Composite peer score
    # --------------------------------------------------------

    if percentile_columns:

        result[
            "peer_composite_score"
        ] = (
            result[
                percentile_columns
            ]
            .mean(
                axis=1,
                skipna=True,
            )
            .round(2)
        )

        result[
            "metrics_available_for_score"
        ] = (
            result[
                percentile_columns
            ]
            .notna()
            .sum(
                axis=1
            )
        )

    else:

        result[
            "peer_composite_score"
        ] = np.nan

        result[
            "metrics_available_for_score"
        ] = 0

    # --------------------------------------------------------
    # Overall peer rank
    # --------------------------------------------------------

    result[
        "peer_overall_rank"
    ] = (
        result
        .groupby(
            "analysis_group"
        )[
            "peer_composite_score"
        ]
        .rank(
            method="min",
            ascending=False,
            na_option="bottom",
        )
    )

    # --------------------------------------------------------
    # Overall peer percentile
    # --------------------------------------------------------

    result[
        "peer_overall_percentile"
    ] = (
        result
        .groupby(
            "analysis_group",
            group_keys=False,
        )[
            "peer_composite_score"
        ]
        .transform(
            lambda series:
            percentile_score(
                series,
                higher_is_better=True,
            )
        )
        .round(2)
    )

    # --------------------------------------------------------
    # Peer position
    # --------------------------------------------------------

    result[
        "peer_position"
    ] = (
        result[
            "peer_overall_percentile"
        ]
        .apply(
            classify_peer_position
        )
    )

    print()
    print(
        "PEER POSITION DISTRIBUTION"
    )

    print("-" * 70)

    print(
        result[
            "peer_position"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    return result


# ============================================================
# CREATE PEER-GROUP SUMMARY
# ============================================================

def create_peer_summary(
    result,
):

    print()
    print("=" * 70)
    print(
        "CREATING PEER GROUP SUMMARY"
    )
    print("=" * 70)

    summary = (
        result
        .groupby(
            "analysis_group",
            dropna=False,
        )
        .agg(
            company_count=(
                "company_id",
                "nunique",
            ),
            average_peer_score=(
                "peer_composite_score",
                "mean",
            ),
            median_peer_score=(
                "peer_composite_score",
                "median",
            ),
            best_peer_score=(
                "peer_composite_score",
                "max",
            ),
            lowest_peer_score=(
                "peer_composite_score",
                "min",
            ),
        )
        .reset_index()
    )

    score_columns = [
        "average_peer_score",
        "median_peer_score",
        "best_peer_score",
        "lowest_peer_score",
    ]

    for column in score_columns:

        summary[column] = (
            summary[column]
            .round(2)
        )

    # --------------------------------------------------------
    # Identify leader of each analysis group
    # --------------------------------------------------------

    leaders = (
        result
        .sort_values(
            [
                "analysis_group",
                "peer_composite_score",
                "company_id",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates(
            subset=[
                "analysis_group"
            ],
            keep="first",
        )
        [
            [
                "analysis_group",
                "company_id",
                "peer_composite_score",
            ]
        ]
        .rename(
            columns={
                "company_id":
                    "peer_group_leader",

                "peer_composite_score":
                    "leader_score",
            }
        )
    )

    summary = summary.merge(
        leaders,
        on="analysis_group",
        how="left",
    )

    print(
        f"Peer groups summarized: "
        f"{len(summary)}"
    )

    return summary


# ============================================================
# VALIDATION
# ============================================================

def validate_results(
    result,
):

    print()
    print("=" * 70)
    print(
        "PEER ANALYSIS VALIDATION"
    )
    print("=" * 70)

    failures = []
    warnings = []

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    row_count = len(result)

    print(
        f"Rows generated:              "
        f"{row_count}"
    )

    if row_count == 0:

        failures.append(
            "Peer analysis produced zero rows."
        )

    # --------------------------------------------------------
    # Company coverage
    # --------------------------------------------------------

    company_count = (
        result[
            "company_id"
        ]
        .nunique()
    )

    print(
        f"Distinct companies:          "
        f"{company_count}"
    )

    if company_count < 92:

        warnings.append(
            f"Only {company_count} companies "
            "are represented."
        )

    # --------------------------------------------------------
    # Duplicate companies
    # --------------------------------------------------------

    duplicate_count = int(
        result
        .duplicated(
            subset=[
                "company_id"
            ]
        )
        .sum()
    )

    print(
        f"Duplicate company rows:      "
        f"{duplicate_count}"
    )

    if duplicate_count > 0:

        failures.append(
            f"Found {duplicate_count} "
            "duplicate company rows."
        )

    # --------------------------------------------------------
    # Missing analysis groups
    # --------------------------------------------------------

    missing_groups = int(
        result[
            "analysis_group"
        ]
        .isna()
        .sum()
    )

    print(
        f"Missing analysis groups:     "
        f"{missing_groups}"
    )

    if missing_groups > 0:

        failures.append(
            f"{missing_groups} companies "
            "have no analysis group."
        )

    # --------------------------------------------------------
    # Unclassified companies
    # --------------------------------------------------------

    unclassified_count = int(
        (
            result[
                "analysis_group"
            ]
            == "Unclassified"
        )
        .sum()
    )

    print(
        f"Unclassified companies:      "
        f"{unclassified_count}"
    )

    if unclassified_count > 0:

        warnings.append(
            f"{unclassified_count} companies "
            "remain unclassified."
        )

    # --------------------------------------------------------
    # Single-company groups
    # --------------------------------------------------------

    group_counts = (
        result
        .groupby(
            "analysis_group"
        )[
            "company_id"
        ]
        .nunique()
    )

    single_company_groups = int(
        (
            group_counts
            == 1
        )
        .sum()
    )

    print(
        f"Single-company groups:       "
        f"{single_company_groups}"
    )

    if single_company_groups > 0:

        warnings.append(
            f"{single_company_groups} analysis "
            "groups contain only one company."
        )

    # --------------------------------------------------------
    # Missing composite scores
    # --------------------------------------------------------

    missing_scores = int(
        result[
            "peer_composite_score"
        ]
        .isna()
        .sum()
    )

    print(
        f"Missing composite scores:    "
        f"{missing_scores}"
    )

    if missing_scores > 0:

        warnings.append(
            f"{missing_scores} companies have "
            "no peer composite score."
        )

    # --------------------------------------------------------
    # Invalid percentile values
    # --------------------------------------------------------

    invalid_percentiles = int(
        (
            (
                result[
                    "peer_overall_percentile"
                ]
                < 0
            )
            |
            (
                result[
                    "peer_overall_percentile"
                ]
                > 100
            )
        )
        .fillna(False)
        .sum()
    )

    print(
        f"Invalid peer percentiles:    "
        f"{invalid_percentiles}"
    )

    if invalid_percentiles > 0:

        failures.append(
            f"Found {invalid_percentiles} "
            "invalid percentile values."
        )

    # --------------------------------------------------------
    # Print warnings
    # --------------------------------------------------------

    if warnings:

        print()
        print("WARNINGS")
        print("-" * 70)

        for number, warning in enumerate(
            warnings,
            start=1,
        ):

            print(
                f"{number}. {warning}"
            )

    # --------------------------------------------------------
    # Print failures
    # --------------------------------------------------------

    if failures:

        print()
        print("FAILURES")
        print("-" * 70)

        for number, failure in enumerate(
            failures,
            start=1,
        ):

            print(
                f"{number}. {failure}"
            )

        return False

    print()
    print(
        "PASS: Peer analysis validation "
        "completed with no critical failures."
    )

    return True


# ============================================================
# EXPORT RESULTS
# ============================================================

def export_results(
    result,
    summary,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Put important columns first
    # --------------------------------------------------------

    priority_columns = [
        "company_id",
        "year",
        "peer_group_name",
        "is_benchmark",
        "broad_sector",
        "sub_sector",
        "market_cap_category",
        "index_weight_pct",
        "peer_source",
        "analysis_group",
        "peer_group_size",
        "peer_composite_score",
        "peer_overall_rank",
        "peer_overall_percentile",
        "peer_position",
        "metrics_available_for_score",
    ]

    existing_priority_columns = [
        column
        for column in priority_columns
        if column in result.columns
    ]

    remaining_columns = [
        column
        for column in result.columns
        if column
        not in existing_priority_columns
    ]

    result = result[
        existing_priority_columns
        + remaining_columns
    ]

    # --------------------------------------------------------
    # Sort output
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "analysis_group",
            "peer_overall_rank",
            "company_id",
        ],
        ascending=[
            True,
            True,
            True,
        ],
    )

    # --------------------------------------------------------
    # Export detailed peer analysis
    # --------------------------------------------------------

    result.to_csv(
        PEER_ANALYSIS_CSV,
        index=False,
    )

    # --------------------------------------------------------
    # Export peer-group summary
    # --------------------------------------------------------

    summary.to_csv(
        PEER_SUMMARY_CSV,
        index=False,
    )

    print()
    print("=" * 70)
    print("EXPORT COMPLETE")
    print("=" * 70)

    print()
    print(
        "Peer analysis:"
    )

    print(
        PEER_ANALYSIS_CSV
    )

    print()
    print(
        "Peer-group summary:"
    )

    print(
        PEER_SUMMARY_CSV
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "SPRINT 2 - FINANCIAL RATIO ENGINE"
    )
    print(
        "PEER ANALYSIS"
    )
    print("=" * 70)

    print(
        f"Database: {DB_PATH}"
    )

    # --------------------------------------------------------
    # Validate database path
    # --------------------------------------------------------

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found:\n"
            f"{DB_PATH}"
        )

    # --------------------------------------------------------
    # Connect
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        # ----------------------------------------------------
        # Load data
        # ----------------------------------------------------

        (
            ratios,
            companies,
            peer_groups,
            sectors,
        ) = load_data(
            conn
        )

        # ----------------------------------------------------
        # Prepare peer groups
        # ----------------------------------------------------

        data = prepare_peer_data(
            ratios,
            companies,
            peer_groups,
            sectors,
        )

        # ----------------------------------------------------
        # Calculate rankings
        # ----------------------------------------------------

        result = (
            calculate_peer_metrics(
                data
            )
        )

        # ----------------------------------------------------
        # Create summary
        # ----------------------------------------------------

        summary = (
            create_peer_summary(
                result
            )
        )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        passed = (
            validate_results(
                result
            )
        )

        # ----------------------------------------------------
        # Export
        # ----------------------------------------------------

        export_results(
            result,
            summary,
        )

        # ----------------------------------------------------
        # Final status
        # ----------------------------------------------------

        print()
        print("=" * 70)

        if passed:

            print(
                "PEER ANALYSIS STATUS: PASS"
            )

            print(
                "Peer comparison results were "
                "successfully generated."
            )

        else:

            print(
                "PEER ANALYSIS STATUS: FAIL"
            )

            print(
                "Review the validation failures above."
            )

        print("=" * 70)

    finally:

        conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()