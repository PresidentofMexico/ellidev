# Changelog

All notable changes to the Elli project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned (Post-Offsite)
- Phase 9.2: Snowflake enterprise data integration (financial data, portfolio exposure)
- Phase 11: LevPro integration
- Phase 6: Additional Salesforce workflows (TABLED)

### Future Considerations
- **Chart Generation**: Extract SQL from Cortex Agent responses, execute queries, generate charts with matplotlib/plotly, upload images to Slack

---

## [0.3.0] - 2026-02-03 - v0.3 Production Deployment Release

### Milestone
This release marks **v0.3 Production Deployment** - production hardening and channel-based Opportunity types for Azure deployment.

### Added
- **Production Hardening**:
  - Graceful shutdown handlers (SIGTERM/SIGINT) for clean container termination
  - Startup validation with clear error messages for missing credentials
  - Improved health check script (`healthcheck.py`) verifying env vars and module imports
  - Updated Dockerfile HEALTHCHECK to use Python health check script
- **Channel-Based Opportunity RecordTypes**:
  - New `config/channel_config.py` module for Slack channel → Business Unit mapping
  - `ChannelConfigManager` class with JSON-based configuration from environment variables
  - RecordTypeId assignment based on which Slack channel the deal was created from
  - Default field values per business unit (e.g., Strategy__c)
  - `BusinessUnitConfig` dataclass for structured configuration
- **DealSession Enhancements**:
  - Added `business_unit` and `record_type_id` fields to `DealSession` dataclass
  - Auto-lookup of business unit config when creating deal sessions
- **Environment Variables**:
  - `CHANNEL_BU_MAPPING` - JSON mapping channel IDs to business unit names
  - `BU_RECORD_TYPES` - JSON mapping business units to Salesforce RecordTypeIds
  - `BU_FIELD_DEFAULTS` - JSON mapping business units to default field values

### Changed
- **`app.py`**: Added signal handlers and startup validation
- **`Dockerfile`**: Updated HEALTHCHECK command to use `healthcheck.py`
- **`listeners/messages.py`**: Added business unit lookup when creating DealSession
- **`workflows/salesforce.py`**: Added RecordTypeId to opportunity creation, JSON private_metadata with channel_id
- **`.env.example`**: Documented channel configuration variables
- **`scripts/deploy-azure.sh`**: Added channel config env vars to deployment

### Technical Details
- **Graceful Shutdown**: Handles SIGTERM (container stop) and SIGINT (Ctrl+C) with logging
- **Startup Validation**: Checks required tokens, warns about optional credentials
- **Channel Config**: Singleton pattern with environment variable reload support
- **RecordType Assignment**: Looks up channel → BU → RecordTypeId at opportunity creation time

### Testing
- ✅ All 72 existing tests pass after changes
- ✅ Graceful shutdown verified with manual SIGTERM
- ✅ Health check verified in Docker container
- ⏳ Channel-based RecordTypes pending Salesforce admin RecordTypeId values

### Breaking Changes
- None - All existing functionality preserved
- Channel configuration is optional (disabled by default if env vars not set)

---

## [0.2.0] - 2026-01-30 - v0.2 Salesforce Integration Release

### Milestone
This release marks **v0.2 Salesforce Integration** - full OAuth authentication and deal creation from Slack threads.

### Added
- **Salesforce OAuth Web Server Flow**: Production-ready authentication replacing session IDs
  - Refresh token auto-renewal for stable, long-running connections
  - Secure authorization code exchange with PKCE
  - Environment variables: `SF_CONSUMER_KEY`, `SF_CONSUMER_SECRET`, `SF_REFRESH_TOKEN`, `SF_INSTANCE_URL`
- **"Add New Deal" Thread Reply**: Create Salesforce opportunities directly from deal messages
  - Detects deal-related messages in Slack threads
  - Parses deal information from message content
  - Extracts: company name, sponsor, deal source, strategy, security type
  - Pre-fills modal with parsed data for quick opportunity creation
- **Account Lookup with TBD Fallback**: Intelligent lookup for Deal Source Account and Primary Sponsor
  - Searches Salesforce accounts by name using SOSL
  - Falls back to "TBD" account if exact match not found
  - Logs fallback usage for visibility and debugging
  - Prevents validation errors on required lookup fields
- **Custom Salesforce Fields Support**:
  - `Strategy__c` - Deal strategy selection (dropdown)
  - `Security_Type__c` - Security type classification (dropdown)
  - `Deal_Source_Account__c` - Account lookup field for deal source
  - `Primary_Sponsor__c` - Account lookup field for PE sponsor
- **Deal Parser Service**: `services/deal_parser.py` (new file)
  - Regex-based extraction from deal messages
  - Company name detection with intelligent parsing
  - EBITDA extraction with range support
  - Sponsor, source, and stage detection
  - Validation to prevent greedy regex matching

### Changed
- **`services/sf_client.py`**: Major enhancements
  - Added OAuth token refresh mechanism with automatic renewal
  - Added `search_accounts()` method for account lookup
  - Added `create_opportunity()` method for deal creation
  - Enhanced error handling with detailed logging
- **`workflows/salesforce.py`**: New deal creation workflow
  - Added `handle_create_submission()` for opportunity creation
  - Added `find_account_id()` helper with TBD fallback logic
  - Added deal creation modal with all custom fields
  - Pre-fill support for parsed deal data
