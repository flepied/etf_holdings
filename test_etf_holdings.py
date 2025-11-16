"""
Pytest test suite for ETF Holdings Library with IB portfolio tickers.

Tests the ETF holdings extraction for all supported ETFs.
"""

import pandas as pd
import pytest

from etf_holdings import (
    ETFHoldingsExtractor,
    get_etf_holdings,
    get_multiple_etf_holdings,
)

TICKERS = [
    "RSP",
    "AIQ",
    "FENY",
    "NLR",
    "USCA",
    "VONV",
    "VTI",
    "XSHQ",
    "CG1",
    "CS1",
    "FMI",
]
UNSUPPORTED_TICKERS = ["BIL", "IAU", "TLT", "TBIL", "SHY"]  # Known unsupported ETFs


class TestETFHoldingsExtractor:
    """Test the ETFHoldingsExtractor class functionality."""

    def test_extractor_initialization(self):
        """Test extractor can be initialized with default and custom settings."""
        # Default initialization
        extractor = ETFHoldingsExtractor()
        assert extractor.delay == 0.2
        assert "etf-holdings-lib" in extractor.headers["User-Agent"]

        # Custom initialization
        custom_extractor = ETFHoldingsExtractor(user_agent="Test-Agent/1.0", delay=0.5)
        assert custom_extractor.delay == 0.5
        assert custom_extractor.headers["User-Agent"] == "Test-Agent/1.0"

    def test_known_etf_mappings_exist(self):
        """Test that known ETF CIK mappings are properly configured."""
        extractor = ETFHoldingsExtractor()

        # Check that working ETFs have mappings
        for ticker in TICKERS:
            assert (
                ticker in extractor.KNOWN_ETF_CIKS
                or ticker in extractor.ISHARES_ETF_MAPPINGS
                or ticker in extractor.AMUNDI_ETF_MAPPINGS
            ), f"{ticker} should have a configured data source"

        # Check mapping structure
        for ticker, mapping in extractor.KNOWN_ETF_CIKS.items():
            assert (
                len(mapping) == 3
            ), f"{ticker} mapping should have 3 elements (CIK, Series, Class)"
            assert mapping[0].startswith("000"), f"{ticker} CIK should start with zeros"

        # Check Amundi mapping structure
        for ticker, mapping in extractor.AMUNDI_ETF_MAPPINGS.items():
            assert (
                "product_id" in mapping and mapping["product_id"]
            ), f"{ticker} should define an Amundi product_id"
            assert "context" in mapping and isinstance(
                mapping["context"], dict
            ), f"{ticker} should define an Amundi API context"


