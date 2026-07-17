import pytest

from src.etl.normaliser import normalize_year, normalize_ticker


@pytest.mark.parametrize(
    "value, expected",
    [
        (2024, 2024),
        (2020.0, 2020),
        ("2023", 2023),
        (" 2022 ", 2022),
        ("FY2021", 2021),
        ("2020-21", 2020),
        ("Year 2019", 2019),
        ("01/01/2018", 2018),
        ("25", 2025),
        ("99", 1999),
        ("00", 2000),
        (None, None),
        ("", None),
        ("   ", None),
        ("invalid", None),
        (date := __import__("datetime").date(2024, 1, 1), 2024),
        (__import__("datetime").datetime(2023, 5, 1), 2023),
        (1950, 1950),
        (2050, 2050),
        ("FY 2017-18", 2017),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("RELIANCE", "RELIANCE"),
        ("reliance", "RELIANCE"),
        (" reliance ", "RELIANCE"),
        ("RELIANCE.NS", "RELIANCE"),
        ("RELIANCE.BO", "RELIANCE"),
        ("NSE:RELIANCE", "RELIANCE"),
        ("BSE:RELIANCE", "RELIANCE"),
        ("TCS", "TCS"),
        ("tcs.ns", "TCS"),
        ("INFY ", "INFY"),
        (" HDFCBANK.NS ", "HDFCBANK"),
        ("NSE:SBIN", "SBIN"),
        ("BSE:ITC", "ITC"),
        ("BAJAJ FINANCE", "BAJAJFINANCE"),
        (None, None),
        ("", None),
        ("   ", None),
        ("MARUTI.NS", "MARUTI"),
        ("ICICIBANK.BO", "ICICIBANK"),
        ("NSE:LT", "LT"),
    ],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected