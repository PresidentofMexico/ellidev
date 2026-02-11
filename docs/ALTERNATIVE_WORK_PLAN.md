# Alternative Work Plan - While Awaiting Snowflake Environment Details

**Created**: 2026-01-15
**Status**: Planning
**Context**: Phase 5.3 complete, Snowflake integration blocked on environment discovery

## Overview

While awaiting answers to Snowflake environment questions, we have identified several high-value work streams that:
1. Don't depend on Snowflake environment details
2. Will benefit the Snowflake integration when implemented
3. Improve overall code quality and maintainability
4. Add production-readiness features

## Recommended Priority Order

### Option 1: Phase 7 - Logging and Monitoring (HIGH PRIORITY)
**Why Now**: Essential for production deployment and will be invaluable for debugging Snowflake queries

### Option 2: Phase 8 - Unit Tests and Integration Tests (HIGH PRIORITY)
**Why Now**: Ensures existing features work correctly before adding Snowflake complexity

### Option 3: Code Quality Improvements (MEDIUM PRIORITY)
**Why Now**: Makes codebase more maintainable for future Snowflake work

### Option 4: Documentation and User Guides (MEDIUM PRIORITY)
**Why Now**: Helps users understand current features while preparing for enterprise data integration

### Option 5: Infrastructure Preparation (LOW PRIORITY)
**Why Now**: Groundwork for production deployment with enterprise data

---

## Option 1: Phase 7 - Logging and Monitoring

### Goals
1. **Structured Logging**: Replace print statements with proper logging
2. **Query Audit Trail**: Log all RAG queries, Salesforce operations, and AI calls
3. **Performance Metrics**: Track response times, API calls, and cache hits
4. **Error Tracking**: Comprehensive error logging with context

### Benefits for Snowflake Integration
- Query audit trail will be essential for debugging SQL generation
- Performance metrics will help tune Snowflake query performance
- Structured logs will help diagnose connection issues
- Error tracking will catch edge cases in metadata queries

### Implementation Plan

#### 7.1: Structured Logging Framework
**Files to Create**:
- `services/logger.py` - Centralized logging configuration
- `services/metrics.py` - Performance metrics collection

**Features**:
```python
# services/logger.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    """Structured logging with JSON output for production"""

    def log_query(self, user_id: str, query: str, source: str, duration_ms: float):
        """Log user query with context"""

    def log_api_call(self, service: str, method: str, duration_ms: float, success: bool):
        """Log external API call"""

    def log_rag_search(self, query: str, sources_found: int, relevance_scores: List[float]):
        """Log RAG search results"""

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with full context"""
```

**Configuration**:
```bash
# .env additions
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'text' for development
LOG_FILE=logs/elli.log
ENABLE_METRICS=true
```

**Changes Required**:
- Modify `listeners/mentions.py` to use structured logger
- Modify `services/rag_service.py` to log searches
- Modify `services/sf_client.py` to log API calls
- Modify `services/ai_service.py` to log AI requests

#### 7.2: Query Audit Trail
**Purpose**: Track all user queries and system responses

**Schema**:
```json
{
  "timestamp": "2026-01-15T10:30:00Z",
  "user_id": "U12345",
  "channel_id": "C67890",
  "query": "What opportunities are in negotiation?",
  "query_type": "rag_search",
  "sources_used": ["salesforce_record", "document"],
  "results_count": 3,
  "duration_ms": 245,
  "success": true
}
```

**Storage**:
- Option A: JSON lines file (`logs/query_audit.jsonl`)
- Option B: Snowflake table (future, when enterprise connection available)

#### 7.3: Performance Metrics
**Metrics to Track**:
- Query response time (p50, p95, p99)
- RAG search latency
- Salesforce API call latency
- AI service latency
- Cache hit rates (for future caching)
- Error rates by component

**Dashboard** (Future):
- Use logs to create performance dashboard
- Alert on anomalies (slow queries, high error rates)

#### 7.4: Error Tracking
**Enhanced Error Context**:
```python
def log_error(self, error: Exception, context: Dict[str, Any]):
    """
    Log error with full context for debugging

    Context includes:
    - User ID and channel
    - Query that triggered error
    - Service/component that failed
    - Stack trace
    - System state (mock mode, API availability)
    """
```

### Effort Estimate
- **Lines of Code**: ~500 lines
- **Files Created**: 2 new files
- **Files Modified**: 8 files
- **Complexity**: Medium
- **Time**: Can be implemented incrementally

---

## Option 2: Phase 8 - Unit Tests and Integration Tests