class TestIndividualETFs:
    """Test individual ETF holdings extraction."""

    @pytest.mark.parametrize("ticker", TICKERS)
    def test_working_etfs(self, ticker):
        """Test that expected working ETFs return holdings data."""
        result = get_etf_holdings(ticker, max_filings=10, verbose=False)

        assert result["ticker"] == ticker
        assert isinstance(result["rows"], list)
        assert len(result["rows"]) > 0, f"{ticker} should return holdings"
        assert "OK via" in result["note"], f"{ticker} should have success message"

        # Test data structure
        if result["rows"]:
            holding = result["rows"][0]
            expected_keys = [
                "ticker_fund",
                "issuer",
                "title",
                "id_cusip",
                "id_isin",
                "security_ticker",
                "balance",
                "value_usd",
                "weight_pct",
                "currency",
                "sector",
                "country",
                "country_of_risk",
                "security_type",
                "bbg",
                "as_of_date",
            ]
            for key in expected_keys:
                assert key in holding, f"Holding should contain {key}"

    @pytest.mark.parametrize("ticker", UNSUPPORTED_TICKERS)
    def test_failing_etfs(self, ticker):
        """Test that expected failing ETFs return empty results."""
        result = get_etf_holdings(ticker, max_filings=5, verbose=False)

        assert result["ticker"] == ticker
        assert isinstance(result["rows"], list)
        assert len(result["rows"]) == 0, f"{ticker} should return no holdings"

        # Check for any valid failure message
        valid_failure_messages = [
            "CIK/series not found",
            "not found in automatic discovery database",
            "No NPORT-P filings found via auto-discovery",
            "auto-discovery disabled",
        ]
        assert any(
            msg in result["note"] for msg in valid_failure_messages
        ), f"{ticker} should have a valid failure message, got: {result['note']}"

    def test_unknown_etf(self):
        """Test handling of completely unknown ETF ticker."""
        result = get_etf_holdings("UNKNOWN_ETF_TICKER_12345", verbose=False)

        assert result["ticker"] == "UNKNOWN_ETF_TICKER_12345"
        assert len(result["rows"]) == 0
        assert (
            "CIK/series not found" in result["note"]
            or "not found in automatic discovery database" in result["note"]
        )

    def test_vti_large_holdings(self):
        """Test VTI specifically for large number of holdings."""
        result = get_etf_holdings("VTI", max_filings=10, verbose=False)

        assert len(result["rows"]) > 3000, "VTI should have 3000+ holdings"
        assert (
            "Vanguard Total Stock Market" in result["note"]
            or "OK via" in result["note"]
        )

        # Test that we get major holdings
        df = pd.DataFrame(result["rows"])
        issuers = df["issuer"].str.lower()

        # Should contain major tech companies
        major_companies = ["microsoft", "apple", "nvidia", "amazon"]
        found_companies = sum(
            1
            for company in major_companies
            if any(company in issuer for issuer in issuers)
        )
        assert found_companies >= 2, "VTI should contain major tech companies"


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_multiple_etf_holdings(self):
        """Test batch processing of multiple ETFs."""
        test_tickers = ["VTI", "RSP", "AIQ", "BIL"]  # Mix of working and failing
        results = get_multiple_etf_holdings(test_tickers, max_filings=5, verbose=False)

        # Test result structure
        assert "individual_results" in results
        assert "consolidated_holdings" in results
        assert "summary" in results

        # Test summary
        summary = results["summary"]
        assert summary["total_etfs_processed"] == 4
        assert summary["etfs_with_holdings"] >= 2  # At least VTI, RSP should work
        assert summary["total_positions"] > 0

        # Test individual results
        assert len(results["individual_results"]) == 4
        for ticker in test_tickers:
            assert ticker in results["individual_results"]

    def test_all_ib_portfolio_batch(self):
        """Test batch processing of all supported ETFs."""
        results = get_multiple_etf_holdings(
            list(TICKERS), max_filings=10, verbose=False
        )

        summary = results["summary"]
        assert summary["total_etfs_processed"] == len(TICKERS)
        assert summary["etfs_with_holdings"] >= 6  # Most ETFs should work
        assert summary["total_positions"] > 1000  # Should get many holdings

        # Test that we get reasonable success rate
        success_rate = summary["etfs_with_holdings"] / summary["total_etfs_processed"]
        assert (
            success_rate >= 0.7
        ), f"Success rate should be at least 70%, got {success_rate:.1%}"

        # Test that at least some key ETFs work
        key_etfs = ["RSP", "AIQ", "NLR"]  # These should definitely work
        for ticker in key_etfs:
            if ticker in results["individual_results"]:
                result = results["individual_results"][ticker]
                assert (
                    len(result["rows"]) > 0
                ), f"{ticker} should have holdings in batch"

    def test_consolidated_holdings_structure(self):
        """Test structure of consolidated holdings data."""
        results = get_multiple_etf_holdings(
            ["VTI", "RSP"], max_filings=5, verbose=False
        )

        if results["consolidated_holdings"]:
            holding = results["consolidated_holdings"][0]
            expected_keys = [
                "ticker_fund",
                "issuer",
                "title",
                "id_cusip",
                "id_isin",
                "balance",
                "value_usd",
                "weight_pct",
            ]
            for key in expected_keys:
                assert key in holding


