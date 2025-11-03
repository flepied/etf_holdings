#!/usr/bin/env python3
"""
Portfolio Overlap Analyzer

Analyzes ETF portfolio overlap by finding stocks that are owned through multiple ETFs.
Provides insights into diversification and concentration risks.
"""

import argparse
import pandas as pd
from collections import defaultdict, Counter
from typing import List, Dict
import sys
from etf_holdings import get_multiple_etf_holdings


def analyze_portfolio_overlap(
    tickers: List[str], max_filings: int = 50, verbose: bool = False
) -> Dict:
    """
    Analyze portfolio overlap across multiple ETFs.

    Args:
        tickers: List of ETF ticker symbols
        max_filings: Maximum filings to check per ETF
        verbose: Print detailed progress

    Returns:
        Dict containing overlap analysis results
    """
    print(f"Analyzing portfolio overlap for {len(tickers)} ETFs: {', '.join(tickers)}")

    # Get holdings for all ETFs
    results = get_multiple_etf_holdings(
        tickers, max_filings=max_filings, verbose=verbose
    )

    if not results["consolidated_holdings"]:
        print("❌ No holdings data found for any ETFs")
        return {}

    # Convert to DataFrame for analysis
    df = pd.DataFrame(results["consolidated_holdings"])

    # Improved security matching logic
    def create_security_id(row):
        cusip = row["id_cusip"] or ""
        issuer = row["issuer"] or ""
        title = row["title"] or ""

        # Extract ticker from title if available (e.g., "NVIDIA CORP (NVDA)")
        ticker = ""
        if "(" in title and ")" in title:
            ticker = title[title.rfind("(") + 1 : title.rfind(")")].strip()

        # Primary matching strategy: Use ticker if available (most reliable)
        if ticker and len(ticker) <= 6:  # Valid ticker symbols are typically 1-6 chars
            return f"TICKER:{ticker.upper()}"

        # Secondary: If we have CUSIP, use it
        if cusip and cusip.strip():
            return f"CUSIP:{cusip}"

        # Tertiary: normalize company name for matching
        if issuer:
            # Normalize issuer name: uppercase, remove common suffixes, clean whitespace
            normalized = issuer.upper().strip()
            # Remove common corporate suffixes that might differ
            suffixes = [
                " INC",
                " CORP",
                " CO",
                " LTD",
                " LLC",
                " LP",
                " CORPORATION",
                " INCORPORATED",
                " COMPANY",
            ]
            for suffix in suffixes:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)].strip()
                    break
            return f"NAME:{normalized}"

        return f"UNKNOWN:{cusip}|{issuer}"

    df["security_id"] = df.apply(create_security_id, axis=1)

    # Cross-reference mapping to find matches between different ID types
    # Create a mapping of normalized names to all identifiers for the same company
    name_to_ids = defaultdict(set)

    for _, row in df.iterrows():
        issuer = row["issuer"] or ""
        title = row["title"] or ""
        security_id = row["security_id"]

        if issuer:
            # Normalize company name
            normalized = issuer.upper().strip()
            suffixes = [
                " INC",
                " CORP",
                " CO",
                " LTD",
                " LLC",
                " LP",
                " CORPORATION",
                " INCORPORATED",
                " COMPANY",
            ]
            for suffix in suffixes:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)].strip()
                    break
            name_to_ids[normalized].add(security_id)

        # Also extract ticker from iShares titles
        if "(" in title and ")" in title:
            ticker = title[title.rfind("(") + 1 : title.rfind(")")].strip()
            if ticker and len(ticker) <= 6:
                # Map this ticker to all other IDs for same normalized name
                if issuer:
                    normalized = issuer.upper().strip()
                    for suffix in [
                        " INC",
                        " CORP",
                        " CO",
                        " LTD",
                        " LLC",
                        " LP",
                        " CORPORATION",
                        " INCORPORATED",
                        " COMPANY",
                    ]:
                        if normalized.endswith(suffix):
                            normalized = normalized[: -len(suffix)].strip()
                            break
                    name_to_ids[normalized].add(f"TICKER:{ticker.upper()}")

    # Create unified security IDs by merging related identifiers
    id_mapping = {}
    for normalized_name, id_set in name_to_ids.items():
        if len(id_set) > 1:
            # Multiple IDs for same company - use the first one as canonical
            canonical_id = sorted(list(id_set))[0]  # Sort for consistency
            for id_val in id_set:
                id_mapping[id_val] = canonical_id

    # Apply the mapping to unify security IDs
    df["unified_security_id"] = df["security_id"].map(lambda x: id_mapping.get(x, x))

    # Count occurrences of each security across ETFs using unified IDs
    security_counts = defaultdict(list)
    security_details = {}

    for _, row in df.iterrows():
        security_id = row["unified_security_id"]
        etf = row["ticker_fund"]

        security_counts[security_id].append(etf)
        if security_id not in security_details:
            security_details[security_id] = {
                "issuer": row["issuer"],
                "title": row["title"],
                "cusip": row["id_cusip"],
                "isin": row["id_isin"],
            }

    # Find overlapping securities (appear in 2+ ETFs)
    overlapping_securities = {
        sec_id: etfs
        for sec_id, etfs in security_counts.items()
        if len(set(etfs)) > 1  # Use set to handle duplicates
    }

    # Calculate overlap statistics
    total_unique_securities = len(security_counts)
    overlapping_count = len(overlapping_securities)
    overlap_percentage = (
        (overlapping_count / total_unique_securities * 100)
        if total_unique_securities > 0
        else 0
    )

    # ETF pair overlap analysis
    etf_pair_overlaps = defaultdict(int)
    for sec_id, etfs in overlapping_securities.items():
        unique_etfs = list(set(etfs))
        for i in range(len(unique_etfs)):
            for j in range(i + 1, len(unique_etfs)):
                pair = tuple(sorted([unique_etfs[i], unique_etfs[j]]))
                etf_pair_overlaps[pair] += 1

    # Most overlapped securities
    overlap_frequency = Counter(
        len(set(etfs)) for etfs in overlapping_securities.values()
    )

    return {
        "summary": {
            "total_etfs": len(tickers),
            "etfs_with_data": results["summary"]["etfs_with_holdings"],
            "total_unique_securities": total_unique_securities,
            "overlapping_securities": overlapping_count,
            "overlap_percentage": overlap_percentage,
            "total_positions": results["summary"]["total_positions"],
        },
        "overlapping_securities": overlapping_securities,
        "security_details": security_details,
        "etf_pair_overlaps": dict(etf_pair_overlaps),
        "overlap_frequency": dict(overlap_frequency),
        "individual_results": results["individual_results"],
    }


