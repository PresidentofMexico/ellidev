# Phase 5.3: Advanced RAG Features - Implementation Plan

**Version**: 0.6.0 (Planned)
**Status**: In Progress
**Agent**: Claude Code (Sonnet 4.5)

## Overview

Phase 5.3 enhances the RAG system with advanced features that integrate live Salesforce data into the knowledge base, enabling Elli to answer questions about CRM data using the same semantic search capabilities.

## Goals

1. **Salesforce Data Integration**: Query and ingest live Salesforce data as RAG context
2. **Dynamic Knowledge Updates**: Refresh CRM data on-demand or scheduled
3. **Hybrid Search**: Combine static knowledge base with dynamic CRM data
4. **Enhanced Query Routing**: Smart detection of CRM-related queries
5. **Data Source Attribution**: Clearly distinguish between documents and CRM records

## Features

### 5.3.1: Salesforce Data Ingestion

**Purpose**: Pull Salesforce opportunities, accounts, and contacts into vector store

**Components**:
- `services/salesforce_rag.py` - Salesforce RAG integration service
- `scripts/ingest_salesforce.py` - CLI tool to sync Salesforce data
- Enhanced `services/sf_client.py` - Add bulk query methods

**Data to Ingest**:
- **Opportunities**: Name, stage, amount, close date, description, account
- **Accounts**: Name, industry, description, website, employee count
- **Contacts**: Name, title, email, account, phone

**Chunking Strategy**:
```python
# Each Salesforce record becomes a chunk
chunk = {
    "chunk_id": f"sf_opportunity_{opp_id}",
    "document_id": f"salesforce_opportunities",
    "content": formatted_record_text,
    "metadata": {
        "type": "salesforce_record",
        "object_type": "Opportunity",
        "record_id": opp_id,
        "last_modified": timestamp,
        "stage": stage,
        "amount": amount
    }
}
```

### 5.3.2: Hybrid Search Enhancement

**Purpose**: Search across both static documents and dynamic Salesforce data

**Implementation**:
- Enhanced `should_use_rag()` to detect CRM queries
- Separate search paths for documents vs records
- Unified result ranking and presentation

**CRM Query Detection Keywords**:
- "opportunity", "deal", "pipeline", "forecast"
- "account", "customer", "client"
- "contact", "who handles", "sales rep"
- "stage", "close date", "amount", "value"

### 5.3.3: Data Refresh Strategy

**Options**:

**Option A: On-Demand Refresh** (Recommended for Phase 5.3.1)
- Manual CLI command: `python scripts/ingest_salesforce.py --refresh`
- Simple, predictable, no background jobs
- User controls when data is updated

**Option B: Scheduled Refresh** (Future: Phase 5.3.2)
- Cron job or scheduler
- Automatic nightly sync
- Requires background task management

**Option C: Real-Time Sync** (Future: Phase 5.3.3)
- Salesforce webhooks/streaming API
- Complex infrastructure
- Overkill for most use cases

**Decision**: Start with Option A (on-demand), enhance later if needed.

### 5.3.4: Source Attribution Enhancement

**Current Format**:
```
📚 Sources:
• Product Info (Relevance: 95%)
```

**Enhanced Format**:
```
📚 Sources:
• Product Info [Document] (Relevance: 95%)
• Acme Corp - $250K Opportunity [Salesforce] (Relevance: 89%)
• Sarah Johnson, VP Operations [Salesforce Contact] (Relevance: 82%)
```

**Implementation**:
- Check `metadata.type` to determine source type
- Format accordingly with icons/labels
- Include record-specific details (amount, stage, title)

## Technical Architecture

### Data Flow

```
Salesforce API
     ↓
SalesforceRAG Service
     ↓
Format as chunks
     ↓
Vector Store (with metadata)
     ↓
Semantic Search
     ↓
RAG Pipeline
     ↓
Response with mixed sources
```

### File Structure

```
/services
├── salesforce_rag.py       # NEW: Salesforce RAG integration
├── sf_client.py            # MODIFIED: Add bulk query methods
├── vector_store.py         # No changes needed
└── rag_service.py          # MODIFIED: Enhanced source formatting

/scripts
└── ingest_salesforce.py    # NEW: CLI tool for Salesforce sync
```

## Implementation Steps

### Step 1: Create SalesforceRAG Service

**File**: `services/salesforce_rag.py`

