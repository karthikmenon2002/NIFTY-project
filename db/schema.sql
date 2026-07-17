PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS peer_groups;
DROP TABLE IF EXISTS financial_ratios;
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS prosandcons;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS analysis;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS balancesheet;
DROP TABLE IF EXISTS profitandloss;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

CREATE TABLE profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax REAL,
    net_profit REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    investments REAL,
    other_assets REAL,
    total_assets REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    net_cash_flow REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    metric TEXT,
    value REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    document_type TEXT,
    document_url TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    type TEXT,
    description TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,

    -- Profitability
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    return_on_capital_employed_pct REAL,
    return_on_assets_pct REAL,

    -- Leverage and efficiency
    debt_to_equity REAL,
    high_leverage_flag INTEGER DEFAULT 0,
    interest_coverage REAL,
    icr_label TEXT,
    icr_warning_flag INTEGER DEFAULT 0,
    net_debt REAL,
    asset_turnover REAL,

    -- Cash-flow KPIs
    free_cash_flow_cr REAL,
    cash_from_operations_cr REAL,
    cfo_pat_ratio REAL,
    cfo_quality_label TEXT,
    capex_cr REAL,
    capex_intensity_pct REAL,
    capex_intensity_label TEXT,
    fcf_conversion_rate_pct REAL,

    -- Per-share / capital metrics
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,

    -- CAGR metrics
    revenue_cagr_3yr REAL,
    revenue_cagr_3yr_flag TEXT,
    revenue_cagr_5yr REAL,
    revenue_cagr_5yr_flag TEXT,
    revenue_cagr_10yr REAL,
    revenue_cagr_10yr_flag TEXT,

    pat_cagr_3yr REAL,
    pat_cagr_3yr_flag TEXT,
    pat_cagr_5yr REAL,
    pat_cagr_5yr_flag TEXT,
    pat_cagr_10yr REAL,
    pat_cagr_10yr_flag TEXT,

    eps_cagr_3yr REAL,
    eps_cagr_3yr_flag TEXT,
    eps_cagr_5yr REAL,
    eps_cagr_5yr_flag TEXT,
    eps_cagr_10yr REAL,
    eps_cagr_10yr_flag TEXT,

    -- Capital allocation
    cfo_sign TEXT,
    cfi_sign TEXT,
    cff_sign TEXT,
    capital_allocation_pattern TEXT,

    -- Composite score
    composite_quality_score REAL,

    UNIQUE(company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(id)
        ON DELETE CASCADE
);

CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    peer_company_id TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(id)
);