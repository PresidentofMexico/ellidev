"""
Company data aggregation service.

Aggregates company context from multiple sources:
- Salesforce (accounts, opportunities, contacts)
- RAG knowledge base
- Financial data (placeholder for Snowflake integration)
- Portfolio exposure (placeholder)
"""

from typing import Dict, List, Optional
from services.sf_client import SalesforceClient
from services.vector_store import VectorStore
from services.logger import logger


class CompanyAggregator:
    """
    Aggregates company data from multiple sources for context retrieval.
    """

    def __init__(
        self,
        sf_client: Optional[SalesforceClient] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        """
        Initialize company aggregator.

        Args:
            sf_client: SalesforceClient instance (optional, creates new if not provided)
            vector_store: VectorStore instance (optional, creates new if not provided)
        """
        self.sf_client = sf_client or SalesforceClient()
        self.vector_store = vector_store or VectorStore()

    def get_company_context(self, company_name: str) -> Dict:
        """
        Aggregate all company data from multiple sources.

        Args:
            company_name: Company name to search for

        Returns:
            Dictionary containing:
            - account: Account information from Salesforce
            - opportunities: List of opportunities
            - contacts: List of contacts
            - knowledge_base: Relevant knowledge base chunks
            - financials: Financial summary (placeholder)
            - portfolio_exposure: Portfolio exposure info (placeholder)
        """
        logger.info(
            f"Aggregating context for company: {company_name}",
            service="company_aggregator",
            company=company_name
        )

        context = {
            "account": self._get_account_info(company_name),
            "opportunities": self._get_opportunities(company_name),
            "contacts": self._get_contacts(company_name),
            "knowledge_base": self._search_knowledge_base(company_name),
            "financials": self._get_financials(company_name),
            "portfolio_exposure": self._get_portfolio_exposure(company_name),
        }

        logger.info(
            f"Context aggregation complete for {company_name}",
            service="company_aggregator",
            company=company_name,
            has_account=context["account"] is not None,
            opportunity_count=len(context["opportunities"]),
            contact_count=len(context["contacts"]),
            kb_results=len(context["knowledge_base"])
        )

        return context

    def _get_account_info(self, company_name: str) -> Optional[Dict]:
        """
        Get account information from Salesforce.

        Args:
            company_name: Company name to search

        Returns:
            Account dictionary or None if not found
        """
        try:
            accounts = self.sf_client.search_accounts(company_name)
            if accounts:
                return accounts[0]  # Return best match
            return None
        except Exception as e:
            logger.error(
                f"Error fetching account for {company_name}: {e}",
                service="company_aggregator",
                error=str(e)
            )
            return None

    def _get_opportunities(self, company_name: str) -> List[Dict]:
        """
        Get opportunities for a company from Salesforce.

        Args:
            company_name: Company name to search

        Returns:
            List of opportunity dictionaries
        """
        try:
            return self.sf_client.search_opportunities(company_name)
        except Exception as e:
            logger.error(
                f"Error fetching opportunities for {company_name}: {e}",
                service="company_aggregator",
                error=str(e)
            )
            return []

    def _get_contacts(self, company_name: str) -> List[Dict]:
        """
        Get contacts for a company from Salesforce.

        Args:
            company_name: Company name to search

        Returns:
            List of contact dictionaries
        """
        try:
            return self.sf_client.search_contacts(company_name=company_name)
        except Exception as e:
            logger.error(
                f"Error fetching contacts for {company_name}: {e}",
                service="company_aggregator",
                error=str(e)
            )
            return []

    def _search_knowledge_base(self, company_name: str) -> List[Dict]:
        """
        Search knowledge base for company-related content.

        Args:
            company_name: Company name to search

        Returns:
            List of relevant knowledge base chunks
        """
        try:
            results = self.vector_store.search(company_name, top_k=5)

            # Filter to only include relevant results (score > 0.3)
            relevant = [r for r in results if r.get("score", 0) > 0.3]

            return relevant
        except Exception as e:
            logger.error(
                f"Error searching knowledge base for {company_name}: {e}",
                service="company_aggregator",
                error=str(e)
            )
            return []

    def _get_financials(self, company_name: str) -> Optional[str]:
        """
        Get financial summary for a company.

        This is a placeholder for future Snowflake enterprise data integration.
        See docs/SNOWFLAKE_DATA_INTEGRATION_PLAN.md for implementation details.

        Args:
            company_name: Company name to search

        Returns:
            Financial summary string or None
        """
        # TODO: Implement when Snowflake enterprise data integration is complete
        # This would query financial tables in Snowflake for:
        # - Revenue data
        # - Payment history
        # - Credit terms
        # - Outstanding invoices

        # For now, return mock data if company matches known mock companies
        mock_financials = {
            "acme": "Revenue: $2.5M (FY25) | Payment Terms: Net 30 | Status: Good Standing",
            "techstart": "Revenue: $500K (FY25) | Payment Terms: Net 45 | Status: New Customer",
            "global": "Revenue: $8.2M (FY25) | Payment Terms: Net 15 | Status: Strategic Account",
        }

        company_lower = company_name.lower()
        for key, value in mock_financials.items():
            if key in company_lower:
                return value

        return None

    def _get_portfolio_exposure(self, company_name: str) -> Optional[str]:
        """
        Get portfolio exposure information for a company.

        This is a placeholder for future implementation.

        Args:
            company_name: Company name to search

        Returns:
            Portfolio exposure string or None
        """
        # TODO: Define and implement portfolio exposure metrics
        # This could include:
        # - Total deal value exposure
        # - Risk metrics
        # - Concentration analysis

        return None