**Key Methods**:
```python
class SalesforceRAG:
    def __init__(self, sf_client, vector_store):
        """Initialize with SF client and vector store"""

    def fetch_opportunities(self, limit=100) -> List[Dict]:
        """Fetch recent opportunities from Salesforce"""

    def fetch_accounts(self, limit=100) -> List[Dict]:
        """Fetch accounts from Salesforce"""

    def fetch_contacts(self, limit=100) -> List[Dict]:
        """Fetch contacts from Salesforce"""

    def format_opportunity_chunk(self, opp: Dict) -> Dict:
        """Format opportunity as vector store chunk"""

    def format_account_chunk(self, account: Dict) -> Dict:
        """Format account as vector store chunk"""

    def format_contact_chunk(self, contact: Dict) -> Dict:
        """Format contact as vector store chunk"""

    def ingest_salesforce_data(self, objects=['opportunities', 'accounts', 'contacts']) -> Dict:
        """Ingest selected Salesforce objects into vector store"""
```

### Step 2: Enhance SF Client

**File**: `services/sf_client.py`

**New Methods**:
```python
def query_opportunities_bulk(self, limit=100) -> List[Dict]:
    """Query opportunities with all relevant fields"""

def query_accounts_bulk(self, limit=100) -> List[Dict]:
    """Query accounts with all relevant fields"""

def query_contacts_bulk(self, limit=100) -> List[Dict]:
    """Query contacts with all relevant fields"""
```

### Step 3: Create CLI Ingestion Tool

**File**: `scripts/ingest_salesforce.py`

**Features**:
- `--objects` flag: Choose which objects to sync (opportunities, accounts, contacts)
- `--limit` flag: Limit number of records
- `--refresh` flag: Clear existing Salesforce data first
- Progress reporting
- Statistics summary

**Usage**:
```bash
# Sync all Salesforce data
python scripts/ingest_salesforce.py

# Sync only opportunities
python scripts/ingest_salesforce.py --objects opportunities

# Refresh opportunities (clear and re-sync)
python scripts/ingest_salesforce.py --objects opportunities --refresh

# Limit to 50 records
python scripts/ingest_salesforce.py --limit 50
```

### Step 4: Enhance RAG Service

**File**: `services/rag_service.py`

**Changes**:

1. **Enhanced Query Detection**:
```python
def should_use_rag(self, query: str) -> bool:
    # Add CRM keywords to existing detection
    crm_keywords = ["opportunity", "deal", "account", "customer", "contact"]
    return any(keyword in query.lower() for keyword in rag_keywords + crm_keywords)
```

2. **Enhanced Source Formatting**:
```python
def _format_source(self, chunk: Dict) -> str:
    metadata = chunk.get("metadata", {})
    source_type = metadata.get("type", "document")

    if source_type == "salesforce_record":
        object_type = metadata.get("object_type", "Record")
        # Format: "Acme Corp - $250K Opportunity [Salesforce]"
        return self._format_salesforce_source(chunk)
    else:
        # Format: "Product Info [Document]"
        return self._format_document_source(chunk)
```

### Step 5: Update Configuration

**File**: `.env.example`

**New Variables**:
```bash
# Salesforce RAG Configuration (Phase 5.3)
SALESFORCE_RAG_ENABLED=true
SALESFORCE_RAG_OBJECTS=opportunities,accounts,contacts
SALESFORCE_RAG_LIMIT=100
SALESFORCE_RAG_AUTO_REFRESH=false
```

## Testing Strategy

### Mock Mode Testing

**Without Salesforce Credentials**:
- Create mock Salesforce record chunks
- Test hybrid search with mixed sources
- Verify source attribution formatting
- Test CRM query detection

### Real Mode Testing

**With Salesforce Credentials**:
1. Run `ingest_salesforce.py` to sync data
2. Query: "What deals are in negotiation?"
3. Verify: Response includes Salesforce opportunities
4. Query: "Who is the contact at Acme Corp?"
5. Verify: Response includes Salesforce contact info
6. Check source citations include [Salesforce] labels

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SALESFORCE_RAG_ENABLED` | `true` | Enable Salesforce RAG integration |
| `SALESFORCE_RAG_OBJECTS` | `opportunities,accounts,contacts` | Which objects to ingest |
| `SALESFORCE_RAG_LIMIT` | `100` | Max records per object |
| `SALESFORCE_RAG_AUTO_REFRESH` | `false` | Auto-refresh on bot start (future) |

## Usage Examples

### Example 1: CRM Query

```
You: @Elli What opportunities are in the negotiation stage?

Elli: Based on current Salesforce data:

      • Acme Corp Renewal - $250K, closes 2026-02-15
      • TechStart Expansion - $180K, closes 2026-02-28
      • Global Systems New Contract - $420K, closes 2026-03-10

      📚 Sources:
      • Acme Corp - $250K Opportunity [Salesforce] (Relevance: 95%)
      • TechStart - $180K Opportunity [Salesforce] (Relevance: 93%)
      • Global Systems - $420K Opportunity [Salesforce] (Relevance: 91%)
```

### Example 2: Hybrid Query

```
You: @Elli What's our pricing for enterprise customers like Acme Corp?

