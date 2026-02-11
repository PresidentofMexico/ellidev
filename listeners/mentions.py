from slack_bolt import App
from services.ai_service import AIService
from services.rag_service import RAGService
from services.vector_store import VectorStore
from services.semantic_memory import SemanticMemory
from services.logger import logger
from services.metrics import metrics
import time
import threading
from dataclasses import dataclass
from typing import Optional

# Initialize services at module level (singleton pattern)
ai_service = AIService()
vector_store = VectorStore()
rag_service = RAGService(vector_store=vector_store, ai_service=ai_service)
semantic_memory = SemanticMemory(vector_store=vector_store, ai_service=ai_service)

# Thread-safe message count tracking with lock
_thread_counts_lock = threading.Lock()
thread_message_counts = {}

# Constants for input validation
MAX_QUERY_LENGTH = 4000  # Slack message limit is 4000 chars
MAX_LOG_QUERY_LENGTH = 500  # Truncate queries in logs


@dataclass
class MessageContext:
    """Context data extracted from a Slack message/event."""
    user_text: str
    channel_id: str
    user_id: str
    thread_ts: str
    event_ts: str
    is_thread: bool


def _validate_and_truncate_input(text: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Validate and truncate user input to prevent oversized data.

    Args:
        text: Raw user input text
        max_length: Maximum allowed length

    Returns:
        Validated and potentially truncated text
    """
    if not text:
        return ""
    # Strip whitespace and truncate if needed
    text = text.strip()
    if len(text) > max_length:
        logger.warning(
            f"Input truncated from {len(text)} to {max_length} chars",
            service="mentions"
        )
        return text[:max_length]
    return text


def _increment_thread_count(thread_ts: str) -> int:
    """
    Thread-safe increment of message count for a thread.

    Args:
        thread_ts: Thread timestamp identifier

    Returns:
        Current message count for the thread
    """
    with _thread_counts_lock:
        if thread_ts not in thread_message_counts:
            thread_message_counts[thread_ts] = 0
        thread_message_counts[thread_ts] += 1
        return thread_message_counts[thread_ts]


def _extract_message_context(event_or_message: dict, is_event: bool = True) -> MessageContext:
    """
    Extract common context from a Slack event or message.

    Args:
        event_or_message: Slack event or message dictionary
        is_event: True for app_mention events, False for message events

    Returns:
        MessageContext with extracted data
    """
    user_text = _validate_and_truncate_input(event_or_message.get("text", ""))
    channel_id = event_or_message["channel"]
    user_id = event_or_message["user"]
    event_ts = event_or_message["ts"]
    thread_ts = event_or_message.get("thread_ts", event_ts)
    is_thread = thread_ts != event_ts

    return MessageContext(
        user_text=user_text,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        event_ts=event_ts,
        is_thread=is_thread
    )


def _handle_memory_summarization(
    client,
    ctx: MessageContext,
    message_count: int
) -> Optional[str]:
    """
    Check if memory summarization is needed and perform it.

    Args:
        client: Slack client
        ctx: Message context
        message_count: Current message count for the thread

    Returns:
        Memory ID if summary was created, None otherwise
    """
    if not semantic_memory.should_summarize(message_count):
        return None

    # Fetch full thread history for summarization (up to 50 messages)
    full_history = fetch_thread_history(client, ctx.channel_id, ctx.thread_ts, limit=50)

    if not full_history:
        return None

    # Generate and store summary
    context = {
        "user_id": ctx.user_id,
        "channel_id": ctx.channel_id,
        "thread_ts": ctx.thread_ts,
        "timestamp": ctx.event_ts
    }
    summary = semantic_memory.generate_summary(full_history, context)
    memory_id = semantic_memory.store_memory(summary, context)

    if memory_id:
        logger.log_memory_operation(
            operation="summarize",
            user_id=ctx.user_id,
            thread_id=ctx.thread_ts,
            success=True,
            details={
                "memory_id": memory_id,
                "message_count": len(full_history)
            }
        )

    return memory_id


def _retrieve_relevant_memories(ctx: MessageContext) -> list:
    """
    Retrieve relevant memories if the query references past conversations.

    Args:
        ctx: Message context

    Returns:
        List of relevant memories
    """
    if not semantic_memory.enabled or not semantic_memory.should_use_memory(ctx.user_text):
        return []

    memories = semantic_memory.retrieve_memories(
        ctx.user_text,
        user_id=ctx.user_id,
        top_k=2
    )

    if memories:
        logger.log_memory_operation(
            operation="retrieve",
            user_id=ctx.user_id,
            thread_id=ctx.thread_ts,
            success=True,
            details={"memories_found": len(memories)}
        )

    return memories


def _format_rag_response(result: dict) -> tuple[str, list]:
    """
    Format a RAG response with sources and memories.

    Args:
        result: RAG service result dictionary

    Returns:
        Tuple of (formatted_answer, sources_used_list)
    """
    answer = result["answer"]
    sources_used = []

    # Add sources section if available
    if result.get("sources"):
        answer += "\n\n📚 **Sources:**"
        for source in result["sources"][:3]:
            citation, source_type = format_source_citation(source)
            sources_used.append(source_type)
            answer += f"\n{citation}"

    # Add memories section if available
    if result.get("memories_used"):
        answer += "\n\n💭 **Relevant Past Conversations:**"
        sources_used.append("conversation_memory")
        for memory in result["memories_used"]:
            date = memory.get("created_at", "")[:10]
            topic = memory.get("summary", {}).get("topic", "")[:50]
            answer += f"\n• {topic} (from {date})"

    return answer, sources_used


def _process_query(
    client,
    say,
    ctx: MessageContext,
    start_time: float
) -> None:
    """
    Process a user query through the RAG/AI pipeline.

    This is the core logic shared between app mentions and DMs.

    Args:
        client: Slack client
        say: Slack say function
        ctx: Message context
        start_time: Query start time for metrics
    """
    # Increment thread count (thread-safe)
    message_count = _increment_thread_count(ctx.thread_ts)

    # Check if we should create a memory summary
    _handle_memory_summarization(client, ctx, message_count)

    # Fetch thread history (recent 5 messages) if in a thread
    history = []
    if ctx.is_thread:
        history = fetch_thread_history(client, ctx.channel_id, ctx.thread_ts, limit=5)

    # Retrieve relevant memories
    memories = _retrieve_relevant_memories(ctx)

    # Check if query should use RAG
    if rag_service.enabled and rag_service.should_use_rag(ctx.user_text):
        result = rag_service.answer_with_context(
            ctx.user_text,
            history=history,
            memories=memories
        )

        if result["context_used"]:
            answer, sources_used = _format_rag_response(result)
            say(answer)

            # Log successful query with RAG
            duration_ms = (time.time() - start_time) * 1000
            logger.log_query(
                user_id=ctx.user_id,
                channel_id=ctx.channel_id,
                query=ctx.user_text[:MAX_LOG_QUERY_LENGTH],
                query_type="rag_search",
                duration_ms=duration_ms,
                success=True,
                sources_used=list(set(sources_used)),
                results_count=len(result.get("sources", []))
            )
            metrics.record_query_time(duration_ms)
            return

    # Fall back to regular AI response
    ai_answer = ai_service.get_response(ctx.user_text, history=history)
    say(ai_answer)

    # Log successful query with direct AI
    duration_ms = (time.time() - start_time) * 1000
    logger.log_query(
        user_id=ctx.user_id,
        channel_id=ctx.channel_id,
        query=ctx.user_text[:MAX_LOG_QUERY_LENGTH],
        query_type="direct_ai",
        duration_ms=duration_ms,
        success=True
    )
    metrics.record_query_time(duration_ms)


def format_source_citation(source: dict) -> tuple[str, str]:
    """
    Format a source citation based on its metadata.

    Args:
        source: Source dictionary with content, metadata, and score

    Returns:
        Tuple of (formatted_citation, source_type)
    """
    metadata = source.get("metadata", {})
    source_type = metadata.get("type", "document")
    data_source = metadata.get("source", "")
    relevance = source.get("score", 0)

    # Aladdin Security Master records
    if data_source == "aladdin_security_master":
        security_name = metadata.get("issuer_name", "Unknown Security")
        ticker = metadata.get("ticker", "")
        if ticker:
            security_name = f"{security_name} ({ticker})"
        return f"• {security_name} [Aladdin] (Relevance: {relevance:.0%})", "aladdin_security_master"

    # Salesforce records
    elif source_type == "salesforce_record":
        object_type = metadata.get("object_type", "Record")
        if object_type == "Opportunity":
            name = source["content"].split("\n")[0].replace("Opportunity: ", "")
            amount = metadata.get("amount", 0)
            stage = metadata.get("stage", "")
            return f"• {name} - ${amount:,.0f} ({stage}) [Salesforce] (Relevance: {relevance:.0%})", source_type
        elif object_type == "Contact":
            name = source["content"].split("\n")[0].replace("Contact: ", "")
            title = metadata.get("title", "")
            return f"• {name}, {title} [Salesforce Contact] (Relevance: {relevance:.0%})", source_type
        elif object_type == "Account":
            name = source["content"].split("\n")[0].replace("Account: ", "")
            return f"• {name} [Salesforce Account] (Relevance: {relevance:.0%})", source_type
        else:
            name = source["content"].split("\n")[0]
            return f"• {name} [Salesforce] (Relevance: {relevance:.0%})", source_type

    # Default: regular documents
    else:
        doc_id = source.get("document_id", "unknown").replace("_", " ").title()
        return f"• {doc_id} [Document] (Relevance: {relevance:.0%})", source_type


def fetch_thread_history(client, channel_id: str, thread_ts: str, limit: int = 5) -> list:
    """
    Fetch conversation history from a Slack thread.

    Args:
        client: Slack client
        channel_id: Channel ID
        thread_ts: Thread timestamp
        limit: Maximum number of messages to fetch (default 5)

    Returns:
        List of message dictionaries with role and content
    """
    try:
        # Fetch thread replies
        response = client.conversations_replies(
            channel=channel_id, ts=thread_ts, limit=limit + 1  # +1 for parent message
        )

        history = []
        bot_user_id = client.auth_test()["user_id"]

        for msg in response["messages"]:
            # Skip the current message (it will be processed separately)
            if msg.get("ts") == thread_ts and len(response["messages"]) > 1:
                continue

            content = msg.get("text", "")
            user_id = msg.get("user", "")

            # Determine role based on whether it's the bot or a user
            if user_id == bot_user_id:
                role = "assistant"
            else:
                role = "user"

            history.append({"role": role, "content": content})

        # Return last N messages (excluding current)
        return history[-limit:] if len(history) > limit else history

    except Exception as e:
        logger.warning(f"Could not fetch thread history: {e}", service="mentions", error=str(e))
        return []


def register_mention_listeners(app: App):
    @app.event("app_mention")
    def handle_mentions(event, say, client):
        """
        Handle app mentions with semantic memory, RAG, and context awareness.

        Args:
            event: Slack event data
            say: Slack say function
            client: Slack client for API calls
        """
        start_time = time.time()
        ctx = _extract_message_context(event, is_event=True)

        logger.info(
            f"Received app mention from user {ctx.user_id}",
            user_id=ctx.user_id,
            channel_id=ctx.channel_id,
            query=ctx.user_text[:MAX_LOG_QUERY_LENGTH]
        )

        say("👀 Let me check on that...")

        _process_query(client, say, ctx, start_time)

    # Handle Direct Messages (DMs)
    @app.event("message")
    def handle_dm(message, say, client):
        """
        Handle direct messages to the bot with thread-aware context.

        Args:
            message: Slack message data
            say: Slack say function
            client: Slack client for API calls
        """
        # Only process direct messages (prevents double-replying in channels)
        if message.get("channel_type") != "im":
            return

        # Skip messages with subtypes (bot messages, edits, etc.)
        if message.get("subtype") is not None:
            return

        # Skip messages that match Salesforce workflow patterns
        # These are handled by the messages.py listener
        if _is_salesforce_workflow_message(message.get("text", "")):
            return

        start_time = time.time()
        ctx = _extract_message_context(message, is_event=False)

        logger.info(
            f"Received DM from user {ctx.user_id}",
            user_id=ctx.user_id,
            channel_id=ctx.channel_id,
            query=ctx.user_text[:MAX_LOG_QUERY_LENGTH]
        )

        _process_query(client, say, ctx, start_time)


def _is_salesforce_workflow_message(text: str) -> bool:
    """
    Check if a message matches Salesforce workflow patterns.

    This prevents the DM handler from responding to messages that
    should be handled by the Salesforce workflow in messages.py.

    Args:
        text: Message text to check

    Returns:
        True if message matches a Salesforce workflow pattern
    """
    if not text:
        return False

    text_lower = text.lower()

    # Direct keyword matches
    if "update salesforce" in text_lower:
        return True
    if "urgent help" in text_lower:
        return True
    if "add new deal:" in text_lower:
        return True

    # Stage update patterns: "update X to Y" or "set X stage to Y"
    stage_keywords = ["discovery", "negotiation", "closed won", "proposal"]

    if "update" in text_lower and "to" in text_lower:
        if any(stage in text_lower for stage in stage_keywords):
            return True

    if "set" in text_lower and "stage" in text_lower:
        return True

    return False