- **`listeners/messages.py`**: Thread reply detection
  - Added "add new deal" button detection in threads
  - Added deal message parsing and modal pre-fill
  - Integration with deal parser service

### Technical Details
- **OAuth Flow**: Web Server Flow (authorization code + PKCE) per Salesforce best practices
- **Account Search**: SOSL query with fuzzy matching for flexible name lookups
- **Deal Parser**: Non-greedy regex patterns with character limits to prevent over-matching
- **TBD Fallback**: Searches for account named "TBD" as placeholder when lookup fails
- **Field Mapping**: Custom fields mapped to Slack modal inputs with validation

### Testing
- ✅ OAuth token refresh verified with 30-day expiry
- ✅ Deal creation tested end-to-end (Opportunity ID: 006VR00000Rwe5ZYAR)
- ✅ Account lookup verified (Houlihan Lokey, AEA Investors LLC)
- ✅ TBD fallback tested when account not found
- ✅ Deal parser tested with various message formats
- ✅ Custom fields populated correctly in Salesforce

### Breaking Changes
- None - All existing functionality preserved
- OAuth is now the recommended authentication method (session ID deprecated)

---

## [0.1.0] - 2026-01-29 - v0.1 MVP Release

### Milestone
This release marks the **v0.1 MVP** - the first fully functional version of Elli with Snowflake Cortex Agent integration.

### Added
- **`/ask-deal-agent` Slash Command**: Query deal/pipeline data via Snowflake Cortex Agents
  - Natural language queries about deals, EBITDA, pipeline, etc.
  - Real-time data from DEAL_AGENT semantic model
  - Table and list responses properly formatted for Slack
- **Cortex Agents REST API Integration**: `services/cortex_analyst_service.py`
  - SSE (Server-Sent Events) streaming response parsing
  - Event-type based parsing (`response.text.delta` vs `response.thinking.delta`)
  - Proper separation of thinking steps vs final answer
- **Dual Authentication Support**:
  - PAT (Programmatic Access Token) - Simple setup for development
  - JWT Key-Pair - Secure option for production (no stored secrets)
- **SSE Event-Type Parsing**: Per Snowflake documentation
  - Collects only `response.text.delta` events (final answer)
  - Ignores `response.thinking.delta` events (internal reasoning)
  - Falls back to `response` event for aggregated response

### Changed
- **Version**: Updated from 0.8.0 to 0.1.0 MVP
- **README.md**: Updated for v0.1 MVP with new features and examples
- **AGENTS.md**: Added Phase 9.1.3 breadcrumb and v0.1 milestone entry

### Technical Details
- **API Endpoint**: `/api/v2/databases/{db}/schemas/{schema}/agents/{name}:run`
- **Event Types** (per [Snowflake docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run)):
  | Event Type | Purpose | Action |
  |------------|---------|--------|
  | `response.thinking.delta` | Internal reasoning | Ignore |
  | `response.text.delta` | Final answer tokens | Collect |
  | `response` | Aggregated response | Fallback |

### Testing
- ✅ Simple questions (e.g., "how many deals in 2025") - Working
- ✅ Range queries (e.g., "EBITDA between $20-100MM") - Working
- ✅ Table queries (e.g., "top 10 by EBITDA") - Working
- ✅ Mock mode for development without credentials - Working

### Breaking Changes
- None - All existing functionality preserved

---

## [0.8.0] - 2026-01-15 - Phase 8: Unit Tests and Integration Tests

### Added
- Comprehensive test framework with pytest
- Unit tests for all core services
- Integration tests for end-to-end flows
- Code coverage tracking (>70% target)

---

## [0.7.0] - 2026-01-15 - Phase 7: Logging and Monitoring

### Added
- **Structured Logging Service**: `services/logger.py` (450+ lines)
  - JSON-formatted logging for production monitoring
  - Text-formatted logging for development
  - Multiple log levels (INFO, WARNING, ERROR, DEBUG)
  - Console and file output handlers
  - Separate query audit log in JSON Lines format
- **Logging Features**:
  - `log_query()`: Track all user queries with duration, success, sources used
  - `log_api_call()`: Monitor external API calls (Salesforce, Snowflake Cortex)
  - `log_rag_search()`: RAG search operations with relevance scores
  - `log_error()`: Comprehensive error logging with stack traces and context
  - `log_workflow()`: Salesforce workflow execution tracking
  - `log_memory_operation()`: Semantic memory operations (summarize, retrieve)
- **Performance Metrics Service**: `services/metrics.py` (350+ lines)
  - In-memory time-windowed metrics (60-minute rolling window)
  - Query response time statistics (p50, p95, p99, avg, min, max)
  - API call tracking by service and method with success rates
  - RAG search performance metrics
  - Error rate tracking by component
  - Cache hit/miss tracking (for future caching)
- **Query Audit Trail**: `logs/query_audit.jsonl`
  - Complete logging of all user interactions
  - JSON Lines format for easy parsing
  - Includes user_id, query, query_type, duration, success, sources used
  - Compliance and analytics ready
- **Logging Configuration**: Added to `.env.example`
  - LOG_LEVEL (default: INFO)
  - LOG_FORMAT (json or text)
  - LOG_FILE (default: logs/elli.log)
  - QUERY_AUDIT_FILE (default: logs/query_audit.jsonl)
  - ENABLE_METRICS (default: true)

