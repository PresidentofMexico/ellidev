import os
import time
from typing import Optional
from services.logger import logger
from services.metrics import metrics
from services.sf_oauth import SalesforceOAuth


# ===========================================
# SALESFORCE PICKLIST VALUES (Eldridge Org)
# ===========================================

# Strategy picklist values
STRATEGY_VALUES = [
    "Administrative",
    "Asset Based",
    "Corporate Credit",
    "Eldridge Industries",
    "Eldridge Sports & Entertainment",
    "GP Solutions",
    "Other",
    "RE Credit",
    "RE Equity",
    "Structured Credit",
]

# Security Type picklist values (partial list - most common)
SECURITY_TYPE_VALUES = [
    "1L Term Loan A",
    "2L Term Loan",
    "Acquisition / Majority",
    "Asset Based Loan",
    "Bond",
    "CLO",
    "CLO Debt",
    "CLO Equity",
    "CLO Hybrid",
    "Common Equity",
    "Construction Loan",
    "Convertible Note",
    "Delay Draw Term Loan",
    "Equipment Lease",
    "Fund Commitment",
    "GP Financing",
    "GP Interest",
    "GP Stakes",
    "Junior Sub Debt",
    "Lease",
    "Mortgage",
    "Other",
    "Other Equity",
    "Other Senior Debt",
    "Other Sub Debt",
    "PIPE",
    "Preferred Equity",
    "Promissory Note",
    "Revolving Line of Credit",
    "SAFE",
    "Secured Note",
    "Senior Sub Debt",
    "Series A",
    "Series B",
    "Series C",
    "Series D",
    "Series E",
    "Series F",
    "Series Seed",
    "SPAC",
    "Subordinated Debt",
    "Surplus Note",
    "Tax Lease",
    "Term Loan",
    "Unsecured Note",
    "Unsubordinated Debt",
    "Warrants",
    "WBS",
]

# Stage picklist values
STAGE_VALUES = [
    "Initial Review",
    "Proposal",
    "Term Sheet",
    "Diligence",
    "Execution",
    "Pre-Close",
    "Closed Funded",
    "Syndication",
    "On Hold",
    "Exited",
    "Dead",
    "Passed",
    "Needs Analysis",
    "Tracking",
    "Closed Lost",
    "Active",
    "Completed",
]

# Common stages for new deals (subset for UI)
COMMON_STAGES = [
    "Initial Review",
    "Proposal",
    "Term Sheet",
    "Diligence",
    "Execution",
    "Pre-Close",
]


