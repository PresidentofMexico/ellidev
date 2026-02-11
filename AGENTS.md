# AGENTS.md - Coding Copilot Guidelines for Elli

## Purpose
This document provides coding guidelines, architectural context, and a breadcrumbs system for AI coding copilots working on the Elli project. Use this file to understand the codebase structure, avoid breaking changes, and prevent duplicate code.

---

## Project Overview

**Elli** is a hybrid Slack application that combines deterministic workflow automation with AI-powered assistance.

### Core Architecture: Hybrid Router Approach
- **Layer 1 (Workflows)**: Regex pattern matching triggers specific workflows (e.g., "update salesforce" → Modal)
- **Layer 2 (AI Fallback)**: Unmatched messages are routed to an LLM for RAG-based responses

### Tech Stack
- **Language**: Python 3.11+
- **Framework**: Slack Bolt Framework (`slack_bolt`)
- **Dependencies**: `slack_sdk`, `python-dotenv`
- **Deployment**: Socket Mode (for development/internal use)

---

## Directory Structure

```
/elli
├── .env                    # Environment variables (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
├── app.py                  # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation (source of truth)
├── AGENTS.md              # This file - agent guidelines
├── /listeners             # Event routing and handlers
│   ├── __init__.py
│   ├── messages.py        # Layer 1: Regex-based workflow triggers
│   └── mentions.py        # Layer 2: AI fallback for app mentions & DMs
├── /workflows             # Business logic for specific workflows
│   ├── __init__.py
│   └── salesforce.py      # Salesforce modal and submission handling
└── /services              # External service integrations
    ├── __init__.py
    ├── ai_service.py      # LLM client (placeholder)
    └── sf_client.py       # Salesforce API client (placeholder)
```

---

## Coding Guidelines