### Changed
- **`listeners/mentions.py`**: Integrated comprehensive logging
  - Query timing (start to finish)
  - Query type classification (rag_search vs direct_ai)
  - Source tracking (document, salesforce_record, conversation_memory)
  - Memory operation logging (summarize, retrieve with details)
  - Success/failure tracking with error context
  - Metrics recording for all queries
- **`services/rag_service.py`**: Added RAG operation logging
  - Vector search timing and result counts
  - Source relevance scores and types
  - Snowflake Cortex API call timing
  - Error context with query details
  - Metrics recording for searches and API calls
- **`services/sf_client.py`**: Added Salesforce API logging
  - Connection status logging
  - Search operation timing with result counts
  - Update operation workflow logging
  - API call success/failure tracking
  - Error context with operation details
  - Metrics recording for all API calls
- **`services/ai_service.py`**: Added AI service logging
  - Connection status logging
  - Cortex API call timing and context
  - Query logging with history indicator
  - Error tracking with full context
  - Metrics recording for API calls

### Features
- **Production Monitoring**: JSON logs integrate with log aggregation tools (ELK, Splunk, Datadog)
- **Performance Tracking**: Identify slow queries and API bottlenecks with p50/p95/p99 metrics
- **Error Detection**: Proactive error monitoring with full stack traces and context
- **Audit Compliance**: Complete query audit trail for compliance requirements
- **Development Debugging**: Text logs for local development with detailed context
- **Metrics API**: Programmatic access to metrics for dashboards and alerting
- **Snowflake Prep**: Logging infrastructure ready for Snowflake SQL debugging

### Technical Details
- **Singleton Pattern**: Both logger and metrics use singleton pattern for global access
- **Time-Windowed Metrics**: 60-minute rolling window with automatic cleanup
- **Log Rotation**: Supports standard log rotation (configure at OS/infrastructure level)
- **Performance Impact**: Minimal overhead (~0.5ms per log, ~0.1ms per metric)
- **Async Logging**: File handlers provide async-like performance
- **Mock Mode Support**: All logging works without Snowflake/Salesforce credentials

### Backward Compatibility
- ✅ All Phase 1-5.3 functionality remains intact
- ✅ Logging is additive only (no behavior changes)
- ✅ Metrics collection is optional (ENABLE_METRICS=true/false)
- ✅ Logs directory created automatically
- ✅ Graceful fallback if log directory unwritable
- ✅ No breaking changes to existing workflows

### Performance
- Minimal logging overhead (~0.5ms per entry)
- Efficient in-memory metrics (~0.1ms per record)
- No database queries for logging
- Automatic cleanup of old metrics
- Optional metrics (can be disabled)

### Usage Examples

**Query Audit Entry**:
```json
{
  "timestamp": "2026-01-15T10:30:00Z",
  "user_id": "U12345",
  "channel_id": "C67890",
  "query": "What opportunities are in negotiation?",
  "query_type": "rag_search",
  "duration_ms": 245.3,
  "success": true,
  "sources_used": ["salesforce_record"],
  "results_count": 3
}
```

**Metrics Access**:
```python
from services.metrics import metrics

stats = metrics.get_all_stats()
print(f"Query p95: {stats['query_times']['p95_ms']}ms")
print(f"SF Success Rate: {stats['api_calls']['salesforce']['success_rate']:.1%}")
```

**Log Viewing**:
```bash
# Main log
tail -f logs/elli.log

# Audit trail
tail -f logs/query_audit.jsonl

# Parse JSON logs
cat logs/elli.log | jq '.level="ERROR"'
```

### Design Decisions
- **JSON Format**: Chosen for production monitoring and log aggregation tools
- **Separate Audit Log**: Query audit trail separate for compliance and analytics
- **In-Memory Metrics**: 60-minute window balances memory usage with real-time data
- **Singleton Pattern**: Global access to logger and metrics without dependency injection
- **Time-Windowed Cleanup**: Automatic cleanup prevents memory growth

### Known Issues
- **Cognitive Complexity**: `listeners/mentions.py` has complexity of 143 (threshold 15)
  - Tracked for Phase 8 (Code Quality refactoring)
  - Does not affect functionality or logging
- **Code Duplication**: Some literal strings duplicated (e.g., "cortex.complete")
  - Tracked for Phase 8 (Code Quality refactoring)
  - Does not affect functionality

---

## [0.6.0] - 2026-01-14 - Phase 5.3: Salesforce RAG Integration

### Added
- **SalesforceRAG Service**: `services/salesforce_rag.py` (550+ lines)
  - Fetches opportunities, accounts, and contacts from Salesforce
  - Formats CRM records as vector store chunks for semantic search
  - Handles both real Salesforce API and mock mode
  - Configurable object types and record limits
- **Salesforce Data Features**:
  - `fetch_opportunities()`: Retrieves recent opportunities with all relevant fields
  - `fetch_accounts()`: Retrieves accounts with industry, description, contact info
  - `fetch_contacts()`: Retrieves contacts with title, email, phone, account
  - `format_opportunity_chunk()`: Formats opportunities for vector search
  - `format_account_chunk()`: Formats accounts for vector search
  - `format_contact_chunk()`: Formats contacts for vector search
  - `ingest_salesforce_data()`: Batch ingestion with progress tracking
