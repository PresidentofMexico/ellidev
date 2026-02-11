# Phase 5: Enhanced AI - RAG with Vector Search and Semantic Memory

## Overview

**Goal**: Transform Elli from a conversational AI into an intelligent knowledge assistant that can retrieve and reason over enterprise data using Retrieval Augmented Generation (RAG) and semantic memory.

**Current State (Phase 4)**:
- ✅ Thread-aware conversation memory (5 messages)
- ✅ Snowflake Cortex LLM integration (llama3-70b)
- ✅ Salesforce opportunity search and updates
- ✅ Mock fallback for all external services

**Target State (Phase 5)**:
- 🎯 Vector-based semantic search over enterprise documents
- 🎯 Long-term semantic memory beyond thread context
- 🎯 RAG pipeline: Query → Retrieve → Augment → Generate
- 🎯 Salesforce + document knowledge integration
- 🎯 Citation and source attribution

---

## Architecture Design

### 1. RAG Pipeline Flow

```
User Query
    ↓
[Query Analysis]
    ↓
[Vector Search] → Retrieve top K relevant documents/chunks
    ↓
[Context Ranking] → Rerank by relevance
    ↓
[Prompt Augmentation] → Inject retrieved context into LLM prompt
    ↓
[Snowflake Cortex] → Generate response with citations
    ↓
Response + Sources
```

### 2. Vector Store Strategy

**Option A: Snowflake Cortex Vector Search (Recommended)**
- **Pros**: Native integration, same credentials, SQL-based
- **Cons**: Requires Snowflake Enterprise edition
- **Implementation**: Use `SNOWFLAKE.CORTEX.SEARCH_PREVIEW()` function

**Option B: External Vector Database**
- **Options**: Pinecone, Weaviate, Qdrant, ChromaDB
- **Pros**: More features, specialized for vector search
- **Cons**: Additional service, more complexity

**Recommendation**: Start with Option A (Snowflake Cortex Vector Search) for seamless integration. Provide Option B as fallback.

### 3. Embedding Strategy

**Embedding Model**: Use Snowflake Cortex `EMBED_TEXT_768()` function
- Model: `e5-base-v2` (768 dimensions)
- Consistent with Snowflake ecosystem
- No external API calls needed

### 4. Document Sources

**Phase 5.1 - Internal Knowledge Base**:
- Markdown documents in `/knowledge` folder
- Product documentation
- Sales playbooks
- FAQ documents

**Phase 5.2 - Salesforce Integration** (future):
- Opportunity notes
- Account history
- Case descriptions

**Phase 5.3 - External Sources** (future):
- Web scraping
- API integrations
- File uploads

---

## Implementation Plan

### Task 1: Knowledge Base Setup

**Files to create**:
- `/knowledge/` directory for documents
- `/knowledge/product_info.md` (sample document)
- `/knowledge/sales_playbook.md` (sample document)

**Sample content**: Create 3-5 knowledge documents with realistic enterprise content.

### Task 2: Vector Store Service

**New file**: `services/vector_store.py`

**Key classes and methods**:
```python
class VectorStore:
    def __init__(self):
        """Initialize vector store (Snowflake Cortex or fallback)"""

    def ingest_documents(self, documents: list[dict]) -> bool:
        """
        Chunk and embed documents, store in vector DB.

        Args:
            documents: [{"id": "doc1", "content": "...", "metadata": {...}}]

        Returns:
            Success boolean
        """

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Semantic search for relevant document chunks.

        Args:
            query: User's question
            top_k: Number of results to return

        Returns:
            [{"content": "...", "score": 0.95, "metadata": {...}}]
        """

    def _embed_text(self, text: str) -> list[float]:
        """Generate embedding using Snowflake Cortex"""
```

**Snowflake Implementation**:
```python
# Create Cortex Search Service
CREATE CORTEX SEARCH SERVICE elli_knowledge_search
    ON content
    ATTRIBUTES metadata
    WAREHOUSE = your_warehouse
    TARGET_LAG = '1 minute'
    AS (
        SELECT
            chunk_id,
            content,
            metadata,
            SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', content) as embedding
        FROM elli_knowledge_base
    );

# Query the search service
SELECT * FROM TABLE(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'elli_knowledge_search',
        'What is our pricing model?'
    )
) LIMIT 5;
```

**Mock Implementation**:
- In-memory keyword search as fallback
- Returns hardcoded "knowledge chunks" based on keywords

### Task 3: Document Chunking

**New file**: `services/chunking.py`

**Strategy**:
- Chunk size: 500 tokens (~375 words)
- Overlap: 50 tokens (10%)
- Preserve sentence boundaries

**Key function**:
```python
def chunk_document(content: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Split document into overlapping chunks.

    Returns:
        [{"chunk_id": "doc1_chunk_0", "content": "...", "start": 0, "end": 500}]
    """
```

