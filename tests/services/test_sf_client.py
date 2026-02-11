"""
Tests for services/sf_client.py

Tests the Salesforce client including opportunity search,
updates, and mock mode fallback.
"""

import pytest
from unittest.mock import Mock, patch
from services.sf_client import SalesforceClient


class TestSalesforceClient:
    """Tests for SalesforceClient class"""

    def test_initialization_mock_mode_no_credentials(self, mock_env_no_credentials):
        """Test client initializes in mock mode without credentials"""
        client = SalesforceClient()

        assert client.is_mock is True
        assert client.sf is None

    def test_search_opportunities_mock_mode(self, mock_env_no_credentials, sample_opportunities_list):
        """Test opportunity search in mock mode"""
        client = SalesforceClient()

        results = client.search_opportunities("Acme Corp")

        assert len(results) == 2
        assert all("Acme Corp" in opp["Name"] for opp in results)

    def test_search_opportunities_returns_correct_fields(self, mock_env_no_credentials):
        """Test that search returns expected fields"""
        client = SalesforceClient()

        results = client.search_opportunities("Acme")

        assert len(results) > 0
        for opp in results:
            assert "Id" in opp
            assert "Name" in opp
            assert "StageName" in opp
            assert "CloseDate" in opp

    def test_search_opportunities_case_insensitive(self, mock_env_no_credentials):
        """Test that search is case insensitive"""
        client = SalesforceClient()

        results1 = client.search_opportunities("acme")
        results2 = client.search_opportunities("ACME")
        results3 = client.search_opportunities("Acme")

        assert len(results1) == len(results2) == len(results3)

    def test_search_opportunities_no_matches(self, mock_env_no_credentials):
        """Test search with no matching opportunities"""
        client = SalesforceClient()

        results = client.search_opportunities("NonexistentCompany")

        assert len(results) == 0

    def test_update_opportunity_stage_mock_mode(self, mock_env_no_credentials):
        """Test opportunity update in mock mode"""
        client = SalesforceClient()

        success = client.update_opportunity_stage(
            "006xx000001234AAA",
            "Acme Corp - Q1 Expansion",
            "Closed Won"
        )

        assert success is True

    def test_initialization_with_credentials_but_no_library(self, mock_env_no_credentials):
        """Test that client falls back to mock mode when library not installed"""
        # Even with credentials, if library isn't installed, it should be mock mode
        client = SalesforceClient(
            username="test@example.com",
            password="password",
            security_token="token"
        )

        # Will be mock if simple_salesforce isn't installed
        # This test verifies the fallback behavior works
        assert client.is_mock is True  # Falls back to mock without library
        # Can still search in mock mode
        results = client.search_opportunities("Acme")
        assert isinstance(results, list)


@pytest.mark.unit
class TestSalesforceClientMockData:
    """Tests for mock data accuracy"""

    def test_mock_opportunities_have_required_fields(self, mock_env_no_credentials):
        """Test that all mock opportunities have required fields"""
        client = SalesforceClient()

        results = client.search_opportunities("")  # Get all mock opps

        for opp in results:
            assert "Id" in opp
            assert "Name" in opp
            assert "StageName" in opp
            assert "CloseDate" in opp
            assert len(opp["Id"]) > 0
            assert len(opp["Name"]) > 0