- **CLI Ingestion Tool**: `scripts/ingest_salesforce.py` (150 lines)
  - On-demand Salesforce data synchronization
  - Supports `--objects` flag to choose which object types to sync
  - Supports `--limit` flag to control record volume
  - Supports `--refresh` flag for future refresh functionality
  - Progress reporting and statistics summary
- **Hybrid Search Architecture**:
  - Searches across both static documents AND live Salesforce data
  - Unified ranking and presentation of mixed sources
  - Semantic search over CRM records using same vector store
- **Salesforce RAG Configuration**: Added to `.env.example`
  - SALESFORCE_RAG_ENABLED (default: true)
  - SALESFORCE_RAG_OBJECTS (default: opportunities,accounts,contacts)
  - SALESFORCE_RAG_LIMIT (default: 100 records per object)

### Changed
- **`services/rag_service.py`**: Enhanced CRM query detection
  - Added 20+ CRM-specific keywords to `should_use_rag()`
  - Keywords: opportunity, deal, pipeline, account, customer, contact, stage, close date, amount
  - Automatically routes CRM queries to RAG pipeline
- **`listeners/mentions.py`**: Enhanced source formatting
  - Distinguishes between document sources and Salesforce records
  - Opportunity sources show: Name - $Amount (Stage) [Salesforce]
  - Contact sources show: Name, Title [Salesforce Contact]
  - Account sources show: Name [Salesforce Account]
  - Document sources show: Document Name [Document]
  - Applied to both `handle_mentions()` and `handle_dm()`

### Features
- **Hybrid Search**: Seamlessly combines knowledge base documents with live CRM data
- **Smart CRM Detection**: Automatically detects queries about deals, accounts, contacts
- **Enhanced Citations**: Clear visual distinction between document and Salesforce sources
- **On-Demand Sync**: CLI tool allows manual data refresh when needed
- **Mock Mode**: Full CRM RAG functionality without Salesforce credentials
- **Metadata Preservation**: Stores stage, amount, close date, title, email in metadata

### Technical Details
- **Record Formatting**:
  - Opportunities: Name, account, stage, amount, close date, owner, description
  - Accounts: Name, industry, description, website, employees, phone, location
  - Contacts: Name, title, email, phone, account, owner
- **Chunk Structure**:
  ```python
  {
    "chunk_id": "sf_opportunity_{id}",
    "document_id": "salesforce_opportunities",
    "content": "Formatted record text",
    "metadata": {
      "type": "salesforce_record",
      "object_type": "Opportunity",
      "record_id": id,
      "stage": stage,
      "amount": amount,
      ...
    }
  }
  ```
- **Storage**: CRM records stored alongside knowledge base chunks, differentiated by metadata type
- **Query Detection**: 20+ CRM keywords trigger RAG pipeline automatically
- **Source Attribution**: Metadata type determines formatting in response citations

### Backward Compatibility
- ✅ All Phase 1-5.2 functionality remains intact
- ✅ Salesforce RAG is opt-in (controlled by SALESFORCE_RAG_ENABLED)
- ✅ Falls back to regular AI response if disabled or no SF credentials
- ✅ No breaking changes to existing workflows
- ✅ Works in mock mode with sample CRM data
- ✅ Static knowledge base works independently

### Performance
- Lightweight record formatting (no complex transformations)
- Batch ingestion reduces API calls
- Configurable limits prevent overwhelming vector store
- Reuses existing vector search infrastructure
- Mock mode provides instant testing without API latency

### Testing
- ✅ Syntax validation passed for all new and modified files
- ✅ Mock mode tested with sample opportunities, accounts, contacts
- ✅ Hybrid search tested with mixed document and CRM sources
- ✅ Source formatting verified for all object types
- ✅ CRM query detection tested with various keywords
- ⏳ Real Salesforce API ingestion pending user credentials

### Usage Examples

**CRM Query**:
```
User: "What deals are in negotiation?"
Response: Lists opportunities with sources like:
  • Acme Corp Renewal - $250,000 (Negotiation) [Salesforce] (Relevance: 95%)
```

**Contact Lookup**:
```
User: "Who should I contact at TechStart?"
Response: Shows contact with sources like:
  • Michael Chen, VP Engineering [Salesforce Contact] (Relevance: 97%)
```

**Hybrid Query**:
```
User: "What's our pricing for customers like Acme Corp?"
Response: Combines both:
  • Product Info - Enterprise Tier [Document] (Relevance: 94%)
  • Acme Corp Account [Salesforce] (Relevance: 89%)
```

### CLI Tool Usage

```bash
# Sync all Salesforce data
python scripts/ingest_salesforce.py

# Sync only opportunities
python scripts/ingest_salesforce.py --objects opportunities

# Limit to 50 records per object
python scripts/ingest_salesforce.py --limit 50

# Sync with progress reporting
python scripts/ingest_salesforce.py --objects opportunities,accounts,contacts
```

### Design Decisions
- **On-Demand Sync (Option A)**: Simple, predictable, user-controlled refresh
  - Alternative (Option B - Scheduled): Cron-based auto-refresh (future phase)
  - Alternative (Option C - Real-Time): Webhook-based sync (complex, future phase)
- **Unified Vector Store**: Single storage for documents + CRM records
  - Simpler architecture, reuses existing infrastructure
  - Differentiated by metadata.type field
- **CLI Tool**: Manual control over data refresh
  - Acceptable for Phase 5.3.1, can enhance with automation later

---

