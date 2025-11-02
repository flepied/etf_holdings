# -*- coding: utf-8 -*-
"""
ETF Holdings Extractor Library

Extract US ETF holdings via SEC (EDGAR) from tickers.
- Inputs: List of ETF tickers or individual ticker
- Outputs: Holdings data with issuer, title, CUSIP, ISIN, balance, value, weight
"""

import time
import requests
from lxml import etree
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SEC endpoints
BASE = "https://data.sec.gov"
BASE_ARCHIVES = "https://www.sec.gov"
USER_AGENT = {"User-Agent": "etf-holdings-lib/1.0 (contact: holdings@example.com)"}
REQUEST_DELAY = 0.2  # SEC rate limiting


class ETFHoldingsExtractor:
    """
    Main class for extracting ETF holdings from SEC N-PORT filings.
    """

    # Known ETF CIK mappings - expandable
    KNOWN_ETF_CIKS = {
        # SPDR Series Trust ETFs
        "RSP": ("0001064642", None, None),  # SPDR S&P 500 Equal Weight ETF
        # Global X Funds ETFs
        "AIQ": ("0001432353", None, None),  # Global X AI & Technology ETF
        # VanEck ETF Trust
        "NLR": ("0001137360", None, None),  # VanEck Uranium+Nuclear Energy ETF
        # First Trust Exchange-Traded Fund
        "FENY": ("0001284940", None, None),  # First Trust Energy Income & Growth Fund
        # Vanguard Index Funds - Each series files separately
        "VTI": ("0000036405", "S000002848", None),  # Vanguard Total Stock Market ETF
        "VONV": ("0000036405", None, None),  # Vanguard Russell 1000 Value ETF
        # Invesco Exchange-Traded Fund Trust
        "XSHQ": ("0001378872", None, None),  # Invesco Scientific and Technology ETF
        # ETF Series Solutions
        "USCA": ("0001540305", None, None),  # Xtrackers MSCI USA ESG Leaders ETF
    }

    def __init__(self, user_agent: Optional[str] = None, delay: float = 0.2):
        """
        Initialize the ETF Holdings Extractor.

        Args:
            user_agent: Custom user agent for SEC requests
            delay: Delay between requests to respect SEC rate limits
        """
        self.delay = delay
        self.headers = {"User-Agent": user_agent or USER_AGENT["User-Agent"]}

    def get_etf_holdings(
        self, ticker: str, max_filings: int = 50, verbose: bool = False
    ) -> Dict:
        """
        Get holdings for a single ETF ticker.

        Args:
            ticker: ETF ticker symbol (e.g., 'VTI', 'RSP')
            max_filings: Maximum number of filings to check
            verbose: Print detailed progress information

        Returns:
            Dict with keys: 'ticker', 'rows', 'note'
            - rows: List of holdings dictionaries
            - note: Status message
        """
        return self._fetch_and_parse_holdings_for_ticker(ticker, verbose, max_filings)

    def get_multiple_etf_holdings(
        self, tickers: List[str], max_filings: int = 50, verbose: bool = False
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
        all_results = {}
        all_rows = []

        for ticker in tickers:
            if verbose:
                logger.info(f"Processing {ticker}...")

            result = self.get_etf_holdings(ticker, max_filings, verbose)
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

    def _resolve_cik_series_from_ticker(
        self, ticker: str, verbose: bool = False
    ) -> Optional[Dict]:
        """Resolve CIK and series information for a ticker."""
        # Check manual mapping first
        if ticker in self.KNOWN_ETF_CIKS:
            cik, series_id, class_id = self.KNOWN_ETF_CIKS[ticker]
            if verbose:
                logger.info(
                    f"Found {ticker} in manual mapping: CIK {cik}, Series {series_id}"
                )

            # Get trust name
            try:
                sub = self._get_submissions(cik)
                name = sub.get("name", "Unknown ETF")
            except Exception:
                name = f"ETF {ticker}"

            return {
                "cik": cik,
                "trust_name": name,
                "series_id": series_id,
                "series_name": None,
                "class_id": class_id,
                "ticker": ticker,
            }

        # Could add more discovery logic here for unknown tickers
        return None

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

        # Sort from most recent to oldest
        out.sort(key=lambda x: x["filingDate"], reverse=True)
        return out

    def _fetch_filing_docs(self, cik: str, accession: str) -> tuple:
        """Fetch filing documents list from SEC."""
        fund_cik = int(cik)
        base = f"{BASE_ARCHIVES}/Archives/edgar/data/{fund_cik}/{accession}"

        # Fetch document index
        idx_url = f"{base}/index.json"
        r = requests.get(idx_url, headers=self.headers, timeout=30)
        r.raise_for_status()
        time.sleep(self.delay)

        idx = r.json()
        files = idx.get("directory", {}).get("item", [])
        return base, files

    def _find_nport_doc(self, files: List[Dict]) -> Optional[str]:
        """Find the N-PORT XML document in filing files."""
        # Look for primary_doc.xml first
        for f in files:
            name = f.get("name", "")
            if name.lower() == "primary_doc.xml":
                return name

        # Then look for files with "nport" in the name
        for f in files:
            name = f.get("name", "").lower()
            if name.endswith(".xml") and "nport" in name:
                return f.get("name")

        # Fallback: any .xml file
        for f in files:
            name = f.get("name", "").lower()
            if name.endswith(".xml"):
                return f.get("name")

        return None

    def _parse_nport_xml(
        self, content: bytes, ticker: Optional[str] = None
    ) -> List[Dict]:
        """Parse N-PORT XML and extract positions."""
        try:
            root = etree.fromstring(content)

            # Define namespaces
            ns = {
                "edgar": "http://www.sec.gov/edgar/nport",
                "com": "http://www.sec.gov/edgar/common",
                "ncom": "http://www.sec.gov/edgar/nportcommon",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            }

            # Update with document namespaces
            for prefix, uri in root.nsmap.items():
                if prefix is not None:
                    ns[prefix] = uri

            # Try various XPath patterns for investment positions
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
                        # Helper function to extract text from various possible tag names
                        def get_text(*tag_names):
                            for tag in tag_names:
                                # Try with and without namespaces
                                for ns_prefix in ["edgar:", "ncom:", ""]:
                                    xpath = f".//{ns_prefix}{tag}/text()"
                                    result = sec.xpath(xpath, namespaces=ns)
                                    if result:
                                        return result[0].strip()
                            return ""

                        # Extract position data
                        issuer = get_text("issuer", "issuerName", "name")
                        title = get_text("title", "description", "securityTitle")
                        cusip = get_text("cusip", "cusipNum")
                        isin = get_text("isin", "isinNum")
                        balance = get_text("balance", "shares", "amount", "qty")
                        value = get_text("valUSD", "value", "fairValue", "marketValue")
                        pct = get_text("pctVal", "percentOfPortfolio", "weight")

                        if issuer or title or cusip:  # Only add if we got some data
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

                    if rows:  # If we found positions, stop trying other patterns
                        break

                except Exception as e:
                    logger.debug(f"Error with path {path}: {e}")
                    continue

            return rows

        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return []

    def _find_ticker_in_nport_preview(
        self, content: bytes, ticker: str, series_id: Optional[str] = None
    ) -> bool:
        """Quick check if ticker appears in N-PORT XML."""
        try:
            # Convert to string for searching
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="ignore")[:100000]  # First 100KB
            else:
                text = str(content)[:100000]

            # If we have a series ID, check for exact match first
            if series_id:
                series_patterns = [
                    f"<seriesId>{series_id}</seriesId>",
                    f'seriesId="{series_id}"',
                    f">{series_id}<",
                ]
                if any(pattern in text for pattern in series_patterns):
                    return True

            # Search patterns
            patterns = [
                f"<ticker>{ticker}</ticker>",
                f'ticker="{ticker}"',
                f">{ticker}<",
                f" {ticker} ",
            ]

            # Special handling for specific ETFs
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

            found = any(pattern.lower() in text.lower() for pattern in patterns)
            return found
        except Exception:
            return False

    def _fetch_and_parse_holdings_for_ticker(
        self, ticker: str, verbose: bool = False, max_filings: int = 50
    ) -> Dict:
        """Fetch and parse holdings for a specific ticker."""
        info = self._resolve_cik_series_from_ticker(ticker, verbose=verbose)
        if not info:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "CIK/series not found via known trusts.",
            }

        if verbose:
            logger.info(
                f"Fetching N-PORT filings for {ticker} from {info['trust_name']}..."
            )

        filings = self._list_recent_filings_for_cik(info["cik"])

        if not filings:
            return {
                "ticker": ticker,
                "rows": [],
                "note": "No N-PORT filings found for this CIK.",
            }

        if verbose:
            logger.info(f"Found {len(filings)} total N-PORT filings")
            logger.info(
                f"Checking up to {min(max_filings, len(filings))} recent filings..."
            )

        # Limit search to recent filings
        filings_to_check = filings[:max_filings]

        for idx, f in enumerate(filings_to_check, 1):
            try:
                if verbose and idx % 10 == 0:
                    logger.info(f"Checked {idx}/{len(filings_to_check)} filings...")

                base, files = self._fetch_filing_docs(info["cik"], f["accession"])
                docname = self._find_nport_doc(files)
                if not docname:
                    continue

                url = f"{base}/{docname}"
                r = requests.get(url, headers=self.headers, timeout=60)
                r.raise_for_status()
                time.sleep(self.delay)
                content = r.content

                # Quick pre-check: does this filing mention our ticker or series ID?
                ticker_found = self._find_ticker_in_nport_preview(
                    content, ticker, info.get("series_id")
                )

                if verbose:
                    logger.debug(f"Ticker/Series check result: {ticker_found}")

                # If we have a series ID, only parse files with that series
                if info.get("series_id") and not ticker_found:
                    continue

                # For Vanguard ETFs without series ID, search more aggressively
                if not info.get("series_id") and not ticker_found:
                    if ticker in ["VTI", "VONV"]:
                        if idx > 20:  # Search more filings for Vanguard
                            continue
                    else:
                        if idx > 5:  # Only try first 5 filings for general search
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
                        "note": f"OK via {f['form']} {f['filingDate']} (checked {idx} filings)",
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


# Convenience functions for direct usage
def get_etf_holdings(ticker: str, max_filings: int = 50, verbose: bool = False) -> Dict:
    """
    Get holdings for a single ETF ticker.

    Args:
        ticker: ETF ticker symbol (e.g., 'VTI', 'RSP')
        max_filings: Maximum number of filings to check
        verbose: Print detailed progress information

    Returns:
        Dict with keys: 'ticker', 'rows', 'note'
    """
    extractor = ETFHoldingsExtractor()
    return extractor.get_etf_holdings(ticker, max_filings, verbose)


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
    return extractor.get_multiple_etf_holdings(tickers, max_filings, verbose)