### Task 4: RAG Service

**New file**: `services/rag_service.py`

**Key class**:
```python
class RAGService:
    def __init__(self, vector_store: VectorStore, ai_service: AIService):
        """Initialize RAG pipeline"""

    def answer_with_context(self, query: str, top_k: int = 3) -> dict:
        """
        RAG pipeline: Retrieve → Augment → Generate.

        Returns:
            {
                "answer": "...",
                "sources": [{"content": "...", "score": 0.95}],
                "context_used": True
            }
        """
```

**RAG Prompt Template**:
```
You are Elli, a helpful enterprise assistant.

Use the following context to answer the user's question. If the context doesn't contain relevant information, say so.

CONTEXT:
---
[Chunk 1 - Score: 0.95]
{retrieved_chunk_1}

[Chunk 2 - Score: 0.89]
{retrieved_chunk_2}
---

CONVERSATION HISTORY:
{thread_history}

USER QUESTION: {user_query}

Provide a helpful answer and cite the relevant context chunks if used.
```

### Task 5: Semantic Memory

**New file**: `services/semantic_memory.py`

**Purpose**: Store and retrieve long-term conversation summaries beyond 5-message thread history.

**Key functions**:
```python
def save_conversation_summary(user_id: str, thread_ts: str, summary: dict):
    """
    Store conversation summary in vector store for later retrieval.

    Args:
        user_id: Slack user ID
        thread_ts: Thread timestamp
        summary: {
            "topic": "Acme Corp deal status",
            "key_points": ["Negotiation stage", "Q3 close date"],
            "entities": ["Acme Corp"],
            "timestamp": "2026-01-14"
        }
    """

def retrieve_relevant_memories(user_id: str, query: str, top_k: int = 3) -> list[dict]:
    """
    Find past conversations relevant to current query.

    Returns:
        [{"summary": {...}, "relevance_score": 0.85}]
    """
```

**Strategy**:
- Every 10 messages in a thread, generate a summary using LLM
- Embed the summary and store in vector store
- When user asks a question, search past conversations
- Include relevant past context in prompt

### Task 6: Update Mentions Listener

**Modify**: `listeners/mentions.py`

**Changes**:
```python
# Add RAG service initialization
from services.rag_service import RAGService
from services.vector_store import VectorStore

vector_store = VectorStore()
rag_service = RAGService(vector_store, ai_service)

def handle_mentions(event, say, client):
    user_text = event["text"]

    # Fetch thread history (existing)
    history = fetch_thread_history(client, channel_id, thread_ts)

    # NEW: Check if query would benefit from RAG
    if should_use_rag(user_text):
        result = rag_service.answer_with_context(user_text, top_k=3)

        if result["context_used"]:
            # Format response with citations
            response = format_response_with_sources(result)
            say(response)
            return

    # Fallback to regular AI response (existing)
    ai_answer = ai_service.get_response(user_text, history=history)
    say(ai_answer)
```

**Helper function**:
```python
def should_use_rag(query: str) -> bool:
    """Determine if query needs knowledge retrieval"""
    rag_keywords = ["what is", "how do", "tell me about", "explain", "pricing", "product"]
    return any(keyword in query.lower() for keyword in rag_keywords)
```

### Task 7: CLI Utilities

**New file**: `scripts/ingest_knowledge.py`

**Purpose**: CLI tool to ingest documents into vector store.

