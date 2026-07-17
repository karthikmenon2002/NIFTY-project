"""Data normalisation utilities for the NIFTY100 ETL pipeline."""

import re
from datetime import date, datetime


def normalize_year(value):
    """Convert different year formats into a four-digit integer."""
    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.year

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    text = str(value).strip()

    if not text:
        return None

    match = re.search(r"(19|20)\d{2}", text)
    if match:
        return int(match.group())

    if text.isdigit():
        year = int(text)
        if 0 <= year <= 99:
            return 2000 + year if year <= 50 else 1900 + year

    return None


def normalize_ticker(value):
    """Standardise Indian stock ticker symbols."""
    if value is None:
        return None

    ticker = str(value).strip().upper()

    if not ticker:
        return None

    # Remove common exchange suffixes
    ticker = re.sub(r"\.(NS|BO)$", "", ticker)

    # Remove exchange prefixes
    ticker = re.sub(r"^(NSE|BSE):", "", ticker)

    # Remove unwanted spaces
    ticker = ticker.strip().replace(" ", "")

    return ticker if ticker else None