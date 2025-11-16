#!/usr/bin/env python3
"""
Country Data Enricher

Enriches ETF holdings with country/geographic information using yfinance API.
Includes disk-based caching to minimize API calls and respect rate limits.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from country_normalizer import normalize_holdings

logger = logging.getLogger(__name__)


class CountryCache:
    """
    Persistent cache for ticker-to-country mappings.
    """

    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_days: int = 90):
        """
        Initialize country data cache.

        Args:
            cache_dir: Directory for cache files (default: ~/.etf_holdings_cache/countries)
            cache_ttl_days: Cache time-to-live in days (default: 90, country data is stable)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".etf_holdings_cache" / "countries"

        self.cache_ttl_days = cache_ttl_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "ticker_country_mapping.json"

        # Load existing cache
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} entries from country cache")
                    return data
            except Exception as e:
                logger.warning(f"Error loading country cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache_data, f, indent=2)
            logger.debug(f"Saved {len(self.cache_data)} entries to country cache")
        except Exception as e:
            logger.error(f"Error saving country cache: {e}")

    def get(self, ticker: str) -> Optional[str]:
        """
        Get cached country for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Country code/name if cached and valid, None otherwise
        """
        if not ticker:
            return None

        ticker_upper = ticker.upper()
        entry = self.cache_data.get(ticker_upper)

        if not entry:
            return None

        # Check if cache entry is still valid
        try:
            cached_time = datetime.fromisoformat(entry["cached_at"])
            expiry_time = cached_time + timedelta(days=self.cache_ttl_days)

            if datetime.now() > expiry_time:
                logger.debug(f"Cache expired for {ticker_upper}")
                return None

            return entry["country"]
        except Exception as e:
            logger.debug(f"Error checking cache for {ticker_upper}: {e}")
            return None

    def set(self, ticker: str, country: str):
        """
        Store ticker-to-country mapping in cache.

        Args:
            ticker: Stock ticker symbol
            country: Country code/name
        """
        if not ticker:
            return

        ticker_upper = ticker.upper()
        self.cache_data[ticker_upper] = {
            "country": country,
            "cached_at": datetime.now().isoformat(),
        }
        self._save_cache()

    def clear(self):
        """Clear all cached country data."""
        self.cache_data = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cleared country cache")

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cache_dir": str(self.cache_dir),
            "cache_file": str(self.cache_file),
            "ttl_days": self.cache_ttl_days,
            "total_entries": len(self.cache_data),
            "cache_size_kb": (
                self.cache_file.stat().st_size / 1024 if self.cache_file.exists() else 0
            ),
        }