class SalesforceClient:
    """
    Salesforce API client with multiple authentication methods.

    Supports:
    1. OAuth Web Server Flow with Refresh Token (SSO-compatible, recommended)
    2. Session ID + Instance URL (SSO-compatible, temporary)
    3. Username/Password + Security Token (traditional, non-SSO only)

    Authentication priority:
    1. OAuth with Refresh Token (if SF_CONSUMER_KEY, SF_CONSUMER_SECRET, and SF_REFRESH_TOKEN are set)
    2. OAuth Web Server Flow (if SF_CONSUMER_KEY and SF_CONSUMER_SECRET are set - will prompt for browser login)
    3. Session ID (if SF_SESSION_ID is set - temporary, expires)
    4. Username/Password (if SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN are set)
    5. Mock mode (if no credentials are found)
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        session_id: Optional[str] = None,
        instance_url: Optional[str] = None,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize Salesforce client with real or mock connection.

        Args:
            username: Salesforce username (optional, defaults to env var)
            password: Salesforce password (optional, defaults to env var)
            security_token: Salesforce security token (optional, defaults to env var)
            session_id: Active session ID for SSO users (optional, defaults to env var)
            instance_url: Salesforce instance URL e.g. https://yourfirm.my.salesforce.com
            consumer_key: OAuth Connected App consumer key (optional, defaults to env var)
            consumer_secret: OAuth Connected App consumer secret (optional, defaults to env var)
            refresh_token: OAuth refresh token for automatic token renewal (optional, defaults to env var)
        """
        # Load credentials from env vars or parameters
        self.username = username or os.environ.get("SF_USERNAME")
        self.password = password or os.environ.get("SF_PASSWORD")
        self.security_token = security_token or os.environ.get("SF_SECURITY_TOKEN")
        self.session_id = session_id or os.environ.get("SF_SESSION_ID")
        self.instance_url = instance_url or os.environ.get("SF_INSTANCE_URL")
        self.consumer_key = consumer_key or os.environ.get("SF_CONSUMER_KEY")
        self.consumer_secret = consumer_secret or os.environ.get("SF_CONSUMER_SECRET")
        self.refresh_token = refresh_token or os.environ.get("SF_REFRESH_TOKEN")

        # OAuth handler for token refresh
        self._oauth_handler: Optional[SalesforceOAuth] = None

        # Try to initialize real Salesforce connection
        self.sf = None
        self.is_mock = True
        self.auth_method = None

        # Priority 1: OAuth with Refresh Token (SSO-compatible, auto-renewing)
        if self.consumer_key and self.consumer_secret and self.refresh_token:
            self._connect_with_oauth_refresh()

        # Priority 2: OAuth Web Server Flow (will prompt for browser login)
        elif self.consumer_key and self.consumer_secret:
            self._connect_with_oauth_flow()

        # Priority 3: Session ID (SSO-compatible, temporary)
        elif self.session_id and self.instance_url:
            self._connect_with_session_id()

        # Priority 4: Username/Password + Security Token (traditional)
        elif self.username and self.password and self.security_token:
            self._connect_with_password()

        # Fallback: Mock mode
        else:
            logger.info(
                "Salesforce credentials not found, using mock mode",
                service="salesforce",
                mode="mock"
            )

    def _connect_with_session_id(self):
        """Connect using an existing session ID (SSO-compatible)."""
        try:
            from simple_salesforce import Salesforce

            self.sf = Salesforce(
                session_id=self.session_id,
                instance_url=self.instance_url,
            )
            self.is_mock = False
            self.auth_method = "session_id"
            logger.info(
                "Connected to Salesforce API via session ID",
                service="salesforce",
                mode="real",
                auth_method="session_id"
            )
        except ImportError:
            logger.warning(
                "simple-salesforce not installed, using mock mode",
                service="salesforce"
            )
        except Exception as e:
            logger.error(
                f"Could not connect to Salesforce with session ID: {e}",
                service="salesforce",
                error=str(e),
                auth_method="session_id"
            )
            logger.log_error(e, context={"service": "salesforce", "method": "_connect_with_session_id"})

    def _connect_with_oauth_refresh(self):
        """Connect using OAuth refresh token (SSO-compatible, auto-renewing)."""
        try:
            from simple_salesforce import Salesforce

            # Use OAuth handler to refresh the access token
            self._oauth_handler = SalesforceOAuth(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                instance_url=self.instance_url,
                refresh_token=self.refresh_token,
            )

            tokens = self._oauth_handler.get_access_token()
            if not tokens:
                logger.error(
                    "Could not refresh OAuth access token",
                    service="salesforce",
                    auth_method="oauth_refresh"
                )
                return

            self.sf = Salesforce(
                session_id=tokens.access_token,
                instance_url=tokens.instance_url,
            )
            self.is_mock = False
            self.auth_method = "oauth_refresh"
            self.instance_url = tokens.instance_url

            logger.info(
                "Connected to Salesforce API via OAuth refresh token",
                service="salesforce",
                mode="real",
                auth_method="oauth_refresh",
                instance_url=tokens.instance_url
            )
        except ImportError:
            logger.warning(
                "simple-salesforce not installed, using mock mode",
                service="salesforce"
            )
        except Exception as e:
            logger.error(
                f"Could not connect to Salesforce with OAuth refresh: {e}",
                service="salesforce",
                error=str(e),
                auth_method="oauth_refresh"
            )
            logger.log_error(e, context={"service": "salesforce", "method": "_connect_with_oauth_refresh"})

    def _connect_with_oauth_flow(self):
        """Connect using OAuth Web Server Flow (will prompt for browser login)."""
        try:
            from simple_salesforce import Salesforce

            # Use OAuth handler to initiate the full flow
            self._oauth_handler = SalesforceOAuth(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                instance_url=self.instance_url,
            )

            tokens = self._oauth_handler.get_access_token()
            if not tokens:
                logger.error(
                    "OAuth flow failed or was cancelled",
                    service="salesforce",
                    auth_method="oauth_flow"
                )
                return

            self.sf = Salesforce(
                session_id=tokens.access_token,
                instance_url=tokens.instance_url,
            )
            self.is_mock = False
            self.auth_method = "oauth_flow"
            self.instance_url = tokens.instance_url
            self.refresh_token = tokens.refresh_token

            logger.info(
                "Connected to Salesforce API via OAuth Web Server Flow",
                service="salesforce",
                mode="real",
                auth_method="oauth_flow",
                instance_url=tokens.instance_url
            )
        except ImportError:
            logger.warning(
                "simple-salesforce not installed, using mock mode",
                service="salesforce"
            )
        except Exception as e:
            logger.error(
                f"Could not connect to Salesforce with OAuth flow: {e}",
                service="salesforce",
                error=str(e),
                auth_method="oauth_flow"
            )
            logger.log_error(e, context={"service": "salesforce", "method": "_connect_with_oauth_flow"})

    def _refresh_token_if_needed(self) -> bool:
        """
        Refresh the access token if we have an OAuth handler.

        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if not self._oauth_handler:
            return False

        try:
            tokens = self._oauth_handler.get_access_token()
            if tokens:
                from simple_salesforce import Salesforce
                self.sf = Salesforce(
                    session_id=tokens.access_token,
                    instance_url=tokens.instance_url,
                )
                return True
        except Exception as e:
            logger.error(f"Token refresh failed: {e}", service="salesforce")

        return False

    def _connect_with_oauth(self):
        """Connect using OAuth Connected App credentials (SSO-compatible)."""
        try:
            from simple_salesforce import Salesforce

            # Use OAuth 2.0 username-password flow with connected app
            self.sf = Salesforce(
                username=self.username,
                password=self.password,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                domain="login" if not self.instance_url else None,
                instance_url=self.instance_url,
            )
            self.is_mock = False
            self.auth_method = "oauth"
            logger.info(
                "Connected to Salesforce API via OAuth",
                service="salesforce",
                mode="real",
                auth_method="oauth"
            )
        except ImportError:
            logger.warning(
                "simple-salesforce not installed, using mock mode",
                service="salesforce"
            )
        except Exception as e:
            logger.error(
                f"Could not connect to Salesforce with OAuth: {e}",
                service="salesforce",
                error=str(e),
                auth_method="oauth"
            )
            logger.log_error(e, context={"service": "salesforce", "method": "_connect_with_oauth"})

    def _connect_with_password(self):
        """Connect using username/password + security token (traditional)."""
        try:
            from simple_salesforce import Salesforce

            self.sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
            )
            self.is_mock = False
            self.auth_method = "password"
            logger.info(
                "Connected to Salesforce API via password",
                service="salesforce",
                mode="real",
                auth_method="password"
            )
        except ImportError:
            logger.warning(
                "simple-salesforce not installed, using mock mode",
                service="salesforce"
            )
        except Exception as e:
            logger.error(
                f"Could not connect to Salesforce: {e}",
                service="salesforce",
                error=str(e),
                auth_method="password"
            )
            logger.log_error(e, context={"service": "salesforce", "method": "_connect_with_password"})

    def search_opportunities(self, company_name: str) -> list[dict]:
        """
        Search for opportunities by company name.

        Args:
            company_name: The company name to search for

        Returns:
            List of opportunity dictionaries with Id, Name, StageName, CloseDate
        """
        if not self.is_mock and self.sf:
            try:
                start_time = time.time()
                # SOQL query to search for opportunities
                query = f"SELECT Id, Name, StageName, CloseDate FROM Opportunity WHERE Name LIKE '%{company_name}%' LIMIT 5"
                result = self.sf.query(query)
                duration_ms = (time.time() - start_time) * 1000

                opportunities = []
                for record in result.get("records", []):
                    opportunities.append(
                        {
                            "Id": record.get("Id"),
                            "Name": record.get("Name"),
                            "StageName": record.get("StageName"),
                            "CloseDate": record.get("CloseDate"),
                        }
                    )

                logger.log_api_call(
                    service="salesforce",
                    method="search_opportunities",
                    duration_ms=duration_ms,
                    success=True,
                    context={"company_name": company_name, "results_count": len(opportunities)}
                )
                metrics.record_api_call("salesforce", "search_opportunities", duration_ms, True)

                return opportunities
            except Exception as e:
                logger.log_error(e, context={
                    "service": "salesforce",
                    "method": "search_opportunities",
                    "company_name": company_name
                })
                metrics.record_error("salesforce", type(e).__name__)
                return self._mock_search_opportunities(company_name)
        else:
            # Mock mode fallback
            logger.debug(f"Mock search for opportunities: {company_name}", service="salesforce", mode="mock")
            return self._mock_search_opportunities(company_name)

    def _mock_search_opportunities(self, company_name: str) -> list[dict]:
        """
        Mock search for local testing without Salesforce credentials.

        Args:
            company_name: The company name to search for

        Returns:
            List of mock opportunity dictionaries
        """
        # Mock database of opportunities
        mock_opportunities = [
            {
                "Id": "006xx000001234AAA",
                "Name": "Acme Corp - Q1 Expansion",
                "StageName": "Discovery",
                "CloseDate": "2026-03-31",
            },
            {
                "Id": "006xx000001234BBB",
                "Name": "Acme Corp - Enterprise Deal",
                "StageName": "Negotiation",
                "CloseDate": "2026-04-15",
            },
            {
                "Id": "006xx000001234CCC",
                "Name": "TechStart Inc - Pilot",
                "StageName": "Discovery",
                "CloseDate": "2026-02-28",
            },
            {
                "Id": "006xx000001234DDD",
                "Name": "Global Systems - Migration",
                "StageName": "Closed Won",
                "CloseDate": "2026-01-15",
            },
        ]

        # Filter mock opportunities by company name (case-insensitive)
        company_lower = company_name.lower()
        matches = [
            opp for opp in mock_opportunities if company_lower in opp["Name"].lower()
        ]

        return matches

    def update_opportunity_stage(
        self, opp_id: str, opp_name: str, new_stage: str
    ) -> bool:
        """
        Update an opportunity's stage in Salesforce.

        Args:
            opp_id: Salesforce opportunity ID
            opp_name: Opportunity name (for logging)
            new_stage: The new stage value

        Returns:
            True on success, False on failure
        """
        if not self.is_mock and self.sf:
            try:
                start_time = time.time()
                self.sf.Opportunity.update(opp_id, {"StageName": new_stage})
                duration_ms = (time.time() - start_time) * 1000

                logger.log_workflow(
                    workflow_type="salesforce_update",
                    user_id="system",
                    action="update_opportunity_stage",
                    success=True,
                    duration_ms=duration_ms,
                    details={
                        "opp_id": opp_id,
                        "opp_name": opp_name,
                        "new_stage": new_stage
                    }
                )
                logger.log_api_call(
                    service="salesforce",
                    method="update_opportunity",
                    duration_ms=duration_ms,
                    success=True,
                    context={"opp_id": opp_id, "opp_name": opp_name, "new_stage": new_stage}
                )
                metrics.record_api_call("salesforce", "update_opportunity", duration_ms, True)

                return True
            except Exception as e:
                logger.log_error(e, context={
                    "service": "salesforce",
                    "method": "update_opportunity_stage",
                    "opp_id": opp_id,
                    "opp_name": opp_name,
                    "new_stage": new_stage
                })
                metrics.record_error("salesforce", type(e).__name__)
                logger.log_workflow(
                    workflow_type="salesforce_update",
                    user_id="system",
                    action="update_opportunity_stage",
                    success=False,
                    duration_ms=0,
                    details={"error": str(e)}
                )
                return False
        else:
            # Mock mode
            logger.info(
                f"Mock: Would update '{opp_name}' to stage '{new_stage}'",
                service="salesforce",
                mode="mock",
                opp_id=opp_id,
                opp_name=opp_name,
                new_stage=new_stage
            )
            return True

    def create_opportunity(self, data: dict, _retry: bool = True) -> tuple[bool, str]:
        """
        Create a new opportunity in Salesforce.

        Args:
            data: Dictionary containing opportunity fields:
                - Name: Opportunity name (required)
                - Strategy__c: Strategy picklist value (required)
                - Security_Type__c: Security type picklist value (required)
                - StageName: Current stage (required)
                - CloseDate: Expected close date YYYY-MM-DD (required)
                - Amount: Deal amount (optional)
                - AccountId: Associated account ID (optional)
            _retry: Internal flag for retry logic (do not set manually)

        Returns:
            Tuple of (success: bool, opportunity_id: str)
            On failure, opportunity_id will be empty string
        """
        if not self.is_mock and self.sf:
            try:
                start_time = time.time()
                result = self.sf.Opportunity.create(data)
                duration_ms = (time.time() - start_time) * 1000

                opp_id = result.get("id", "")
                success = result.get("success", False)

                logger.log_workflow(
                    workflow_type="salesforce_create",
                    user_id="system",
                    action="create_opportunity",
                    success=success,
                    duration_ms=duration_ms,
                    details={
                        "opp_id": opp_id,
                        "opp_name": data.get("Name"),
                        "amount": data.get("Amount"),
                        "stage": data.get("StageName"),
                        "close_date": data.get("CloseDate")
                    }
                )
                logger.log_api_call(
                    service="salesforce",
                    method="create_opportunity",
                    duration_ms=duration_ms,
                    success=success,
                    context={"opp_id": opp_id, "opp_name": data.get("Name")}
                )
                metrics.record_api_call("salesforce", "create_opportunity", duration_ms, success)

                return (success, opp_id)
            except Exception as e:
                # Check if this is a session expiry error and we can retry
                error_name = type(e).__name__
                is_session_error = "ExpiredSession" in error_name or "INVALID_SESSION_ID" in str(e)

                if is_session_error and _retry and self._oauth_handler:
                    logger.info(
                        "Session expired, attempting to refresh token and retry",
                        service="salesforce"
                    )
                    if self._refresh_token_if_needed():
                        # Retry the operation once with the new token
                        return self.create_opportunity(data, _retry=False)

                logger.log_error(e, context={
                    "service": "salesforce",
                    "method": "create_opportunity",
                    "data": data
                })
                metrics.record_error("salesforce", error_name)
                return (False, "")
        else:
            # Mock mode - generate a fake ID
            import uuid
            mock_id = f"006xx{uuid.uuid4().hex[:12].upper()}"

            logger.info(
                f"Mock: Created opportunity '{data.get('Name')}' with ID {mock_id}",
                service="salesforce",
                mode="mock",
                opp_id=mock_id,
                opp_name=data.get("Name"),
                amount=data.get("Amount"),
                stage=data.get("StageName"),
                close_date=data.get("CloseDate")
            )
            return (True, mock_id)

    def search_accounts(self, company_name: str) -> list[dict]:
        """
        Search for accounts by company name.

        Args:
            company_name: The company name to search for

        Returns:
            List of account dictionaries with Id, Name, Industry, Website
        """
        if not self.is_mock and self.sf:
            try:
                start_time = time.time()
                query = f"SELECT Id, Name, Industry, Website, Phone, BillingCity, BillingState FROM Account WHERE Name LIKE '%{company_name}%' LIMIT 5"
                result = self.sf.query(query)
                duration_ms = (time.time() - start_time) * 1000

                accounts = []
                for record in result.get("records", []):
                    accounts.append({
                        "Id": record.get("Id"),
                        "Name": record.get("Name"),
                        "Industry": record.get("Industry"),
                        "Website": record.get("Website"),
                        "Phone": record.get("Phone"),
                        "BillingCity": record.get("BillingCity"),
                        "BillingState": record.get("BillingState"),
                    })

                logger.log_api_call(
                    service="salesforce",
                    method="search_accounts",
                    duration_ms=duration_ms,
                    success=True,
                    context={"company_name": company_name, "results_count": len(accounts)}
                )
                metrics.record_api_call("salesforce", "search_accounts", duration_ms, True)

                return accounts
            except Exception as e:
                logger.log_error(e, context={
                    "service": "salesforce",
                    "method": "search_accounts",
                    "company_name": company_name
                })
                metrics.record_error("salesforce", type(e).__name__)
                return self._mock_search_accounts(company_name)
        else:
            return self._mock_search_accounts(company_name)

    def _mock_search_accounts(self, company_name: str) -> list[dict]:
        """Mock account search for testing."""
        mock_accounts = [
            {
                "Id": "001xx000001234AAA",
                "Name": "Acme Corp",
                "Industry": "Technology",
                "Website": "https://acme.example.com",
                "Phone": "(555) 123-4567",
                "BillingCity": "San Francisco",
                "BillingState": "CA",
            },
            {
                "Id": "001xx000001234BBB",
                "Name": "TechStart Inc",
                "Industry": "Software",
                "Website": "https://techstart.example.com",
                "Phone": "(555) 987-6543",
                "BillingCity": "Austin",
                "BillingState": "TX",
            },
            {
                "Id": "001xx000001234CCC",
                "Name": "Global Systems",
                "Industry": "Consulting",
                "Website": "https://globalsystems.example.com",
                "Phone": "(555) 456-7890",
                "BillingCity": "New York",
                "BillingState": "NY",
            },
        ]

        company_lower = company_name.lower()
        return [acc for acc in mock_accounts if company_lower in acc["Name"].lower()]

    def search_contacts(self, company_name: str = None, account_id: str = None) -> list[dict]:
        """
        Search for contacts by company name or account ID.

        Args:
            company_name: Company name to search for
            account_id: Salesforce account ID

        Returns:
            List of contact dictionaries
        """
        if not self.is_mock and self.sf:
            try:
                start_time = time.time()

                if account_id:
                    query = f"SELECT Id, Name, Title, Email, Phone FROM Contact WHERE AccountId = '{account_id}' LIMIT 10"
                else:
                    query = f"SELECT Id, Name, Title, Email, Phone, Account.Name FROM Contact WHERE Account.Name LIKE '%{company_name}%' LIMIT 10"

                result = self.sf.query(query)
                duration_ms = (time.time() - start_time) * 1000

                contacts = []
                for record in result.get("records", []):
                    contacts.append({
                        "Id": record.get("Id"),
                        "Name": record.get("Name"),
                        "Title": record.get("Title"),
                        "Email": record.get("Email"),
                        "Phone": record.get("Phone"),
                    })

                logger.log_api_call(
                    service="salesforce",
                    method="search_contacts",
                    duration_ms=duration_ms,
                    success=True,
                    context={"company_name": company_name, "account_id": account_id, "results_count": len(contacts)}
                )
                metrics.record_api_call("salesforce", "search_contacts", duration_ms, True)

                return contacts
            except Exception as e:
                logger.log_error(e, context={
                    "service": "salesforce",
                    "method": "search_contacts",
                    "company_name": company_name,
                    "account_id": account_id
                })
                metrics.record_error("salesforce", type(e).__name__)
                return self._mock_search_contacts(company_name)
        else:
            return self._mock_search_contacts(company_name)

    def _mock_search_contacts(self, company_name: str = None) -> list[dict]:
        """Mock contact search for testing."""
        mock_contacts = [
            {
                "Id": "003xx000001234AAA",
                "Name": "John Smith",
                "Title": "VP of Sales",
                "Email": "john.smith@acme.example.com",
                "Phone": "(555) 111-2222",
                "AccountName": "Acme Corp",
            },
            {
                "Id": "003xx000001234BBB",
                "Name": "Jane Doe",
                "Title": "CTO",
                "Email": "jane.doe@acme.example.com",
                "Phone": "(555) 333-4444",
                "AccountName": "Acme Corp",
            },
            {
                "Id": "003xx000001234CCC",
                "Name": "Bob Wilson",
                "Title": "CEO",
                "Email": "bob@techstart.example.com",
                "Phone": "(555) 555-6666",
                "AccountName": "TechStart Inc",
            },
        ]

        if not company_name:
            return mock_contacts[:2]

        company_lower = company_name.lower()
        return [c for c in mock_contacts if company_lower in c.get("AccountName", "").lower()]