## [0.5.1] - 2026-01-14 - Phase 5.2: Semantic Memory

### Added
- **Semantic Memory Service**: `services/semantic_memory.py` (350+ lines)
  - Long-term conversation memory beyond thread history
  - Auto-summarization every N messages (configurable interval)
  - LLM-based summary generation with structured output
  - Mock fallback with pattern-based entity extraction
  - Memory storage in vector store with metadata
  - Semantic search across past conversations
  - Relevance scoring: Similarity (50%) + Recency (30%) + User Match (20%)
- **Memory Features**:
  - `should_summarize()`: Checks if summary should be created based on message count
  - `generate_summary()`: Creates structured summaries with topic, entities, key points, conversation type
  - `store_memory()`: Saves summaries to vector store with full context
  - `retrieve_memories()`: Searches relevant past conversations with date filtering
  - `should_use_memory()`: Detects queries referencing past conversations
- **Three-Layer Context Architecture**:
  - Thread History: Last 5 messages (current session)
  - Semantic Memory: Past conversations (last 30 days)
  - Knowledge Base: Company documents (permanent)
- **Memory Configuration**: Added to `.env.example`
  - SEMANTIC_MEMORY_ENABLED (default: true)
  - MEMORY_SUMMARY_INTERVAL (default: 10 messages)
  - MEMORY_SEARCH_DAYS_BACK (default: 30 days)
  - MEMORY_TOP_K (default: 2 memories)

### Changed
- **`services/rag_service.py`**: Enhanced to accept memories parameter
  - `answer_with_context()` now accepts optional `memories` parameter
  - `_build_rag_prompt()` includes semantic memory section in prompts
  - `_generate_mock_rag_response()` references memory context
  - Response format includes `memories_used` array
- **`listeners/mentions.py`**: Integrated semantic memory
  - Added `semantic_memory` service initialization (singleton pattern)
  - Added `thread_message_counts` dictionary for in-memory tracking
  - Auto-summarization trigger after N messages (configurable)
  - Memory retrieval for queries referencing past conversations
  - Memory citation formatting in responses with dates
  - Applied to both `handle_mentions()` and `handle_dm()`
  - Fetches full thread history (50 messages) for summarization

### Features
- **Auto-Summarization**: Creates summaries every 10 messages by default
- **Smart Memory Retrieval**: Detects queries like "what did we discuss", "you mentioned", "earlier"
- **Memory Citations**: Responses include past conversation references with dates
- **Recency Bias**: More recent memories score higher (exponential decay with 30-day half-life)
- **User Context**: Memories filtered by user for privacy
- **Conversation Types**: Categorizes conversations (deal_inquiry, product_question, support_request, policy_question, general)

### Technical Details
- **Summary Structure**:
  ```json
  {
    "topic": "Brief one-sentence summary",
    "entities": ["Entity1", "Entity2"],
    "key_points": ["Point 1", "Point 2"],
    "conversation_type": "category",
    "message_count": 10
  }
  ```
- **Relevance Score Formula**: `0.5 * similarity + 0.3 * recency + 0.2 * user_match`
- **Memory Storage**: Stored as vector chunks with type "conversation_memory"
- **In-Memory Tracking**: Module-level dictionary tracks message counts per thread
- **Date Filtering**: Only retrieves memories from last N days (configurable)

### Backward Compatibility
- ✅ All Phase 1-5.1 functionality remains intact
- ✅ Semantic memory is optional (controlled by SEMANTIC_MEMORY_ENABLED)
- ✅ Falls back to regular RAG/AI response if memory disabled
- ✅ No breaking changes to existing workflows
- ✅ Works in mock mode without Snowflake credentials
- ✅ In-memory tracking resets on restart (acceptable for MVP)

### Performance
- Lightweight in-memory message count tracking
- Summarization only at configurable intervals (default: every 10 messages)
- Limited memory search window (default: 30 days)
- Top-K filtering reduces noise (default: 2 memories)
- Efficient vector search reuses existing infrastructure

### Testing
- ✅ Syntax validation passed for all modified files
- ✅ Mock mode tested with pattern-based summarization
- ✅ Memory retrieval tested with relevance scoring
- ✅ Three-layer context integration verified
- ⏳ Real Snowflake Cortex memory generation pending user credentials

### Design Decisions
- **Option A Selected**: In-memory message count tracking for Phase 5.2.1
  - Simple, fast implementation
  - No additional vector store queries
  - Trade-off: Resets on bot restart (acceptable for MVP)
- **Three Context Layers**: Provides comprehensive context without overwhelming LLM
- **Auto-Summarization**: Triggered by message count (not time) for predictability
- **Relevance Scoring**: Weighted combination balances semantic match, recency, and user privacy

---

## [0.5.0] - 2026-01-14 - Phase 5.1: RAG with Vector Search

### Added
- **RAG Pipeline**: Retrieval Augmented Generation for knowledge-based queries
  - Semantic search over document chunks
  - Context augmentation with retrieved information
  - Source citation in AI responses
- **Vector Store Service**: `services/vector_store.py`
  - Snowflake Cortex integration for vector storage and search
  - Mock in-memory fallback for testing without Snowflake
  - CRUD operations: ingest, search, get, delete
  - Statistics tracking (total chunks, documents)
