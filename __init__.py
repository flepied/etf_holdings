"""
ETF Holdings Library

A Python library for extracting ETF holdings data from SEC N-PORT filings.
Supports major ETF families including Vanguard, SPDR, Global X, VanEck, and more.
"""

from .etf_holdings import (
    ETFHoldingsExtractor,
    get_etf_holdings,
    get_multiple_etf_holdings,
)

__version__ = "1.0.0"
__all__ = ["ETFHoldingsExtractor", "get_etf_holdings", "get_multiple_etf_holdings"]