class CountryEnricher:
    """
    Enriches holdings data with country information using external APIs.
    """

    def __init__(
        self,
        enable_cache: bool = True,
        cache_dir: Optional[str] = None,
        cache_ttl_days: int = 90,
    ):
        """
        Initialize the country enricher.

        Args:
            enable_cache: Enable disk-based caching (default: True)
            cache_dir: Custom cache directory
            cache_ttl_days: Cache time-to-live in days (default: 90)
        """
        self.enable_cache = enable_cache

        if self.enable_cache:
            self.cache = CountryCache(
                cache_dir=cache_dir, cache_ttl_days=cache_ttl_days
            )
            logger.info(f"Country cache enabled (TTL: {cache_ttl_days} days)")
        else:
            self.cache = None
            logger.info("Country cache disabled")

    def _get_country_from_yfinance(self, ticker: str) -> str:
        """
        Fetch country information from yfinance API.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Country code/name or empty string if not available
        """
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info

            # Try different country fields
            country = (
                info.get("country")
                or info.get("countryOfIncorporation")
                or info.get("headquarters")
                or ""
            )

            return str(country).strip() if country else ""

        except ImportError:
            logger.error("yfinance not installed. Install with: pip install yfinance")
            return ""
        except Exception as e:
            logger.debug(f"Error fetching country for {ticker}: {e}")
            return ""

    def get_country(self, ticker: str, use_cache: bool = True) -> str:
        """
        Get country for a ticker, using cache if available.

        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data (default: True)

        Returns:
            Country code/name or empty string
        """
        if not ticker:
            return ""

        ticker_upper = ticker.upper()

        # Try cache first
        if use_cache and self.enable_cache and self.cache:
            cached_country = self.cache.get(ticker_upper)
            if cached_country is not None:
                logger.debug(f"Cache hit for {ticker_upper}: {cached_country}")
                return cached_country

        # Fetch from API
        logger.debug(f"Fetching country for {ticker_upper} from yfinance...")
        country = self._get_country_from_yfinance(ticker_upper)

        # Store in cache (even empty results to avoid repeated API calls)
        if self.enable_cache and self.cache:
            self.cache.set(ticker_upper, country)

        return country

    def enrich_holdings(
        self,
        holdings: List[Dict],
        force_refresh: bool = False,
        verbose: bool = False,
    ) -> List[Dict]:
        """
        Enrich holdings list with country information.

        Args:
            holdings: List of holding dictionaries
            force_refresh: Force API call even if data exists in cache
            verbose: Print progress information

        Returns:
            Holdings list with country field populated
        """
        if not holdings:
            return []

        enriched_holdings = []
        cache_hits = 0
        api_calls = 0

        for i, holding in enumerate(holdings, 1):
            # Skip if country already populated
            country = holding.get("country", "").strip()
            country_of_risk = holding.get("country_of_risk", "").strip()

            # Use country_of_risk as fallback if country is empty
            if country_of_risk and not country:
                holding["country"] = country_of_risk
                enriched_holdings.append(holding)
                continue

            if country and not force_refresh:
                enriched_holdings.append(holding)
                continue

            # Get ticker from various possible fields
            ticker = (
                holding.get("security_ticker")
                or holding.get("ticker")
                or holding.get("symbol")
                or ""
            ).strip()

            if not ticker:
                # Try to extract from title (e.g., "NVIDIA CORP (NVDA)")
                title = holding.get("title", "")
                if "(" in title and ")" in title:
                    ticker = title[title.rfind("(") + 1 : title.rfind(")")].strip()

            if ticker:
                # Check cache first if not forcing refresh
                use_cache = not force_refresh
                if use_cache and self.enable_cache and self.cache:
                    country = self.cache.get(ticker)
                    if country is not None:
                        cache_hits += 1
                    else:
                        country = self.get_country(ticker, use_cache=False)
                        api_calls += 1
                else:
                    country = self.get_country(ticker, use_cache=use_cache)
                    api_calls += 1

                holding["country"] = country

                if verbose and i % 50 == 0:
                    logger.info(
                        f"Enriched {i}/{len(holdings)} holdings "
                        f"(cache hits: {cache_hits}, API calls: {api_calls})"
                    )

            enriched_holdings.append(holding)

        if verbose:
            logger.info(
                f"✅ Enrichment complete: {len(enriched_holdings)} holdings "
                f"(cache hits: {cache_hits}, API calls: {api_calls})"
            )

        # Normalize country data to ensure consistency
        enriched_holdings = normalize_holdings(enriched_holdings, field="country")

        if verbose:
            logger.info("✅ Country data normalized to ISO codes")

        return enriched_holdings

    def clear_cache(self):
        """Clear the country cache."""
        if self.enable_cache and self.cache:
            self.cache.clear()
        else:
            logger.info("Cache is disabled")

    def get_cache_stats(self) -> Optional[Dict]:
        """Get cache statistics."""
        if self.enable_cache and self.cache:
            return self.cache.get_stats()
        return None


# Convenience function
def enrich_holdings_with_country(
    holdings: List[Dict],
    enable_cache: bool = True,
    cache_dir: Optional[str] = None,
    verbose: bool = False,
) -> List[Dict]:
    """
    Convenience function to enrich holdings with country data.

    Args:
        holdings: List of holding dictionaries
        enable_cache: Enable caching (default: True)
        cache_dir: Custom cache directory
        verbose: Print progress information

    Returns:
        Holdings list with country field populated
    """
    enricher = CountryEnricher(enable_cache=enable_cache, cache_dir=cache_dir)
    return enricher.enrich_holdings(holdings, verbose=verbose)


if __name__ == "__main__":
    # Test the country enricher
    print("Testing Country Enricher...")

    # Test with sample holdings
    sample_holdings = [
        {"security_ticker": "AAPL", "issuer": "Apple Inc"},
        {"security_ticker": "MSFT", "issuer": "Microsoft Corp"},
        {"security_ticker": "NVDA", "issuer": "NVIDIA Corp"},
    ]

    enricher = CountryEnricher(enable_cache=True)

    print("\nEnriching sample holdings...")
    enriched = enricher.enrich_holdings(sample_holdings, verbose=True)

    print("\nResults:")
    for holding in enriched:
        print(f"  {holding['security_ticker']}: {holding.get('country', 'N/A')}")

    # Show cache stats
    stats = enricher.get_cache_stats()
    if stats:
        print(f"\nCache stats: {stats['total_entries']} entries cached")

    print("\n✅ Country enricher test complete!")
