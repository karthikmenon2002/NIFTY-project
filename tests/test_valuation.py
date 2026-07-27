from pathlib import Path

from src.analytics.valuation import run


def test_valuation_outputs_created(tmp_path):
    summary_path, flags_path = run(output_dir=tmp_path)

    assert Path(summary_path).exists()
    assert Path(flags_path).exists()

    import pandas as pd

    summary = pd.read_excel(summary_path)
    flags = pd.read_csv(flags_path)

    assert len(summary) == 92
    assert {"company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"}.issubset(summary.columns)
    assert {"company_id", "company_name", "sector", "flag"}.issubset(flags.columns)
    assert set(flags["flag"].unique()).issubset({"Caution", "Discount"})
