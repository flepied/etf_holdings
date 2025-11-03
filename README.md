# ETF Holdings Library

A Python library for extracting ETF holdings data from SEC N-PORT filings with **automatic ticker discovery**. Works with any ETF that files NPORT forms, expanding coverage beyond manually curated lists.

## Features

- **Automatic ticker discovery** - Works with any ETF in the SEC database (10,000+ tickers)
- **Known ETF optimization** - Fast processing for curated high-quality ETFs
- **Comprehensive coverage** - Major ETF families: Vanguard, SPDR, Global X, VanEck, Invesco, iShares
- **Intelligent fallback** - Uses known mappings first, auto-discovery second
- **Rate-limited requests** - Built-in SEC compliance and proper error handling
- **Clean data output** - Structured data with issuer, CUSIP, ISIN, values, and weights
- **Batch processing** - Single ETF and multiple ETF processing capabilities
- **Portfolio overlap analysis** - Identify shared holdings across multiple ETFs
- **Smart caching** - Disk-based cache with automatic expiration (3-day default TTL)

## Supported ETFs

### Known High-Performance ETFs (Optimized)
These ETFs use curated mappings for fastest processing:

- **VTI** - Vanguard Total Stock Market ETF (3,582+ positions) ⚡
- **SPY** - SPDR S&P 500 ETF Trust (504+ positions) ⚡
- **QQQ** - Invesco QQQ Trust (101+ positions) ⚡
- **RSP** - SPDR S&P 500 Equal Weight ETF ⚡
- **NLR** - VanEck Uranium+Nuclear Energy ETF ⚡
- **XSHQ** - Invesco Scientific and Technology ETF ⚡
- **AIQ** - Global X AI & Technology ETF ⚡
- **USCA** - Xtrackers MSCI USA ESG Leaders ETF ⚡
- **FENY** - First Trust Energy Income & Growth Fund ⚡
- **VONV** - Vanguard Russell 1000 Value ETF ⚡

### Automatic Discovery Coverage
**10,000+ additional ETFs** supported via automatic ticker-to-CIK discovery. The library will automatically attempt to find and extract holdings for any ETF ticker, including:

- iShares ETFs (some)
- Additional Vanguard ETFs  
- SPDR family ETFs
- Invesco ETFs
- And many more...

## Installation

```bash
pip install -e .
```

## Quick Start

### Single ETF Holdings

```python
from etf_holdings import get_etf_holdings

# Get VTI holdings
result = get_etf_holdings('VTI', verbose=True)
print(f"Found {len(result['rows'])} positions for VTI")

# Access holdings data
for holding in result['rows'][:5]:  # First 5 positions
    print(f"{holding['issuer']}: ${holding['value_usd']}")
```

### Multiple ETF Holdings

```python
from etf_holdings import get_multiple_etf_holdings

# Get holdings for multiple ETFs
tickers = ['VTI', 'NLR', 'RSP']
results = get_multiple_etf_holdings(tickers, verbose=True)

print(f"Total positions: {results['summary']['total_positions']}")
print(f"ETFs with data: {results['summary']['etfs_with_holdings']}")
```

### Using the Class Interface

```python
from etf_holdings import ETFHoldingsExtractor

# Create extractor instance
extractor = ETFHoldingsExtractor(delay=0.3)  # Custom rate limiting

# Get holdings
result = extractor.get_etf_holdings('VTI', max_filings=25)

# Process results
if result['rows']:
    import pandas as pd
    df = pd.DataFrame(result['rows'])
    print(df.head())
```

## Data Structure

Each holding record contains:

```python
{
    "ticker_fund": "VTI",                    # ETF ticker
    "issuer": "Apple Inc",                   # Company name
    "title": "Apple Inc Common Stock",       # Security description
    "id_cusip": "037833100",                # CUSIP identifier
    "id_isin": "US0378331005",              # ISIN identifier
    "balance": "1000000.00",                # Shares/units held
    "value_usd": "150000000.00",            # USD value
    "weight_pct": "2.5"                     # Portfolio weight %
}
```

## Advanced Usage

### Custom Configuration

```python
from etf_holdings import ETFHoldingsExtractor

# Custom user agent and rate limiting
extractor = ETFHoldingsExtractor(
    user_agent="MyApp/1.0 (contact@example.com)",
    delay=0.5  # Slower requests
)

# Search more filings for hard-to-find ETFs
result = extractor.get_etf_holdings('VONV', max_filings=100)
```

### Error Handling

```python
from etf_holdings import get_etf_holdings

result = get_etf_holdings('UNKNOWN_ETF')

if not result['rows']:
    print(f"No data found: {result['note']}")
else:
    print(f"Success: {len(result['rows'])} positions")
```

## Portfolio Overlap Analysis

The library includes a powerful portfolio analysis tool to identify overlapping holdings across multiple ETFs:

