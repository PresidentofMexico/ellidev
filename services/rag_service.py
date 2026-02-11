import os
import time
from typing import Dict, List, Optional
from services.vector_store import VectorStore
from services.ai_service import AIService
from services.logger import logger
from services.metrics import metrics


class RAGService:
    """
    Retrieval Augmented Generation (RAG) service.

    Combines vector search with LLM generation to provide context-aware answers.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        ai_service: Optional[AIService] = None,
        enabled: bool = None,
        top_k: int = None,
        relevance_threshold: float = 0.3,
    ):
        """
        Initialize RAG service.

        Args:
            vector_store: VectorStore instance (optional, creates new if not provided)
            ai_service: AIService instance (optional, creates new if not provided)
            enabled: Whether RAG is enabled (optional, reads from env var)
            top_k: Number of chunks to retrieve (optional, reads from env var)
            relevance_threshold: Minimum relevance score (0.0-1.0)
        """
        self.vector_store = vector_store or VectorStore()
        self.ai_service = ai_service or AIService()

        # Read configuration from environment
        self.enabled = (
            enabled
            if enabled is not None
            else os.environ.get("RAG_ENABLED", "true").lower() == "true"
        )
        self.top_k = top_k if top_k is not None else int(os.environ.get("RAG_TOP_K", "3"))
        self.relevance_threshold = relevance_threshold

        if self.enabled:
            logger.info(f"RAG service initialized (top_k={self.top_k})", top_k=self.top_k)
        else:
            logger.info("RAG service initialized but disabled", enabled=False)

    def answer_with_context(
        self, query: str, history: Optional[List[Dict]] = None, memories: Optional[List[Dict]] = None
    ) -> Dict:
        """
        RAG pipeline: Retrieve relevant context → Augment prompt → Generate answer.

        Args:
            query: User's question
            history: Optional conversation history (thread)
            memories: Optional past conversation summaries (semantic memory)

        Returns:
            Dictionary with structure:
            {
                "answer": "...",
                "sources": [{"content": "...", "score": 0.95, "document_id": "..."}],
                "memories_used": [{"summary": {...}, "relevance": 0.85}],
                "context_used": True/False
            }
        """
        start_time = time.time()

        if not self.enabled:
            # RAG disabled, fall back to regular AI response
            answer = self.ai_service.get_response(query, history=history)
            return {"answer": answer, "sources": [], "context_used": False}

        # Step 1: Retrieve relevant chunks
        search_start = time.time()
        retrieved_chunks = self.vector_store.search(query, top_k=self.top_k)
        search_duration_ms = (time.time() - search_start) * 1000

        # Filter by relevance threshold
        relevant_chunks = [
            chunk for chunk in retrieved_chunks if chunk["score"] >= self.relevance_threshold
        ]

        # Log RAG search
        relevance_scores = [chunk["score"] for chunk in relevant_chunks]
        search_types = list({chunk.get("metadata", {}).get("type", "document") for chunk in relevant_chunks})

        logger.log_rag_search(
            query=query,
            sources_found=len(relevant_chunks),
            relevance_scores=relevance_scores if relevance_scores else [0],
            duration_ms=search_duration_ms,
            search_types=search_types
        )
        metrics.record_rag_search(search_duration_ms, len(relevant_chunks))

        if not relevant_chunks:
            # No relevant context found, fall back to regular AI response
            logger.info("No relevant chunks found, falling back to direct AI", query=query[:100])
            answer = self.ai_service.get_response(query, history=history)
            return {
                "answer": answer,
                "sources": [],
                "context_used": False,
                "note": "No relevant knowledge base results found",
            }

        # Step 2: Augment prompt with retrieved context and memories
        augmented_prompt = self._build_rag_prompt(query, relevant_chunks, history, memories)

        # Step 3: Generate answer using AI service
        if not self.ai_service.is_mock and self.ai_service.connection:
            # Real Snowflake Cortex mode
            answer = self._generate_with_snowflake(augmented_prompt)
        else:
            # Mock mode
            answer = self._generate_mock_rag_response(query, relevant_chunks, memories)

        # Step 4: Format sources
        sources = [
            {
                "content": chunk["content"][:200] + "..."
                if len(chunk["content"]) > 200
                else chunk["content"],
                "score": chunk["score"],
                "document_id": chunk["document_id"],
                "chunk_id": chunk["chunk_id"],
                "metadata": chunk.get("metadata", {}),
            }
            for chunk in relevant_chunks
        ]

        # Step 5: Format memories
        memories_used = memories if memories else []

        # Log completion
        total_duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"RAG answer generated with {len(sources)} sources",
            query=query[:100],
            sources_count=len(sources),
            memories_count=len(memories_used),
            total_duration_ms=round(total_duration_ms, 2)
        )

        return {
            "answer": answer,
            "sources": sources,
            "memories_used": memories_used,
            "context_used": True
        }

    def _build_rag_prompt(
        self, query: str, chunks: List[Dict], history: Optional[List[Dict]], memories: Optional[List[Dict]] = None
    ) -> str:
        """
        Build augmented prompt with retrieved context and memories.

        Args:
            query: User's question
            chunks: Retrieved document chunks
            history: Optional conversation history
            memories: Optional past conversation summaries

        Returns:
            Augmented prompt string
        """
        system_prompt = "You are Elli, a helpful enterprise assistant."

        # Build context section from retrieved chunks
        context_section = "\n\nCONTEXT FROM KNOWLEDGE BASE:\n---\n"
        for i, chunk in enumerate(chunks, 1):
            context_section += f"[Chunk {i} - Relevance: {chunk['score']:.0%}]\n"
            context_section += f"{chunk['content']}\n\n"
        context_section += "---\n"

        # Build semantic memory section
        memory_section = ""
        if memories:
            memory_section = "\n\nPAST CONVERSATIONS (SEMANTIC MEMORY):\n"
            for i, memory in enumerate(memories, 1):
                summary = memory.get("summary", {})
                created_at = memory.get("created_at", "unknown")
                memory_section += f"[Memory {i} from {created_at[:10]}]\n"
                memory_section += f"Topic: {summary.get('topic', 'N/A')}\n"
                if summary.get("key_points"):
                    memory_section += "Key Points:\n"
                    for point in summary["key_points"][:3]:  # Limit to 3 points
                        memory_section += f"- {point}\n"
                memory_section += "\n"

        # Build conversation history section
        history_section = ""
        if history:
            history_section = "\n\nRECENT THREAD HISTORY:\n"
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_section += f"{role}: {msg['content']}\n"
            history_section += "\n"

        # Combine into full prompt
        instruction = (
            "\n\nINSTRUCTIONS:\n"
            "Use the context from the knowledge base to answer the user's question. "
            "If you reference past conversations from semantic memory, mention the date. "
            "If the context contains relevant information, cite it in your answer. "
            "If the context doesn't contain enough information, say so and provide what you can. "
            "Be specific and reference details from the context when applicable.\n"
        )

        full_prompt = (
            f"{system_prompt}{context_section}{memory_section}{history_section}{instruction}"
            f"\nUSER QUESTION: {query}\n\nANSWER:"
        )

        return full_prompt

    def _generate_with_snowflake(self, prompt: str) -> str:
        """
        Generate answer using Snowflake Cortex with RAG prompt.

        Args:
            prompt: Augmented prompt with context

        Returns:
            Generated answer
        """
        try:
            api_start = time.time()
            cursor = self.ai_service.connection.cursor()

            query = """
                SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', %s) as response
            """

            cursor.execute(query, (prompt,))
            result = cursor.fetchone()
            cursor.close()

            api_duration_ms = (time.time() - api_start) * 1000

            if result and result[0]:
                logger.log_api_call(
                    service="snowflake",
                    method="cortex.complete",
                    duration_ms=api_duration_ms,
                    success=True,
                    context={"model": "llama3-70b", "prompt_length": len(prompt)}
                )
                metrics.record_api_call("snowflake", "cortex.complete", api_duration_ms, True)
                return result[0]
            else:
                logger.log_api_call(
                    service="snowflake",
                    method="cortex.complete",
                    duration_ms=api_duration_ms,
                    success=False,
                    error="Empty response"
                )
                metrics.record_api_call("snowflake", "cortex.complete", api_duration_ms, False)
                return "I apologize, but I couldn't generate a response at this time."

        except Exception as e:
            logger.log_error(e, context={"service": "rag", "method": "_generate_with_snowflake"})
            metrics.record_error("rag", type(e).__name__)
            return "I encountered an error while processing your request."

    def _generate_mock_rag_response(self, query: str, chunks: List[Dict], memories: Optional[List[Dict]] = None) -> str:
        """
        Generate mock RAG response for testing without Snowflake.

        Args:
            query: User's question
            chunks: Retrieved chunks
            memories: Optional past conversation summaries

        Returns:
            Mock answer with context
        """
        # Extract key information from chunks
        chunk_excerpts = []
        for chunk in chunks[:2]:  # Use top 2 chunks
            # Get first 150 chars of content
            excerpt = chunk["content"][:150].strip()
            if len(chunk["content"]) > 150:
                excerpt += "..."
            chunk_excerpts.append(excerpt)

        # Build answer based on query type
        query_lower = query.lower()

        # Check if we have memory context to reference
        memory_context = ""
        if memories:
            memory = memories[0]
            summary = memory.get("summary", {})
            created_at = memory.get("created_at", "")[:10]
            memory_context = f"\n\nBased on our conversation from {created_at}, we discussed {summary.get('topic', 'this topic')}. "

        if "pricing" in query_lower or "cost" in query_lower or "payment" in query_lower:
            answer = (
                f"Based on our knowledge base{memory_context if memory_context else ''}:\n\n"
                f"• {chunk_excerpts[0] if chunk_excerpts else 'Standard tier starts at $49/user/month'}\n\n"
                "For detailed pricing information and custom enterprise quotes, "
                "please contact our sales team."
            )
        elif "how" in query_lower or "what" in query_lower:
            answer = (
                f"Based on the knowledge base{memory_context if memory_context else ''}:\n\n"
                f"{chunk_excerpts[0] if chunk_excerpts else 'Information found in our documentation.'}\n\n"
                "Let me know if you need more specific details!"
            )
        else:
            answer = (
                f"Based on relevant information from our knowledge base{memory_context if memory_context else ''}:\n\n"
                f"{chunk_excerpts[0] if chunk_excerpts else 'I found relevant information in our documentation.'}\n\n"
                "Is there anything specific you'd like to know more about?"
            )

        # Add mock mode indicator
        answer += (
            "\n\n*This is a context-aware RAG response from Elli's mock mode 🧠 - "
            "Connect to Snowflake Cortex for real AI insights!*"
        )

        return answer

    def should_use_rag(self, query: str) -> bool:
        """
        Determine if a query should use RAG or regular AI response.

        Args:
            query: User's question

        Returns:
            True if RAG should be used, False otherwise
        """
        query_lower = query.lower()

        # Keywords that suggest knowledge retrieval
        rag_keywords = [
            "what is",
            "what are",
            "how do",
            "how to",
            "tell me about",
            "explain",
            "describe",
            "pricing",
            "price",
            "cost",
            "payment",
            "product",
            "feature",
            "support",
            "policy",
            "documentation",
            "guide",
        ]

        # CRM/Salesforce keywords (Phase 5.3)
        crm_keywords = [
            "opportunity",
            "opportunities",
            "deal",
            "deals",
            "pipeline",
            "forecast",
            "account",
            "accounts",
            "customer",
            "customers",
            "client",
            "clients",
            "contact",
            "contacts",
            "who handles",
            "sales rep",
            "stage",
            "close date",
            "amount",
            "value",
        ]

        # Check if query contains RAG or CRM keywords
        all_keywords = rag_keywords + crm_keywords
        return any(keyword in query_lower for keyword in all_keywords)

    def get_stats(self) -> Dict:
        """
        Get RAG service statistics.

        Returns:
            Dictionary with stats
        """
        vector_stats = self.vector_store.get_stats()

        return {
            "enabled": self.enabled,
            "top_k": self.top_k,
            "relevance_threshold": self.relevance_threshold,
            "vector_store_mode": "mock" if self.vector_store.is_mock else "snowflake",
            "ai_service_mode": "mock" if self.ai_service.is_mock else "snowflake",
            "total_chunks": vector_stats.get("total_chunks", 0),
            "total_documents": vector_stats.get("total_documents", 0),
        }