### Goals
1. **Test Coverage**: Achieve >80% coverage on core services
2. **Regression Prevention**: Catch bugs before deployment
3. **Mock Testing**: Validate mock mode behavior
4. **Integration Tests**: Test full workflows end-to-end

### Benefits for Snowflake Integration
- Test framework will be used for Snowflake SQL generation tests
- Mock patterns will extend to enterprise Snowflake service
- Confidence that existing features won't break with new changes
- Faster development cycle with automated testing

### Implementation Plan

#### 8.1: Test Framework Setup
**Files to Create**:
- `tests/__init__.py`
- `tests/conftest.py` - pytest fixtures
- `pytest.ini` - pytest configuration
- `.coveragerc` - coverage configuration

**Dependencies to Add**:
```bash
# requirements-dev.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-asyncio==0.21.1
```

**Configuration**:
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

#### 8.2: Service Layer Tests
**Test Files to Create**:
- `tests/services/test_ai_service.py` - AI service tests
- `tests/services/test_sf_client.py` - Salesforce client tests
- `tests/services/test_rag_service.py` - RAG service tests
- `tests/services/test_vector_store.py` - Vector store tests
- `tests/services/test_salesforce_rag.py` - Salesforce RAG tests
- `tests/services/test_semantic_memory.py` - Semantic memory tests

**Example Test Structure**:
```python
# tests/services/test_rag_service.py
import pytest
from services.rag_service import RAGService

class TestRAGService:

    @pytest.fixture
    def rag_service(self):
        """Create RAGService instance for testing"""
        return RAGService()

    def test_should_use_rag_with_rag_keywords(self, rag_service):
        """Test RAG detection with knowledge base keywords"""
        assert rag_service.should_use_rag("What are our payment terms?")
        assert rag_service.should_use_rag("How do I configure the product?")

    def test_should_use_rag_with_crm_keywords(self, rag_service):
        """Test RAG detection with CRM keywords"""
        assert rag_service.should_use_rag("What opportunities are open?")
        assert rag_service.should_use_rag("Show me contacts at Acme Corp")

    def test_should_not_use_rag_for_general_queries(self, rag_service):
        """Test that general queries don't trigger RAG"""
        assert not rag_service.should_use_rag("Hello!")
        assert not rag_service.should_use_rag("How are you?")

    def test_mock_search_returns_results(self, rag_service):
        """Test mock mode returns sample results"""
        results = rag_service._mock_search("payment terms")
        assert len(results) == 3
        assert all("content" in r for r in results)
```

#### 8.3: Workflow Tests
**Test Files to Create**:
- `tests/workflows/test_salesforce.py` - Salesforce workflow tests

**Test Scenarios**:
- Entity extraction from natural language
- Modal pre-filling with opportunity data
- Opportunity update submission
- Error handling (no results, multiple results, API failures)

#### 8.4: Integration Tests
**Test Files to Create**:
- `tests/integration/test_mention_flow.py` - End-to-end mention flow
- `tests/integration/test_salesforce_flow.py` - Full Salesforce workflow
- `tests/integration/test_rag_flow.py` - RAG search flow

**Example Integration Test**:
```python
# tests/integration/test_rag_flow.py
def test_rag_search_with_salesforce_data(slack_client_mock):
    """Test RAG search finds Salesforce records"""
    # Ingest test Salesforce data
    # Send query to bot
    # Verify response includes Salesforce sources
    # Verify source formatting is correct
```

#### 8.5: Mock Mode Tests
**Purpose**: Ensure mock mode provides realistic behavior

**Test Coverage**:
- Mock AI responses with keyword detection
- Mock Salesforce searches return reasonable data
- Mock RAG searches return sample documents
- Mock vector store operations

### Effort Estimate
- **Lines of Code**: ~1,500 lines
- **Files Created**: 15+ test files
- **Complexity**: Medium
- **Time**: Can be implemented incrementally (start with critical services)

---

## Option 3: Code Quality Improvements

### Goals
1. **Reduce Complexity**: Refactor complex functions
2. **Error Handling**: Add comprehensive error handling
3. **Type Hints**: Complete type hint coverage
4. **Code Documentation**: Add docstrings to all public methods

### Benefits for Snowflake Integration
- Cleaner code patterns to follow for Snowflake services
- Better error handling will extend to SQL generation errors
- Type hints will catch bugs during development
- Documentation will help future developers

### Implementation Plan

#### 3.1: Refactor Complex Functions
**Target**: `listeners/mentions.py` (high cognitive complexity)

**Current Issues**:
- `handle_mentions()` is ~200 lines with nested logic
- `handle_dm()` duplicates logic from `handle_mentions()`
- Source formatting logic is repeated