### Command Line Usage

```bash
# Analyze overlap between major index ETFs
python analyze_portfolio.py VTI SPY QQQ

# Export analysis to CSV
python analyze_portfolio.py VTI SPY --export overlap_analysis.csv

# Quick analysis with fewer filings
python analyze_portfolio.py VTI SPY --max-filings 10 --top 15

# Verbose output with detailed progress
python analyze_portfolio.py VTI RSP AIQ --verbose
```

### Example Output

```
📊 PORTFOLIO OVERLAP ANALYSIS REPORT
================================================================================

📈 SUMMARY STATISTICS
   • Total ETFs analyzed: 2
   • ETFs with data: 2
   • Total positions: 4,086
   • Unique securities: 3,574
   • Overlapping securities: 475
   • Overlap percentage: 13.3%

🏆 TOP MOST OVERLAPPED SECURITIES
    1. United Airlines Holdings Inc (CUSIP: 910047109)
       Found in 2 ETFs: SPY, VTI
    2. Digital Realty Trust Inc (CUSIP: 253868103)
       Found in 2 ETFs: SPY, VTI
```

### Portfolio Analysis Features

- **Overlap Detection** - Finds securities held in multiple ETFs
- **Diversification Scoring** - Measures portfolio concentration risk
- **ETF Pair Analysis** - Shows which ETF combinations have highest overlap
- **CSV Export** - Export detailed overlap data for further analysis
- **Risk Assessment** - Provides diversification recommendations

## Smart Caching System

The library includes intelligent disk-based caching to dramatically improve performance and reduce SEC API calls:

### Automatic Caching

```python
from etf_holdings import get_etf_holdings

# First call - fetches from SEC and caches
result = get_etf_holdings('VTI')  # ~2-3 seconds

# Second call - instant from cache  
result = get_etf_holdings('VTI')  # ~0.01 seconds
```

### Cache Configuration

```python
from etf_holdings import ETFHoldingsExtractor

# Custom cache settings
extractor = ETFHoldingsExtractor(
    enable_cache=True,           # Enable caching (default: True)
    cache_dir="./my_cache",      # Custom cache directory
    cache_ttl_days=7             # Cache for 7 days (default: 3)
)

# Disable caching (two ways)
extractor = ETFHoldingsExtractor(enable_cache=False)  # Completely disabled
extractor = ETFHoldingsExtractor(cache_ttl_days=0)   # TTL-based disable
```

### Cache Management

```bash
# View cache statistics
python cache_manager.py stats

# Clear specific ETF cache
python cache_manager.py clear VTI

# Clear all cache
python cache_manager.py clear

# Clean up expired entries
python cache_manager.py cleanup

# Show cache location
python cache_manager.py info
```

### Cache Benefits

- **Speed**: 100x faster for repeated requests (0.01s vs 2-3s)
- **Reliability**: Reduces dependency on SEC server availability
- **Rate limiting**: Avoids SEC rate limit issues for repeated analysis
- **Automatic expiration**: Ensures data freshness (3-day default)
- **Smart invalidation**: Different max_filings create separate cache entries
- **Flexible control**: Set `cache_ttl_days=0` to disable caching via TTL

**Performance Example:**
```
Portfolio analysis (4 ETFs):
- Without cache: ~15-20 seconds
- With cache: ~0.5 seconds (97% faster!)
```

## Adding New ETFs

To add support for a new ETF, you need to find its CIK and optionally series ID:

```python
# In etf_holdings.py, add to KNOWN_ETF_CIKS:
KNOWN_ETF_CIKS = {
    # ... existing mappings ...
    "NEW_ETF": ("CIK_NUMBER", "SERIES_ID", None),
}
```

Use the discovery mode in the original script to find the correct CIK and series information.

## Rate Limiting

The library respects SEC rate limits with:
- Default 200ms delay between requests
- Configurable delays via the `delay` parameter
- Proper error handling for rate limit responses

## Requirements

- Python 3.8+
- requests>=2.25.0
- pandas>=1.3.0
- lxml>=4.6.0
- sec-edgar-downloader>=5.0.0

## Data Sources

This library extracts data from SEC EDGAR N-PORT filings, which are required quarterly reports that provide detailed portfolio holdings for registered investment companies, including ETFs.

## Limitations

- Depends on ETFs filing N-PORT forms (most major ETFs do)
- Some newer ETFs may not have sufficient filing history
- Complex trust structures may require manual CIK/series mapping
- Subject to SEC rate limiting (built-in handling provided)

## Contributing

To add support for additional ETFs:

1. Research the ETF's SEC CIK and series structure
2. Add the mapping to `KNOWN_ETF_CIKS`
3. Test the extraction with various filing dates
4. Submit a pull request with the verified mapping

## License

Apache License - see LICENSE file for details.
