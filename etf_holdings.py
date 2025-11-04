#!/usr/bin/env python3
"""
ETF Holdings Extractor Library

Extract US ETF holdings via SEC (EDGAR) from tickers using automatic discovery.
- Inputs: List of ETF tickers or individual ticker
- Outputs: Holdings data with issuer, title, CUSIP, ISIN, balance, value, weight
- Features: Automatic ticker-to-CIK discovery and known mappings fallback
"""

import time
import tempfile
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import requests
from lxml import etree
from sec_edgar_downloader import Downloader
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SEC endpoints
BASE = "https://data.sec.gov"
BASE_ARCHIVES = "https://www.sec.gov"
USER_AGENT = {"User-Agent": "etf-holdings-lib/2.0 (contact@example.com)"}
REQUEST_DELAY = 0.2


class ETFHoldingsCache:
    """
    Disk-based cache for ETF holdings data with automatic expiration.
    """

    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_days: int = 3):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache files (default: ~/.etf_holdings_cache)
            cache_ttl_days: Cache time-to-live in days (default: 3, 0=disable caching)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".etf_holdings_cache"

        self.cache_ttl_days = cache_ttl_days
        self.cache_dir.mkdir(exist_ok=True)

        # Create cache info file if it doesn't exist
        self.info_file = self.cache_dir / "cache_info.json"
        if not self.info_file.exists():
            self._write_cache_info({})

    def _get_cache_filename(self, ticker: str, max_filings: int) -> str:
        """Generate a human-readable cache filename."""
        # Include max_filings to handle different search depths
        return f"{ticker.upper()}_{max_filings}.json"

    def _get_cache_file(self, ticker: str, max_filings: int) -> Path:
        """Get the cache file path for a given ticker and max_filings."""
        filename = self._get_cache_filename(ticker, max_filings)
        return self.cache_dir / filename

    def _write_cache_info(self, info: Dict):
        """Write cache metadata."""
        with open(self.info_file, "w") as f:
            json.dump(info, f, indent=2)

    def _read_cache_info(self) -> Dict:
        """Read cache metadata."""
        try:
            with open(self.info_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def is_cache_valid(self, ticker: str, max_filings: int) -> bool:
        """Check if cached data exists and is still valid."""
        # If TTL is 0, disable caching completely
        if self.cache_ttl_days <= 0:
            return False

        cache_file = self._get_cache_file(ticker, max_filings)

        if not cache_file.exists():
            return False

        try:
            # Check file modification time
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            expiry_time = file_time + timedelta(days=self.cache_ttl_days)

            if datetime.now() > expiry_time:
                logger.debug(f"Cache expired for {ticker} (cached: {file_time})")
                return False

            return True
        except Exception as e:
            logger.debug(f"Error checking cache validity for {ticker}: {e}")
            return False

    def get_cached_data(self, ticker: str, max_filings: int) -> Optional[Dict]:
        """Retrieve cached holdings data if valid."""
        if not self.is_cache_valid(ticker, max_filings):
            return None

        cache_file = self._get_cache_file(ticker, max_filings)

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)

            logger.info(
                f"📁 Using cached data for {ticker} ({len(data.get('rows', []))} holdings)"
            )
            return data
        except Exception as e:
            logger.error(f"Error reading cache for {ticker}: {e}")
            return None

    def store_data(self, ticker: str, max_filings: int, data: Dict):
        """Store holdings data in cache."""
        # If TTL is 0, don't store anything
        if self.cache_ttl_days <= 0:
            logger.debug(f"Caching disabled (TTL=0), not storing {ticker}")
            return

        cache_file = self._get_cache_file(ticker, max_filings)

        try:
            # Add cache metadata
            cached_data = {
                **data,
                "_cache_info": {
                    "ticker": ticker,
                    "max_filings": max_filings,
                    "cached_at": datetime.now().isoformat(),
                    "filename": self._get_cache_filename(ticker, max_filings),
                },
            }

            with open(cache_file, "w") as f:
                json.dump(cached_data, f, indent=2)

            # Update cache info
            info = self._read_cache_info()
            info[ticker] = {
                "filename": self._get_cache_filename(ticker, max_filings),
                "cached_at": datetime.now().isoformat(),
                "max_filings": max_filings,
                "holdings_count": len(data.get("rows", [])),
            }
            self._write_cache_info(info)

            logger.info(
                f"💾 Cached {ticker} data ({len(data.get('rows', []))} holdings)"
            )
        except Exception as e:
            logger.error(f"Error storing cache for {ticker}: {e}")

    def clear_cache(self, ticker: Optional[str] = None):
        """Clear cache for specific ticker or all cache."""
        if ticker:
            # Clear specific ticker - need to find all files for this ticker
            info = self._read_cache_info()
            ticker_upper = ticker.upper()

            # Find all cache files for this ticker (different max_filings)
            cleared_files = []
            for cache_ticker, cache_info in list(info.items()):
                if cache_ticker == ticker_upper:
                    filename = cache_info["filename"]
                    cache_file = self.cache_dir / filename
                    if cache_file.exists():
                        cache_file.unlink()
                        cleared_files.append(filename)
                    del info[cache_ticker]

            # Also check for any orphaned files matching the ticker pattern
            pattern = f"{ticker_upper}_*.json"
            for cache_file in self.cache_dir.glob(pattern):
                if cache_file.name != "cache_info.json":
                    cache_file.unlink()
                    if cache_file.name not in cleared_files:
                        cleared_files.append(cache_file.name)

            if cleared_files:
                self._write_cache_info(info)
                logger.info(
                    f"🗑️  Cleared {len(cleared_files)} cache file(s) for {ticker}: {', '.join(cleared_files)}"
                )
            else:
                logger.info(f"No cache found for {ticker}")
        else:
            # Clear all cache
            import shutil

            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                self._write_cache_info({})
                logger.info("🗑️  Cleared all cache")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        info = self._read_cache_info()

        total_files = len(list(self.cache_dir.glob("*.json"))) - 1  # Exclude info file
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))

        stats = {
            "cache_dir": str(self.cache_dir),
            "ttl_days": self.cache_ttl_days,
            "total_cached_etfs": len(info),
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cached_etfs": info,
        }

        return stats

    def cleanup_expired(self):
        """Remove expired cache entries."""
        info = self._read_cache_info()
        expired_tickers = []

        for ticker, ticker_info in info.items():
            if not self.is_cache_valid(ticker, ticker_info["max_filings"]):
                filename = ticker_info["filename"]
                cache_file = self.cache_dir / filename
                if cache_file.exists():
                    cache_file.unlink()
                expired_tickers.append(ticker)

        # Update info file
        for ticker in expired_tickers:
            del info[ticker]
        self._write_cache_info(info)

        if expired_tickers:
            logger.info(f"🧹 Cleaned up {len(expired_tickers)} expired cache entries")

        return len(expired_tickers)


