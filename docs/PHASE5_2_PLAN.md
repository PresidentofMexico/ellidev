# Phase 5.2 Plan: Semantic Memory

**Version**: 0.5.1 (Planned)
**Status**: Planning 📋
**Dependencies**: Phase 5.1 (RAG with Vector Search)

## Overview

Phase 5.2 implements **Semantic Memory** - the ability for Elli to remember past conversations beyond the current thread's 5-message history and retrieve relevant memories when needed.

### The Problem

**Current State (Phase 5.1):**
```
Day 1:
User: @Elli Tell me about the Acme Corp deal
Elli: [Detailed response about Acme Corp...]

[15 messages later in same thread]
User: What was the status of that deal?
Elli: [Still has context from thread history]

Day 3 (new thread):
User: @Elli What was the status of the Acme deal we discussed?
Elli: I don't have information about previous conversations.
```

**Limitation**: Thread history only goes back 5 messages and doesn't persist across threads.

**Target State (Phase 5.2):**
```
Day 3 (new thread):
User: @Elli What was the status of the Acme deal we discussed?
Elli: Based on our conversation from January 14th, the Acme Corp deal
      was in Negotiation stage with a Q1 2026 close date valued at $250K.

      Would you like me to check for any updates? 🔍

      💭 Memory: Conversation from 2026-01-14 in #sales channel
```

## Architecture Design

### Semantic Memory Flow

```
Conversation Happens
    ↓
[Every N messages] → Trigger summarization
    ↓
[Generate Summary] → LLM creates structured summary
    ↓
[Extract Metadata] → Entities, topics, key points
    ↓
[Store in Vector DB] → Save with embedding
    ↓
[Tag with Context] → User, channel, thread, timestamp

---

User Asks Question
    ↓
[Check for Memory Keywords] → "we discussed", "earlier", "before"
    ↓
[Search Memory Store] → Find relevant past conversations
    ↓
[Rank by Relevance] → Score: recency + relevance + same user
    ↓
[Include in Context] → Add to prompt with timestamp
    ↓
[Generate Response] → AI with full memory context
```

### Data Schema

#### Conversation Memory Table

```sql
CREATE TABLE elli_conversation_memory (
    memory_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    channel_id VARCHAR,
    thread_ts VARCHAR,
    summary TEXT,
    embedding VECTOR(FLOAT, 768),
    metadata VARIANT,  -- JSON structure below
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE INDEX idx_user_channel ON elli_conversation_memory(user_id, channel_id);
CREATE INDEX idx_created_at ON elli_conversation_memory(created_at);
```

#### Metadata Structure

```json
{
    "topic": "Acme Corp deal status",
    "entities": ["Acme Corp", "Q1 2026", "Negotiation"],
    "key_points": [
        "Deal in Negotiation stage",
        "Close date: Q1 2026",
        "Deal value: $250,000"
    ],
    "conversation_type": "deal_inquiry",
    "message_count": 12,
    "channel_name": "sales",
    "participants": ["U123456", "U789012"]
}
```

## Implementation Plan

### Task 1: Semantic Memory Service

**New file**: `services/semantic_memory.py`