- **Document Chunking Service**: `services/chunking.py`
  - Token-based chunking with configurable size (default 500 tokens)
  - Overlapping chunks for context preservation (default 50 tokens)
  - Sentence-aware splitting with markdown header preservation
  - Batch processing support
- **RAG Service**: `services/rag_service.py`
  - Full RAG pipeline orchestration
  - Query classification (should_use_rag)
  - Relevance threshold filtering (default 0.3)
  - Mock mode with keyword-based search
- **Knowledge Base**: `/knowledge` directory
  - Sample documents: product_info.md, sales_playbook.md, company_faq.md
  - Documentation: knowledge/README.md with guidelines
- **CLI Ingestion Tool**: `scripts/ingest_knowledge.py`
  - Recursive directory scanning
  - Batch document processing
  - Progress reporting and statistics
  - Support for single files or directories

### Changed
- **`listeners/mentions.py`**: Added RAG capability
  - Integrated RAG service for knowledge-based queries
  - Smart query routing (RAG vs regular AI)
  - Source formatting in responses
  - Works for both app mentions and DMs
- **`.env.example`**: Added RAG configuration
  - RAG_ENABLED (default: true)
  - RAG_TOP_K (default: 3)
  - RAG_CHUNK_SIZE (default: 500)
  - RAG_CHUNK_OVERLAP (default: 50)
- **`requirements.txt`**: Added Phase 5 dependencies
  - numpy==1.26.3 (vector operations)
  - scikit-learn==1.4.0 (cosine similarity for mock mode)

### Features
- **Semantic Search**: Find relevant information using meaning, not just keywords
- **Source Attribution**: AI responses include citations with relevance scores
- **Knowledge Base Management**: Easy document ingestion via CLI
- **Mock Mode**: Full RAG functionality without Snowflake credentials

### Technical Details
- Chunk size: 500 tokens (~375 words)
- Overlap: 50 tokens (10%)
- Top K results: 3 chunks per query
- Relevance threshold: 0.3 (30%)
- Embedding model: e5-base-v2 (768 dimensions) via Snowflake Cortex

### Backward Compatibility
- ✅ All Phase 1-4 functionality remains intact
- ✅ RAG is optional (controlled by RAG_ENABLED env var)
- ✅ Falls back to regular AI response if RAG disabled or no results
- ✅ No breaking changes to existing workflows
- ✅ Works in mock mode without Snowflake credentials

### Performance
- In-memory mock store for fast testing
- Snowflake Cortex for production-scale vector search
- Configurable top_k to control latency vs accuracy
- Chunk overlap prevents context loss at boundaries

### Testing
- ✅ Syntax validation passed for all new files
- ✅ Mock mode tested with keyword-based search
- ✅ CLI ingestion tool tested with sample documents
- ✅ RAG pipeline tested end-to-end in mock mode
- ⏳ Real Snowflake Cortex vector search pending user credentials

---

## [0.4.0] - 2026-01-14 - Phase 4: Conversation Memory

### Added
- **Thread-Aware Context**: AI now maintains conversation memory across Slack threads
  - New `fetch_thread_history()` function retrieves last 5 messages from threads
  - Automatically detects thread context using `thread_ts`
  - Works in both channel mentions and direct messages
- **Context-Aware Prompting**: Enhanced prompt engineering with conversation history
  - Real mode: Formats history as "User: ... / Assistant: ..." context
  - Mock mode: Extracts entities (Acme Corp, TechStart, Global Systems) from history
- **Pronoun Resolution**: Handles context-dependent queries
  - Example: "Who is Acme?" → "Update it" (resolves to "Acme Corp")
  - Detects pronouns: it, them, that, this, those
- **Role Detection**: Automatically identifies user vs bot messages
  - Uses `auth_test()` API to get bot user ID
  - Properly formats conversation as user/assistant pairs

### Changed
- **`listeners/mentions.py`**: Added thread history support
  - `handle_mentions()` now accepts `client` parameter for API calls
  - `handle_dm()` now accepts `client` parameter for API calls
  - New `fetch_thread_history()` helper function
  - Graceful error handling for permission issues
- **`services/ai_service.py`**: Enhanced context awareness
  - `get_response()` now accepts optional `history` parameter
  - `_get_mock_response()` now accepts optional `history` parameter
  - Smart entity extraction from conversation history
  - Context notes in generic responses
  - Improved pronoun resolution in mock mode

### Backward Compatibility
- ✅ All Phase 3, 2, and 1 functionality remains intact
- ✅ Single messages work as before (no history passed)
- ✅ No breaking changes to existing workflows
- ✅ History parameter is optional (defaults to None)

### Performance
- History limited to 5 messages to optimize token usage
- Caches bot_user_id from auth_test() call
- Minimal overhead for non-threaded messages

### Testing
- ✅ Syntax validation passed for all modified files
- ✅ Mock mode tested with pronoun resolution
- ✅ Thread context extraction validated
- ⏳ Real Snowflake Cortex with history pending user credentials

---

## [0.3.0] - 2026-01-14 - Phase 3: Snowflake Cortex AI Integration

### Added
- **Snowflake Cortex Integration**: Real LLM responses using Snowflake Cortex
  - Uses `SNOWFLAKE.CORTEX.COMPLETE()` SQL function
  - Model: `llama3-70b` for enterprise-grade AI responses
  - System prompt: "You are Elli, a helpful enterprise assistant."
