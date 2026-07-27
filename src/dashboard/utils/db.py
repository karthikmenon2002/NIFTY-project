from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
MARKET_CAP_PATH = PROJECT_ROOT / "data" / "supporting" / "market_cap.xlsx"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    conn = _connect()
    try:
        df = pd.read_sql_query(
            """
            SELECT c.id AS company_id, c.company_name, c.about_company, c.website,
                   c.nse_profile, c.bse_profile, c.face_value, c.book_value,
                   c.roce_percentage, c.roe_percentage,
                   s.broad_sector, s.sub_sector, s.market_cap_category
            FROM companies c
            LEFT JOIN sectors s ON c.id = s.company_id
            ORDER BY c.company_name
            """,
            conn,
        )
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_ratios(ticker=None, year=None) -> pd.DataFrame:
    conn = _connect()
    try:
        query = "SELECT * FROM financial_ratios"
        params = []
        if ticker is not None:
            query += " WHERE company_id = ?"
            params.append(ticker)
        elif year is not None:
            query += " WHERE year = ?"
            params.append(year)

        df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            return df

        market_cap = get_market_cap_data()
        if {"company_id", "year"}.issubset(market_cap.columns):
            market_cap = market_cap[["company_id", "year", "market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"]].copy()
            df = df.merge(market_cap, on=["company_id", "year"], how="left")

        return df.sort_values(["company_id", "year"]).reset_index(drop=True)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        df = pd.read_sql_query(
            "SELECT company_id, year, sales, expenses, operating_profit, net_profit FROM profitandloss WHERE company_id = ? ORDER BY year",
            conn,
            params=[ticker],
        )
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql_query(
            "SELECT company_id, year, equity_capital, reserves, borrowings, total_assets FROM balancesheet WHERE company_id = ? ORDER BY year",
            conn,
            params=[ticker],
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql_query(
            "SELECT company_id, year, operating_cash_flow, investing_cash_flow, financing_cash_flow, net_cash_flow FROM cashflow WHERE company_id = ? ORDER BY year",
            conn,
            params=[ticker],
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql_query(
            """
            SELECT s.company_id, c.company_name, s.broad_sector, s.sub_sector, s.market_cap_category
            FROM sectors s
            LEFT JOIN companies c ON s.company_id = c.id
            ORDER BY c.company_name
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None) -> pd.DataFrame:
    conn = _connect()
    try:
        query = """
            SELECT pg.peer_group_name, pg.company_id, c.company_name, s.broad_sector, s.sub_sector, pg.is_benchmark
            FROM peer_groups pg
            LEFT JOIN companies c ON pg.company_id = c.id
            LEFT JOIN sectors s ON pg.company_id = s.company_id
        """
        params = []
        if group_name:
            query += " WHERE pg.peer_group_name = ?"
            params.append(group_name)
        query += " ORDER BY pg.peer_group_name, c.company_name"
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_market_cap_data() -> pd.DataFrame:
    return pd.read_excel(MARKET_CAP_PATH)


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> pd.DataFrame:
    summary_path = PROJECT_ROOT / "output" / "valuation_summary.xlsx"
    if not summary_path.exists():
        return pd.DataFrame(columns=["company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"])
    df = pd.read_excel(summary_path)
    return df[df["company_id"].astype(str).str.upper() == ticker.upper()].copy()