**Key class**:
```python
class SemanticMemory:
    def __init__(self, vector_store: VectorStore, ai_service: AIService):
        """Initialize semantic memory service"""
        self.vector_store = vector_store
        self.ai_service = ai_service
        self.summary_interval = int(os.environ.get("MEMORY_SUMMARY_INTERVAL", "10"))
        self.memory_enabled = os.environ.get("SEMANTIC_MEMORY_ENABLED", "true").lower() == "true"

    def should_summarize(self, thread_message_count: int) -> bool:
        """Check if we should create a summary (every N messages)"""
        return (thread_message_count > 0 and
                thread_message_count % self.summary_interval == 0)

    def generate_summary(self, messages: list, context: dict) -> dict:
        """
        Generate structured summary of conversation.

        Args:
            messages: List of message dicts with role and content
            context: {"user_id": "...", "channel_id": "...", "thread_ts": "..."}

        Returns:
            {
                "summary": "Conversation summary text",
                "topic": "Main topic",
                "entities": ["Entity1", "Entity2"],
                "key_points": ["Point 1", "Point 2"]
            }
        """

    def store_memory(self, summary: dict, context: dict) -> str:
        """
        Store conversation summary in vector store.

        Args:
            summary: Summary dict from generate_summary()
            context: Conversation context (user, channel, thread, timestamp)

        Returns:
            memory_id
        """

    def retrieve_memories(
        self,
        query: str,
        user_id: str = None,
        top_k: int = 3,
        days_back: int = 30
    ) -> list:
        """
        Search for relevant past conversations.

        Args:
            query: Current query or topic
            user_id: Optional user filter (search only this user's memories)
            top_k: Number of memories to retrieve
            days_back: Only search memories from last N days

        Returns:
            [{"summary": {...}, "relevance": 0.85, "created_at": "..."}]
        """

    def should_use_memory(self, query: str) -> bool:
        """
        Determine if query references past conversations.

        Keywords: "we discussed", "earlier", "before", "last time",
                  "you said", "previous", "remember"
        """
```

### Task 2: Summary Generation Prompt

**Prompt template for LLM**:
```
You are a conversation summarizer. Generate a structured summary of this conversation.

CONVERSATION:
User: Tell me about the Acme Corp deal
Assistant: Acme Corp is currently in Negotiation stage...
User: What's the close date?
Assistant: The expected close date is Q1 2026, specifically March 31st.
User: What's the deal value?
Assistant: The deal is valued at $250,000.

INSTRUCTIONS:
1. Summarize the main topic in one sentence
2. Extract key entities (companies, people, dates, amounts)
3. List 3-5 key points from the conversation
4. Categorize the conversation type (deal_inquiry, product_question, support_request, etc.)

FORMAT YOUR RESPONSE AS JSON:
{
    "topic": "Brief one-sentence summary",
    "entities": ["Entity1", "Entity2", "Entity3"],
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    "conversation_type": "category"
}
```

### Task 3: Memory-Aware Prompting

**Update**: `services/rag_service.py`

Add memory integration to RAG prompt:
```python
def answer_with_context(self, query: str, history: list = None, memories: list = None):
    """
    RAG pipeline with semantic memory.

    Args:
        query: User's question
        history: Thread history (5 messages)
        memories: Past conversation summaries

    Returns:
        {"answer": "...", "sources": [...], "memories_used": [...]}
    """
```

**Enhanced prompt template**:
```
You are Elli, a helpful enterprise assistant.

CONTEXT FROM KNOWLEDGE BASE:
[Chunk 1 - Relevance: 95%]
Product pricing information...

PAST CONVERSATIONS (SEMANTIC MEMORY):
[Memory from 2026-01-14]
Topic: Acme Corp deal status
Key Points:
- Deal in Negotiation stage
- Close date: Q1 2026
- Deal value: $250,000

RECENT THREAD HISTORY:
User: What about the deal?
Assistant: Let me check...

CURRENT QUESTION: What was the status of the Acme deal?

INSTRUCTIONS:
- Use memory from past conversations when relevant
- Mention when you're referencing a previous conversation
- Include the date of the memory if citing it
```

### Task 4: Update Listeners

**Modify**: `listeners/mentions.py`

