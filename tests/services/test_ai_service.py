"""
Tests for services/ai_service.py

Tests the AI service including Snowflake Cortex integration,
mock responses, and conversation history handling.
"""

import pytest
from unittest.mock import Mock, patch
from services.ai_service import AIService


class TestAIService:
    """Tests for AIService class"""

    def test_initialization_mock_mode_no_credentials(self, mock_env_no_credentials):
        """Test AI service initializes in mock mode without credentials"""
        service = AIService()

        assert service.is_mock is True
        assert service.connection is None

    def test_get_response_mock_mode(self, mock_env_no_credentials):
        """Test get_response in mock mode"""
        service = AIService()

        response = service.get_response("What is our revenue?")

        assert response is not None
        assert len(response) > 0
        assert "mock" in response.lower()

    def test_get_response_with_conversation_history(self, mock_env_no_credentials, sample_conversation_history):
        """Test get_response with conversation history"""
        service = AIService()

        response = service.get_response(
            "What else?",
            history=sample_conversation_history
        )

        assert response is not None

    def test_mock_response_context_awareness(self, mock_env_no_credentials):
        """Test that mock responses use conversation context"""
        service = AIService()

        history = [
            {"role": "user", "content": "Tell me about Acme Corp"},
            {"role": "assistant", "content": "Acme Corp is a major customer"}
        ]

        response = service.get_response("Update it to Closed Won", history=history)

        assert "Acme Corp" in response

    def test_mock_response_keyword_detection(self, mock_env_no_credentials):
        """Test that mock responses detect keywords"""
        service = AIService()

        revenue_response = service.get_response("What is our revenue?")
        customer_response = service.get_response("Tell me about customers")
        help_response = service.get_response("What can you do?")

        assert "revenue" in revenue_response.lower()
        assert "customer" in customer_response.lower()
        assert "help" in help_response.lower() or "can" in help_response.lower()

    @patch('snowflake.connector.connect')
    def test_get_response_real_mode(self, mock_connect, mock_snowflake_connection):
        """Test get_response with real Snowflake connection"""
        mock_connect.return_value = mock_snowflake_connection

        service = AIService(
            user="test",
            password="pass",
            account="account",
            warehouse="warehouse"
        )

        response = service.get_response("Test query")

        assert service.is_mock is False
        assert response == "Mock AI response"

    def test_close_connection(self, mock_env_no_credentials):
        """Test close method"""
        service = AIService()

        # Should not raise error even without connection
        service.close()


@pytest.mark.unit
class TestAIServiceMockResponses:
    """Tests for AI service mock response generation"""

    def test_mock_response_for_revenue_query(self, mock_env_no_credentials):
        """Test mock response for revenue queries"""
        service = AIService()

        response = service._get_mock_response("What is Q3 revenue?")

        assert "revenue" in response.lower() or "Q3" in response

    def test_mock_response_for_customer_query(self, mock_env_no_credentials):
        """Test mock response for customer queries"""
        service = AIService()

        response = service._get_mock_response("Tell me about customers")

        assert "customer" in response.lower()

    def test_mock_response_includes_mock_indicator(self, mock_env_no_credentials):
        """Test that mock responses indicate mock mode"""
        service = AIService()

        response = service._get_mock_response("Any question")

        assert "mock" in response.lower()
        assert "Snowflake Cortex" in response or "snowflake" in response.lower()