```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

**Functionality**:
- Scan directory for markdown files
- Chunk documents
- Generate embeddings
- Store in vector store
- Show progress and statistics

---

## Data Schema

### Vector Store Table (Snowflake)

```sql
CREATE TABLE elli_knowledge_base (
    chunk_id VARCHAR PRIMARY KEY,
    document_id VARCHAR,
    content TEXT,
    embedding VECTOR(FLOAT, 768),
    metadata VARIANT,  -- JSON: {"source": "...", "title": "...", "timestamp": "..."}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

CREATE INDEX idx_embedding ON elli_knowledge_base
USING VECTOR_COSINE_SIMILARITY(embedding);
```

### Semantic Memory Table (Snowflake)

```sql
CREATE TABLE elli_conversation_memory (
    memory_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    thread_ts VARCHAR,
    summary TEXT,
    embedding VECTOR(FLOAT, 768),
    metadata VARIANT,  -- {"topic": "...", "entities": [...], "key_points": [...]}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

---

## Environment Variables

**Add to `.env.example`**:

```bash
# Vector Store Configuration (Phase 5)
# Option A: Snowflake Cortex Vector Search (recommended)
# Uses existing SNOWFLAKE_* credentials
# VECTOR_STORE_TYPE=snowflake

# Option B: External Vector Database (alternative)
# VECTOR_STORE_TYPE=pinecone
# PINECONE_API_KEY=your-api-key
# PINECONE_ENVIRONMENT=us-west1-gcp
# PINECONE_INDEX_NAME=elli-knowledge

# RAG Configuration
RAG_ENABLED=true
RAG_TOP_K=3  # Number of chunks to retrieve
RAG_CHUNK_SIZE=500  # Tokens per chunk
RAG_CHUNK_OVERLAP=50  # Token overlap between chunks

# Semantic Memory Configuration
SEMANTIC_MEMORY_ENABLED=true
SEMANTIC_MEMORY_SUMMARY_INTERVAL=10  # Summarize every N messages
```

---

## Dependencies to Add

**Update `requirements.txt`**:

```
# Existing dependencies
slack_bolt==1.18.0
slack_sdk==3.27.1
python-dotenv==1.0.0
simple-salesforce==1.12.6
snowflake-connector-python[pandas]==3.6.0
pandas==2.1.4

# Phase 5: RAG and Vector Search
tiktoken==0.5.2               # Token counting for chunking
nltk==3.8.1                   # Sentence tokenization
numpy==1.26.3                 # Vector operations
scikit-learn==1.4.0           # Cosine similarity (mock mode)

# Optional: External vector stores (if not using Snowflake)
# pinecone-client==3.0.0
# weaviate-client==4.4.0
# chromadb==0.4.22
```

---

## Testing Strategy

### Test Cases

**1. Knowledge Ingestion**:
- ✅ Ingest 5 sample documents
- ✅ Verify chunking creates ~20 chunks
- ✅ Verify embeddings are 768 dimensions
- ✅ Verify metadata preserved

**2. Vector Search**:
- ✅ Query: "What is our pricing model?" → Returns pricing document chunks
- ✅ Query: "How do I close a deal?" → Returns sales playbook chunks
- ✅ Verify top_k parameter works
- ✅ Verify relevance scores are reasonable (>0.7 for good matches)

**3. RAG Pipeline**:
- ✅ User asks: "@Elli What are our payment terms?"
- ✅ System retrieves relevant chunks from knowledge base
- ✅ System augments prompt with context
- ✅ LLM generates answer with citations
- ✅ Response includes source attribution

**4. Semantic Memory**:
- ✅ User has 15-message thread about "Acme Corp deal"
- ✅ System generates summary after 10 messages
- ✅ 1 day later, user asks: "@Elli What was the status of the Acme deal?"
- ✅ System retrieves past conversation summary
- ✅ Response references previous discussion

**5. Mock Mode**:
- ✅ Without Snowflake credentials, system uses keyword-based mock search
- ✅ Mock returns hardcoded "knowledge chunks"
- ✅ User still gets helpful responses

---

## Migration Path

### Phase 5.1: Basic RAG (Week 1)
- ✅ Create vector store service with Snowflake Cortex
- ✅ Implement document chunking
- ✅ Build RAG service
- ✅ Create 5 sample knowledge documents
- ✅ Update mentions listener with RAG capability
- ✅ Add CLI ingestion tool

### Phase 5.2: Semantic Memory (Week 2)
- ✅ Implement conversation summarization
- ✅ Store summaries in vector store
- ✅ Retrieve relevant past conversations
- ✅ Integrate with RAG pipeline

### Phase 5.3: Advanced Features (Week 3+)
- ✅ Salesforce data integration (search over opportunity notes)
- ✅ Citation formatting improvements
- ✅ Relevance threshold tuning
- ✅ Hybrid search (keyword + semantic)

---

## Success Metrics

### Functional Metrics
- ✅ Can ingest 100+ documents successfully
- ✅ Search returns relevant results in <2 seconds
- ✅ RAG responses cite sources accurately
- ✅ Mock mode works without credentials

### User Experience Metrics
- ✅ User asks product question → Gets accurate answer with sources
- ✅ User references past conversation → System remembers context
- ✅ Response quality improves compared to Phase 4

### Technical Metrics
- ✅ Vector store contains 500+ chunks
- ✅ Average relevance score >0.75 for top 3 results
- ✅ End-to-end latency <3 seconds (retrieve + generate)
- ✅ Zero breaking changes to Phase 1-4 functionality

---

## Backward Compatibility

**Zero Breaking Changes**:
- ✅ All Phase 1-4 functionality remains intact
- ✅ RAG is optional (controlled by `RAG_ENABLED` env var)
- ✅ Falls back to regular AI response if RAG fails
- ✅ Works in mock mode without Snowflake credentials

**Feature Flags**:
```python
RAG_ENABLED = os.environ.get("RAG_ENABLED", "false").lower() == "true"
SEMANTIC_MEMORY_ENABLED = os.environ.get("SEMANTIC_MEMORY_ENABLED", "false").lower() == "true"
```

---

## Risks and Mitigations

### Risk 1: Snowflake Cortex Vector Search not available
- **Mitigation**: Implement mock fallback with keyword search
- **Alternative**: Provide integration with Pinecone/Weaviate

### Risk 2: Chunking strategy doesn't preserve context
- **Mitigation**: Use sentence-aware chunking with NLTK
- **Alternative**: Increase overlap to 100 tokens (20%)

### Risk 3: Irrelevant results from vector search
- **Mitigation**: Implement relevance threshold (e.g., >0.7)
- **Mitigation**: Add reranking step using Snowflake Cortex

### Risk 4: LLM hallucination despite RAG
- **Mitigation**: Add instruction to cite sources
- **Mitigation**: Format retrieved chunks with scores
- **Mitigation**: Log queries and responses for quality monitoring

---

## Documentation Updates

**Files to update**:
- ✅ `README.md`: Add Phase 5 to roadmap completion, update version to 0.5.0
- ✅ `CHANGELOG.md`: Document Phase 5 changes
- ✅ `AGENTS.md`: Add Phase 5 breadcrumb entry
- ✅ `docs/ARCHITECTURE.md`: Add RAG pipeline diagram
- ✅ `docs/TESTING_GUIDE.md`: Add Phase 5 test scenarios

**New documentation**:
- ✅ `docs/PHASE5_SUMMARY.md`: Detailed implementation summary
- ✅ `docs/RAG_GUIDE.md`: How to use RAG features, knowledge ingestion
- ✅ `knowledge/README.md`: Guidelines for creating knowledge documents

---

## Open Questions

1. **Vector Store Choice**: Should we support external vector databases (Pinecone, Weaviate) from day 1, or Snowflake-only initially?
   - **Recommendation**: Snowflake-only for Phase 5.1, add external support in 5.3

2. **Chunk Size**: 500 tokens might be too large for some queries, too small for others.
   - **Recommendation**: Start with 500, make it configurable via env var

3. **Semantic Memory Trigger**: When should we summarize conversations?
   - **Recommendation**: Every 10 messages, or when thread goes idle for 1 hour

4. **Citation Format**: How should we present sources to users?
   - **Recommendation**: Markdown format with document title and relevance score

5. **Salesforce Integration**: Should Phase 5 include Salesforce opportunity notes in RAG?
   - **Recommendation**: Phase 5.3 - start with static documents first

---

## Example User Interactions

### Before Phase 5 (Current):
```
User: @Elli What are our payment terms?
Elli: I analyzed your request: 'What are our payment terms?'.

      According to the Snowflake Data Warehouse (mock data), I found
      relevant information that might help answer your question. 📈

      *This is a mock response from Elli's brain 🧠*
```

### After Phase 5 (RAG Enabled):
```
User: @Elli What are our payment terms?
Elli: Based on our knowledge base, here are our standard payment terms:

      • Net 30 for customers with established credit
      • 50% upfront, 50% on delivery for new customers
      • Early payment discount: 2% if paid within 10 days
      • Enterprise contracts: Custom terms available

      📚 Sources:
      • Sales Playbook - Payment Terms (Relevance: 94%)
      • Product Documentation - Billing Section (Relevance: 87%)
```

### With Semantic Memory:
```
[Day 1]
User: @Elli Tell me about the Acme Corp deal
Elli: Acme Corp is currently in Negotiation stage with a close date
      of March 31, 2026. Deal value: $250,000. 📊

[Day 3]
User: @Elli What was the status of that deal we discussed?
Elli: Based on our conversation from January 14th, you asked about
      the Acme Corp deal. It's currently in Negotiation stage with
      a Q1 2026 close date.

      Would you like me to check for any updates? 🔍
```

---

## Next Steps

**To proceed with Phase 5 implementation, I need your approval on**:

1. ✅ **Vector Store Choice**: Snowflake Cortex Vector Search (primary) with mock fallback?
2. ✅ **Scope**: Start with Phase 5.1 (Basic RAG) before moving to 5.2 (Semantic Memory)?
3. ✅ **Knowledge Sources**: Begin with static markdown documents in `/knowledge`?
4. ✅ **External Dependencies**: Add Pinecone/Weaviate support later (Phase 5.3)?

**Once approved, implementation will proceed in this order**:
1. Create knowledge base documents (samples)
2. Implement vector store service
3. Implement chunking service
4. Implement RAG service
5. Update mentions listener
6. Create CLI ingestion tool
7. Add tests and documentation
8. Update CHANGELOG to v0.5.0

---

**Estimated Effort**: 40-60 hours (distributed over Phase 5.1, 5.2, 5.3)

**Version**: 0.5.0 when Phase 5.1 complete, 0.5.1 for 5.2, 0.5.2 for 5.3

**Status**: ⏳ Awaiting approval to begin implementation