Track message counts and trigger summarization:
```python
# Module-level tracking (simple in-memory for MVP)
thread_message_counts = {}

@app.event("app_mention")
def handle_mentions(event, say, client):
    # ... existing code ...

    thread_ts = event.get("thread_ts", event["ts"])

    # Track message count
    if thread_ts not in thread_message_counts:
        thread_message_counts[thread_ts] = 0
    thread_message_counts[thread_ts] += 1

    # Check if we should summarize
    if semantic_memory.should_summarize(thread_message_counts[thread_ts]):
        # Fetch full thread history
        full_history = fetch_thread_history(client, channel_id, thread_ts, limit=50)

        # Generate and store summary
        context = {
            "user_id": event["user"],
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "timestamp": event["ts"]
        }
        summary = semantic_memory.generate_summary(full_history, context)
        memory_id = semantic_memory.store_memory(summary, context)

        print(f"💭 Created memory: {memory_id}")

    # Retrieve relevant memories
    memories = []
    if semantic_memory.should_use_memory(user_text):
        memories = semantic_memory.retrieve_memories(
            user_text,
            user_id=event["user"],
            top_k=2
        )

    # Pass memories to RAG service
    result = rag_service.answer_with_context(
        user_text,
        history=history,
        memories=memories
    )
```

### Task 5: Memory-Aware Response Formatting

**Update response to cite memories**:
```python
if result.get("memories_used"):
    answer += "\n\n💭 **Relevant Past Conversations:**"
    for memory in result["memories_used"]:
        date = memory["created_at"]
        topic = memory["summary"]["topic"]
        answer += f"\n• {topic} (from {date})"
```

### Task 6: Configuration

**Add to `.env.example`**:
```bash
# Semantic Memory Configuration (Phase 5.2)
SEMANTIC_MEMORY_ENABLED=true
MEMORY_SUMMARY_INTERVAL=10  # Summarize every N messages
MEMORY_SEARCH_DAYS_BACK=30  # Search last 30 days
MEMORY_TOP_K=2  # Retrieve top 2 memories
```

### Task 7: Mock Mode Implementation

**Mock summary generation** (without LLM):
```python
def _generate_mock_summary(self, messages: list) -> dict:
    """Generate simple mock summary from messages"""

    # Extract entities (simple pattern matching)
    entities = set()
    for msg in messages:
        content = msg["content"]
        # Look for capitalized words (potential entities)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        entities.update(words[:5])  # Limit to 5

    # Generate topic from first message
    first_msg = messages[0]["content"] if messages else "General conversation"
    topic = first_msg[:100]  # First 100 chars

    # Extract key points (first sentence of each message)
    key_points = []
    for msg in messages[:5]:  # Limit to 5 key points
        first_sentence = msg["content"].split('.')[0]
        if first_sentence:
            key_points.append(first_sentence.strip())

    return {
        "topic": topic,
        "entities": list(entities),
        "key_points": key_points,
        "conversation_type": "general"
    }
```

## Usage Examples

### Example 1: Deal Follow-Up

**Day 1 - Initial Conversation:**
```
User: @Elli Tell me about the Acme Corp deal
Elli: Acme Corp is in Negotiation stage with a close date of Q1 2026.
      The deal is valued at $250,000.

[After 10 messages, Elli automatically creates a memory]
System: 💭 Created memory: acme_deal_20260114
```

**Day 3 - Follow-Up:**
```
User: @Elli What was the status of that Acme deal we discussed?
Elli: Based on our conversation from January 14th, the Acme Corp deal
      was in Negotiation stage with a Q1 2026 close date valued at $250K.

      Would you like me to check for any updates in Salesforce? 🔍

      💭 Relevant Past Conversations:
      • Acme Corp deal inquiry (from 2026-01-14)
```

### Example 2: Product Question Recall

**Week 1:**
```
User: @Elli What features are in the Professional tier?
Elli: [Lists features from knowledge base]

[Summarized after 10 messages]
```

**Week 2:**
```
User: @Elli You mentioned something about the Professional tier before
Elli: Yes! In our conversation from January 14th, we discussed the
      Professional tier which includes unlimited workflows, 20K AI queries,
      and priority support at $99/user/month.

      💭 Relevant Past Conversations:
      • Professional tier features inquiry (from 2026-01-14)
```

### Example 3: Multi-Topic Recall

