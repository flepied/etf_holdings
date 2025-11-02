# ETF Holdings Library

A Python library for extracting ETF holdings data from SEC N-PORT filings. Supports major ETF families including Vanguard, SPDR, Global X, VanEck, Invesco, and more.

## Features

- Extract detailed holdings data from SEC N-PORT filings
- Support for major ETF providers (Vanguard, SPDR, Global X, VanEck, etc.)
- Rate-limited SEC API requests with proper error handling
- Clean, structured data output with issuer, CUSIP, ISIN, values, and weights
- Both single ETF and batch processing capabilities

## Supported ETFs

Currently supports these ETFs with proven data extraction:

- **VTI** - Vanguard Total Stock Market ETF (3,582+ positions)
- **NLR** - VanEck Uranium+Nuclear Energy ETF 
- **XSHQ** - Invesco Scientific and Technology ETF
- **AIQ** - Global X AI & Technology ETF
- **USCA** - Xtrackers MSCI USA ESG Leaders ETF
- **FENY** - First Trust Energy Income & Growth Fund
- **RSP** - SPDR S&P 500 Equal Weight ETF

Additional ETFs can be added by extending the CIK mapping configuration.

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