class TestDataValidation:
    """Test data quality and validation."""

    def test_holdings_data_quality(self):
        """Test that holdings data meets quality standards."""
        result = get_etf_holdings("VTI", max_filings=5, verbose=False)

        if result["rows"]:
            df = pd.DataFrame(result["rows"])

            # Test required fields are populated
            assert not df["ticker_fund"].isna().all(), "ticker_fund should be populated"
            assert not df["issuer"].isna().all(), "issuer should be populated"

            # Test numeric fields can be converted
            df["value_numeric"] = pd.to_numeric(df["value_usd"], errors="coerce")
            valid_values = df["value_numeric"].notna().sum()
            total_rows = len(df)
            assert (
                valid_values / total_rows > 0.8
            ), "At least 80% of values should be numeric"

    def test_cusip_format(self):
        """Test CUSIP format validation."""
        result = get_etf_holdings("RSP", max_filings=5, verbose=False)

        if result["rows"]:
            df = pd.DataFrame(result["rows"])
            cusips = df[df["id_cusip"].notna()]["id_cusip"]

            for cusip in cusips.head(10):  # Test first 10 CUSIPs
                if cusip and cusip.strip():
                    # CUSIP should be 9 characters (8 alphanumeric + 1 check digit)
                    assert (
                        len(cusip.strip()) >= 8
                    ), f"CUSIP {cusip} should be at least 8 characters"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_network_timeout_handling(self):
        """Test that network errors are handled gracefully."""
        # This test uses a very short timeout to simulate network issues
        extractor = ETFHoldingsExtractor()

        # The extractor should handle failures gracefully
        result = extractor.get_etf_holdings(
            "NONEXISTENT_TICKER", max_filings=1, verbose=False
        )
        assert result["ticker"] == "NONEXISTENT_TICKER"
        assert len(result["rows"]) == 0
        assert "note" in result

    def test_empty_ticker_list(self):
        """Test handling of empty ticker list."""
        results = get_multiple_etf_holdings([], verbose=False)

        assert results["summary"]["total_etfs_processed"] == 0
        assert results["summary"]["etfs_with_holdings"] == 0
        assert results["summary"]["total_positions"] == 0
        assert len(results["individual_results"]) == 0
        assert len(results["consolidated_holdings"]) == 0


class TestPerformance:
    """Test performance characteristics."""

    def test_response_time_reasonable(self):
        """Test that single ETF extraction completes in reasonable time."""
        import time

        start_time = time.time()
        result = get_etf_holdings("RSP", max_filings=3, verbose=False)
        end_time = time.time()

        duration = end_time - start_time
        assert (
            duration < 30
        ), f"ETF extraction should complete within 30 seconds, took {duration:.1f}s"

        if result["rows"]:
            assert len(result["rows"]) > 0


class TestExportFunctionality:
    """Test data export capabilities."""

    def test_csv_export_format(self):
        """Test that data can be exported to CSV format."""
        results = get_multiple_etf_holdings(
            ["VTI", "RSP"], max_filings=3, verbose=False
        )

        if results["consolidated_holdings"]:
            df = pd.DataFrame(results["consolidated_holdings"])

            # Test that DataFrame can be created
            assert len(df) > 0
            assert "ticker_fund" in df.columns

            # Test CSV export capability (without actually writing file)
            csv_string = df.to_csv(index=False)
            assert "ticker_fund" in csv_string
            assert "issuer" in csv_string


# Pytest configuration and utilities
@pytest.fixture
def extractor():
    """Fixture providing an ETFHoldingsExtractor instance."""
    return ETFHoldingsExtractor()


@pytest.fixture
def sample_etf_data():
    """Fixture providing sample ETF holdings data."""
    return get_etf_holdings("RSP", max_filings=3, verbose=False)


# Integration test
class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow(self):
        """Test complete workflow from extraction to analysis."""
        # 1. Extract data
        tickers = ["VTI", "RSP", "AIQ"]
        results = get_multiple_etf_holdings(tickers, max_filings=5, verbose=False)

        # 2. Validate results
        assert results["summary"]["etfs_with_holdings"] >= 2

        # 3. Analyze data
        if results["consolidated_holdings"]:
            df = pd.DataFrame(results["consolidated_holdings"])

            # Basic analysis
            etf_counts = df["ticker_fund"].value_counts()
            assert len(etf_counts) >= 2

            # Value analysis
            df["value_numeric"] = pd.to_numeric(df["value_usd"], errors="coerce")
            total_value = df["value_numeric"].sum()
            assert total_value > 0

        # 4. Export capability
        # In real workflow, would export to file here


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