def print_overlap_report(analysis: Dict, top_n: int = 20):
    """Print a formatted overlap analysis report."""
    if not analysis:
        return

    summary = analysis["summary"]

    print("\n" + "=" * 80)
    print("📊 PORTFOLIO OVERLAP ANALYSIS REPORT")
    print("=" * 80)

    # Summary statistics
    print("\n📈 SUMMARY STATISTICS")
    print(f"   • Total ETFs analyzed: {summary['total_etfs']}")
    print(f"   • ETFs with data: {summary['etfs_with_data']}")
    print(f"   • Total positions: {summary['total_positions']:,}")
    print(f"   • Unique securities: {summary['total_unique_securities']:,}")
    print(f"   • Overlapping securities: {summary['overlapping_securities']:,}")
    print(f"   • Overlap percentage: {summary['overlap_percentage']:.1f}%")

    # ETF-level summary
    print("\n📋 ETF HOLDINGS SUMMARY")
    for etf, result in analysis["individual_results"].items():
        status = "✅" if result["rows"] else "❌"
        print(f"   {status} {etf}: {len(result['rows']):,} holdings")

    if not analysis["overlapping_securities"]:
        print("\n🎯 No overlapping securities found - perfect diversification!")
        return

    # Overlap frequency distribution
    print("\n📊 OVERLAP FREQUENCY DISTRIBUTION")
    for num_etfs, count in sorted(analysis["overlap_frequency"].items(), reverse=True):
        print(f"   • Securities in {num_etfs} ETFs: {count:,}")

    # Top ETF pair overlaps
    print("\n🔗 TOP ETF PAIR OVERLAPS")
    etf_pairs = sorted(
        analysis["etf_pair_overlaps"].items(), key=lambda x: x[1], reverse=True
    )
    for (etf1, etf2), count in etf_pairs[:10]:
        print(f"   • {etf1} ↔ {etf2}: {count:,} shared securities")

    # Most overlapped securities
    print(f"\n🏆 TOP {top_n} MOST OVERLAPPED SECURITIES")
    overlapped_by_count = []
    for sec_id, etfs in analysis["overlapping_securities"].items():
        unique_etfs = list(set(etfs))
        details = analysis["security_details"][sec_id]
        overlapped_by_count.append((len(unique_etfs), unique_etfs, details))

    overlapped_by_count.sort(key=lambda x: x[0], reverse=True)

    for i, (count, etfs, details) in enumerate(overlapped_by_count[:top_n], 1):
        issuer = details["issuer"] or "Unknown"
        cusip = details["cusip"] or "N/A"
        print(f"\n   {i:2d}. {issuer}")
        print(f"       CUSIP: {cusip}")
        print(f"       Found in {count} ETFs: {', '.join(sorted(etfs))}")