- **Enhanced Mock Mode**: Intelligent keyword-based responses
  - Revenue/sales queries → Financial data responses
  - Customer/client queries → Customer information
  - Help queries → Feature overview
  - Generic queries → Contextual responses
- **Singleton Pattern**: AI service initialized once at module level for performance
- **Connection Management**: Automatic cleanup with `__del__` method
- **Smart Workflow Detection**: Enhanced DM handler to prevent conflicts with Salesforce patterns
- **Documentation Organization**: Created `docs/` folder for better project structure

### Changed
- **`services/ai_service.py`**: Complete rewrite
  - Real Snowflake connector integration
  - Enhanced mock responses with keyword detection
  - Removed hardcoded `time.sleep()` delay
  - Added connection pooling support
  - Environment variables: `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`, `SNOWFLAKE_ROLE`
- **`listeners/mentions.py`**: Updated to use real AIService
  - Removed local `get_ai_response()` mock function
  - Integrated AIService singleton
  - Enhanced workflow pattern detection to prevent conflicts
  - Added proper type hints and docstrings
- **`.env.example`**: Added comprehensive Snowflake configuration
- **Project Structure**: Moved documentation files to `docs/` folder
  - Moved: `ARCHITECTURE.md`, `CI_CD.md`, `CONTRIBUTING.md`, `PHASE2_SUMMARY.md`, `TESTING_GUIDE.md`
  - Kept in root: `README.md`, `AGENTS.md`, `CHANGELOG.md`

### Dependencies
- Added `snowflake-connector-python[pandas]==3.6.0` - Snowflake database connector
- Added `pandas==2.1.4` - Data manipulation (Snowflake dependency)

### Backward Compatibility
- ✅ All Phase 2 and Phase 1 functionality remains intact
- ✅ Mock mode still works without Snowflake credentials
- ✅ No breaking changes to existing workflows

### Testing
- ✅ Syntax validation passed for all modified files
- ✅ Mock mode tested with enhanced keyword responses
- ⏳ Real Snowflake Cortex testing pending user credentials

---

## [0.2.0] - 2026-01-14 - Phase 2: Smart Salesforce Integration

### Added
- **Entity Extraction**: Regex patterns now extract company names and target stages from natural language
  - Pattern: `"Update [Company] to [Stage]"`
  - Pattern: `"Set [Company] stage to [Stage]"`
- **Intelligent Search**: `SalesforceClient.search_opportunities()` method searches by company name
- **Smart Result Handling**:
  - 0 results: Sends "not found" message
  - 1 result: Auto-displays with pre-filled update button
  - Multiple results: Shows disambiguation dropdown
- **Real Salesforce API Integration**: Full `simple-salesforce` integration with graceful mock fallback
- **Pre-filled Modals**: Modals now support pre-filling opportunity ID, name, and stage
- **Mock Mode**: Comprehensive mock data for testing without Salesforce credentials
- **New Action Handlers**:
  - `handle_smart_update_single_click`: Handles single result button clicks
  - `handle_smart_update_select`: Handles multiple result dropdown selections

### Changed
- **`services/sf_client.py`**: Complete rewrite with real API support
  - Added `search_opportunities(company_name)` method
  - Added `_mock_search_opportunities(company_name)` for testing
  - Enhanced `update_opportunity_stage()` to accept opportunity ID
  - Now uses environment variables: `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN`
- **`workflows/salesforce.py`**: Major enhancements
  - Added `handle_smart_update()` function for intelligent routing
  - Enhanced `open_salesforce_modal()` with optional pre-fill parameters
  - Updated `handle_salesforce_submission()` to use opportunity IDs from `private_metadata`
  - Added stage constants: `STAGE_DISCOVERY`, `STAGE_NEGOTIATION`, `STAGE_CLOSED_WON`
  - Added `STAGE_MAPPING` dictionary for user-friendly stage names
- **`listeners/messages.py`**: Smart pattern matching
  - Added `trigger_smart_update()` for "Update [Company] to [Stage]" pattern
  - Added `trigger_smart_set_stage()` for "Set [Company] stage to [Stage]" pattern
  - Reorganized into sections: Smart Triggers, Action Handlers, Legacy Fallback
  - Legacy "update salesforce" command now uses exact match pattern
- **`.env.example`**: Updated Salesforce variable names from `SALESFORCE_*` to `SF_*`

### Dependencies
- Added `simple-salesforce==1.12.6` for Salesforce API integration

### Documentation
- Added `PHASE2_SUMMARY.md`: Comprehensive Phase 2 implementation summary
- Added `TESTING_GUIDE.md`: Step-by-step testing instructions with scenarios
- Added `ARCHITECTURE.md`: Visual diagrams and data flow documentation
- Updated `AGENTS.md`: Added Phase 2 breadcrumb entry with detailed context
- Added this `CHANGELOG.md`: Project version history

### Backward Compatibility
- ✅ All Phase 1 functionality remains intact
- ✅ Legacy "update salesforce" command still works
- ✅ No breaking changes to existing workflows

### Testing
- ✅ Syntax validation passed for all modified files
- ✅ Mock mode tested with predefined data
- ✅ Graceful fallback confirmed when credentials missing
- ⏳ Real Salesforce API testing pending user credentials

---

## [0.1.0] - 2026-01-14 - Phase 1: Modular Refactoring

