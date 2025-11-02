#!/usr/bin/env python3
"""
Example usage of the ETF Holdings Library
"""

from etf_holdings import (
    get_etf_holdings,
    get_multiple_etf_holdings,
    ETFHoldingsExtractor,
)
import pandas as pd


def example_single_etf():
    """Example: Get holdings for a single ETF"""
    print("=" * 60)
    print("Example 1: Single ETF Holdings (VTI)")
    print("=" * 60)

    # Get VTI holdings
    result = get_etf_holdings("VTI", verbose=True)

    if result["rows"]:
        print(f"\n✅ Success! Found {len(result['rows'])} positions for VTI")
        print(f"Status: {result['note']}")

        # Convert to DataFrame for analysis
        df = pd.DataFrame(result["rows"])

        # Show top holdings by value
        print("\n📊 Top 10 Holdings by Value:")
        df["value_numeric"] = pd.to_numeric(df["value_usd"], errors="coerce")
        top_holdings = df.nlargest(10, "value_numeric")

        for i, (_, holding) in enumerate(top_holdings.iterrows(), 1):
            issuer = holding["issuer"][:40]  # Truncate long names
            value = (
                f"${float(holding['value_numeric']):,.0f}"
                if pd.notnull(holding["value_numeric"])
                else "N/A"
            )
            weight = holding["weight_pct"] if holding["weight_pct"] else "N/A"
            print(f"  {i:2d}. {issuer:<40} {value:>15} ({weight}%)")
    else:
        print(f"❌ No data found: {result['note']}")


def example_multiple_etfs():
    """Example: Get holdings for multiple ETFs"""
    print("\n" + "=" * 60)
    print("Example 2: Multiple ETF Holdings")
    print("=" * 60)

    tickers = ["RSP", "NLR", "AIQ"]
    results = get_multiple_etf_holdings(tickers, verbose=True)

    print(f"\n📈 Summary:")
    print(f"  • ETFs processed: {results['summary']['total_etfs_processed']}")
    print(f"  • ETFs with data: {results['summary']['etfs_with_holdings']}")
    print(f"  • Total positions: {results['summary']['total_positions']}")

    print(f"\n📋 Individual Results:")
    for ticker, result in results["individual_results"].items():
        status = "✅" if result["rows"] else "❌"
        count = len(result["rows"])
        print(f"  {status} {ticker}: {count} positions - {result['note']}")


def example_custom_extractor():
    """Example: Using the class interface with custom settings"""
    print("\n" + "=" * 60)
    print("Example 3: Custom Extractor Configuration")
    print("=" * 60)

    # Create extractor with custom settings
    extractor = ETFHoldingsExtractor(
        user_agent="ETF-Analysis-Tool/1.0 (research@example.com)",
        delay=0.3,  # Slower rate limiting
    )

    # Get holdings with more extensive search
    result = extractor.get_etf_holdings("XSHQ", max_filings=30, verbose=True)

    if result["rows"]:
        df = pd.DataFrame(result["rows"])

        print(f"\n🎯 XSHQ Analysis:")
        print(f"  • Total positions: {len(df)}")

        # Analyze by sector (basic analysis based on issuer names)
        print(f"  • Sample issuers: {', '.join(df['issuer'].head(5).tolist())}")

        # Show value distribution
        df["value_numeric"] = pd.to_numeric(df["value_usd"], errors="coerce")
        total_value = df["value_numeric"].sum()
        print(f"  • Total portfolio value: ${total_value:,.0f}")


def example_error_handling():
    """Example: Error handling for unknown ETFs"""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    # Try an unknown ETF
    result = get_etf_holdings("UNKNOWN_ETF")

    if not result["rows"]:
        print(f"⚠️  Expected failure for unknown ETF:")
        print(f"   Ticker: {result['ticker']}")
        print(f"   Message: {result['note']}")

    # Try a known problematic ETF
    result = get_etf_holdings("VONV")

    if not result["rows"]:
        print(f"\n⚠️  Known issue with VONV:")
        print(f"   Ticker: {result['ticker']}")
        print(f"   Message: {result['note']}")
        print(
            f"   Note: VONV requires additional research for proper CIK/series mapping"
        )


if __name__ == "__main__":
    print("ETF Holdings Library - Example Usage")
    print("This may take a few minutes due to SEC rate limiting...")

    try:
        example_single_etf()
        example_multiple_etfs()
        example_custom_extractor()
        example_error_handling()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print(
            "Make sure you have internet connectivity and the required dependencies installed."
        )
