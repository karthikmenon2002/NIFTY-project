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
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL,
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
    year INTEGER,
    ratio_name TEXT,
    ratio_value REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    peer_company_id TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(id)
);