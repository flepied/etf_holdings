#!/usr/bin/env python3
"""
ETF Holdings Cache Manager

Command-line tool for managing ETF holdings cache.
"""

import argparse
import sys

from etf_holdings import ETFHoldingsExtractor


def print_cache_stats(stats):
    """Print formatted cache statistics."""
    if not stats:
        print("❌ Cache is disabled or not available")
        return

    print("\n📊 CACHE STATISTICS")
    print("=" * 50)
    print(f"Cache directory: {stats['cache_dir']}")
    print(f"Cache TTL: {stats['ttl_days']} days")
    print(f"Total cached ETFs: {stats['total_cached_etfs']}")
    print(f"Total cache files: {stats['total_files']}")
    print(f"Total cache size: {stats['total_size_mb']} MB")

    if stats["cached_etfs"]:
        print(f"\n📋 CACHED ETFs:")
        for ticker, info in stats["cached_etfs"].items():
            print(
                f"  • {ticker}: {info['holdings_count']:,} holdings "
                f"(cached: {info['cached_at'][:10]}, max_filings: {info['max_filings']})"
            )
    else:
        print("\n📭 No ETFs currently cached")


def main():
    parser = argparse.ArgumentParser(
        description="Manage ETF holdings cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show cache statistics
  python cache_manager.py stats

  # Clear all cache
  python cache_manager.py clear

  # Clear specific ETF
  python cache_manager.py clear VTI

  # Clean up expired entries
  python cache_manager.py cleanup

  # Show cache location
  python cache_manager.py info
        """,
    )

    parser.add_argument(
        "action",
        choices=["stats", "clear", "cleanup", "info"],
        help="Action to perform",
    )

    parser.add_argument(
        "ticker",
        nargs="?",
        help="ETF ticker for clear action (optional - clears all if not specified)",
    )

    parser.add_argument("--cache-dir", help="Custom cache directory")

    parser.add_argument(
        "--cache-ttl-days", type=int, default=3, help="Cache TTL in days (default: 3)"
    )

    args = parser.parse_args()

    # Initialize extractor with cache enabled
    try:
        extractor = ETFHoldingsExtractor(
            enable_cache=True,
            cache_dir=args.cache_dir,
            cache_ttl_days=args.cache_ttl_days,
        )

        if args.action == "stats":
            stats = extractor.get_cache_stats()
            print_cache_stats(stats)

        elif args.action == "clear":
            if args.ticker:
                print(f"Clearing cache for {args.ticker.upper()}...")
                extractor.clear_cache(args.ticker.upper())
            else:
                print("Clearing all cache...")
                extractor.clear_cache()

        elif args.action == "cleanup":
            print("Cleaning up expired cache entries...")
            cleaned = extractor.cleanup_expired_cache()
            if cleaned > 0:
                print(f"✅ Cleaned up {cleaned} expired entries")
            else:
                print("✅ No expired entries found")

        elif args.action == "info":
            stats = extractor.get_cache_stats()
            if stats:
                print(f"Cache directory: {stats['cache_dir']}")
                print(f"Cache TTL: {stats['ttl_days']} days")
            else:
                print("❌ Cache is disabled")

    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
