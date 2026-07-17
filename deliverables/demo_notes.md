Sprint 3 Demo Notes

- Purpose: Financial Screener + Peer Engine deliverables for Sprint 3.
- Key outputs:
  - output/screener_output.xlsx — 6 preset sheets, sorted by composite score.
  - output/peer_comparison.xlsx — 11 peer-group sheets, percentile colour-coding, benchmark highlighted.
  - reports/radar_charts/ — PNG radar charts for each company.
  - DB table: `peer_percentiles` populated in `db/nifty100.db`.
- Tests: All unit tests passed (40 tests, 0 failures).

How to run locally:

```bash
python -m pip install -r requirements.txt  # or pandas numpy pyyaml openpyxl matplotlib pytest
python src/screener/engine.py
python src/analytics/peer.py
python src/analytics/peer_report.py
python src/analytics/radar_charts.py
```

Quick checks during demo:
- Open `output/screener_output.xlsx` → check `quality_compounder` top-5 ROE/D/E.
- Open `output/peer_comparison.xlsx` → verify 11 sheets and median row at bottom.
- View `reports/radar_charts/<COMPANY>_radar.png` for peer-overlay.

Contact: Prepared by automation scripts in `src/screener/engine.py`, `src/analytics/peer.py`, `src/analytics/peer_report.py`, `src/analytics/radar_charts.py`.