```
User: @Elli What have we discussed about pricing recently?
Elli: Looking at our recent conversations, we've discussed:

      1. Professional tier pricing ($99/user/month) - Jan 14
      2. Payment terms (Net 30, 50/50 for new customers) - Jan 15
      3. Enterprise custom pricing options - Jan 16

      Which would you like to know more about?

      💭 Relevant Past Conversations:
      • Professional tier features inquiry (from 2026-01-14)
      • Payment terms question (from 2026-01-15)
```

## Technical Considerations

### Memory vs RAG vs Thread History

| Feature | Scope | Persistence | Use Case |
|---------|-------|-------------|----------|
| **Thread History** | 5 messages | Current session | Immediate context, pronouns |
| **RAG (Knowledge Base)** | All documents | Permanent | Company knowledge, policies |
| **Semantic Memory** | Past conversations | 30-90 days | Personal history, follow-ups |

### Priority Order

When responding to a query:
1. Check thread history (5 messages)
2. Check semantic memory (if query references past)
3. Check knowledge base (if information query)
4. Fall back to base LLM

### Storage Considerations

**Estimated sizes:**
- 1 conversation summary: ~500 tokens (~1KB)
- 100 users × 10 conversations/month = 1,000 summaries/month
- Annual storage: ~12MB (negligible)

**Retention policy:**
- Keep memories for 90 days
- Archive older memories (optional)
- User can request memory deletion (GDPR)

### Privacy Considerations

**Data stored:**
- Conversation summaries (not full messages)
- User ID, channel ID, thread ID
- Timestamps and metadata
- No sensitive content should be in summaries

**Controls:**
- Users can disable memory: `SEMANTIC_MEMORY_ENABLED=false`
- Admins can delete memories: `semantic_memory.delete_user_memories(user_id)`
- Memories are user-specific by default

## Implementation Phases

### Phase 5.2.1: Basic Memory (Week 1)
- ✅ Implement SemanticMemory service
- ✅ Summary generation (LLM + mock)
- ✅ Store summaries in vector store
- ✅ Basic memory retrieval

### Phase 5.2.2: Integration (Week 2)
- ✅ Update listeners to track message counts
- ✅ Trigger summarization every N messages
- ✅ Integrate memories into RAG pipeline
- ✅ Format responses with memory citations

### Phase 5.2.3: Polish (Week 3)
- ✅ Relevance scoring (recency + similarity + same user)
- ✅ Memory deletion and management
- ✅ Privacy controls
- ✅ Documentation and testing

## Configuration Options

### Tuning Parameters

```bash
# How often to summarize (messages)
MEMORY_SUMMARY_INTERVAL=10  # Default: every 10 messages
# Options: 5 (frequent), 10 (balanced), 20 (sparse)

# How far back to search
MEMORY_SEARCH_DAYS_BACK=30  # Default: 30 days
# Options: 7 (week), 30 (month), 90 (quarter)

# How many memories to include
MEMORY_TOP_K=2  # Default: top 2
# Options: 1 (focused), 2 (balanced), 3 (comprehensive)
```

### Memory Relevance Scoring

```python
def calculate_memory_score(memory, query, current_user_id):
    """
    Score = Semantic Similarity (0.5)
          + Recency (0.3)
          + User Match (0.2)
    """

    # Semantic similarity (from vector search)
    similarity_score = memory["vector_similarity"]

    # Recency (exponential decay)
    days_old = (datetime.now() - memory["created_at"]).days
    recency_score = math.exp(-days_old / 30)  # 30-day half-life

    # User match bonus
    user_match_score = 1.0 if memory["user_id"] == current_user_id else 0.5

    # Weighted combination
    total_score = (
        0.5 * similarity_score +
        0.3 * recency_score +
        0.2 * user_match_score
    )

    return total_score
```

## Testing Strategy

### Test Cases

**1. Summary Generation**
- ✅ Summarize 10-message conversation
- ✅ Extract entities correctly
- ✅ Generate relevant key points
- ✅ Categorize conversation type

**2. Memory Storage**
- ✅ Store summary in vector store
- ✅ Attach correct metadata
- ✅ Generate valid memory_id