**Refactoring Plan**:
```python
# Break down into smaller functions:

def extract_query_from_mention(message: Dict) -> str:
    """Extract clean query text from mention"""

def search_with_rag(query: str) -> Tuple[str, List[Dict]]:
    """Perform RAG search and return answer + sources"""

def format_sources_section(sources: List[Dict]) -> str:
    """Format sources list for Slack message"""

def format_salesforce_source(source: Dict) -> str:
    """Format Salesforce record source"""

def format_document_source(source: Dict) -> str:
    """Format document source"""

def format_memory_source(source: Dict) -> str:
    """Format semantic memory source"""
```

#### 3.2: Enhanced Error Handling
**Current State**: Basic error handling with print statements

**Enhanced Error Handling**:
```python
# services/sf_client.py - Example enhanced error handling

def search_opportunities(self, query: str) -> List[Dict]:
    """Search Salesforce opportunities with comprehensive error handling"""
    try:
        if self.mock_mode:
            return self._mock_search(query)

        # Real Salesforce search
        results = self.sf.query(soql)
        return results["records"]

    except SalesforceAuthenticationFailed as e:
        logger.error("Salesforce authentication failed", extra={"error": str(e)})
        raise ServiceUnavailableError("Unable to connect to Salesforce. Please check credentials.")

    except SalesforceExpiredSession as e:
        logger.warning("Salesforce session expired, retrying...")
        self._refresh_session()
        return self.search_opportunities(query)  # Retry once

    except Exception as e:
        logger.error("Unexpected error in Salesforce search", extra={
            "error": str(e),
            "query": query,
            "stack_trace": traceback.format_exc()
        })
        raise ServiceError(f"Salesforce search failed: {str(e)}")
```

**Create Custom Exception Classes**:
```python
# services/exceptions.py (NEW FILE)

class ElliError(Exception):
    """Base exception for Elli application"""

class ServiceUnavailableError(ElliError):
    """External service is unavailable"""

class ServiceError(ElliError):
    """Error occurred in service layer"""

class ValidationError(ElliError):
    """Input validation failed"""

class ConfigurationError(ElliError):
    """Configuration is invalid or missing"""
```

#### 3.3: Complete Type Hints
**Target Files**:
- `services/ai_service.py`
- `services/rag_service.py`
- `workflows/salesforce.py`

**Add Type Hints**:
```python
from typing import Dict, List, Optional, Tuple, Any

def search_opportunities(
    self,
    query: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Search opportunities with full type hints"""
```

#### 3.4: Documentation Completeness
**Add Docstrings**:
- All public methods need docstrings
- All classes need class-level docstrings
- All modules need module-level docstrings

**Docstring Format**:
```python
def search_with_context(
    self,
    query: str,
    conversation_history: List[Dict],
    use_memory: bool = True
) -> Tuple[str, List[Dict]]:
    """
    Search using RAG with conversation context and semantic memory.

    Args:
        query: The user's question or query
        conversation_history: Recent messages from thread (up to 5)
        use_memory: Whether to include semantic memory in search

    Returns:
        Tuple of (answer_text, sources_list)

    Raises:
        ServiceError: If RAG search fails

    Example:
        >>> answer, sources = rag.search_with_context(
        ...     "What are payment terms?",
        ...     conversation_history=[],
        ...     use_memory=True
        ... )
    """
```

### Effort Estimate
- **Lines Changed**: ~800 lines modified
- **Files Created**: 1 (exceptions.py)
- **Files Modified**: 10+ files
- **Complexity**: Medium
- **Time**: Can be done incrementally

---

## Option 4: Documentation and User Guides

### Goals
1. **User Guide**: Help users get maximum value from Elli
2. **Admin Guide**: Help administrators deploy and configure
3. **Query Guide**: Best practices for writing queries
4. **Troubleshooting Guide**: Common issues and solutions

### Implementation Plan

#### 4.1: User Guide
**File**: `docs/USER_GUIDE.md`

**Contents**:
- Introduction to Elli's capabilities
- How to update Salesforce opportunities
- How to ask knowledge base questions
- How to search CRM data
- Understanding conversation memory
- Best practices for query writing
- Example queries and expected responses

#### 4.2: Admin Guide
**File**: `docs/ADMIN_GUIDE.md`

**Contents**:
- Deployment options (local, Docker, cloud)
- Environment variable reference
- Slack app configuration steps
- Salesforce connection setup
- Snowflake Cortex setup
- Knowledge base ingestion procedures
- Monitoring and maintenance
- Security best practices

