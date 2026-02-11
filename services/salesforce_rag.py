import os
from typing import Dict, List, Optional
from datetime import datetime
from services.logger import logger


class SalesforceRAG:
    """
    Salesforce RAG integration service.

    Fetches Salesforce data (opportunities, accounts, contacts) and formats
    them as vector store chunks for semantic search.
    """

    def __init__(self, sf_client=None, vector_store=None):
        """
        Initialize Salesforce RAG service.

        Args:
            sf_client: SalesforceClient instance (optional, creates new if not provided)
            vector_store: VectorStore instance (optional, creates new if not provided)
        """
        from services.sf_client import SalesforceClient
        from services.vector_store import VectorStore

        self.sf_client = sf_client or SalesforceClient()
        self.vector_store = vector_store or VectorStore()

        # Configuration
        self.enabled = (
            os.environ.get("SALESFORCE_RAG_ENABLED", "true").lower() == "true"
        )
        self.objects = os.environ.get(
            "SALESFORCE_RAG_OBJECTS", "opportunities,accounts,contacts"
        ).split(",")
        self.limit = int(os.environ.get("SALESFORCE_RAG_LIMIT", "100"))

        if self.enabled:
            logger.info(f"Salesforce RAG initialized (objects={self.objects}, limit={self.limit})", service="salesforce_rag")
        else:
            logger.warning("Salesforce RAG disabled (SALESFORCE_RAG_ENABLED=false)", service="salesforce_rag")

    def fetch_opportunities(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch recent opportunities from Salesforce.

        Args:
            limit: Maximum number of records (optional, uses config default)

        Returns:
            List of opportunity dictionaries
        """
        limit = limit or self.limit

        if not self.sf_client.is_mock and self.sf_client.sf:
            # Real Salesforce query
            query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate,
                       Description, AccountId, Account.Name,
                       OwnerId, Owner.Name, LastModifiedDate
                FROM Opportunity
                ORDER BY LastModifiedDate DESC
                LIMIT {limit}
            """
            try:
                result = self.sf_client.sf.query(query)
                return result.get("records", [])
            except Exception as e:
                logger.error(f"Error fetching opportunities: {e}", service="salesforce_rag", error=str(e))
                return self._mock_opportunities(limit)
        else:
            # Mock mode
            return self._mock_opportunities(limit)

    def fetch_accounts(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch accounts from Salesforce.

        Args:
            limit: Maximum number of records (optional, uses config default)

        Returns:
            List of account dictionaries
        """
        limit = limit or self.limit

        if not self.sf_client.is_mock and self.sf_client.sf:
            # Real Salesforce query
            query = f"""
                SELECT Id, Name, Industry, Description, Website,
                       NumberOfEmployees, Phone, BillingCity,
                       BillingState, LastModifiedDate
                FROM Account
                ORDER BY LastModifiedDate DESC
                LIMIT {limit}
            """
            try:
                result = self.sf_client.sf.query(query)
                return result.get("records", [])
            except Exception as e:
                logger.error(f"Error fetching accounts: {e}", service="salesforce_rag", error=str(e))
                return self._mock_accounts(limit)
        else:
            # Mock mode
            return self._mock_accounts(limit)

    def fetch_contacts(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch contacts from Salesforce.

        Args:
            limit: Maximum number of records (optional, uses config default)

        Returns:
            List of contact dictionaries
        """
        limit = limit or self.limit

        if not self.sf_client.is_mock and self.sf_client.sf:
            # Real Salesforce query
            query = f"""
                SELECT Id, Name, Title, Email, Phone, AccountId,
                       Account.Name, OwnerId, Owner.Name,
                       LastModifiedDate
                FROM Contact
                WHERE Email != null
                ORDER BY LastModifiedDate DESC
                LIMIT {limit}
            """
            try:
                result = self.sf_client.sf.query(query)
                return result.get("records", [])
            except Exception as e:
                logger.error(f"Error fetching contacts: {e}", service="salesforce_rag", error=str(e))
                return self._mock_contacts(limit)
        else:
            # Mock mode
            return self._mock_contacts(limit)

    def format_opportunity_chunk(self, opp: Dict) -> Dict:
        """
        Format Salesforce opportunity as vector store chunk.

        Args:
            opp: Opportunity record from Salesforce

        Returns:
            Chunk dictionary for vector store
        """
        # Extract fields safely
        opp_id = opp.get("Id", "unknown")
        name = opp.get("Name", "Untitled Opportunity")
        stage = opp.get("StageName", "Unknown")
        amount = opp.get("Amount", 0)
        close_date = opp.get("CloseDate", "Unknown")
        description = opp.get("Description", "")
        account_name = opp.get("Account", {}).get("Name", "Unknown Account")
        owner_name = opp.get("Owner", {}).get("Name", "Unknown Owner")
        last_modified = opp.get("LastModifiedDate", datetime.now().isoformat())

        # Build searchable content
        content = f"""Opportunity: {name}
Account: {account_name}
Stage: {stage}
Amount: ${amount:,.2f} USD
Close Date: {close_date}
Owner: {owner_name}
"""
        if description:
            content += f"Description: {description}\n"

        # Build metadata
        metadata = {
            "type": "salesforce_record",
            "object_type": "Opportunity",
            "record_id": opp_id,
            "last_modified": last_modified,
            "stage": stage,
            "amount": amount,
            "close_date": close_date,
            "account_name": account_name,
            "owner_name": owner_name
        }

        return {
            "chunk_id": f"sf_opportunity_{opp_id}",
            "document_id": "salesforce_opportunities",
            "content": content.strip(),
            "metadata": metadata
        }

    def format_account_chunk(self, account: Dict) -> Dict:
        """
        Format Salesforce account as vector store chunk.

        Args:
            account: Account record from Salesforce

        Returns:
            Chunk dictionary for vector store
        """
        # Extract fields safely
        account_id = account.get("Id", "unknown")
        name = account.get("Name", "Untitled Account")
        industry = account.get("Industry", "Unknown")
        description = account.get("Description", "")
        website = account.get("Website", "")
        employees = account.get("NumberOfEmployees", 0)
        phone = account.get("Phone", "")
        city = account.get("BillingCity", "")
        state = account.get("BillingState", "")
        last_modified = account.get("LastModifiedDate", datetime.now().isoformat())

        # Build searchable content
        content = f"""Account: {name}
Industry: {industry}
"""
        if employees:
            content += f"Employees: {employees}\n"
        if website:
            content += f"Website: {website}\n"
        if phone:
            content += f"Phone: {phone}\n"
        if city or state:
            location = f"{city}, {state}" if city and state else (city or state)
            content += f"Location: {location}\n"
        if description:
            content += f"Description: {description}\n"

        # Build metadata
        metadata = {
            "type": "salesforce_record",
            "object_type": "Account",
            "record_id": account_id,
            "last_modified": last_modified,
            "industry": industry,
            "employees": employees,
            "website": website
        }

        return {
            "chunk_id": f"sf_account_{account_id}",
            "document_id": "salesforce_accounts",
            "content": content.strip(),
            "metadata": metadata
        }

    def format_contact_chunk(self, contact: Dict) -> Dict:
        """
        Format Salesforce contact as vector store chunk.

        Args:
            contact: Contact record from Salesforce

        Returns:
            Chunk dictionary for vector store
        """
        # Extract fields safely
        contact_id = contact.get("Id", "unknown")
        name = contact.get("Name", "Untitled Contact")
        title = contact.get("Title", "")
        email = contact.get("Email", "")
        phone = contact.get("Phone", "")
        account_name = contact.get("Account", {}).get("Name", "Unknown Account")
        owner_name = contact.get("Owner", {}).get("Name", "Unknown Owner")
        last_modified = contact.get("LastModifiedDate", datetime.now().isoformat())

        # Build searchable content
        content = f"""Contact: {name}
Account: {account_name}
"""
        if title:
            content += f"Title: {title}\n"
        if email:
            content += f"Email: {email}\n"
        if phone:
            content += f"Phone: {phone}\n"
        content += f"Owner: {owner_name}\n"

        # Build metadata
        metadata = {
            "type": "salesforce_record",
            "object_type": "Contact",
            "record_id": contact_id,
            "last_modified": last_modified,
            "title": title,
            "email": email,
            "phone": phone,
            "account_name": account_name,
            "owner_name": owner_name
        }

        return {
            "chunk_id": f"sf_contact_{contact_id}",
            "document_id": "salesforce_contacts",
            "content": content.strip(),
            "metadata": metadata
        }

    def ingest_salesforce_data(
        self,
        objects: Optional[List[str]] = None,
        refresh: bool = False
    ) -> Dict:
        """
        Ingest Salesforce data into vector store.

        Args:
            objects: List of object types to ingest (optional, uses config default)
            refresh: If True, clear existing Salesforce data first

        Returns:
            Statistics dictionary with counts per object
        """
        objects = objects or self.objects
        stats = {
            "opportunities": 0,
            "accounts": 0,
            "contacts": 0,
            "total": 0,
            "errors": []
        }

        logger.info(f"Ingesting Salesforce data: {objects}", service="salesforce_rag", objects=objects)

        # Refresh: Clear existing Salesforce chunks (future implementation)
        if refresh:
            logger.warning("Refresh not yet implemented - data will be added incrementally", service="salesforce_rag")

        all_chunks = []

        # Ingest Opportunities
        if "opportunities" in objects:
            logger.info("Fetching opportunities...", service="salesforce_rag")
            opportunities = self.fetch_opportunities()
            for opp in opportunities:
                try:
                    chunk = self.format_opportunity_chunk(opp)
                    all_chunks.append(chunk)
                    stats["opportunities"] += 1
                except Exception as e:
                    stats["errors"].append(f"Opportunity {opp.get('Id')}: {e}")

        # Ingest Accounts
        if "accounts" in objects:
            logger.info("Fetching accounts...", service="salesforce_rag")
            accounts = self.fetch_accounts()
            for account in accounts:
                try:
                    chunk = self.format_account_chunk(account)
                    all_chunks.append(chunk)
                    stats["accounts"] += 1
                except Exception as e:
                    stats["errors"].append(f"Account {account.get('Id')}: {e}")

        # Ingest Contacts
        if "contacts" in objects:
            logger.info("Fetching contacts...", service="salesforce_rag")
            contacts = self.fetch_contacts()
            for contact in contacts:
                try:
                    chunk = self.format_contact_chunk(contact)
                    all_chunks.append(chunk)
                    stats["contacts"] += 1
                except Exception as e:
                    stats["errors"].append(f"Contact {contact.get('Id')}: {e}")

        # Store in vector store
        if all_chunks:
            logger.info(f"Storing {len(all_chunks)} chunks in vector store...", service="salesforce_rag", chunk_count=len(all_chunks))
            success = self.vector_store.ingest_documents(all_chunks)

            if success:
                stats["total"] = len(all_chunks)
                logger.info(f"Successfully ingested {stats['total']} Salesforce records", service="salesforce_rag", total=stats['total'])
            else:
                logger.error("Failed to ingest Salesforce data", service="salesforce_rag")
                stats["errors"].append("Vector store ingestion failed")
        else:
            logger.warning("No chunks to ingest", service="salesforce_rag")

        return stats

    # Mock data generators
    def _mock_opportunities(self, limit: int) -> List[Dict]:
        """Generate mock opportunity data."""
        mock_opps = [
            {
                "Id": "006xx000001",
                "Name": "Acme Corp Renewal",
                "StageName": "Negotiation",
                "Amount": 250000,
                "CloseDate": "2026-02-15",
                "Description": "Annual renewal for Acme Corp with expanded user count",
                "Account": {"Name": "Acme Corp"},
                "Owner": {"Name": "Sarah Johnson"},
                "LastModifiedDate": "2026-01-14T10:00:00.000+0000"
            },
            {
                "Id": "006xx000002",
                "Name": "TechStart Expansion",
                "StageName": "Proposal",
                "Amount": 180000,
                "CloseDate": "2026-02-28",
                "Description": "Expanding TechStart from Standard to Enterprise tier",
                "Account": {"Name": "TechStart Inc"},
                "Owner": {"Name": "Michael Chen"},
                "LastModifiedDate": "2026-01-13T15:30:00.000+0000"
            },
            {
                "Id": "006xx000003",
                "Name": "Global Systems New Contract",
                "StageName": "Discovery",
                "Amount": 420000,
                "CloseDate": "2026-03-10",
                "Description": "New enterprise contract with custom integrations",
                "Account": {"Name": "Global Systems"},
                "Owner": {"Name": "Sarah Johnson"},
                "LastModifiedDate": "2026-01-12T09:15:00.000+0000"
            }
        ]
        return mock_opps[:limit]

    def _mock_accounts(self, limit: int) -> List[Dict]:
        """Generate mock account data."""
        mock_accounts = [
            {
                "Id": "001xx000001",
                "Name": "Acme Corp",
                "Industry": "Technology",
                "Description": "Leading technology company specializing in enterprise software",
                "Website": "https://acmecorp.example.com",
                "NumberOfEmployees": 5000,
                "Phone": "(555) 123-4567",
                "BillingCity": "San Francisco",
                "BillingState": "CA",
                "LastModifiedDate": "2026-01-14T10:00:00.000+0000"
            },
            {
                "Id": "001xx000002",
                "Name": "TechStart Inc",
                "Industry": "Technology",
                "Description": "Fast-growing startup in the AI/ML space",
                "Website": "https://techstart.io",
                "NumberOfEmployees": 250,
                "Phone": "(555) 234-5678",
                "BillingCity": "Austin",
                "BillingState": "TX",
                "LastModifiedDate": "2026-01-13T15:30:00.000+0000"
            },
            {
                "Id": "001xx000003",
                "Name": "Global Systems",
                "Industry": "Manufacturing",
                "Description": "Global manufacturing company with operations in 50 countries",
                "Website": "https://globalsystems.example.com",
                "NumberOfEmployees": 50000,
                "Phone": "(555) 345-6789",
                "BillingCity": "Chicago",
                "BillingState": "IL",
                "LastModifiedDate": "2026-01-12T09:15:00.000+0000"
            }
        ]
        return mock_accounts[:limit]

    def _mock_contacts(self, limit: int) -> List[Dict]:
        """Generate mock contact data."""
        mock_contacts = [
            {
                "Id": "003xx000001",
                "Name": "Sarah Johnson",
                "Title": "VP of Operations",
                "Email": "sjohnson@acmecorp.example.com",
                "Phone": "(555) 123-4501",
                "Account": {"Name": "Acme Corp"},
                "Owner": {"Name": "Sarah Johnson"},
                "LastModifiedDate": "2026-01-14T10:00:00.000+0000"
            },
            {
                "Id": "003xx000002",
                "Name": "Michael Chen",
                "Title": "VP of Engineering",
                "Email": "mchen@techstart.io",
                "Phone": "(555) 234-5601",
                "Account": {"Name": "TechStart Inc"},
                "Owner": {"Name": "Michael Chen"},
                "LastModifiedDate": "2026-01-13T15:30:00.000+0000"
            },
            {
                "Id": "003xx000003",
                "Name": "Jennifer Martinez",
                "Title": "CTO",
                "Email": "jmartinez@globalsystems.example.com",
                "Phone": "(555) 345-6701",
                "Account": {"Name": "Global Systems"},
                "Owner": {"Name": "Sarah Johnson"},
                "LastModifiedDate": "2026-01-12T09:15:00.000+0000"
            }
        ]
        return mock_contacts[:limit]

    def get_stats(self) -> Dict:
        """
        Get Salesforce RAG statistics.

        Returns:
            Dictionary with stats
        """
        vector_stats = self.vector_store.get_stats()

        return {
            "enabled": self.enabled,
            "objects": self.objects,
            "limit": self.limit,
            "sf_mode": "mock" if self.sf_client.is_mock else "real",
            "vector_store_mode": "mock" if self.vector_store.is_mock else "snowflake",
            "total_chunks": vector_stats.get("total_chunks", 0)
        }