class ETFHoldingsExtractor:
    """
    ETF Holdings Extractor with automatic ticker discovery.

    Combines manual CIK mappings with automatic discovery via sec-edgar-downloader.
    """

    # Known working ETF CIK mappings
    KNOWN_ETF_CIKS = {
        # SPDR Series Trust ETFs
        "RSP": ("0001064642", None, None),
        # Global X Funds ETFs
        "AIQ": ("0001432353", None, None),
        # VanEck ETF Trust
        "NLR": ("0001137360", None, None),
        # First Trust Exchange-Traded Fund
        "FENY": ("0001284940", None, None),
        # Vanguard Index Funds
        "VTI": ("0000036405", "S000002848", None),
        "VONV": ("0000036405", None, None),
        # Invesco Exchange-Traded Fund Trust
        "XSHQ": ("0001378872", None, None),
        # ETF Series Solutions
        "USCA": ("0001540305", None, None),
        # Newly discovered via sec-edgar-downloader
        "QQQ": ("0001067839", None, None),  # Invesco QQQ Trust
        "SPY": ("0000884394", None, None),  # SPDR S&P 500 ETF Trust
    }

    # iShares ETFs - Use CSV data source instead of SEC filings
    ISHARES_ETF_MAPPINGS = {
        "URTH": "239696",  # iShares MSCI World ETF
        "IVV": "239726",  # iShares Core S&P 500 ETF
        "EFA": "239623",  # iShares MSCI EAFE ETF
        "IEMG": "244048",  # iShares Core MSCI Emerging Markets IMI Index ETF
        "ACWI": "239600",  # iShares MSCI ACWI ETF
        "AGG": "239458",  # iShares Core US Aggregate Bond ETF
        "IJH": "239763",  # iShares Core S&P Mid-Cap ETF
        "IJR": "239774",  # iShares Core S&P Small-Cap ETF
        "IEFA": "251622",  # iShares Core MSCI EAFE IMI Index ETF
        "ITOT": "239724",  # iShares Core S&P Total US Stock Market ETF
    }

    # Amundi UCITS ETFs - Use Amundi product API (composition tab)
    AMUNDI_ETF_MAPPINGS = {
        "CG1": {
            "product_id": "FR0010655712",  # Amundi ETF DAX UCITS ETF DR
            "base_url": "https://www.amundietf.fr",
            "context": {
                "countryCode": "FRA",
                "languageCode": "fr",
                "userProfileName": "INSTIT",
            },
        },
        "CS1": {
            "product_id": "FR0010655746",  # Amundi IBEX 35 UCITS ETF ACC
            "base_url": "https://www.amundietf.fr",
            "context": {
                "countryCode": "FRA",
                "languageCode": "fr",
                "userProfileName": "INSTIT",
            },
        },
        "FMI": {
            "product_id": "LU1681037518",  # Amundi Italy MIB ESG UCITS ETF
            "base_url": "https://www.amundietf.fr",
            "context": {
                "countryCode": "FRA",
                "languageCode": "fr",
                "userProfileName": "INSTIT",
            },
        },
    }

    def __init__(
        self,
        user_agent: Optional[str] = None,
        delay: float = 0.2,
        enable_auto_discovery: bool = True,
        enable_cache: bool = True,
        cache_dir: Optional[str] = None,
        cache_ttl_days: int = 3,
    ):
        """
        Initialize the ETF Holdings Extractor.

        Args:
            user_agent: Custom user agent for SEC requests
            delay: Delay between requests to respect SEC rate limits
            enable_auto_discovery: Enable automatic ticker-to-CIK discovery
            enable_cache: Enable disk-based caching (default: True)
            cache_dir: Custom cache directory (default: ~/.etf_holdings_cache)
            cache_ttl_days: Cache time-to-live in days (default: 3, 0=disable caching)
        """
        self.delay = delay
        self.headers = {"User-Agent": user_agent or USER_AGENT["User-Agent"]}
        self.enable_auto_discovery = enable_auto_discovery
        self.enable_cache = enable_cache

        # Initialize caching
        if self.enable_cache:
            self.cache = ETFHoldingsCache(
                cache_dir=cache_dir, cache_ttl_days=cache_ttl_days
            )
            if cache_ttl_days <= 0:
                logger.info("📁 Cache system initialized but disabled (TTL=0)")
            else:
                logger.info(f"📁 Cache enabled (TTL: {cache_ttl_days} days)")
        else:
            self.cache = None
            logger.info("Cache disabled")

        # Initialize auto-discovery components
        if self.enable_auto_discovery:
            self.temp_folder = tempfile.mkdtemp(prefix="etf_holdings_")
            self.downloader = Downloader(
                company_name="ETF Holdings Library",
                email_address="contact@example.com",
                download_folder=self.temp_folder,
            )
            logger.info("Auto-discovery enabled")
        else:
            self.downloader = None
            logger.info("Auto-discovery disabled")

    def get_etf_holdings(
        self, ticker: str, max_filings: int = 50, verbose: bool = False
    ) -> Dict:
        """
        Get holdings for a single ETF ticker with automatic discovery fallback.

        Args:
            ticker: ETF ticker symbol
            max_filings: Maximum number of filings to check
            verbose: Print detailed progress information

        Returns:
            Dict with keys: 'ticker', 'rows', 'note'
        """
        ticker = ticker.upper()

        # Check cache first
        if self.enable_cache and self.cache:
            cached_data = self.cache.get_cached_data(ticker, max_filings)
            if cached_data:
                # Remove cache metadata before returning
                result = {k: v for k, v in cached_data.items() if k != "_cache_info"}
                return result

        # Cache miss - fetch fresh data
        result = self._fetch_fresh_data(ticker, max_filings, verbose)

        # Store in cache if enabled and we got data
        if self.enable_cache and self.cache and result.get("rows"):
            self.cache.store_data(ticker, max_filings, result)

        return result

    def _fetch_fresh_data(self, ticker: str, max_filings: int, verbose: bool) -> Dict:
        """Fetch fresh data from SEC (not cached)."""
        # Try iShares CSV first
        if ticker in self.ISHARES_ETF_MAPPINGS:
            if verbose:
                logger.info(f"Using iShares CSV extraction for {ticker}")
            return self._extract_via_ishares_csv(ticker, verbose)

        # Try Amundi API for European UCITS ETFs
        if ticker in self.AMUNDI_ETF_MAPPINGS:
            if verbose:
                logger.info(f"Using Amundi API extraction for {ticker}")
            return self._extract_via_amundi_api(ticker, verbose)

        # Try known mappings second (faster and more reliable)
        if ticker in self.KNOWN_ETF_CIKS:
            if verbose:
                logger.info(f"Using known mapping for {ticker}")
            return self._extract_via_known_mapping(ticker, max_filings, verbose)

        # Fallback to auto-discovery
        if self.enable_auto_discovery:
            if verbose:
                logger.info(f"Attempting auto-discovery for {ticker}")
            return self._extract_via_auto_discovery(ticker, max_filings, verbose)

        # No mapping found and auto-discovery disabled
        return {
            "ticker": ticker,
            "rows": [],
            "note": "CIK/series not found via known trusts (auto-discovery disabled).",
        }

    def _extract_via_known_mapping(
        self, ticker: str, max_filings: int, verbose: bool
    ) -> Dict:
        """Extract holdings using known CIK mappings (original method)."""
        cik, series_id, class_id = self.KNOWN_ETF_CIKS[ticker]

        if verbose:
            logger.info(f"Fetching N-PORT filings for {ticker} from known CIK {cik}...")

        filings = self._list_recent_filings_for_cik(cik)

        if not filings:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "No N-PORT filings found for this CIK.",
            }

        if verbose:
            logger.info(f"Found {len(filings)} total N-PORT filings")

        # Limit search to recent filings
        filings_to_check = filings[:max_filings]

        for idx, f in enumerate(filings_to_check, 1):
            try:
                if verbose and idx % 10 == 0:
                    logger.info(f"Checked {idx}/{len(filings_to_check)} filings...")

                base, files = self._fetch_filing_docs(cik, f["accession"])
                docname = self._find_nport_doc(files)
                if not docname:
                    continue

                url = f"{base}/{docname}"
                r = requests.get(url, headers=self.headers, timeout=60)
                r.raise_for_status()
                time.sleep(self.delay)
                content = r.content

                # Quick pre-check for series ID if needed
                if series_id and not self._find_ticker_in_content(
                    content, ticker, series_id
                ):
                    continue

                if verbose:
                    logger.info(
                        f"✓ Found {ticker} in filing {f['filingDate']} - parsing..."
                    )

                # Parse the full document
                rows = self._parse_nport_xml(content, ticker=ticker)

                if rows:
                    return {
                        "ticker": ticker,
                        "rows": rows,
                        "note": f"OK via {f['form']} {f['filingDate']} (known mapping)",
                    }

            except Exception as e:
                if verbose:
                    logger.error(f"Error on filing {f['filingDate']}: {str(e)[:100]}")
                continue

        return {
            "ticker": ticker,
            "rows": [],
            "note": f"No holdings found after checking {len(filings_to_check)} filings.",
        }

    def _extract_via_auto_discovery(
        self, ticker: str, max_filings: int, verbose: bool
    ) -> Dict:
        """Extract holdings using automatic CIK discovery."""
        # Check if ticker exists in sec-edgar-downloader mapping
        if ticker not in self.downloader.ticker_to_cik_mapping:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "Ticker not found in automatic discovery database.",
            }

        cik = self.downloader.ticker_to_cik_mapping[ticker]

        if verbose:
            logger.info(f"Auto-discovered CIK {cik} for {ticker}")

        try:
            # Download NPORT filings
            num_downloaded = self.downloader.get(
                form="NPORT-P",
                ticker_or_cik=cik,
                limit=min(max_filings, 10),  # Limit auto-discovery downloads
                include_amends=False,
            )

            if verbose:
                logger.info(f"Downloaded {num_downloaded} N-PORT filings for {ticker}")

            if num_downloaded == 0:
                return {
                    "ticker": ticker,
                    "rows": [],
                    "note": "No NPORT-P filings found via auto-discovery.",
                }

            # Parse downloaded filings
            return self._parse_auto_discovered_filings(ticker, cik, verbose)

        except Exception as e:
            logger.error(f"Auto-discovery error for {ticker}: {e}")
            return {
                "ticker": ticker,
                "rows": [],
                "note": f"Auto-discovery failed: {str(e)[:100]}",
            }

    def _parse_auto_discovered_filings(
        self, ticker: str, cik: str, verbose: bool
    ) -> Dict:
        """Parse filings downloaded via auto-discovery."""
        cik_folder = Path(self.temp_folder) / "sec-edgar-filings" / cik / "NPORT-P"

        if not cik_folder.exists():
            return {
                "ticker": ticker,
                "rows": [],
                "note": "No downloaded filings found.",
            }

        # Get filing directories, sorted by date (newest first)
        filing_dirs = sorted(
            [d for d in cik_folder.iterdir() if d.is_dir()], reverse=True
        )

        for filing_dir in filing_dirs:
            try:
                submission_file = filing_dir / "full-submission.txt"
                if not submission_file.exists():
                    continue

                if verbose:
                    logger.info(f"Parsing auto-discovered file: {submission_file}")

                # Extract XML from submission file
                xml_content = self._extract_xml_from_submission(submission_file)
                if not xml_content:
                    continue

                # Parse holdings
                rows = self._parse_nport_xml(xml_content, ticker=ticker)

                if rows:
                    filing_date = (
                        filing_dir.name.split("-")[0]
                        if "-" in filing_dir.name
                        else "unknown"
                    )
                    return {
                        "ticker": ticker,
                        "rows": rows,
                        "note": f"OK via NPORT-P {filing_date} (auto-discovery)",
                    }

            except Exception as e:
                if verbose:
                    logger.error(f"Error parsing auto-discovered filing: {e}")
                continue

        return {
            "ticker": ticker,
            "rows": [],
            "note": f"No holdings found in {len(filing_dirs)} auto-discovered filings.",
        }

    def _extract_via_ishares_csv(self, ticker: str, verbose: bool) -> Dict:
        """Extract holdings via iShares CSV download."""
        import csv
        import io

        product_id = self.ISHARES_ETF_MAPPINGS[ticker]

        if verbose:
            logger.info(
                f"Downloading iShares CSV for {ticker} (Product ID: {product_id})"
            )

        # Construct iShares CSV URL
        url = f"https://www.ishares.com/us/products/{product_id}/ishares-{ticker.lower()}-etf/1467271812596.ajax?fileType=csv&fileName={ticker}_holdings&dataType=fund"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            time.sleep(self.delay)

            # Parse CSV content
            content = response.text
            if verbose:
                logger.info(f"Downloaded {len(content)} bytes of CSV data")

            return self._parse_ishares_csv(content, ticker, verbose)

        except Exception as e:
            logger.error(f"Error downloading iShares CSV for {ticker}: {e}")
            return {
                "ticker": ticker,
                "rows": [],
                "note": f"Failed to download iShares CSV: {str(e)[:100]}",
            }

    def _parse_ishares_csv(self, content: str, ticker: str, verbose: bool) -> Dict:
        """Parse iShares CSV format and extract holdings."""
        import csv
        import io

        try:
            lines = content.strip().split("\n")

            # Find the header line (contains "Ticker,Name,Sector...")
            header_line_idx = None
            for i, line in enumerate(lines):
                if line.startswith("Ticker,Name,Sector"):
                    header_line_idx = i
                    break

            if header_line_idx is None:
                return {
                    "ticker": ticker,
                    "rows": [],
                    "note": "Could not find CSV header in iShares data",
                }

            # Extract data lines (skip header and any footer)
            data_lines = lines[header_line_idx:]

            # Parse CSV
            reader = csv.DictReader(io.StringIO("\n".join(data_lines)))

            rows = []
            for row in reader:
                # Skip empty rows or cash entries
                ticker_val = row.get("Ticker", "") or ""
                name_val = row.get("Name", "") or ""

                if not ticker_val or ticker_val == "-" or not name_val:
                    continue

                # Clean values safely
                def safe_clean(value, default=""):
                    if value is None:
                        return default
                    return (
                        str(value)
                        .replace(",", "")
                        .replace("$", "")
                        .replace('"', "")
                        .strip()
                    )

                # Convert to our standard format
                holding = {
                    "ticker_fund": ticker,
                    "issuer": safe_clean(name_val),
                    "title": f"{safe_clean(name_val)} ({safe_clean(ticker_val)})",
                    "id_cusip": "",  # iShares doesn't provide CUSIP in CSV
                    "id_isin": "",  # iShares doesn't provide ISIN in CSV
                    "balance": safe_clean(row.get("Quantity", "")),
                    "value_usd": safe_clean(row.get("Market Value", "")),
                    "weight_pct": safe_clean(row.get("Weight (%)", "")),
                }

                # Only add if we have meaningful data
                if holding["issuer"] and holding["issuer"] != "-":
                    rows.append(holding)

            if verbose:
                logger.info(f"Parsed {len(rows)} holdings from iShares CSV")

            return {
                "ticker": ticker,
                "rows": rows,
                "note": f"OK via iShares CSV download ({len(rows)} holdings)",
            }

        except Exception as e:
            logger.error(f"Error parsing iShares CSV for {ticker}: {e}")
            return {
                "ticker": ticker,
                "rows": [],
                "note": f"Error parsing iShares CSV: {str(e)[:100]}",
            }

    def _extract_via_amundi_api(self, ticker: str, verbose: bool) -> Dict:
        """Extract holdings via Amundi UCITS API."""
        mapping = self.AMUNDI_ETF_MAPPINGS[ticker]
        product_id = mapping["product_id"]
        base_url = mapping.get("base_url", "https://www.amundietf.fr").rstrip("/")
        context = mapping.get(
            "context",
            {"countryCode": "FRA", "languageCode": "fr", "userProfileName": "INSTIT"},
        )
        composition_fields = mapping.get(
            "composition_fields",
            [
                "date",
                "type",
                "bbg",
                "isin",
                "name",
                "weight",
                "quantity",
                "currency",
                "sector",
                "country",
                "countryOfRisk",
            ],
        )

        payload = {
            "productIds": [product_id],
            "context": context,
            "composition": {"compositionFields": composition_fields},
        }

        url = f"{base_url}/mapi/ProductAPI/getProductsData"

        try:
            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            time.sleep(self.delay)

            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Amundi data for {ticker}: {e}")
            return {
                "ticker": ticker,
                "rows": [],
                "note": f"Failed to fetch Amundi data: {str(e)[:100]}",
            }
        except ValueError as e:
            logger.error(f"Error parsing Amundi JSON for {ticker}: {e}")
            return {
                "ticker": ticker,
                "rows": [],
                "note": f"Invalid JSON from Amundi API: {str(e)[:100]}",
            }

        products = data.get("products") or []
        if not products:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "No product data returned by Amundi API.",
            }

        product = products[0]
        composition = product.get("composition") or {}
        composition_data = composition.get("compositionData") or []

        if verbose:
            logger.info(
                f"Received {len(composition_data)} holdings from Amundi API for {ticker}"
            )

        if not composition_data:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "No composition data returned by Amundi API.",
            }

        def format_number(value) -> str:
            if value is None:
                return ""
            if isinstance(value, (int,)):
                return str(value)
            if isinstance(value, float):
                if value != value:  # NaN check
                    return ""
                if value.is_integer():
                    return str(int(value))
                return f"{value:.6f}".rstrip("0").rstrip(".")
            return str(value)

        def format_percent(value) -> str:
            if value is None:
                return ""
            try:
                pct = float(value) * 100.0
                return f"{pct:.6f}".rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                return str(value)

        rows = []
        as_of_date = ""

        for entry in composition_data:
            characteristics = entry.get("compositionCharacteristics") or {}
            name = (characteristics.get("name") or "").strip()

            if not name:
                continue

            if not as_of_date:
                as_of_date = (characteristics.get("date") or "").strip()

            weight_val = entry.get("weight")
            if weight_val is None:
                weight_val = characteristics.get("weight")

            bbg_value = (characteristics.get("bbg") or "").strip()
            title = f"{name} ({bbg_value})" if bbg_value else name

            row = {
                "ticker_fund": ticker,
                "issuer": name,
                "title": title,
                "id_cusip": "",
                "id_isin": (characteristics.get("isin") or "").strip(),
                "balance": format_number(characteristics.get("quantity")),
                "value_usd": "",
                "weight_pct": format_percent(weight_val),
                "currency": (characteristics.get("currency") or "").strip(),
                "sector": (characteristics.get("sector") or "").strip(),
                "country": (characteristics.get("country") or "").strip(),
                "country_of_risk": (characteristics.get("countryOfRisk") or "").strip(),
                "security_type": (characteristics.get("type") or "").strip(),
                "bbg": (characteristics.get("bbg") or "").strip(),
                "as_of_date": (characteristics.get("date") or "").strip(),
            }

            rows.append(row)

        note_suffix = f" as of {as_of_date}" if as_of_date else ""
        note = f"OK via Amundi API ({len(rows)} holdings{note_suffix})"

        return {
            "ticker": ticker,
            "rows": rows,
            "note": note,
        }

    # Include all the helper methods from the original implementation
    def _get_submissions(self, cik_str: str) -> Dict:
        """Get SEC submissions data for a CIK."""
        cik_padded = str(cik_str).zfill(10)
        url = f"{BASE}/submissions/CIK{cik_padded}.json"

        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            r.raise_for_status()
            time.sleep(self.delay)
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching submissions for CIK {cik_padded}: {e}")
            return {}

    def _list_recent_filings_for_cik(
        self, cik: str, form_prefix: tuple = ("NPORT-P", "NPORT-EX")
    ) -> List[Dict]:
        """List recent N-PORT filings for a CIK."""
        sub = self._get_submissions(cik)
        recent = sub.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        accession = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])

        out = []
        for f, a, d, fd in zip(forms, accession, filing_dates, primary_docs):
            if any(f.startswith(p) for p in form_prefix):
                out.append(
                    {
                        "form": f,
                        "accession": a.replace("-", ""),
                        "filingDate": d,
                        "primary": fd,
                    }
                )

        out.sort(key=lambda x: x["filingDate"], reverse=True)
        return out

    def _fetch_filing_docs(self, cik: str, accession: str) -> tuple:
        """Fetch filing documents list from SEC."""
        fund_cik = int(cik)
        base = f"{BASE_ARCHIVES}/Archives/edgar/data/{fund_cik}/{accession}"

        idx_url = f"{base}/index.json"
        r = requests.get(idx_url, headers=self.headers, timeout=30)
        r.raise_for_status()
        time.sleep(self.delay)

        idx = r.json()
        files = idx.get("directory", {}).get("item", [])
        return base, files

    def _find_nport_doc(self, files: List[Dict]) -> Optional[str]:
        """Find the N-PORT XML document in filing files."""
        for f in files:
            name = f.get("name", "")
            if name.lower() == "primary_doc.xml":
                return name

        for f in files:
            name = f.get("name", "").lower()
            if name.endswith(".xml") and "nport" in name:
                return f.get("name")

        for f in files:
            name = f.get("name", "").lower()
            if name.endswith(".xml"):
                return f.get("name")

        return None

    def _extract_xml_from_submission(self, submission_file: Path) -> bytes:
        """Extract XML content from SEC full-submission.txt file."""
        with open(submission_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        xml_start = content.find("<?xml")
        xml_end = content.find("</edgarSubmission>")

        if xml_start == -1 or xml_end == -1:
            return b""

        xml_end += len("</edgarSubmission>")
        xml_content = content[xml_start:xml_end]

        return xml_content.encode("utf-8")

    def _find_ticker_in_content(
        self, content: bytes, ticker: str, series_id: Optional[str] = None
    ) -> bool:
        """Quick check if ticker appears in N-PORT XML."""
        try:
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="ignore")[:100000]
            else:
                text = str(content)[:100000]

            if series_id:
                series_patterns = [
                    f"<seriesId>{series_id}</seriesId>",
                    f'seriesId="{series_id}"',
                    f">{series_id}<",
                ]
                if any(pattern in text for pattern in series_patterns):
                    return True

            patterns = [
                f"<ticker>{ticker}</ticker>",
                f'ticker="{ticker}"',
                f">{ticker}<",
                f" {ticker} ",
            ]

            if ticker == "VTI":
                patterns.extend(
                    [
                        "TOTAL STOCK MARKET",
                        "VANGUARD TOTAL STOCK MARKET INDEX",
                    ]
                )
            elif ticker == "VONV":
                patterns.extend(
                    [
                        "RUSSELL 1000 VALUE",
                        "VANGUARD RUSSELL 1000 VALUE INDEX",
                    ]
                )

            return any(pattern.lower() in text.lower() for pattern in patterns)
        except Exception:
            return False

    def _parse_nport_xml(
        self, content: bytes, ticker: Optional[str] = None
    ) -> List[Dict]:
        """Parse N-PORT XML and extract positions."""
        try:
            root = etree.fromstring(content)

            ns = {
                "edgar": "http://www.sec.gov/edgar/nport",
                "com": "http://www.sec.gov/edgar/common",
                "ncom": "http://www.sec.gov/edgar/nportcommon",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            }

            for prefix, uri in root.nsmap.items():
                if prefix is not None:
                    ns[prefix] = uri

            candidates = [
                ".//edgar:invstOrSecs//edgar:invstOrSec",
                ".//invstOrSecs//invstOrSec",
                ".//investmentOrSecs//investmentOrSec",
                ".//invstOrSec",
                ".//investment",
                ".//position",
            ]

            rows = []
            for path in candidates:
                try:
                    positions = root.xpath(path, namespaces=ns)
                    if not positions:
                        continue

                    logger.info(f"Found {len(positions)} positions using path: {path}")

                    for sec in positions:

                        def get_text(*tag_names):
                            for tag in tag_names:
                                for ns_prefix in ["edgar:", "ncom:", ""]:
                                    xpath = f".//{ns_prefix}{tag}/text()"
                                    result = sec.xpath(xpath, namespaces=ns)
                                    if result:
                                        return result[0].strip()
                            return ""

                        issuer = get_text("issuer", "issuerName", "name")
                        title = get_text("title", "description", "securityTitle")
                        cusip = get_text("cusip", "cusipNum")
                        isin = get_text("isin", "isinNum")
                        balance = get_text("balance", "shares", "amount", "qty")
                        value = get_text("valUSD", "value", "fairValue", "marketValue")
                        pct = get_text("pctVal", "percentOfPortfolio", "weight")

                        if issuer or title or cusip:
                            rows.append(
                                {
                                    "ticker_fund": ticker or "",
                                    "issuer": issuer or title,
                                    "title": title,
                                    "id_cusip": cusip,
                                    "id_isin": isin,
                                    "balance": balance,
                                    "value_usd": value,
                                    "weight_pct": pct,
                                }
                            )

                    if rows:
                        break

                except Exception as e:
                    logger.debug(f"Error with path {path}: {e}")
                    continue

            return rows

        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return []

    def discover_new_ticker(self, ticker: str, verbose: bool = False) -> Optional[str]:
        """
        Discover CIK for a new ticker and test if it has NPORT filings.

        Args:
            ticker: Ticker symbol to discover
            verbose: Print detailed information

        Returns:
            CIK if ticker is found and has NPORT filings, None otherwise
        """
        if not self.enable_auto_discovery:
            return None

        if ticker in self.downloader.ticker_to_cik_mapping:
            cik = self.downloader.ticker_to_cik_mapping[ticker]

            if verbose:
                logger.info(f"Testing NPORT availability for {ticker} (CIK: {cik})")

            # Test if it has NPORT filings
            try:
                num_downloaded = self.downloader.get(
                    form="NPORT-P", ticker_or_cik=cik, limit=1, include_amends=False
                )

                if num_downloaded > 0:
                    if verbose:
                        logger.info(f"✅ {ticker} has NPORT filings - CIK: {cik}")
                    return cik
                else:
                    if verbose:
                        logger.info(f"❌ {ticker} has no NPORT filings")
                    return None

            except Exception as e:
                if verbose:
                    logger.error(f"Error testing {ticker}: {e}")
                return None
        else:
            if verbose:
                logger.info(f"❌ {ticker} not found in ticker mapping")
            return None

    def cleanup(self):
        """Clean up temporary files."""
        if hasattr(self, "temp_folder") and Path(self.temp_folder).exists():
            import shutil

            shutil.rmtree(self.temp_folder)
            logger.info(f"Cleaned up temp folder: {self.temp_folder}")

    # Cache management methods
    def clear_cache(self, ticker: Optional[str] = None):
        """Clear cache for specific ticker or all cache."""
        if self.enable_cache and self.cache:
            self.cache.clear_cache(ticker)
        else:
            logger.info("Cache is disabled")

    def get_cache_stats(self) -> Optional[Dict]:
        """Get cache statistics."""
        if self.enable_cache and self.cache:
            return self.cache.get_cache_stats()
        else:
            logger.info("Cache is disabled")
            return None

    def cleanup_expired_cache(self):
        """Clean up expired cache entries."""
        if self.enable_cache and self.cache:
            return self.cache.cleanup_expired()
        else:
            logger.info("Cache is disabled")
            return 0


