import os
import json
import re
import math
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from services.logger import logger


class SemanticMemory:
    """
    Semantic memory service for storing and retrieving conversation summaries.

    Enables long-term memory beyond thread history by summarizing conversations
    and storing them in the vector store for later retrieval.
    """

    def __init__(self, vector_store=None, ai_service=None):
        """
        Initialize semantic memory service.

        Args:
            vector_store: VectorStore instance (optional, creates new if not provided)
            ai_service: AIService instance (optional, creates new if not provided)
        """
        from services.vector_store import VectorStore
        from services.ai_service import AIService

        self.vector_store = vector_store or VectorStore()
        self.ai_service = ai_service or AIService()

        # Configuration
        self.enabled = (
            os.environ.get("SEMANTIC_MEMORY_ENABLED", "true").lower() == "true"
        )
        self.summary_interval = int(os.environ.get("MEMORY_SUMMARY_INTERVAL", "10"))
        self.search_days_back = int(os.environ.get("MEMORY_SEARCH_DAYS_BACK", "30"))
        self.top_k = int(os.environ.get("MEMORY_TOP_K", "2"))

        if self.enabled:
            logger.info(f"Semantic memory initialized (interval={self.summary_interval})", service="semantic_memory")
        else:
            logger.warning("Semantic memory disabled (SEMANTIC_MEMORY_ENABLED=false)", service="semantic_memory")

    def should_summarize(self, thread_message_count: int) -> bool:
        """
        Check if we should create a summary.

        Args:
            thread_message_count: Number of messages in thread

        Returns:
            True if should summarize
        """
        return (
            self.enabled
            and thread_message_count > 0
            and thread_message_count % self.summary_interval == 0
        )

    def generate_summary(self, messages: List[Dict], context: Dict) -> Dict:
        """
        Generate structured summary of conversation.

        Args:
            messages: List of message dicts [{"role": "user/assistant", "content": "..."}]
            context: {"user_id": "...", "channel_id": "...", "thread_ts": "...", "timestamp": "..."}

        Returns:
            {
                "summary": "Conversation summary text",
                "topic": "Main topic",
                "entities": ["Entity1", "Entity2"],
                "key_points": ["Point 1", "Point 2"],
                "conversation_type": "category"
            }
        """
        if not self.ai_service.is_mock and self.ai_service.connection:
            return self._generate_summary_with_llm(messages, context)
        else:
            return self._generate_mock_summary(messages, context)

    def _build_summary_prompt(self, messages: List[Dict]) -> str:
        """Build prompt for LLM summarization."""
        conversation_text = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        prompt = f"""You are a conversation summarizer. Generate a structured summary of this conversation.

CONVERSATION:
{conversation_text}

INSTRUCTIONS:
1. Summarize the main topic in one sentence
2. Extract key entities (companies, people, dates, amounts, products)
3. List 3-5 key points from the conversation
4. Categorize the conversation type (deal_inquiry, product_question, support_request, policy_question, general)

FORMAT YOUR RESPONSE AS JSON:
{{
    "topic": "Brief one-sentence summary",
    "entities": ["Entity1", "Entity2", "Entity3"],
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    "conversation_type": "category"
}}
"""
        return prompt

    def _generate_summary_with_llm(self, messages: List[Dict], context: Dict) -> Dict:
        """Generate summary using Snowflake Cortex LLM."""
        try:
            prompt = self._build_summary_prompt(messages)

            # Call Snowflake Cortex
            cursor = self.ai_service.connection.cursor()
            query = """
                SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', %s) as response
            """
            cursor.execute(query, (prompt,))
            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                # Parse JSON response
                try:
                    summary = json.loads(result[0])
                    summary["message_count"] = len(messages)
                    return summary
                except json.JSONDecodeError:
                    # Fall back to mock if JSON parsing fails
                    return self._generate_mock_summary(messages, context)
            else:
                return self._generate_mock_summary(messages, context)

        except Exception as e:
            logger.error(f"Error generating summary with LLM: {e}", service="semantic_memory", error=str(e))
            return self._generate_mock_summary(messages, context)

    def _generate_mock_summary(self, messages: List[Dict], context: Dict) -> Dict:
        """Generate simple mock summary from messages."""
        # Extract entities (simple pattern matching)
        entities = set()
        all_content = ""

        for msg in messages:
            content = msg.get("content", "")
            all_content += content + " "
            # Look for capitalized words (potential entities)
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
            entities.update(words[:5])  # Limit to 5

        # Generate topic from first message
        first_msg = messages[0].get("content", "General conversation") if messages else "General conversation"
        topic = first_msg[:100] if len(first_msg) > 100 else first_msg

        # Extract key points (first sentence of each user message)
        key_points = []
        for msg in messages[:5]:  # Limit to 5 key points
            if msg.get("role") == "user":
                content = msg.get("content", "")
                first_sentence = content.split('.')[0] if '.' in content else content[:100]
                if first_sentence.strip():
                    key_points.append(first_sentence.strip())

        # Infer conversation type from content
        content_lower = all_content.lower()
        if any(word in content_lower for word in ["deal", "opportunity", "pipeline", "close"]):
            conv_type = "deal_inquiry"
        elif any(word in content_lower for word in ["pricing", "cost", "payment", "tier"]):
            conv_type = "product_question"
        elif any(word in content_lower for word in ["help", "support", "issue", "problem"]):
            conv_type = "support_request"
        elif any(word in content_lower for word in ["policy", "rule", "guideline", "procedure"]):
            conv_type = "policy_question"
        else:
            conv_type = "general"

        return {
            "summary": f"Conversation about {topic}",
            "topic": topic,
            "entities": list(entities),
            "key_points": key_points if key_points else ["Discussion about " + topic],
            "conversation_type": conv_type,
            "message_count": len(messages)
        }

    def store_memory(self, summary: Dict, context: Dict) -> str:
        """
        Store conversation summary in vector store.

        Args:
            summary: Summary dict from generate_summary()
            context: {
                "user_id": "...",
                "channel_id": "...",
                "thread_ts": "...",
                "timestamp": "...",
                "channel_name": "..." (optional)
            }

        Returns:
            memory_id
        """
        # Generate memory ID
        timestamp = context.get("timestamp", datetime.now().isoformat())
        memory_id = f"memory_{context['user_id']}_{context['thread_ts']}_{timestamp}"

        # Build memory chunk for vector store
        memory_chunk = {
            "chunk_id": memory_id,
            "document_id": f"memory_{context['user_id']}",
            "content": self._format_memory_content(summary),
            "metadata": {
                "type": "conversation_memory",
                "user_id": context["user_id"],
                "channel_id": context["channel_id"],
                "thread_ts": context["thread_ts"],
                "timestamp": timestamp,
                "channel_name": context.get("channel_name", "unknown"),
                "summary": summary,
            }
        }

        # Store in vector store
        success = self.vector_store.ingest_documents([memory_chunk])

        if success:
            logger.info(f"Stored memory: {memory_id}", service="semantic_memory", memory_id=memory_id)
            return memory_id
        else:
            logger.error(f"Failed to store memory: {memory_id}", service="semantic_memory", memory_id=memory_id)
            return None

    def _format_memory_content(self, summary: Dict) -> str:
        """Format summary as searchable text content."""
        content = f"Topic: {summary['topic']}\n\n"

        if summary.get("entities"):
            content += f"Entities: {', '.join(summary['entities'])}\n\n"

        content += "Key Points:\n"
        for point in summary.get("key_points", []):
            content += f"- {point}\n"

        content += f"\nConversation Type: {summary.get('conversation_type', 'general')}"

        return content

    def retrieve_memories(
        self,
        query: str,
        user_id: str = None,
        top_k: int = None,
        days_back: int = None
    ) -> List[Dict]:
        """
        Search for relevant past conversations.

        Args:
            query: Current query or topic
            user_id: Optional user filter (search only this user's memories)
            top_k: Number of memories to retrieve (default: from config)
            days_back: Only search memories from last N days (default: from config)

        Returns:
            [{"summary": {...}, "relevance": 0.85, "created_at": "...", "context": {...}}]
        """
        if not self.enabled:
            return []

        top_k = top_k or self.top_k
        days_back = days_back or self.search_days_back

        # Search vector store for memory chunks
        results = self.vector_store.search(query, top_k=top_k * 2)  # Get extra for filtering

        # Filter and score memories
        memories = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for result in results:
            metadata = result.get("metadata", {})

            # Check if this is a memory (not a knowledge base doc)
            if metadata.get("type") != "conversation_memory":
                continue

            # Filter by user if specified
            if user_id and metadata.get("user_id") != user_id:
                continue

            # Filter by date
            try:
                created_at = datetime.fromisoformat(metadata.get("timestamp", ""))
                if created_at < cutoff_date:
                    continue
            except:
                continue

            # Calculate relevance score
            relevance = self._calculate_memory_score(
                result,
                query,
                user_id,
                created_at
            )

            memories.append({
                "summary": metadata.get("summary", {}),
                "relevance": relevance,
                "created_at": metadata.get("timestamp"),
                "context": {
                    "channel_id": metadata.get("channel_id"),
                    "thread_ts": metadata.get("thread_ts"),
                    "channel_name": metadata.get("channel_name", "unknown")
                }
            })

        # Sort by relevance and return top K
        memories.sort(key=lambda x: x["relevance"], reverse=True)
        return memories[:top_k]

    def _calculate_memory_score(
        self,
        memory: Dict,
        query: str,
        current_user_id: str,
        created_at: datetime
    ) -> float:
        """
        Calculate relevance score for a memory.

        Score = Semantic Similarity (0.5) + Recency (0.3) + User Match (0.2)
        """
        # Semantic similarity (from vector search)
        similarity_score = memory.get("score", 0.5)

        # Recency (exponential decay with 30-day half-life)
        days_old = (datetime.now() - created_at).days
        recency_score = math.exp(-days_old / 30.0)

        # User match bonus
        metadata = memory.get("metadata", {})
        memory_user_id = metadata.get("user_id")
        user_match_score = 1.0 if memory_user_id == current_user_id else 0.5

        # Weighted combination
        total_score = (
            0.5 * similarity_score +
            0.3 * recency_score +
            0.2 * user_match_score
        )

        return total_score

    def should_use_memory(self, query: str) -> bool:
        """
        Determine if query references past conversations.

        Args:
            query: User's query

        Returns:
            True if query likely references past conversations
        """
        query_lower = query.lower()

        memory_keywords = [
            "we discussed",
            "you mentioned",
            "you said",
            "earlier",
            "before",
            "last time",
            "previous",
            "remember",
            "recall",
            "what did we",
            "what was",
            "tell me about",
            "status of"
        ]

        return any(keyword in query_lower for keyword in memory_keywords)

    def delete_user_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user.

        Args:
            user_id: User ID to delete memories for

        Returns:
            Success boolean
        """
        # Note: This would require filtering in vector store
        # For MVP, this is a placeholder for future implementation
        logger.warning(f"Memory deletion for user {user_id} not yet implemented", service="semantic_memory", user_id=user_id)
        return False

    def get_stats(self) -> Dict:
        """
        Get semantic memory statistics.

        Returns:
            Dictionary with stats
        """
        vector_stats = self.vector_store.get_stats()

        return {
            "enabled": self.enabled,
            "summary_interval": self.summary_interval,
            "search_days_back": self.search_days_back,
            "top_k": self.top_k,
            "total_chunks": vector_stats.get("total_chunks", 0),
            # Note: total_chunks includes both memories and knowledge base docs
        }
