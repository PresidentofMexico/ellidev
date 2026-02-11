"""
Shared pytest fixtures for Elli tests.

Provides common test fixtures for mocking services,
creating test data, and setting up test environments.
"""

import pytest
import os
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_env_no_credentials(monkeypatch):
    """Remove all service credentials to force mock mode"""
    monkeypatch.delenv("SNOWFLAKE_USER", raising=False)
    monkeypatch.delenv("SNOWFLAKE_PASSWORD", raising=False)
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    monkeypatch.delenv("SF_USERNAME", raising=False)
    monkeypatch.delenv("SF_PASSWORD", raising=False)
    monkeypatch.delenv("SF_SECURITY_TOKEN", raising=False)


@pytest.fixture
def mock_snowflake_connection():
    """Create mock Snowflake connection"""
    connection = Mock()
    cursor = Mock()

    # Mock cursor methods
    cursor.execute = Mock()
    cursor.fetchone = Mock(return_value=("Mock AI response",))
    cursor.fetchall = Mock(return_value=[])
    cursor.close = Mock()

    connection.cursor = Mock(return_value=cursor)

    return connection


@pytest.fixture
def mock_salesforce_client():
    """Create mock Salesforce client"""
    sf = Mock()

    # Mock opportunity search
    sf.query = Mock(return_value={
        "records": [
            {
                "Id": "006xx000001234AAA",
                "Name": "Acme Corp - Q1 Expansion",
                "StageName": "Discovery",
                "CloseDate": "2026-03-31"
            }
        ]
    })

    # Mock opportunity update
    sf.Opportunity = Mock()
    sf.Opportunity.update = Mock()

    return sf


@pytest.fixture
def sample_opportunity():
    """Sample opportunity data"""
    return {
        "Id": "006xx000001234AAA",
        "Name": "Acme Corp - Q1 Expansion",
        "StageName": "Discovery",
        "CloseDate": "2026-03-31",
        "Amount": 250000,
        "AccountId": "001xx000000123AAA"
    }


@pytest.fixture
def sample_opportunities_list():
    """Sample list of opportunities"""
    return [
        {
            "Id": "006xx000001234AAA",
            "Name": "Acme Corp - Q1 Expansion",
            "StageName": "Discovery",
            "CloseDate": "2026-03-31"
        },
        {
            "Id": "006xx000001234BBB",
            "Name": "Acme Corp - Enterprise Deal",
            "StageName": "Negotiation",
            "CloseDate": "2026-04-15"
        }
    ]


@pytest.fixture
def sample_rag_chunks():
    """Sample RAG chunks for testing"""
    return [
        {
            "chunk_id": "doc1_chunk1",
            "document_id": "product_info",
            "content": "Our payment terms are Net 30 for established customers.",
            "score": 0.95,
            "metadata": {"type": "document", "page": 1}
        },
        {
            "chunk_id": "doc2_chunk1",
            "document_id": "sales_playbook",
            "content": "Early payment discount: 2% if paid within 10 days.",
            "score": 0.87,
            "metadata": {"type": "document", "page": 5}
        },
        {
            "chunk_id": "sf_opp_1",
            "document_id": "salesforce_opportunities",
            "content": "Opportunity: Acme Corp Renewal - $250,000\nStage: Negotiation\nClose Date: 2026-02-15",
            "score": 0.92,
            "metadata": {
                "type": "salesforce_record",
                "object_type": "Opportunity",
                "record_id": "006xx",
                "stage": "Negotiation",
                "amount": 250000
            }
        }
    ]


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history"""
    return [
        {"role": "user", "content": "Who is Acme Corp?"},
        {"role": "assistant", "content": "Acme Corp is one of our top customers..."},
        {"role": "user", "content": "What opportunities do they have?"}
    ]


@pytest.fixture
def sample_semantic_memories():
    """Sample semantic memory entries"""
    return [
        {
            "chunk_id": "memory_1",
            "content": "Discussion about Acme Corp renewal opportunity",
            "created_at": "2026-01-07T10:30:00Z",
            "summary": {
                "topic": "Acme Corp Q4 renewal discussion",
                "entities": ["Acme Corp", "Enterprise tier"],
                "key_points": [
                    "Customer interested in upgrading to Enterprise tier",
                    "Renewal opportunity valued at $250K"
                ],
                "conversation_type": "deal_inquiry"
            },
            "metadata": {
                "type": "conversation_memory",
                "user_id": "U12345",
                "thread_id": "1234567890.123456"
            },
            "score": 0.89
        }
    ]


@pytest.fixture
def disable_logging(monkeypatch):
    """Disable logging for tests to reduce noise"""
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")


@pytest.fixture
def disable_metrics(monkeypatch):
    """Disable metrics for tests"""
    monkeypatch.setenv("ENABLE_METRICS", "false")