# Convenience functions for direct usage
def get_etf_holdings(ticker: str, max_filings: int = 50, verbose: bool = False) -> Dict:
    """
    Get holdings for a single ETF ticker.

    Args:
        ticker: ETF ticker symbol (e.g., 'VTI', 'RSP', 'SPY')
        max_filings: Maximum number of filings to check
        verbose: Print detailed progress information

    Returns:
        Dict with keys: 'ticker', 'rows', 'note'
    """
    extractor = ETFHoldingsExtractor()
    try:
        return extractor.get_etf_holdings(ticker, max_filings, verbose)
    finally:
        extractor.cleanup()


def get_multiple_etf_holdings(
    tickers: List[str], max_filings: int = 50, verbose: bool = False
) -> Dict:
    """
    Get holdings for multiple ETF tickers.

    Args:
        tickers: List of ETF ticker symbols
        max_filings: Maximum number of filings to check per ETF
        verbose: Print detailed progress information

    Returns:
        Dict with consolidated results
    """
    extractor = ETFHoldingsExtractor()
    try:
        all_results = {}
        all_rows = []

        for ticker in tickers:
            if verbose:
                logger.info(f"Processing {ticker}...")

            result = extractor.get_etf_holdings(ticker, max_filings, verbose)
            all_results[ticker] = result

            if result["rows"]:
                all_rows.extend(result["rows"])

        return {
            "individual_results": all_results,
            "consolidated_holdings": all_rows,
            "summary": {
                "total_etfs_processed": len(tickers),
                "etfs_with_holdings": sum(1 for r in all_results.values() if r["rows"]),
                "total_positions": len(all_rows),
            },
        }
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    # Test library functionality
    print("Testing ETF Holdings Extractor Library...")

    # Test known ETF
    print("\n1. Testing known ETF (VTI):")
    result = get_etf_holdings("VTI", max_filings=10, verbose=True)
    print(f"   Result: {len(result['rows'])} holdings - {result['note']}")

    # Test auto-discovered ETF
    print("\n2. Testing auto-discovered ETF (SPY):")
    result = get_etf_holdings("SPY", max_filings=5, verbose=True)
    print(f"   Result: {len(result['rows'])} holdings - {result['note']}")

    # Test batch processing
    print("\n3. Testing batch processing:")
    results = get_multiple_etf_holdings(["RSP", "QQQ"], max_filings=5, verbose=True)
    print(f"   Total positions: {results['summary']['total_positions']}")
    print(
        f"   Working ETFs: {results['summary']['etfs_with_holdings']}/{results['summary']['total_etfs_processed']}"
    )

    print("\n✅ ETF Holdings Extractor testing complete!")