### Added
- **Modular Architecture**: Separated monolithic `app.py` into organized structure
- **Listener Modules**:
  - `listeners/messages.py`: Regex-based workflow triggers
  - `listeners/mentions.py`: AI fallback handlers for app mentions and DMs
- **Workflow Modules**:
  - `workflows/salesforce.py`: Salesforce modal and submission handling
- **Service Modules**:
  - `services/sf_client.py`: Salesforce client placeholder with mock data
  - `services/ai_service.py`: AI service placeholder
- **CI/CD Infrastructure**:
  - `.github/workflows/ci.yml`: Comprehensive CI pipeline (lint, test, security, validate)
  - `.github/workflows/cd.yml`: Deployment pipeline for staging and production
  - `.github/workflows/pr-checks.yml`: PR validation and quality checks
  - `.github/workflows/dependency-review.yml`: Dependency vulnerability scanning
  - `Dockerfile`: Multi-stage Docker build
  - `docker-compose.yml`: Local development environment
  - `Makefile`: Developer productivity commands
  - `pyproject.toml`: Tool configuration (Black, isort, pytest, mypy)
- **Documentation**:
  - `AGENTS.md`: Coding guidelines and breadcrumbs system for AI agents
  - `CI_CD.md`: Complete CI/CD pipeline documentation
  - `CONTRIBUTING.md`: Contributor guidelines
  - `.github/PULL_REQUEST_TEMPLATE.md`: Standardized PR template

### Changed
- **`app.py`**: Simplified to entry point only
  - Removed all listener code
  - Now only initializes app and registers listener modules
- **Environment Variables**: Centralized in `.env` file
- **Project Structure**: Reorganized into `/listeners`, `/workflows`, `/services` directories

### Fixed
- **Duplicate Response Bug**: Fixed in mentions listener
  - Added channel type check to prevent double-replies
  - Added keyword workflow check to avoid conflicts

### Dependencies
- `slack_bolt==1.18.0`
- `slack_sdk==3.27.1`
- `python-dotenv==1.0.0`

### Architecture
- Implemented separation of concerns: Listeners → Workflows → Services
- Socket Mode connection for development/internal use
- Hybrid router approach: Layer 1 (Workflows) and Layer 2 (AI Fallback)

---

## Version Comparison

### Phase 1 vs Phase 2 - Key Differences

| Feature | Phase 1 (v0.1.0) | Phase 2 (v0.2.0) |
|---------|------------------|------------------|
| **Salesforce Trigger** | "update salesforce" only | Entity extraction from natural language |
| **Search Capability** | None | Search by company name |
| **Result Handling** | N/A | 0/1/multiple intelligent routing |
| **API Integration** | Mock only | Real API with mock fallback |
| **Modal Pre-fill** | No | Yes (ID, name, stage) |
| **Patterns Supported** | 1 (simple keyword) | 3 (smart + legacy) |
| **User Experience** | Manual form entry | Smart auto-fill and disambiguation |
| **Dependencies** | 3 packages | 4 packages (+simple-salesforce) |

### Lines of Code

| Component | Phase 1 | Phase 2 | Change |
|-----------|---------|---------|--------|
| `services/sf_client.py` | 25 | 160 | +540% |
| `workflows/salesforce.py` | 48 | 236 | +392% |
| `listeners/messages.py` | 50 | 160 | +220% |
| **Total** | 123 | 556 | +352% |

### Functional Capabilities

**Phase 1:**
- ✅ Basic keyword matching
- ✅ Manual modal entry
- ✅ Mock Salesforce updates

**Phase 2:**
- ✅ Entity extraction
- ✅ Natural language understanding
- ✅ Intelligent search
- ✅ Smart result routing
- ✅ Pre-filled modals
- ✅ Real Salesforce API
- ✅ Graceful fallback
- ✅ Backward compatible

---

## Migration Guide

### From Phase 1 to Phase 2

#### No Breaking Changes!
All Phase 1 functionality continues to work. No migration required.

#### Optional: Enable Real Salesforce API

1. Add to `.env`:
   ```bash
   SF_USERNAME=your-username@company.com
   SF_PASSWORD=your-password
   SF_SECURITY_TOKEN=your-token
   ```

2. Install new dependency:
   ```bash
   pip install -r requirements.txt
   ```

3. Restart the bot:
   ```bash
   python app.py
   ```

#### New Commands Available

You can now use natural language:
- `"Update Acme Corp to Closed Won"`
- `"Set TechStart stage to Negotiation"`

Legacy command still works:
- `"update salesforce"`

---

## Semantic Versioning

### Version Format: MAJOR.MINOR.PATCH

- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Current Version: 0.3.0
- **0**: Pre-1.0 development
- **3**: Production deployment with channel-based Opportunities
- **0**: Initial production release

### Upcoming Versions
- **0.4.0**: Phase 9.2 (Snowflake enterprise data) - Post-offsite planning
- **0.5.0**: Phase 11 (LevPro integration) - Post-offsite planning
- **1.0.0**: Production release - Stable API, post-pilot feedback incorporated

---

## Links

- [AGENTS.md](AGENTS.md) - Coding guidelines and breadcrumbs
- [PHASE2_SUMMARY.md](PHASE2_SUMMARY.md) - Phase 2 detailed summary
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - How to test Phase 2 features
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [CI_CD.md](CI_CD.md) - CI/CD pipeline documentation

---

**Maintained by**: Development Team
**Last Updated**: 2026-02-03
**Current Version**: 0.3.0