#### 4.3: Query Writing Best Practices
**File**: `docs/QUERY_BEST_PRACTICES.md`

**Contents**:
- How to write effective knowledge base queries
- CRM query patterns that work best
- Understanding RAG vs direct AI responses
- Using conversation context effectively
- Examples of good vs poor queries

#### 4.4: Troubleshooting Guide
**File**: `docs/TROUBLESHOOTING.md`

**Contents**:
- Bot not responding → Check Slack tokens
- RAG not finding results → Check knowledge base ingestion
- Salesforce search fails → Check credentials and permissions
- Mock mode behavior → Understanding fallback modes
- Common error messages and solutions

### Effort Estimate
- **Lines of Documentation**: ~2,000 lines
- **Files Created**: 4 new docs
- **Complexity**: Low
- **Time**: Can be written incrementally

---

## Option 5: Infrastructure Preparation

### Goals
1. **Production Deployment**: Docker improvements
2. **CI/CD Enhancements**: Automated testing and deployment
3. **Health Checks**: Service health monitoring
4. **Configuration Management**: Better config handling

### Implementation Plan

#### 5.1: Enhanced Docker Configuration
**Improvements**:
- Multi-stage Docker build for smaller images
- Health check endpoints
- Better secret management
- Production vs development configurations

#### 5.2: CI/CD Pipeline
**Additions**:
- Automated testing on pull requests
- Code quality checks (linting, type checking)
- Security scanning
- Automated deployments to staging/production

#### 5.3: Health Check Endpoint
**New Feature**: Add HTTP health check endpoint

```python
# app.py additions
from flask import Flask, jsonify

health_app = Flask(__name__)

@health_app.route("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "services": {
            "slack": "connected",
            "salesforce": "connected" if sf_client.connected else "mock",
            "snowflake": "connected" if ai_service.connected else "mock",
            "rag": "enabled" if rag_enabled else "disabled"
        }
    })
```

### Effort Estimate
- **Lines of Code**: ~300 lines
- **Files Created**: 3-4 config files
- **Files Modified**: 2-3 files
- **Complexity**: Low-Medium
- **Time**: Can be done incrementally

---

## Recommended Approach

### Phase 1: Start with Logging (Option 1)
**Why First**:
- Provides immediate value for debugging current issues
- Will be essential for Snowflake integration debugging
- Relatively quick to implement
- Doesn't change existing behavior (additive only)

**Deliverables**:
- Structured logging framework
- Query audit trail
- Basic performance metrics
- Enhanced error logging

**Estimated Duration**: 2-3 implementation sessions

### Phase 2: Add Core Tests (Option 2 - Partial)
**Why Second**:
- Ensures existing features work correctly
- Catches regressions early
- Builds confidence before Snowflake work

**Deliverables**:
- Test framework setup
- Tests for core services (RAG, Salesforce RAG, AI)
- Basic integration tests

**Estimated Duration**: 3-4 implementation sessions

### Phase 3: Code Quality (Option 3)
**Why Third**:
- Refine codebase with logging insights
- Clean up code patterns before Snowflake
- Apply lessons learned from testing

**Deliverables**:
- Refactored complex functions
- Enhanced error handling with custom exceptions
- Complete type hints
- Comprehensive docstrings

**Estimated Duration**: 2-3 implementation sessions

### Phase 4: Documentation (Option 4)
**Why Fourth**:
- Document current state before Snowflake changes
- User guide helps users maximize value now
- Admin guide prepares for production deployment

**Deliverables**:
- User guide
- Admin guide
- Query best practices
- Troubleshooting guide

**Estimated Duration**: 1-2 documentation sessions

### Phase 5: Infrastructure (Option 5 - As Needed)
**Why Last**:
- Not blocking other work
- Can be done in parallel with documentation

---

## Decision Time

Which option(s) would you like to proceed with?

1. **Start with Phase 7 (Logging)** - Quick win, high value, prepares for Snowflake
2. **Start with Phase 8 (Testing)** - Build confidence, prevent regressions
3. **Do both in parallel** - Logging in one session, tests in another
4. **All of the above** - Systematic improvement across all areas
5. **Something else** - Custom combination or different priority

**My Recommendation**: Start with **Option 1 (Logging)** because:
- Quick to implement (2-3 sessions)
- Immediate value for debugging current issues
- Critical foundation for Snowflake SQL debugging
- Additive (doesn't change existing behavior)
- Query audit trail will help understand user patterns

Once logging is in place, move to **Option 2 (Testing)** to ensure quality before Snowflake complexity.

---

**Next Steps**: Awaiting your decision on which option to pursue first.