**3. Memory Retrieval**
- ✅ Search by semantic similarity
- ✅ Filter by user_id
- ✅ Filter by date range
- ✅ Rank by relevance score

**4. Integration**
- ✅ Trigger summarization every N messages
- ✅ Retrieve memories for relevant queries
- ✅ Include memories in RAG context
- ✅ Format response with memory citations

**5. Mock Mode**
- ✅ Generate mock summaries without LLM
- ✅ Store and retrieve in mock vector store
- ✅ All functionality works without Snowflake

## Success Metrics

### Functional Metrics
- ✅ Memory generation success rate > 95%
- ✅ Memory retrieval latency < 500ms
- ✅ Relevant memory recall accuracy > 80%
- ✅ Zero data loss during storage

### User Experience Metrics
- ✅ User asks "what did we discuss?" → Gets accurate memory
- ✅ Follow-up questions work across days/weeks
- ✅ No false positives (irrelevant memories retrieved)
- ✅ Privacy controls work as expected

## Risks and Mitigations

### Risk 1: Summary quality without LLM
- **Mitigation**: Mock mode uses pattern-based entity extraction
- **Alternative**: Provide clear upgrade path to Snowflake Cortex

### Risk 2: Memory retrieval irrelevant
- **Mitigation**: Tune relevance threshold and scoring weights
- **Alternative**: Allow users to explicitly request memory search

### Risk 3: Privacy concerns
- **Mitigation**: Clear documentation, opt-out option, data retention policy
- **Alternative**: User-specific memory isolation by default

### Risk 4: Storage growth
- **Mitigation**: 90-day retention, summary-only (not full messages)
- **Alternative**: Archive old memories to cheaper storage

## Dependencies

### New Python Packages
None! Uses existing dependencies:
- `snowflake-connector-python` (already in Phase 3)
- `numpy` (already in Phase 5.1)

### Snowflake Setup
```sql
-- Create memory table (runs automatically on first use)
CREATE TABLE IF NOT EXISTS elli_conversation_memory (
    memory_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    channel_id VARCHAR,
    thread_ts VARCHAR,
    summary TEXT,
    metadata VARIANT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

## Documentation Updates

**Files to create:**
- `docs/PHASE5_2_SUMMARY.md` - Implementation summary
- `docs/SEMANTIC_MEMORY_GUIDE.md` - User guide

**Files to update:**
- `README.md` - Add Phase 5.2 to roadmap
- `CHANGELOG.md` - Add Phase 5.2 entry
- `AGENTS.md` - Add Phase 5.2 breadcrumb
- `.env.example` - Add memory configuration

## Open Questions

### Question 1: Summarization Frequency
**Options:**
- A. Every 10 messages (balanced)
- B. Every 5 messages (frequent, more memories)
- C. On thread close/timeout (sparse, high-quality)

**Recommendation**: Start with A (every 10), make configurable

### Question 2: Memory Scope
**Options:**
- A. User-specific only (private memories)
- B. Channel-wide (shared team memories)
- C. Configurable per installation

**Recommendation**: Start with A (private), add B in Phase 5.3

### Question 3: Memory Deletion
**Options:**
- A. Automatic (90-day retention)
- B. Manual (user requests deletion)
- C. Both

**Recommendation**: C (automatic retention + manual deletion option)

## Next Steps

**To proceed with Phase 5.2 implementation:**

1. ✅ **Approve this plan** - Confirm approach and priorities
2. ⏳ **Implement semantic memory service** - Core functionality
3. ⏳ **Integrate with listeners** - Track and summarize
4. ⏳ **Update RAG pipeline** - Add memory context
5. ⏳ **Test end-to-end** - Verify full workflow
6. ⏳ **Document and release** - v0.5.1

**Estimated effort**: 20-30 hours

---

**Version**: 0.5.1 (Planned)
**Status**: Planning Complete - Ready for Approval
**Dependencies**: Phase 5.1 Complete ✅
