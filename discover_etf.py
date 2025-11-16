#!/usr/bin/env python3
"""
ETF Discovery Tool

Helps discover ETF CIK and filing information for tickers not in the known database.
"""

import argparse
import time

import requests

from etf_holdings import ETFHoldingsExtractor


def search_sec_company_tickers(ticker):
    """Search SEC company tickers database for a ticker."""
    try:
        print(f"🔍 Searching SEC company tickers database for {ticker}...")

        # SEC company tickers endpoint
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "etf-holdings-lib/2.0 (contact@example.com)"}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        time.sleep(0.2)  # Be nice to SEC

        companies = response.json()

        found_companies = []
        for entry in companies.values():
            cik = str(entry["cik_str"]).zfill(10)
            title = entry["title"]
            ticker_in_title = entry.get("ticker", "")

            # Look for ticker in various places
            if (
                ticker.upper() in title.upper()
                or ticker.upper() == ticker_in_title.upper()
                or ticker.upper() in title.upper().split()
            ):
                found_companies.append(
                    {"cik": cik, "title": title, "ticker": ticker_in_title}
                )

        return found_companies

    except Exception as e:
        print(f"❌ Error searching company tickers: {e}")
        return []


def test_cik_for_nport(cik, ticker):
    """Test if a CIK has NPORT filings and try to extract holdings."""
    try:
        print(f"🧪 Testing CIK {cik} for NPORT filings...")

        # Use our extractor with a manual override
        extractor = ETFHoldingsExtractor()

        # Add the ticker to known mappings temporarily
        original_mapping = extractor.KNOWN_ETF_CIKS.copy()
        extractor.KNOWN_ETF_CIKS[ticker.upper()] = (cik, None, None)

        try:
            result = extractor._extract_via_known_mapping(
                ticker.upper(), 10, verbose=True
            )
            if result["rows"]:
                print(
                    f"✅ SUCCESS! Found {len(result['rows'])} holdings for {ticker} with CIK {cik}"
                )
                print(f"   Note: {result['note']}")
                return True, result
            else:
                print(
                    f"⚠️  CIK {cik} has NPORT filings but no holdings found for {ticker}"
                )
                print(f"   Note: {result['note']}")
                return False, result
        finally:
            # Restore original mapping
            extractor.KNOWN_ETF_CIKS = original_mapping
            extractor.cleanup()

    except Exception as e:
        print(f"❌ Error testing CIK {cik}: {e}")
        return False, None


def discover_etf(ticker):
    """Main discovery function for an ETF ticker."""
    print(f"🎯 DISCOVERING ETF: {ticker.upper()}")
    print("=" * 50)

    # Step 1: Check if it's in sec-edgar-downloader
    print(f"\n1. Checking sec-edgar-downloader database...")
    extractor = ETFHoldingsExtractor()

    if hasattr(extractor, "downloader") and extractor.downloader:
        if ticker.upper() in extractor.downloader.ticker_to_cik_mapping:
            cik = extractor.downloader.ticker_to_cik_mapping[ticker.upper()]
            print(f"   ✅ Found in sec-edgar-downloader: CIK {cik}")

            # Test this CIK
            success, result = test_cik_for_nport(cik, ticker)
            if success:
                print(f"\n🎉 DISCOVERY COMPLETE!")
                print(f"   Add this to KNOWN_ETF_CIKS:")
                print(f'   "{ticker.upper()}": ("{cik}", None, None),')
                return cik
        else:
            print(f"   ❌ Not found in sec-edgar-downloader database")

    # Step 2: Search SEC company tickers
    print(f"\n2. Searching SEC company tickers database...")
    companies = search_sec_company_tickers(ticker)

    if not companies:
        print(f"   ❌ No companies found containing '{ticker}'")
        print(f"\n❌ DISCOVERY FAILED")
        print(f"   Possible reasons:")
        print(f"   - Ticker might be misspelled")
        print(f"   - ETF might not be US-domiciled")
        print(f"   - ETF might not file NPORT forms")
        print(f"   - ETF might be too new or delisted")
        return None

    print(f"   ✅ Found {len(companies)} potential matches:")
    for i, company in enumerate(companies, 1):
        print(f"      {i}. {company['title']} (CIK: {company['cik']})")

    # Step 3: Test each CIK for NPORT filings
    print(f"\n3. Testing CIKs for NPORT filings...")

    for i, company in enumerate(companies, 1):
        cik = company["cik"]
        title = company["title"]

        print(f"\n   Testing {i}/{len(companies)}: {title}")
        success, result = test_cik_for_nport(cik, ticker)

        if success:
            print(f"\n🎉 DISCOVERY COMPLETE!")
            print(f"   Company: {title}")
            print(f"   CIK: {cik}")
            print(f"   Holdings: {len(result['rows'])}")
            print(f"\n   Add this to KNOWN_ETF_CIKS:")
            print(f'   "{ticker.upper()}": ("{cik}", None, None),')
            return cik

    print(f"\n❌ DISCOVERY FAILED")
    print(
        f"   Found {len(companies)} potential companies but none had NPORT holdings for {ticker}"
    )
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Discover ETF CIK and filing information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover URTH ETF
  python discover_etf.py URTH

  # Discover multiple ETFs
  python discover_etf.py URTH ACWI VXUS
        """,
    )

    parser.add_argument("tickers", nargs="+", help="ETF ticker symbols to discover")

    args = parser.parse_args()

    for ticker in args.tickers:
        discover_etf(ticker)
        if len(args.tickers) > 1:
            print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