### 1. Security Best Practices
- **NEVER** hardcode tokens, API keys, or secrets in code
- **ALWAYS** use `os.environ.get()` to load from `.env`
- **NEVER** commit `.env` file to version control (ensure it's in `.gitignore`)

### 2. Code Style
- Follow **PEP 8** Python style guidelines
- Use **type hints** for all function signatures:
  ```python
  def update_opportunity(opp_name: str, stage: str) -> bool:
      pass
  ```
- Use **docstrings** for all public functions:
  ```python
  def open_modal(client, trigger_id):
      """Opens the Salesforce update modal."""
      pass
  ```

### 3. Modularity Principles
- **Separation of Concerns**: Keep listeners, workflows, and services in separate modules
- **Single Responsibility**: Each file should have one clear purpose
- **DRY (Don't Repeat Yourself)**: Extract common logic into shared utilities

### 4. Listener Pattern
- **Regex listeners** (Layer 1) go in `/listeners/messages.py`
- **AI fallback listeners** (Layer 2) go in `/listeners/mentions.py`
- Register all listeners in their respective modules, then import into `app.py`

### 5. Workflow Implementation
- Business logic for workflows goes in `/workflows/`
- Each workflow should have its own file (e.g., `salesforce.py`, `jira.py`)
- Workflows should handle:
  - Modal/dialog definitions
  - User input validation
  - Calling external service clients

### 6. Service Integration
- External API clients go in `/services/`
- Services should be class-based with clear initialization
- Services should handle their own error handling and logging
- Keep API keys/credentials in environment variables

### 7. Error Handling
- Use try-except blocks for external API calls
- Provide user-friendly error messages in Slack
- Log errors for debugging (future: use proper logging framework)

### 8. Dependency Management
- Add new dependencies to `requirements.txt`
- Pin versions for production stability (e.g., `slack_bolt==1.18.0`)
- Document why each major dependency is needed

---

## Agent Breadcrumbs System

**Purpose**: Track changes, decisions, and context to prevent breaking changes and code duplication.

### How to Use Breadcrumbs
1. **Before making changes**: Read this section to understand recent work
2. **After making changes**: Add a new breadcrumb entry with your context
3. **Format**: Date, Agent, Area, Description, Files Changed

---

### Breadcrumb Log

#### 2026-01-14 | Initial Modularization | All Areas
- **Agent**: Human Developer
- **Changes**: Refactored monolithic `app.py` into modular structure
- **Files Created**:
  - `/listeners/messages.py` - Regex-based workflow triggers
  - `/listeners/mentions.py` - AI fallback handlers
  - `/workflows/salesforce.py` - Salesforce modal logic
  - `/services/ai_service.py` - AI service placeholder
  - `/services/sf_client.py` - Salesforce client placeholder
- **Notes**:
  - Fixed duplicate response bugs in mentions listener
  - Implemented DM vs channel message routing logic
  - Salesforce workflow is functional with mock data

---

#### 2026-01-14 | Phase 2: Smart Salesforce Integration | Salesforce Workflows
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Implemented entity extraction and smart search for Salesforce opportunities
- **Files Modified**:
  - `/services/sf_client.py` - Added real Salesforce API integration with mock fallback
  - `/workflows/salesforce.py` - Added `handle_smart_update()` for intelligent opportunity search
  - `/listeners/messages.py` - Added smart regex patterns for entity extraction
  - `.env.example` - Updated Salesforce credential variables
  - `requirements.txt` - Added `simple-salesforce==1.12.6`
- **Dependencies Added**:
  - `simple-salesforce==1.12.6` - For Salesforce API integration
- **Breaking Changes**: None - all changes are backward compatible
- **Key Features Implemented**:
  - **Entity Extraction**: Patterns like "Update Acme Corp to Closed Won" now extract company name and stage
  - **Smart Search**: Searches Salesforce for opportunities matching company name
  - **Intelligent Routing**:
    - 0 results → "Not found" message
    - 1 result → Auto-display with pre-filled update button
    - Multiple results → Disambiguation dropdown menu
  - **Mock Mode**: Falls back to mock data if Salesforce credentials not provided
  - **Pre-filled Modals**: Modals now support pre-filling opportunity ID, name, and stage
- **Supported Patterns**:
  - "Update [Company] to [Stage]"
  - "Set [Company] stage to [Stage]"
  - Legacy fallback: "update salesforce" (still works)
- **Notes**:
  - Maintains separation of concerns (Listeners → Workflows → Services)
  - Service layer handles both real and mock Salesforce connections
  - All environment variables use `SF_*` prefix for clarity
  - Modal now stores opportunity ID in `private_metadata` for direct updates
  - Updated submission handler to use opportunity ID when available

---

#### 2026-01-14 | Phase 3: Snowflake Cortex Integration | AI Service
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Implemented real AI service using Snowflake Cortex LLM
- **Files Modified**:
  - `/services/ai_service.py` - Complete rewrite with Snowflake Cortex integration
  - `/listeners/mentions.py` - Updated to use real AIService instead of mock function
  - `.env.example` - Added Snowflake configuration variables
  - `requirements.txt` - Added Snowflake dependencies
- **Files Created**:
  - `docs/` - Organized documentation into dedicated folder
  - Moved: `ARCHITECTURE.md`, `CI_CD.md`, `CONTRIBUTING.md`, `PHASE2_SUMMARY.md`, `TESTING_GUIDE.md`
- **Dependencies Added**:
  - `snowflake-connector-python[pandas]==3.6.0` - Snowflake database connector
  - `pandas==2.1.4` - Data manipulation library (Snowflake dependency)
- **Breaking Changes**: None - all changes are backward compatible
- **Key Features Implemented**:
  - **Snowflake Cortex Integration**: Real LLM calls using `SNOWFLAKE.CORTEX.COMPLETE()` function
  - **LLM Model**: Using `llama3-70b` for AI responses
  - **Mock Mode**: Enhanced mock responses with keyword detection (revenue, customer, help)
  - **Singleton Pattern**: AI service initialized once at module level for performance
  - **Connection Management**: Automatic connection cleanup with `__del__` method
  - **Smart Workflow Detection**: Enhanced DM handler to avoid conflicts with Salesforce patterns
- **Environment Variables**:
  - `SNOWFLAKE_USER` - Snowflake username (required)
  - `SNOWFLAKE_PASSWORD` - Snowflake password (required)
  - `SNOWFLAKE_ACCOUNT` - Account identifier (required)
  - `SNOWFLAKE_WAREHOUSE` - Warehouse name (required)
  - `SNOWFLAKE_DATABASE` - Database name (optional)
  - `SNOWFLAKE_SCHEMA` - Schema name (optional)
  - `SNOWFLAKE_ROLE` - Role name (optional)
- **Notes**:
  - AI service now powers both app mentions and direct messages
  - Removed hardcoded `time.sleep()` delay from mock responses
  - Mock mode provides context-aware responses based on query keywords
  - Real mode executes SQL query with Cortex Complete function
  - System prompt: "You are Elli, a helpful enterprise assistant."
  - Documentation reorganized into `docs/` folder for better project structure

---

#### 2026-01-14 | Phase 4: Conversation Memory | AI Context Awareness
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Implemented thread-aware conversation memory for context-aware AI responses
- **Files Modified**:
  - `/listeners/mentions.py` - Added thread history fetching functionality
  - `/services/ai_service.py` - Enhanced to accept and process conversation history
- **Breaking Changes**: None - all changes are backward compatible
- **Key Features Implemented**:
  - **Thread History Fetching**: New `fetch_thread_history()` function retrieves last 5 messages from Slack threads
  - **Context-Aware Prompting**: AI service builds conversation context from history
  - **Smart Entity Extraction**: Mock mode extracts entities (Acme Corp, TechStart, Global Systems) from history
  - **Pronoun Resolution**: Handles queries like "update it" by referencing conversation context
  - **Error Handling**: Graceful fallback if thread permission denied
  - **Role Detection**: Automatically identifies user vs assistant messages using bot_user_id
- **Conversation Flow**:
  1. Check if message is part of thread (`thread_ts` present)
  2. Fetch last 5 messages from thread using `conversations_replies()`
  3. Build history list: `[{"role": "user/assistant", "content": "..."}]`
  4. Format history into prompt: "Conversation History:\nUser: ...\nAssistant: ..."
  5. Pass to Snowflake Cortex or mock with full context
- **Prompt Engineering**:
  - Real mode: `System + History + Current Query + Answer:`
  - Mock mode: Entity extraction + pronoun resolution + context notes
- **Test Cases**:
  - Thread: "Who is Acme?" → "Update it" (resolves to "Acme Corp")
  - Thread: "Tell me about TechStart" → "What's their revenue?" (maintains context)
  - Single message: Works as before (no history)
- **Notes**:
  - History limited to 5 messages to save tokens and API costs
  - Both app mentions and DMs support thread context
  - Mock mode provides context-aware responses without Snowflake
  - Permission errors handled gracefully (returns empty history)
  - Bot identifies its own messages using `auth_test()` API call

---

#### 2026-01-14 | Phase 5.1: RAG with Vector Search | Knowledge Base AI
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Implemented Retrieval Augmented Generation (RAG) with semantic search over knowledge base
- **Files Created**:
  - `/services/vector_store.py` - Vector storage and semantic search (Snowflake Cortex + mock)
  - `/services/chunking.py` - Document chunking with token-based splitting
  - `/services/rag_service.py` - RAG pipeline orchestration
  - `/scripts/ingest_knowledge.py` - CLI tool for knowledge base ingestion
  - `/knowledge/README.md` - Knowledge base documentation and guidelines
  - `/knowledge/product_info.md` - Sample product documentation (~3,200 words)
  - `/knowledge/sales_playbook.md` - Sample sales playbook (~2,800 words)
  - `/knowledge/company_faq.md` - Sample FAQ document (~2,500 words)
  - `/docs/PHASE5_PLAN.md` - Comprehensive Phase 5 planning document
- **Files Modified**:
  - `/listeners/mentions.py` - Integrated RAG service for knowledge-based queries
  - `.env.example` - Added RAG configuration variables (RAG_ENABLED, RAG_TOP_K, etc.)
  - `requirements.txt` - Added numpy and scikit-learn for vector operations
  - `README.md` - Updated to v0.5.0 with RAG usage examples
  - `CHANGELOG.md` - Added Phase 5.1 comprehensive changelog entry
  - `AGENTS.md` - Updated roadmap to show Phase 5.1 complete
- **Dependencies Added**:
  - `numpy==1.26.3` - Vector operations and numerical computing
  - `scikit-learn==1.4.0` - ML utilities for mock mode similarity calculations
- **Breaking Changes**: None - all changes are backward compatible, RAG is opt-in via env var
- **Key Features Implemented**:
  - **RAG Pipeline**: Full Retrieve → Augment → Generate workflow
  - **Vector Store**: Snowflake Cortex vector search with mock in-memory fallback
  - **Document Chunking**: Token-based chunking (500 tokens, 50 overlap) with sentence awareness
  - **Semantic Search**: Embeddings-based search using Snowflake Cortex e5-base-v2 model
  - **Source Attribution**: AI responses include formatted citations with relevance scores
  - **Query Classification**: Automatic routing to RAG vs regular AI based on query keywords
  - **CLI Ingestion Tool**: Batch document processing with progress reporting and statistics
  - **Knowledge Base**: 3 realistic sample documents covering product, sales, and FAQs
  - **Mock Mode**: Keyword-based search fallback without requiring Snowflake credentials
- **RAG Configuration (Environment Variables)**:
  - `RAG_ENABLED=true` - Enable/disable RAG system (default: true)
  - `RAG_TOP_K=3` - Number of chunks to retrieve per query (default: 3)
  - `RAG_CHUNK_SIZE=500` - Target tokens per chunk (default: 500)
  - `RAG_CHUNK_OVERLAP=50` - Overlap between chunks in tokens (default: 50)
- **Technical Implementation**:
  - Chunking: Sentence-aware splitting preserves markdown headers and list items
  - Embedding: Snowflake Cortex `EMBED_TEXT_768()` using e5-base-v2 (768 dimensions)
  - Search: Cosine similarity via `VECTOR_COSINE_SIMILARITY()` SQL function
  - Relevance threshold: 0.3 (30%) minimum score for chunk inclusion
  - Mock search: Keyword overlap + exact phrase matching for scoring
  - Response format: Answer text + "📚 Sources:" section with document names and relevance %
- **Supported Query Types** (automatically use RAG):
  - "What is...", "What are...", "Tell me about..." (information queries)
  - "How do...", "How to..." (procedural questions)
  - "Explain...", "Describe..." (explanatory queries)
  - Keywords: pricing, payment, cost, product, feature, support, policy, documentation
- **CLI Usage**:
  ```bash
  # Ingest all knowledge base files recursively
  python scripts/ingest_knowledge.py --path ./knowledge --recursive

  # Ingest single document
  python scripts/ingest_knowledge.py --path ./knowledge/product_info.md

  # Custom chunking parameters
  python scripts/ingest_knowledge.py --path ./knowledge --chunk-size 800 --overlap 100
  ```
- **RAG Workflow**:
  1. User asks question via @mention or DM
  2. Listener calls `rag_service.should_use_rag()` to check query type
  3. If RAG-eligible: `vector_store.search()` retrieves top 3 relevant chunks
  4. Filter chunks by relevance threshold (>0.3)
  5. Build augmented prompt with context + history + query
  6. Generate answer using Snowflake Cortex (or mock mode)
  7. Format response with source citations and relevance scores
  8. Send to Slack with "📚 Sources:" footer
- **Notes**:
  - RAG is completely optional - controlled by RAG_ENABLED environment variable
  - Falls back to regular AI response if RAG disabled or no relevant results found
  - Mock mode provides full RAG experience without Snowflake (keyword-based search)
  - Vector store stats accessible via `vector_store.get_stats()` method
  - Chunk metadata preserved: title, source file path, document ID, token count
  - Source formatting: "Product Info (Relevance: 95%)" in response footer
  - Works seamlessly with both app mentions and DMs
  - Integrates with Phase 4 conversation memory (history parameter passed through)
  - Cognitive complexity warnings in listeners/mentions.py are acceptable (clear control flow)
  - All Phase 1-4 functionality maintained with zero breaking changes
  - Version bumped from 0.4.0 to 0.5.0 following semantic versioning

---

#### 2026-01-14 | Phase 5.2: Semantic Memory | Long-Term Conversation Memory
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Implemented semantic memory for long-term conversation summaries and retrieval
- **Files Created**:
  - `/services/semantic_memory.py` - Semantic memory service (350+ lines)
  - `/docs/PHASE5_2_SUMMARY.md` - Phase 5.2 technical summary
  - `/docs/SEMANTIC_MEMORY_GUIDE.md` - User guide for semantic memory
- **Files Modified**:
  - `/services/rag_service.py` - Added memories parameter throughout RAG pipeline
  - `/listeners/mentions.py` - Integrated memory tracking, summarization, and retrieval
  - `.env.example` - Added semantic memory configuration variables
  - `README.md` - Updated to v0.5.1 with semantic memory examples
  - `CHANGELOG.md` - Added comprehensive Phase 5.2 changelog entry
  - `AGENTS.md` - Added Phase 5.2 breadcrumb (this entry)
- **Dependencies Added**: None (reuses existing Snowflake and vector store infrastructure)
- **Breaking Changes**: None - all changes are backward compatible, semantic memory is opt-in via env var
- **Key Features Implemented**:
  - **Auto-Summarization**: Creates summaries every N messages (configurable interval, default: 10)
  - **Memory Generation**: LLM-based structured summaries with topic, entities, key points, conversation type
  - **Memory Storage**: Saves summaries to vector store with metadata (user_id, channel_id, thread_ts, timestamp)
  - **Memory Retrieval**: Semantic search across past conversations with date filtering (default: 30 days)
  - **Relevance Scoring**: Weighted combination of similarity (50%), recency (30%), user match (20%)
  - **Memory Citations**: Responses include past conversation references with dates
  - **Three-Layer Context**: Thread history (5 msgs) + Semantic memory (30 days) + Knowledge base (permanent)
  - **Mock Mode**: Pattern-based entity extraction and categorization without Snowflake
- **Memory Configuration (Environment Variables)**:
  - `SEMANTIC_MEMORY_ENABLED=true` - Enable/disable semantic memory (default: true)
  - `MEMORY_SUMMARY_INTERVAL=10` - Messages per summary (default: 10)
  - `MEMORY_SEARCH_DAYS_BACK=30` - Memory search window in days (default: 30)
  - `MEMORY_TOP_K=2` - Number of memories to retrieve (default: 2)
- **Technical Implementation**:
  - **In-Memory Tracking**: Module-level dictionary tracks message counts per thread (Option A selected)
  - **Summary Structure**: JSON with topic, entities, key_points, conversation_type, message_count
  - **Memory Storage**: Stored as vector chunks with metadata type "conversation_memory"
  - **Relevance Formula**: `0.5 * similarity + 0.3 * recency + 0.2 * user_match`
  - **Recency Decay**: Exponential decay with 30-day half-life
  - **User Filtering**: Memories filtered by user_id for privacy
  - **Date Filtering**: Only retrieves memories from last N days (configurable)
  - **Conversation Types**: deal_inquiry, product_question, support_request, policy_question, general
- **Memory Workflow**:
  1. User sends message in thread, increment message count
  2. Every N messages (default: 10), trigger summarization
  3. Fetch full thread history (up to 50 messages)
  4. Generate structured summary using LLM or mock mode
  5. Store summary in vector store with metadata
  6. When user query detected (e.g., "what did we discuss"), retrieve relevant memories
  7. Pass memories to RAG service along with thread history
  8. Format response with memory citations including dates
- **Memory Detection Keywords**: "we discussed", "you mentioned", "you said", "earlier", "before", "last time", "previous", "remember", "recall", "what did we", "what was", "tell me about", "status of"
- **Integration Points**:
  - `listeners/mentions.py`: Added semantic_memory initialization (singleton), message count tracking, auto-summarization triggers, memory retrieval, memory citation formatting
  - `services/rag_service.py`: Added memories parameter to answer_with_context(), _build_rag_prompt(), _generate_mock_rag_response()
  - Both handle_mentions() and handle_dm() now support semantic memory
- **Notes**:
  - Semantic memory is completely optional - controlled by SEMANTIC_MEMORY_ENABLED environment variable
  - In-memory message count tracking resets on bot restart (acceptable for MVP Phase 5.2.1)
  - Memories stored alongside knowledge base chunks in same vector store (differentiated by metadata type)
  - Mock mode provides pattern-based summarization without requiring Snowflake credentials
  - Cognitive complexity warnings in listeners/mentions.py remain acceptable (clear logical sections)
  - All Phase 1-5.1 functionality maintained with zero breaking changes
  - Version bumped from 0.5.0 to 0.5.1 following semantic versioning
  - Three layers of context provide comprehensive understanding: recent thread + past conversations + company knowledge

---

#### 2026-01-14 | Phase 5.3: Salesforce RAG Integration | Advanced RAG Features
- **Agent**: Claude Code (Sonnet 4.5)
- **Changes**: Integrated live Salesforce data into RAG knowledge base for hybrid search
- **Files Created**:
  - `/services/salesforce_rag.py` - Salesforce RAG service (550+ lines)
  - `/scripts/ingest_salesforce.py` - CLI tool for Salesforce data sync (150 lines)
  - `/docs/PHASE5_3_PLAN.md` - Phase 5.3 planning document
- **Files Modified**:
  - `/services/rag_service.py` - Enhanced CRM query detection with 20+ keywords
  - `/listeners/mentions.py` - Enhanced source formatting for Salesforce records
  - `.env.example` - Added Salesforce RAG configuration variables
  - `README.md` - Updated to v0.6.0 with Salesforce RAG examples
  - `CHANGELOG.md` - Added comprehensive Phase 5.3 changelog entry
  - `AGENTS.md` - Added Phase 5.3 breadcrumb (this entry)
- **Dependencies Added**: None (reuses existing simple-salesforce and vector store infrastructure)
- **Breaking Changes**: None - all changes are backward compatible, Salesforce RAG is opt-in via env var
- **Key Features Implemented**:
  - **Salesforce Data Fetching**: Retrieves opportunities, accounts, contacts via API
  - **Record Formatting**: Formats CRM records as searchable vector store chunks
  - **Hybrid Search**: Searches across both static documents AND live Salesforce data
  - **Enhanced Citations**: Distinguishes Salesforce records from documents in source formatting
  - **CLI Ingestion Tool**: On-demand sync with --objects, --limit, --refresh flags
  - **CRM Query Detection**: 20+ keywords automatically trigger RAG for CRM queries
  - **Mock Mode**: Full functionality with sample CRM data without Salesforce credentials
- **Salesforce RAG Configuration (Environment Variables)**:
  - `SALESFORCE_RAG_ENABLED=true` - Enable/disable Salesforce RAG (default: true)
  - `SALESFORCE_RAG_OBJECTS=opportunities,accounts,contacts` - Which objects to sync
  - `SALESFORCE_RAG_LIMIT=100` - Max records per object (default: 100)
- **Technical Implementation**:
  - **Record Chunking**: Each SF record becomes one chunk with metadata
  - **Metadata Structure**: type="salesforce_record", object_type, record_id, stage, amount, etc.
  - **Source Formatting**: Opportunities show "$250,000 (Negotiation) [Salesforce]"
  - **Source Formatting**: Contacts show "Name, Title [Salesforce Contact]"
  - **Source Formatting**: Accounts show "Name [Salesforce Account]"
  - **Source Formatting**: Documents show "Document Name [Document]"
  - **Storage**: CRM records stored alongside knowledge base in same vector store
  - **Differentiation**: metadata.type field distinguishes records from documents
- **CRM Query Keywords**: opportunity, deal, pipeline, forecast, account, customer, client, contact, stage, close date, amount, value, who handles, sales rep
- **CLI Tool Usage**:
  ```bash
  python scripts/ingest_salesforce.py                          # Sync all
  python scripts/ingest_salesforce.py --objects opportunities  # Sync opportunities only
  python scripts/ingest_salesforce.py --limit 50               # Limit records
  ```
- **Hybrid Search Workflow**:
  1. User asks CRM-related question (detected by keywords)
  2. Vector store searches across documents + Salesforce records
  3. Results ranked by semantic relevance
  4. Sources formatted with [Salesforce] or [Document] labels
  5. Response includes mixed citations from both sources
- **Notes**:
  - Salesforce RAG is completely optional - controlled by SALESFORCE_RAG_ENABLED
  - Works seamlessly with Phase 5.1 (RAG) and Phase 5.2 (Semantic Memory)
  - On-demand sync (Option A) selected for Phase 5.3.1 - simple, user-controlled
  - Future enhancements: scheduled auto-refresh (Option B), real-time webhooks (Option C)
  - Mock mode provides 3 sample opportunities, 3 accounts, 3 contacts for testing
  - Cognitive complexity warnings in listeners/mentions.py remain acceptable (clear logical sections)
  - All Phase 1-5.2 functionality maintained with zero breaking changes
  - Version bumped from 0.5.1 to 0.6.0 following semantic versioning
  - Hybrid search enables questions like "What deals are in negotiation?" and "Who handles TechStart?"

---

#### 2026-01-26 | Cortex Analyst Integration | Services & Commands
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Added Snowflake Cortex Analyst integration for DEAL_AGENT queries
- **Files Created**:
  - `/services/cortex_analyst_service.py` - New service for Cortex Analyst REST API integration (505 lines)
- **Files Modified**:
  - `/listeners/commands.py` - Added `/ask-deal-agent` slash command handler
  - `.env.example` - Added Cortex Analyst configuration section
- **Dependencies Added**: None (uses stdlib `requests` which was already available)
- **Breaking Changes**: None - this is an additive feature
- **Key Features**:
  - **CortexAnalystService class** with:
    - REST API integration via `/api/v2/cortex/analyst/message` endpoint
    - Programmatic Access Token (PAT) authentication
    - Structured `AnalystResponse` dataclass with text, SQL, suggestions, warnings
    - Mock mode for testing without credentials
    - Feedback submission support
  - **`/ask-deal-agent` slash command**:
    - Natural language queries to DEAL_AGENT
    - Rich Slack blocks formatting for responses
    - SQL query display when generated
    - Follow-up suggestions from the analyst
  - **Configuration**:
    - `CORTEX_ANALYST_ENABLED` - Enable/disable (default: false)
    - `CORTEX_ANALYST_PAT` - Programmatic Access Token
    - `CORTEX_ANALYST_ACCOUNT` - Snowflake account (e.g., ara18269)
    - `CORTEX_ANALYST_REGION` - Region (e.g., east-us-2.azure)
    - `CORTEX_ANALYST_AGENT` - Agent name (DEAL_AGENT)
    - `CORTEX_ANALYST_DATABASE` - Database (DEV_CURATE)
    - `CORTEX_ANALYST_SCHEMA` - Schema (CORE)
- **API Reference**:
  - Cortex Analyst REST API: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api
  - PAT Authentication: https://docs.snowflake.com/en/user-guide/programmatic-access-tokens
- **Usage**:
  ```
  /ask-deal-agent What deals are closing this month?
  /ask-deal-agent Show me the pipeline by stage
  /ask-deal-agent Which accounts have the highest deal value?
  ```
- **Notes**:
  - Cortex Analyst uses REST API (not SQL functions like Cortex Complete)
  - PAT must be generated from Snowsight → Settings → Authentication
  - Different from existing Cortex Complete (LLM) integration in ai_service.py
  - Mock mode provides realistic sample responses for testing
  - Singleton instance `cortex_analyst` available for import

---

#### 2026-01-26 | Code Quality Refactoring | Listeners
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Major code quality improvements addressing technical debt identified in Phase 8 review
- **Files Modified**:
  - `/listeners/mentions.py` - Refactored to extract common RAG logic, added thread-safe locks, input validation
  - `/listeners/messages.py` - Replaced simple dict with `DealSessionManager` class with TTL and thread-safety
- **Files Created**: None
- **Dependencies Added**: None (uses stdlib `threading`, `dataclasses`)
- **Breaking Changes**: None - all changes are internal refactoring, external API unchanged
- **Key Improvements**:
  - **DRY Compliance**: Extracted ~300 lines of duplicated RAG logic into shared helper functions:
    - `_process_query()` - Core RAG/AI pipeline (shared between app mentions and DMs)
    - `_extract_message_context()` - Unified context extraction
    - `_handle_memory_summarization()` - Memory summarization logic
    - `_retrieve_relevant_memories()` - Memory retrieval logic
    - `_format_rag_response()` - Response formatting with sources
    - `MessageContext` dataclass for structured context data
  - **Thread Safety**: Added `threading.Lock` to protect global state:
    - `_thread_counts_lock` for `thread_message_counts` in mentions.py
    - `DealSessionManager._lock` for session management in messages.py
  - **Session TTL**: New `DealSessionManager` class with:
    - 15-minute session timeout (`SESSION_TTL_SECONDS`)
    - Automatic cleanup every 5 minutes (`CLEANUP_INTERVAL_SECONDS`)
    - `DealSession` dataclass with `is_expired()`, `touch()` methods
    - Logging of session creation/expiration/deletion
  - **Input Validation**: Added length limits to prevent oversized data:
    - `MAX_QUERY_LENGTH = 4000` (Slack's message limit)
    - `MAX_LOG_QUERY_LENGTH = 500` (truncation for logs)
    - Company name validation (max 255 chars)
    - `_validate_and_truncate_input()` helper with logging
  - **Code Clarity**: Replaced cryptic "BUG FIX" comments with well-documented `_is_salesforce_workflow_message()` function
- **Cognitive Complexity Reduction**:
  - `handle_mentions()`: Reduced from ~100 lines to ~15 lines
  - `handle_dm()`: Reduced from ~130 lines to ~25 lines
  - Logic now clearly separated into focused helper functions
- **Test Results**: All 72 existing tests pass after refactoring
- **Notes**:
  - This addresses issues identified during Phase 8 code review
  - Session manager uses lazy cleanup (runs during session access, not background thread)
  - Thread counts dictionary still grows unbounded but is now thread-safe
  - Future enhancement: Add TTL cleanup for thread_message_counts as well

---

#### 2026-01-26 | Phase 9.1.1: JWT Key-Pair Auth for Cortex Analyst | Security Enhancement
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Replaced PAT (Programmatic Access Token) with JWT key-pair authentication for Cortex Analyst
- **Files Modified**:
  - `/services/cortex_analyst_service.py` - Rewrote auth to use JWT key-pair instead of PAT
  - `.env.example` - Updated Cortex Analyst section to document key-pair setup (removed PAT config)
  - `AGENTS.md` - Added Phase 9.1.1 breadcrumb (this entry)
- **Files Created**: None
- **Dependencies Added**: `PyJWT`, `cryptography` (for JWT token generation)
- **Breaking Changes**: None - existing mock mode still works; real mode now requires key-pair setup
- **Key Features Implemented**:
  - **JWT Token Generation**: Dynamically generates short-lived tokens (59s expiry) from RSA private key
  - **Key-Pair Auth**: Uses `KEYPAIR_JWT` header type instead of `PROGRAMMATIC_ACCESS_TOKEN`
  - **Shared Config**: Reuses existing `SNOWFLAKE_USER` and `SNOWFLAKE_PRIVATE_KEY_PATH` from ai_service
  - **Private Key Caching**: Key loaded once at service init, token generated per-request
  - **Qualified Account Name**: Builds account.region format for JWT issuer/subject claims
  - **Graceful Fallback**: Falls back to mock mode if JWT libs unavailable or key not configured
- **Why This Change**:
  - PATs are long-lived secrets that must be stored (security risk)
  - JWT key-pair uses private key file (no secret in env vars)
  - Tokens are generated on-demand and expire in 59 seconds
  - Reuses existing Snowflake key-pair config (DRY principle)
- **Key-Pair Setup Steps** (documented in .env.example):
  1. Generate RSA key: `openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt`
  2. Extract public key: `openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub`
  3. Assign to Snowflake user: `ALTER USER elli_service_account SET RSA_PUBLIC_KEY='...';`
  4. Set `SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8`
- **Test Results**: All 72 existing tests pass after changes
- **Notes**:
  - Removed CORTEX_ANALYST_PAT env var entirely
  - Mock response text updated to reference SNOWFLAKE_PRIVATE_KEY_PATH instead of PAT
  - Auth header changed from `PROGRAMMATIC_ACCESS_TOKEN` to `KEYPAIR_JWT`
  - JWT claims include: iss, sub (account.user), iat, exp
  - JWT header includes kid (SHA256 fingerprint of public key)

---

#### 2026-01-27 | Phase 9.1.2: PAT Authentication Support | Cortex Analyst
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Added Programmatic Access Token (PAT) as a simpler authentication option for Cortex Analyst
- **Files Modified**:
  - `/services/cortex_analyst_service.py` - Added dual auth support (PAT + key-pair)
  - `/listeners/commands.py` - Updated mock mode message
  - `.env.example` - Documented both auth options with setup instructions
- **Files Created**: None
- **Dependencies Added**: None (PAT uses existing `requests` library)
- **Breaking Changes**: None - existing key-pair auth still works, PAT is additive
- **Key Features Implemented**:
  - **PAT Authentication**: Simple token-based auth via `CORTEX_ANALYST_PAT` env var
  - **Auth Method Priority**: PAT checked first (simplest), then key-pair (more secure)
  - **Auth Method Tracking**: New `auth_method` attribute tracks which auth is in use
  - **Refactored Init**: Extracted `_configure_authentication()` for cleaner code
  - **Updated Headers**: PAT uses `X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN`
- **Why PAT Added**:
  - Snowflake REST API doesn't support WIF (Workload Identity Federation) directly
  - PAT is simpler than key-pair: no RSA key generation, no file management
  - Good for quick setup, testing, and users who can't manage RSA keys
  - Key-pair remains recommended for production (no expiration)
- **Auth Method Comparison**:
  | Method | Setup Complexity | Security | Expiration |
  |--------|-----------------|----------|------------|
  | PAT | Low (UI-generated) | Medium | Yes (90 days typical) |
  | Key-Pair | Medium (openssl) | High | No |
- **PAT Setup Steps**:
  1. Snowsight → Settings → Authentication
  2. Generate new token under "Programmatic Access Tokens"
  3. Copy token immediately (shown only once)
  4. Set `CORTEX_ANALYST_PAT=<token>` in `.env`
- **Testing**: Code review confirms both auth paths work correctly
- **Notes**:
  - Based on research: WIF is Snowflake's preferred auth but only works with drivers, not REST API
  - Per Snowflake docs, REST API supports: OAuth, Key-Pair JWT, and PAT
  - OAuth deemed overkill for service-to-service communication
  - Mock mode message updated to mention both auth options

---

#### 2026-01-27 | Bug Fix: /company Command Registration | Listeners
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Fixed critical bug where /company command was never registered with Slack
- **Files Modified**:
  - `/listeners/commands.py` - Extracted /company handler from nested position inside /ask-deal-agent
- **Files Created**: None
- **Dependencies Added**: None
- **Breaking Changes**: None - this is a bug fix that enables existing functionality
- **Bug Description**:
  - The `/company` slash command handler (lines 190-239) was incorrectly indented inside the `handle_ask_deal_agent` function
  - This meant `@app.command("/company")` was a nested function definition, never actually registered with Slack
  - The `_build_company_response_blocks` helper function was also orphaned outside the registration scope
- **Fix Applied**:
  - Created new `register_company_command(app, aggregator)` function to properly register /company
  - Called this function from `register_command_listeners()` before /ask-deal-agent registration
  - Updated mock mode message to reference `SNOWFLAKE_PRIVATE_KEY_PATH` (was incorrectly referencing deprecated `CORTEX_ANALYST_PAT`)
- **Testing**: Manual code review confirms proper function scoping and registration flow
- **Notes**:
  - This bug likely occurred during Phase 9.1 when /ask-deal-agent was added
  - The /company command should now work as intended when users type `/company Acme Corp`
  - No changes needed to Cortex Analyst integration - it was already correctly implemented

---

#### 2026-01-29 | Phase 9.1.3: SSE Event-Type Parsing for Cortex Agents | Cortex Analyst
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Rewrote SSE response parsing to use official Snowflake event types instead of phrase matching
- **Files Modified**:
  - `/services/cortex_analyst_service.py` - Complete rewrite of `_parse_sse_response()` method
- **Files Created**: None
- **Dependencies Added**: None
- **Breaking Changes**: None - improved reliability of existing feature
- **Problem Solved**:
  - Previous approach used phrase matching ("Based on...", "Here are...") to identify final answers
  - This was fragile and failed when table data was streamed across multiple events
  - Queries like "top 10 highest EBITDAs" returned only intro text, not the actual table
- **Solution Implemented**:
  - Parse SSE `event:` lines to identify event types per Snowflake documentation
  - Collect only `response.text.delta` events (final answer tokens)
  - Ignore `response.thinking.delta` events (internal reasoning)
  - Fall back to `response` event for aggregated final response
- **Event Types (per Snowflake docs)**:
  | Event Type | Purpose | Action |
  |------------|---------|--------|
  | `response.thinking.delta` | Internal reasoning | Ignore |
  | `response.text.delta` | Final answer tokens | Collect |
  | `response` | Aggregated response | Fallback |
- **Documentation Reference**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
- **Testing**: Verified with multiple query types:
  - Simple questions (deals in 2025) - Working
  - Range queries (EBITDA $20-100MM) - Working
  - Table queries (top 10 EBITDAs) - Working (was broken before)
- **Notes**:
  - This approach is much more reliable than phrase matching
  - Works regardless of how the agent phrases its response
  - Properly handles multi-part streaming responses (tables, lists, etc.)

---

#### 2026-01-29 | v0.1 MVP Release | Milestone
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Marked v0.1 as official MVP release with working Cortex Agent integration
- **Key Features in v0.1**:
  - Slack bot with Socket Mode connection
  - `/ask-deal-agent` command for deal/pipeline analytics via Snowflake Cortex Agents
  - `/company` command for aggregated company context (Salesforce + knowledge base)
  - Snowflake Cortex AI for general conversational responses
  - RAG with vector search and knowledge base
  - Conversation memory and context awareness
  - Dual authentication support (PAT + JWT key-pair)
  - Comprehensive logging and metrics
  - Mock mode for development without credentials
- **Upcoming Phases** (post-offsite planning):
  - Salesforce integration improvements
  - LevPro integration
  - CI/CD pipeline setup
  - Additional Cortex Agents/Analysts

---

#### 2026-01-30 | Phase 10: Salesforce OAuth & Deal Creation | v0.2 Release
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Implemented Salesforce OAuth authentication and deal creation from Slack threads
- **Files Created**:
  - `/services/deal_parser.py` - Deal message parser with regex-based extraction
- **Files Modified**:
  - `/services/sf_client.py` - Added OAuth token refresh, account search, opportunity creation
  - `/workflows/salesforce.py` - Added deal creation modal, account lookup helpers, TBD fallback
  - `/listeners/messages.py` - Added "add new deal" thread detection and handling
  - `.env.example` - Updated with OAuth configuration section
- **Dependencies Added**: None (uses existing simple-salesforce library)
- **Breaking Changes**: None - OAuth is recommended but session ID still works as fallback
- **Key Features Implemented**:
  - **Salesforce OAuth Web Server Flow**: Production-ready authentication with auto-refresh
    - Uses refresh token for stable, long-running connections
    - No more session ID expiration issues
    - Environment: `SF_CONSUMER_KEY`, `SF_CONSUMER_SECRET`, `SF_REFRESH_TOKEN`, `SF_INSTANCE_URL`
  - **Deal Creation from Slack Threads**:
    - "Add new deal" button appears in deal discussion threads
    - Modal pre-filled with parsed deal data
    - Creates Salesforce opportunity on submission
  - **Deal Parser Service**:
    - Extracts company name, EBITDA, sponsor, source, strategy, security type
    - Non-greedy regex patterns prevent over-matching
    - Character limits and validation for clean extraction
  - **Account Lookup with TBD Fallback**:
    - `find_account_id()` searches accounts by name using SOSL
    - Falls back to "TBD" account if not found
    - Prevents validation errors on required lookup fields
    - Logs fallback usage for visibility
  - **Custom Salesforce Fields**:
    - `Strategy__c` - Deal strategy dropdown
    - `Security_Type__c` - Security classification
    - `Deal_Source_Account__c` - Account lookup for deal source
    - `Primary_Sponsor__c` - Account lookup for PE sponsor
- **Testing Verified**:
  - OAuth token refresh working with 30-day expiry
  - Opportunity created successfully (ID: 006VR00000Rwe5ZYAR)
  - Account lookups working (Houlihan Lokey, AEA Investors LLC)
  - TBD fallback functioning when account not found
- **Notes**:
  - This completes Phase 10 from the roadmap
  - Version bumped from 0.1.0 to 0.2.0
  - Next steps: Azure deployment, callback URL updates for production

---

#### 2026-01-30 | Phase 12: Azure Deployment | Infrastructure
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Added Azure Container Instance deployment infrastructure and CI/CD pipeline
- **Files Created**:
  - `/scripts/deploy-azure.sh` - Azure deployment script with build/deploy/logs/restart commands
  - `/docs/AZURE_DEPLOYMENT.md` - Comprehensive deployment guide
- **Files Modified**:
  - `/services/sf_oauth.py` - Made callback URL configurable via `SF_OAUTH_CALLBACK_URL` env var
  - `/.github/workflows/cd.yml` - Replaced placeholder steps with real Azure deployment
  - `/.env.example` - Added Azure deployment configuration section
- **Dependencies Added**: None
- **Breaking Changes**: None - existing local development workflow unchanged
- **Key Features Implemented**:
  - **Azure Container Instance Deployment**:
    - Single container deployment (no Kubernetes overhead)
    - Socket Mode (outbound WebSocket only, no public ingress)
    - 1 CPU, 1.5GB RAM configuration (~$40/month)
    - Always-on restart policy
  - **Azure Key Vault Integration**:
    - All secrets stored in Key Vault (not in code or env files)
    - Secrets fetched at deployment time via Azure CLI
    - Secure environment variables (not visible in logs)
  - **Deployment Script** (`scripts/deploy-azure.sh`):
    - `build` - Build and push Docker image to ACR
    - `deploy` - Deploy/update container instance
    - `logs` - Stream container logs
    - `restart` - Restart container
    - `status` - Show container status
    - `all` - Full build and deploy (default)
  - **GitHub Actions CD Pipeline**:
    - Automatic deployment on push to `main` or version tags
    - Build job: smoke tests, Docker build, push to ACR
    - Deploy job: fetch secrets from Key Vault, create container
    - Verify job: check container status, fail on error
    - Rollback workflow dispatch available
  - **OAuth Callback URL Configurability**:
    - Default: `http://localhost:8080/callback` (development)
    - Configurable via `SF_OAUTH_CALLBACK_URL` for production
- **Architecture**:
  ```
  Azure Resource Group (rg-elli-prod)
  ├── Container Registry (elliacr)
  ├── Key Vault (kv-elli-prod)
  └── Container Instance (aci-elli-prod)
  ```
- **Required GitHub Secrets**:
  - `AZURE_CREDENTIALS` - Service principal JSON for Azure login
  - `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` - For smoke tests
- **Notes**:
  - This completes Phase 12 from the roadmap
  - Direct to production (no staging environment per user preference)
  - Future consideration: Chart generation from Cortex Agent SQL responses

---

#### 2026-02-03 | Phase 13: Production Hardening & Channel-Based Opportunities | v0.3 Release
- **Agent**: Claude Code (Opus 4.5)
- **Changes**: Production hardening and channel-based Opportunity RecordType mapping for Azure deployment
- **Files Created**:
  - `/healthcheck.py` - Python health check script for Docker HEALTHCHECK
  - `/config/channel_config.py` - Channel → Business Unit → RecordTypeId configuration manager
  - `/config/__init__.py` - Config package initialization
- **Files Modified**:
  - `/app.py` - Added graceful shutdown handlers (SIGTERM/SIGINT) and startup validation
  - `/Dockerfile` - Updated HEALTHCHECK to use `python healthcheck.py`
  - `/listeners/messages.py` - Added `business_unit` and `record_type_id` to DealSession dataclass
  - `/workflows/salesforce.py` - Added RecordTypeId to opportunity creation, JSON private_metadata with channel_id
  - `/.env.example` - Added channel configuration section with examples
  - `/scripts/deploy-azure.sh` - Added channel config env vars (CHANNEL_BU_MAPPING, BU_RECORD_TYPES, BU_FIELD_DEFAULTS)
- **Dependencies Added**: None
- **Breaking Changes**: None - channel configuration is optional
- **Key Features Implemented**:
  - **Graceful Shutdown**:
    - Signal handlers for SIGTERM (container stop) and SIGINT (Ctrl+C)
    - Logs shutdown signal and exits cleanly
    - Ensures container orchestration works correctly
  - **Health Check Script** (`healthcheck.py`):
    - Verifies required env vars (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
    - Tests core module imports
    - Returns exit code 0 (healthy) or 1 (unhealthy)
    - Used by Docker HEALTHCHECK command
  - **Startup Validation**:
    - Checks required Slack tokens before starting
    - Warns about missing optional credentials (Salesforce, Snowflake, Cortex Analyst)
    - Fails fast with clear error messages
  - **Channel-Based Opportunity Types**:
    - `ChannelConfigManager` class with JSON configuration from env vars
    - Maps Slack channel ID → Business Unit name → Salesforce RecordTypeId
    - Supports default field values per business unit
    - `BusinessUnitConfig` dataclass for structured access
    - Singleton pattern with `channel_config` global instance
  - **DealSession Enhancements**:
    - Added `business_unit: Optional[str]` field
    - Added `record_type_id: Optional[str]` field
    - Auto-lookup from channel_config when creating session
  - **Opportunity Creation Updates**:
    - `private_metadata` now stores JSON with company and channel_id
    - Looks up RecordTypeId from channel_config at creation time
    - Adds RecordTypeId to opportunity data if configured
- **Environment Variables**:
  ```bash
  CHANNEL_BU_MAPPING='{"C12345ABC":"private_credit","C67890DEF":"re_credit"}'
  BU_RECORD_TYPES='{"private_credit":"012xxx","re_credit":"012yyy","default":"012zzz"}'
  BU_FIELD_DEFAULTS='{"private_credit":{"Strategy__c":"Corporate Credit"}}'
  ```
- **Testing**: All 72 existing tests pass after changes
- **Notes**:
  - This completes Phase 13 (Production Deployment) from the roadmap
  - Version bumped from 0.2.0 to 0.3.0
  - Ready for Azure Container Instance deployment
  - RecordTypeIds need to be obtained from Salesforce admin
  - Pilot channels ready for testing once RecordTypeIds configured

---

#### [Template for Future Entries]
```
#### YYYY-MM-DD | [Agent Name] | [Area Modified]
- **Agent**: [Your identifier - e.g., "Claude Code", "Gemini Code Assist", "Developer Name"]
- **Changes**: [Brief description of what was changed/added]
- **Files Modified**: [List of files changed]
- **Files Created**: [List of new files]
- **Dependencies Added**: [Any new packages added to requirements.txt]
- **Breaking Changes**: [Any changes that might affect other parts of the codebase]
- **Notes**: [Additional context, decisions made, things to watch out for]
```

---

## Current Implementation Status

### ✅ Working Features
- Socket Mode connection and authentication
- **Phase 2 Complete**: Smart Salesforce integration with entity extraction
  - Regex patterns extract company names and target stages from messages
  - Intelligent search with 0/1/multiple result handling
  - Pre-filled modals with opportunity data
  - Real Salesforce API integration (with mock fallback)
- **Phase 3 Complete**: Snowflake Cortex AI integration
  - Real LLM responses using Snowflake Cortex `llama3-70b` model
  - App mention handling with AI responses
  - Direct message handling with AI responses
  - Enhanced mock mode with keyword-based responses
  - Graceful fallback when Snowflake credentials unavailable
- **Phase 4 Complete**: Conversation memory and context awareness
  - Thread-aware AI responses with 5-message history
  - Context-aware prompting with conversation history
  - Pronoun resolution ("update it" → references previous entities)
  - Entity extraction from conversation history
  - Works in both threads and DMs
- Salesforce modal with opportunity name and stage selection
- Duplicate response prevention with smart workflow detection
- Legacy "update salesforce" command still supported

### 🚧 Placeholder/Mock Components
- None! All core features now have real implementations with mock fallbacks

### 📋 Planned Features (Roadmap)
- ✅ **Phase 1**: Modular refactoring (Complete)
- ✅ **Phase 2**: Entity extraction and smart Salesforce search (Complete)
- ✅ **Phase 3**: Real LLM integration with Snowflake Cortex (Complete)
- ✅ **Phase 4**: Conversation memory and context awareness (Complete)
- ✅ **Phase 5.1**: RAG with vector search and knowledge base (Complete)
- ✅ **Phase 5.2**: Semantic memory (long-term conversation summaries) (Complete)
- ✅ **Phase 5.3**: Salesforce RAG integration (hybrid search with CRM data) (Complete)
- ⏸️ **Phase 6**: Additional Salesforce workflows (TABLED - no longer priority)
- ✅ **Phase 7**: Logging and monitoring (Complete)
- ✅ **Phase 8**: Unit tests and integration tests (Complete)
- ✅ **Phase 8.1**: Code quality refactoring (Complete) - Thread safety, DRY, input validation
- ✅ **Phase 9.1**: Cortex Analyst integration (Complete) - DEAL_AGENT via REST API
- ✅ **Phase 9.1.1**: JWT key-pair auth for Cortex Analyst (Complete) - No stored secrets
- ✅ **Phase 9.1.2**: PAT authentication support (Complete) - Simpler auth option
- ✅ **Phase 9.1.3**: SSE event-type parsing (Complete) - Reliable response extraction
- **🎉 v0.1 MVP RELEASED** - Core functionality complete and tested
- ✅ **Phase 10**: Salesforce OAuth & deal creation (Complete) - v0.2 release
- **🎉 v0.2 RELEASED** - Salesforce integration complete with OAuth and deal creation
- ✅ **Phase 12**: Azure deployment & CI/CD pipeline (Complete)
- ✅ **Phase 13**: Production hardening & channel-based Opportunities (Complete) - v0.3 release
- **🎉 v0.3 RELEASED** - Production deployment with channel-based Opportunity types
- **Phase 9.2**: Snowflake enterprise data integration (Planned) - Financial data, portfolio exposure
- **Phase 11**: LevPro integration (Planned - post-pilot)
- **Future**: Chart generation from Cortex Agent SQL responses (matplotlib/plotly)

---

## Anti-Patterns to Avoid

### ❌ Don't Do This
- **Hardcoding secrets**: `token = "xoxb-123456789"`
- **Monolithic functions**: 100+ line functions doing multiple things
- **Mixing concerns**: Putting workflow logic in listener files
- **Ignoring types**: `def update(data)` without type hints
- **Global state**: Using global variables for configuration
- **Direct API calls in listeners**: Listeners should delegate to services

### ✅ Do This Instead
- **Environment variables**: `token = os.environ.get("SLACK_BOT_TOKEN")`
- **Small, focused functions**: Each function does one thing well
- **Separation of concerns**: Listeners → Workflows → Services
- **Type hints**: `def update(data: dict) -> bool:`
- **Configuration objects**: Pass config through initialization
- **Service layer**: Listeners call workflows, workflows call services

---

## Testing Guidelines (Future)

When adding tests, follow this structure:
```
/tests
├── test_listeners/
├── test_workflows/
└── test_services/
```

- Use `pytest` as the testing framework
- Mock external API calls (Slack, Salesforce, LLM)
- Aim for >80% code coverage on business logic
- Test edge cases and error handling

---

## Questions or Clarifications?

If you're unsure about:
- **Architecture decisions**: Check [README.md](README.md) first
- **Recent changes**: Review the Breadcrumb Log in this file
- **Code patterns**: Look at existing implementations in the codebase
- **New features**: Discuss approach before implementing to avoid conflicts

---

## Version History

- **v1.0** (2026-01-14): Initial AGENTS.md creation with breadcrumbs system
