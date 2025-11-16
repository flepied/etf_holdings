#!/usr/bin/env python3
"""
Geographic Dispersion Analyzer

Analyzes the geographic distribution of portfolio holdings across countries.
Calculates concentration metrics and visualizes geographic diversification.
"""

import argparse
import sys
from collections import defaultdict
from typing import Dict, List

import pandas as pd

from country_enricher import CountryEnricher
from etf_holdings import get_multiple_etf_holdings


def calculate_geographic_dispersion(holdings: List[Dict]) -> Dict:
    """
    Calculate geographic dispersion metrics for holdings.

    Args:
        holdings: List of holdings with country information

    Returns:
        Dict containing dispersion analysis
    """
    if not holdings:
        return {}

    # Group by country
    country_data = defaultdict(lambda: {"count": 0, "total_value": 0.0, "holdings": []})

    total_value = 0.0
    holdings_with_country = 0
    holdings_without_country = 0

    for holding in holdings:
        # Use normalized country_name if available, otherwise fall back to country field
        country = holding.get("country_name", holding.get("country", "")).strip()
        country_code = holding.get("country_code", "").strip()

        if (
            not country
            or country.upper() in ["N/A", "NONE", ""]
            or country_code == "UNKNOWN"
        ):
            country = "Unknown"
            holdings_without_country += 1
        else:
            holdings_with_country += 1

        # Parse value
        value_str = holding.get("value_usd", "0")
        try:
            value = float(
                str(value_str).replace(",", "").replace("$", "").strip() or "0"
            )
        except (ValueError, AttributeError):
            value = 0.0

        country_data[country]["count"] += 1
        country_data[country]["total_value"] += value
        country_data[country]["holdings"].append(holding)
        total_value += value

    # Calculate percentages
    country_breakdown = []
    for country, data in country_data.items():
        percentage = (data["total_value"] / total_value * 100) if total_value > 0 else 0
        country_breakdown.append(
            {
                "country": country,
                "count": data["count"],
                "total_value": data["total_value"],
                "percentage": percentage,
            }
        )

    # Sort by value
    country_breakdown.sort(key=lambda x: x["total_value"], reverse=True)

    # Calculate Herfindahl-Hirschman Index (HHI) for concentration
    # HHI = sum of squared market shares (0 = perfect diversification, 10000 = monopoly)
    hhi = sum((item["percentage"] ** 2) for item in country_breakdown)

    # Calculate effective number of countries (inverse HHI normalized)
    effective_countries = 10000 / hhi if hhi > 0 else 0

    return {
        "total_holdings": len(holdings),
        "holdings_with_country": holdings_with_country,
        "holdings_without_country": holdings_without_country,
        "total_countries": len(country_data),
        "total_value": total_value,
        "country_breakdown": country_breakdown,
        "hhi": hhi,
        "effective_countries": effective_countries,
    }


def print_geographic_report(analysis: Dict, top_n: int = 20):
    """Print a formatted geographic dispersion report."""
    if not analysis:
        return

    print("\n" + "=" * 80)
    print("🌍 GEOGRAPHIC DISPERSION ANALYSIS")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY")
    print(f"   • Total holdings: {analysis['total_holdings']:,}")
    print(f"   • With country data: {analysis['holdings_with_country']:,}")
    print(f"   • Without country data: {analysis['holdings_without_country']:,}")
    print(f"   • Total countries: {analysis['total_countries']:,}")
    print(f"   • Total value: ${analysis['total_value']:,.0f}")

    # Concentration metrics
    hhi = analysis["hhi"]
    effective_countries = analysis["effective_countries"]

    print("\n📈 CONCENTRATION METRICS")
    print(f"   • HHI (Herfindahl-Hirschman Index): {hhi:.0f}")
    print(f"   • Effective number of countries: {effective_countries:.1f}")

    # Interpret HHI
    if hhi < 1500:
        concentration_level = "Low concentration - Well diversified"
    elif hhi < 2500:
        concentration_level = "Moderate concentration"
    else:
        concentration_level = "High concentration - Geographic risk"

    print(f"   • Concentration level: {concentration_level}")

    # Country breakdown
    print(
        f"\n🌎 TOP {min(top_n, len(analysis['country_breakdown']))} COUNTRIES BY VALUE"
    )
    print(f"{'Rank':<6} {'Country':<25} {'Holdings':<10} {'Value':<20} {'%':<10}")
    print("-" * 80)

    for i, country_data in enumerate(analysis["country_breakdown"][:top_n], 1):
        country = country_data["country"][:24]
        count = country_data["count"]
        value = country_data["total_value"]
        pct = country_data["percentage"]

        print(f"{i:<6} {country:<25} {count:<10,} ${value:<19,.0f} {pct:<10.2f}%")

    # Regional grouping (simplified)
    print("\n🌐 REGIONAL DISTRIBUTION (estimated)")
    regional_data = defaultdict(lambda: {"count": 0, "value": 0.0})

    # Simple region mapping (can be enhanced)
    region_mapping = {
        "United States": "North America",
        "USA": "North America",
        "Canada": "North America",
        "Mexico": "North America",
        "United Kingdom": "Europe",
        "UK": "Europe",
        "Germany": "Europe",
        "France": "Europe",
        "Spain": "Europe",
        "Italy": "Europe",
        "Netherlands": "Europe",
        "Switzerland": "Europe",
        "Sweden": "Europe",
        "China": "Asia",
        "Japan": "Asia",
        "South Korea": "Asia",
        "Taiwan": "Asia",
        "India": "Asia",
        "Singapore": "Asia",
        "Hong Kong": "Asia",
        "Australia": "Oceania",
        "New Zealand": "Oceania",
        "Brazil": "South America",
        "Argentina": "South America",
        "Unknown": "Unknown",
    }

    for country_data in analysis["country_breakdown"]:
        country = country_data["country"]
        region = region_mapping.get(country, "Other")
        regional_data[region]["count"] += country_data["count"]
        regional_data[region]["value"] += country_data["total_value"]

    print(f"{'Region':<25} {'Holdings':<10} {'Value':<20} {'%':<10}")
    print("-" * 80)

    for region, data in sorted(
        regional_data.items(), key=lambda x: x[1]["value"], reverse=True
    ):
        pct = (
            (data["value"] / analysis["total_value"] * 100)
            if analysis["total_value"] > 0
            else 0
        )
        print(
            f"{region:<25} {data['count']:<10,} ${data['value']:<19,.0f} {pct:<10.2f}%"
        )