Elli: For enterprise customers, we offer custom pricing with volume discounts.

      Acme Corp specifically is in our Enterprise tier with:
      • $250K annual contract value
      • Custom integration support included
      • Dedicated account manager: Sarah Johnson

      📚 Sources:
      • Product Info - Enterprise Tier [Document] (Relevance: 94%)
      • Acme Corp Account [Salesforce] (Relevance: 89%)
```

### Example 3: Contact Lookup

```
You: @Elli Who should I contact at TechStart?

Elli: The primary contact at TechStart is:

      Michael Chen, VP of Engineering
      Email: mchen@techstart.io
      Phone: (555) 123-4567

      📚 Sources:
      • Michael Chen, VP Engineering [Salesforce Contact] (Relevance: 97%)
      • TechStart Account [Salesforce] (Relevance: 85%)
```

## Data Privacy & Security

### Considerations

1. **Data Sensitivity**: Salesforce records may contain sensitive business data
2. **Access Control**: Vector store doesn't have user-level permissions
3. **Data Retention**: CRM data stored indefinitely in vector store
4. **Audit Trail**: No logging of who accessed what records

### Recommendations

1. **Filter Sensitive Fields**: Don't ingest SSN, credit cards, etc.
2. **Regular Cleanup**: Periodically refresh to remove stale data
3. **Access Logging**: Log queries that hit Salesforce records (future)
4. **User Filtering**: Only show records owned by/shared with user (future Phase 5.3.2)

### Implementation

**Phase 5.3.1** (Current):
- Basic ingestion without user filtering
- All users see all synced records
- Acceptable for internal teams with shared access

**Phase 5.3.2** (Future):
- Add `owner_id` metadata to chunks
- Filter search results by user permissions
- Integrate with Salesforce sharing rules

## Performance Considerations

### Record Volume

**Assumptions**:
- 100 opportunities × ~500 tokens each = 50K tokens
- 100 accounts × ~300 tokens each = 30K tokens
- 100 contacts × ~200 tokens each = 20K tokens
- **Total**: ~100K tokens (~300 chunks)

**Impact**:
- Minimal on vector search (300 more chunks)
- Mock mode: Slightly slower keyword search
- Real mode: Negligible (Snowflake scales)

### Refresh Frequency

**Recommendations**:
- **Daily**: For most teams (run nightly)
- **Weekly**: For stable pipelines
- **On-Demand**: For specific queries only

## Backward Compatibility

✅ **No Breaking Changes**:
- Salesforce RAG is opt-in (`SALESFORCE_RAG_ENABLED`)
- All existing Phase 1-5.2 functionality intact
- Falls back gracefully if SF credentials missing
- Static knowledge base works independently

## Success Metrics

### Functional Completeness

- [ ] SalesforceRAG service created
- [ ] CLI ingestion tool implemented
- [ ] Enhanced source formatting
- [ ] CRM query detection
- [ ] Hybrid search working
- [ ] Mock mode with sample CRM data
- [ ] Documentation complete

### Code Quality

- [ ] Type hints on all functions
- [ ] Docstrings for public methods
- [ ] Error handling for API failures
- [ ] Consistent code style
- [ ] No breaking changes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Large record volume slows search | Medium | Limit to recent records, pagination |
| Stale data in vector store | Low | Document refresh process, add timestamps |
| API rate limits | Medium | Bulk queries, respect limits, caching |
| Privacy concerns | High | Filter sensitive fields, document data handling |

## Future Enhancements (Phase 5.3.2+)

1. **User Permissions**: Filter results by Salesforce sharing rules
2. **Auto-Refresh**: Scheduled background sync
3. **Real-Time Sync**: Webhook-based updates
4. **Custom Objects**: Support non-standard SF objects
5. **Advanced Filters**: Query by date range, owner, stage
6. **Analytics**: Track most-queried records

## Dependencies

**No New Dependencies**: Reuses existing infrastructure
- ✅ `simple-salesforce` - Already installed (Phase 2)
- ✅ `services/sf_client.py` - Extend existing client
- ✅ `services/vector_store.py` - No changes needed

## Timeline Estimate

| Task | Estimated Lines | Complexity |
|------|----------------|------------|
| SalesforceRAG service | 250 lines | Medium |
| CLI ingestion tool | 150 lines | Low |
| Enhanced SF client | 100 lines | Low |
| RAG service updates | 50 lines | Low |
| Configuration | 10 lines | Low |
| Documentation | 300 lines | Medium |
| **Total** | **860 lines** | **Medium** |

## Ready to Implement

All planning complete. Ready to proceed with implementation.

**Next Step**: Create `services/salesforce_rag.py`

---

**Created by**: Claude Code (Sonnet 4.5)
**Date**: 2026-01-14
**Status**: Planning Complete ✅
