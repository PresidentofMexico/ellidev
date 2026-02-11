"""
Tests for services/rag_service.py

Tests the RAG (Retrieval Augmented Generation) service including
vector search, answer generation, and context building.
"""

import pytest
from unittest.mock import Mock, patch
from services.rag_service import RAGService


@pytest.fixture
def mock_vector_store(sample_rag_chunks):
    """Mock vector store that returns sample chunks"""
    store = Mock()
    store.search = Mock(return_value=sample_rag_chunks)
    store.is_mock = True
    return store


@pytest.fixture
def mock_ai_service():
    """Mock AI service"""
    service = Mock()
    service.is_mock = True
    service.connection = None
    service.get_response = Mock(return_value="Mock AI response")
    return service


@pytest.fixture
def rag_service(mock_vector_store, mock_ai_service, mock_env_no_credentials):
    """Create RAG service with mocked dependencies"""
    return RAGService(
        vector_store=mock_vector_store,
        ai_service=mock_ai_service,
        enabled=True,
        top_k=3
    )


class TestRAGService:
    """Tests for RAGService class"""

    def test_initialization(self, rag_service):
        """Test RAG service initializes correctly"""
        assert rag_service.enabled is True
        assert rag_service.top_k == 3

    def test_should_use_rag_with_rag_keywords(self, rag_service):
        """Test RAG detection with knowledge base keywords"""
        assert rag_service.should_use_rag("What are our payment terms?")
        assert rag_service.should_use_rag("How do I configure the product?")
        assert rag_service.should_use_rag("Tell me about our pricing")

    def test_should_use_rag_with_crm_keywords(self, rag_service):
        """Test RAG detection with CRM keywords"""
        assert rag_service.should_use_rag("What opportunities are open?")
        assert rag_service.should_use_rag("Show me contacts at Acme Corp")
        assert rag_service.should_use_rag("What's in my pipeline?")

    def test_should_not_use_rag_for_general_queries(self, rag_service):
        """Test that general queries don't trigger RAG"""
        assert not rag_service.should_use_rag("Hello!")
        assert not rag_service.should_use_rag("How are you?")
        assert not rag_service.should_use_rag("Thanks!")

    def test_answer_with_context_returns_sources(self, rag_service):
        """Test that answer_with_context returns sources"""
        result = rag_service.answer_with_context("What are payment terms?")

        assert "answer" in result
        assert "sources" in result
        assert "context_used" in result
        assert result["context_used"] is True
        assert len(result["sources"]) > 0

    def test_answer_with_context_filters_by_relevance(self, rag_service, mock_vector_store):
        """Test that low relevance chunks are filtered out"""
        # Add low relevance chunk
        low_relevance_chunks = [
            {"content": "Low relevance", "score": 0.2, "document_id": "test", "chunk_id": "1", "metadata": {}}
        ]
        mock_vector_store.search = Mock(return_value=low_relevance_chunks)

        result = rag_service.answer_with_context("Test query")

        # Should fall back to direct AI since no chunks meet threshold
        assert result["context_used"] is False

    def test_answer_with_conversation_history(self, rag_service, sample_conversation_history):
        """Test answer generation with conversation history"""
        result = rag_service.answer_with_context(
            "What did we discuss?",
            history=sample_conversation_history
        )

        assert result is not None
        assert "answer" in result

    def test_answer_with_memories(self, rag_service, sample_semantic_memories):
        """Test answer generation with semantic memories"""
        result = rag_service.answer_with_context(
            "What did we discuss about Acme Corp?",
            memories=sample_semantic_memories
        )

        assert result is not None
        assert "memories_used" in result
        assert len(result["memories_used"]) == 1

    def test_mock_rag_response_generation(self, rag_service):
        """Test mock RAG response includes context"""
        result = rag_service.answer_with_context("What is pricing?")

        assert "answer" in result
        assert "mock mode" in result["answer"].lower()

    def test_rag_disabled_falls_back_to_ai(self, mock_vector_store, mock_ai_service):
        """Test that disabled RAG falls back to AI service"""
        rag = RAGService(
            vector_store=mock_vector_store,
            ai_service=mock_ai_service,
            enabled=False
        )

        result = rag.answer_with_context("Test query")

        assert result["context_used"] is False
        mock_ai_service.get_response.assert_called_once()

    def test_get_stats(self, rag_service):
        """Test RAG service statistics"""
        stats = rag_service.get_stats()

        assert "enabled" in stats
        assert "top_k" in stats
        assert stats["enabled"] is True
        assert stats["top_k"] == 3


@pytest.mark.unit
class TestRAGServiceMethods:
    """Tests for specific RAG service methods"""

    def test_build_rag_prompt_includes_context(self, rag_service, sample_rag_chunks):
        """Test that RAG prompt includes retrieved context"""
        prompt = rag_service._build_rag_prompt(
            "What are payment terms?",
            sample_rag_chunks[:2],
            None,
            None
        )

        assert "payment terms" in prompt.lower()
        assert "context from knowledge base" in prompt.lower()
        assert "Net 30" in prompt

    def test_build_rag_prompt_includes_history(self, rag_service, sample_rag_chunks, sample_conversation_history):
        """Test that RAG prompt includes conversation history"""
        prompt = rag_service._build_rag_prompt(
            "What else?",
            sample_rag_chunks[:1],
            sample_conversation_history,
            None
        )

        assert "recent thread history" in prompt.lower()
        assert "Acme Corp" in prompt

    def test_build_rag_prompt_includes_memories(self, rag_service, sample_rag_chunks, sample_semantic_memories):
        """Test that RAG prompt includes semantic memories"""
        prompt = rag_service._build_rag_prompt(
            "What did we discuss?",
            sample_rag_chunks[:1],
            None,
            sample_semantic_memories
        )

        assert "semantic memory" in prompt.lower() or "past conversations" in prompt.lower()
        assert "renewal" in prompt.lower()