def export_overlap_csv(analysis: Dict, filename: str = "portfolio_overlap.csv"):
    """Export overlap analysis to CSV file."""
    if not analysis or not analysis["overlapping_securities"]:
        print("No overlapping securities to export")
        return

    # Prepare data for CSV export
    rows = []
    for sec_id, etfs in analysis["overlapping_securities"].items():
        unique_etfs = list(set(etfs))
        details = analysis["security_details"][sec_id]

        rows.append(
            {
                "issuer": details["issuer"] or "",
                "title": details["title"] or "",
                "cusip": details["cusip"] or "",
                "isin": details["isin"] or "",
                "num_etfs": len(unique_etfs),
                "etfs": ", ".join(sorted(unique_etfs)),
                "overlap_score": len(unique_etfs),
            }
        )

    # Create DataFrame and sort by overlap score
    df = pd.DataFrame(rows)
    df = df.sort_values("overlap_score", ascending=False)

    # Export to CSV
    df.to_csv(filename, index=False)
    print(f"\n💾 Overlap analysis exported to: {filename}")
    print(f"   📊 {len(df)} overlapping securities")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze portfolio overlap across multiple ETFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze overlap between major index ETFs
  python analyze_portfolio.py VTI SPY QQQ

  # Analyze specific sector ETFs with export
  python analyze_portfolio.py VTI RSP AIQ NLR --export overlap_analysis.csv

  # Quick analysis with fewer filings
  python analyze_portfolio.py VTI SPY --max-filings 5 --top 10

  # Verbose analysis
  python analyze_portfolio.py VTI RSP AIQ --verbose
        """,
    )

    parser.add_argument(
        "tickers", nargs="+", help="ETF ticker symbols to analyze (e.g., VTI SPY QQQ)"
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
        help="Number of top overlapped securities to show (default: 20)",
    )

    parser.add_argument(
        "--export", type=str, help="Export overlap analysis to CSV file"
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed progress information"
    )

    args = parser.parse_args()

    # Validate tickers
    if len(args.tickers) < 2:
        print("❌ Error: Need at least 2 ETF tickers to analyze overlap")
        sys.exit(1)

    # Convert tickers to uppercase
    tickers = [ticker.upper() for ticker in args.tickers]

    try:
        # Perform overlap analysis
        analysis = analyze_portfolio_overlap(
            tickers=tickers, max_filings=args.max_filings, verbose=args.verbose
        )

        if not analysis:
            print("❌ No analysis results generated")
            sys.exit(1)

        # Print report
        print_overlap_report(analysis, top_n=args.top)

        # Export if requested
        if args.export:
            export_overlap_csv(analysis, args.export)

        # Summary
        overlap_pct = analysis["summary"]["overlap_percentage"]
        if overlap_pct < 10:
            print(f"\n🎯 Excellent diversification! Only {overlap_pct:.1f}% overlap")
        elif overlap_pct < 25:
            print(f"\n👍 Good diversification with {overlap_pct:.1f}% overlap")
        elif overlap_pct < 50:
            print(
                f"\n⚠️  Moderate overlap at {overlap_pct:.1f}% - consider diversifying"
            )
        else:
            print(
                f"\n🚨 High overlap at {overlap_pct:.1f}% - significant concentration risk"
            )

    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
