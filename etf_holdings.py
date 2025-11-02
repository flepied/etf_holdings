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

    def __init__(
        self,
        user_agent: Optional[str] = None,
        delay: float = 0.2,
        enable_auto_discovery: bool = True,
    ):
        """
        Initialize the ETF Holdings Extractor.

        Args:
            user_agent: Custom user agent for SEC requests
            delay: Delay between requests to respect SEC rate limits
            enable_auto_discovery: Enable automatic ticker-to-CIK discovery
        """
        self.delay = delay
        self.headers = {"User-Agent": user_agent or USER_AGENT["User-Agent"]}
        self.enable_auto_discovery = enable_auto_discovery

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
        # Try known mappings first (faster and more reliable)
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