def export_geographic_csv(analysis: Dict, filename: str = "geographic_dispersion.csv"):
    """Export geographic analysis to CSV file."""
    if not analysis or not analysis["country_breakdown"]:
        print("No geographic data to export")
        return

    # Create DataFrame
    df = pd.DataFrame(analysis["country_breakdown"])
    df = df.sort_values("total_value", ascending=False)

    # Export to CSV
    df.to_csv(filename, index=False)
    print(f"\n💾 Geographic analysis exported to: {filename}")
    print(f"   📊 {len(df)} countries")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze geographic distribution of ETF holdings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze geographic distribution for VTI
  python analyze_geographic_dispersion.py VTI

  # Analyze multiple ETFs with export
  python analyze_geographic_dispersion.py VTI SPY QQQ --export geo_analysis.csv

  # Quick analysis with fewer filings
  python analyze_geographic_dispersion.py VTI --max-filings 5

  # Force refresh country data from API
  python analyze_geographic_dispersion.py VTI --force-refresh

  # Verbose output
  python analyze_geographic_dispersion.py VTI SPY --verbose
        """,
    )

    parser.add_argument(
        "tickers",
        nargs="+",
        help="ETF ticker symbols to analyze (e.g., VTI SPY QQQ)",
    )

    parser.add_argument(
        "--max-filings",
        type=int,
        default=50,
        help="Maximum filings to check per ETF (default: 50)",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top countries to show (default: 20)",
    )

    parser.add_argument(
        "--export", type=str, help="Export geographic analysis to CSV file"
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh country data from API (ignore cache)",
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed progress information"
    )

    args = parser.parse_args()

    # Convert tickers to uppercase
    tickers = [ticker.upper() for ticker in args.tickers]

    try:
        # Get ETF holdings
        print(f"Fetching holdings for {len(tickers)} ETF(s): {', '.join(tickers)}")
        results = get_multiple_etf_holdings(
            tickers=tickers, max_filings=args.max_filings, verbose=args.verbose
        )

        if not results["consolidated_holdings"]:
            print("❌ No holdings data found")
            sys.exit(1)

        holdings = results["consolidated_holdings"]
        print(f"✅ Retrieved {len(holdings)} total holdings")

        # Enrich with country data
        print("\n🌍 Enriching holdings with country information...")
        enricher = CountryEnricher(enable_cache=True)
        enriched_holdings = enricher.enrich_holdings(
            holdings, force_refresh=args.force_refresh, verbose=args.verbose
        )

        # Calculate geographic dispersion
        print("\n📊 Calculating geographic dispersion...")
        analysis = calculate_geographic_dispersion(enriched_holdings)

        if not analysis:
            print("❌ No geographic analysis results")
            sys.exit(1)

        # Print report
        print_geographic_report(analysis, top_n=args.top)

        # Export if requested
        if args.export:
            export_geographic_csv(analysis, args.export)

        # Summary assessment
        hhi = analysis["hhi"]
        effective_countries = analysis["effective_countries"]

        print("\n" + "=" * 80)
        print("📋 ASSESSMENT")
        print("=" * 80)

        if effective_countries >= 10:
            print(
                f"✅ Excellent geographic diversification across {effective_countries:.1f} effective countries"
            )
        elif effective_countries >= 5:
            print(
                f"👍 Good geographic diversification across {effective_countries:.1f} effective countries"
            )
        elif effective_countries >= 3:
            print(
                f"⚠️  Moderate geographic concentration - {effective_countries:.1f} effective countries"
            )
        else:
            print(
                f"🚨 High geographic concentration - only {effective_countries:.1f} effective countries"
            )

        # Show cache stats
        if args.verbose:
            cache_stats = enricher.get_cache_stats()
            if cache_stats:
                print(
                    f"\n📁 Country cache: {cache_stats['total_entries']} entries cached"
                )

    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
