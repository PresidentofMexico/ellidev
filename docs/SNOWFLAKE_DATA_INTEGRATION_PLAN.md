# Snowflake Enterprise Data Integration Plan

**Purpose**: Integrate firm's enterprise Snowflake data warehouse into Elli's RAG system
**Status**: Planning
**Date**: 2026-01-14

## Overview

This plan outlines how to connect Elli to your firm's enterprise Snowflake data warehouse, enabling natural language queries over business intelligence data, reports, metrics, and analytics tables.

## Current State

**What Elli Already Has**:
- ✅ Snowflake Cortex connection for AI (Phase 3)
- ✅ Vector store with Snowflake Cortex (Phase 5.1)
- ✅ RAG pipeline for semantic search (Phase 5.1)
- ✅ Hybrid search architecture (Phase 5.3)
- ✅ Source attribution framework

**What's Missing**:
- ❌ Connection to enterprise Snowflake databases/schemas
- ❌ Query generation from natural language
- ❌ Table/column metadata ingestion
- ❌ Data access patterns and permissions

## Architecture Options

### Option A: Metadata-Based RAG (Recommended for Phase 1)

**Concept**: Ingest table/column metadata into vector store, generate SQL queries

```
User Query → RAG Search → Find Relevant Tables → Generate SQL → Execute → Format Results
```

**Pros**:
- Leverages existing RAG infrastructure
- No data duplication (queries live data)
- Respects Snowflake row-level security
- Works with any table structure

**Cons**:
- Requires SQL generation (LLM task)
- Need to handle query errors gracefully
- Complex queries may fail

**Components**:
1. **Metadata Ingestion**: Crawl `INFORMATION_SCHEMA` to get tables/columns/descriptions
2. **Vector Search**: Find relevant tables based on user query
3. **SQL Generation**: LLM generates SQL from natural language + table metadata
4. **Query Execution**: Run SQL against Snowflake
5. **Result Formatting**: Present data in Slack

### Option B: Data Snapshot RAG

**Concept**: Periodically snapshot data into vector store

```
Scheduled Job → Query Snowflake → Format as Chunks → Ingest to Vector Store → RAG Search
```

**Pros**:
- Simple RAG queries (no SQL generation)
- Fast responses (pre-indexed)
- Works with existing pipeline

**Cons**:
- Data staleness (depends on refresh frequency)
- Storage overhead (duplicate data in vector store)
- Doesn't scale to large datasets

**Use Cases**:
- Reports, dashboards, KPIs
- Reference data (products, territories)
- Relatively static data

### Option C: Hybrid Approach (Recommended Long-Term)

**Concept**: Combine metadata RAG + selective data snapshots

```
Static/Reference Data → Snapshot RAG
Live/Transactional Data → Metadata RAG + SQL Generation
```

**Implementation**:
- Product catalogs, reference tables → Snapshot
- Sales metrics, transactions → SQL generation
- Best of both worlds

## Recommended Implementation Plan

### Phase 1: Metadata-Based RAG with SQL Generation

Focus on enabling natural language queries over enterprise Snowflake data.

#### Step 1: Enterprise Snowflake Connection

**New Configuration** (`.env`):
```bash
# Enterprise Snowflake Connection (separate from AI Cortex)
ENTERPRISE_SNOWFLAKE_USER=your-enterprise-user
ENTERPRISE_SNOWFLAKE_PASSWORD=your-enterprise-password
ENTERPRISE_SNOWFLAKE_ACCOUNT=your-enterprise-account
ENTERPRISE_SNOWFLAKE_WAREHOUSE=your-analytics-warehouse
ENTERPRISE_SNOWFLAKE_DATABASE=your-analytics-db
ENTERPRISE_SNOWFLAKE_SCHEMA=your-schema
ENTERPRISE_SNOWFLAKE_ROLE=your-role

# Enable enterprise data queries
ENTERPRISE_DATA_ENABLED=true
ENTERPRISE_DATA_ALLOWED_SCHEMAS=PUBLIC,ANALYTICS,SALES
ENTERPRISE_DATA_QUERY_LIMIT=1000
```

**New Service** (`services/enterprise_snowflake.py`):
```python
class EnterpriseSnowflake:
    """
    Enterprise Snowflake data warehouse connection.

    Separate from Snowflake Cortex AI service - this connects to
    your firm's data warehouse for querying business data.
    """

    def __init__(self):
        # Connect using ENTERPRISE_SNOWFLAKE_* credentials
        # Separate connection from AI Cortex

    def fetch_table_metadata(self, schema: str) -> List[Dict]:
        """Query INFORMATION_SCHEMA for table/column metadata"""

    def execute_query(self, sql: str, limit: int = 1000) -> List[Dict]:
        """Execute SQL query with safety limits"""

    def validate_query(self, sql: str) -> bool:
        """Validate SQL is safe (no DROP, DELETE, etc.)"""
```

#### Step 2: Table Metadata Ingestion

**CLI Tool** (`scripts/ingest_snowflake_metadata.py`):
```bash
# Ingest table metadata from enterprise Snowflake
python scripts/ingest_snowflake_metadata.py --schema ANALYTICS
python scripts/ingest_snowflake_metadata.py --schemas ANALYTICS,SALES,FINANCE
python scripts/ingest_snowflake_metadata.py --database PROD_DW
```

**What Gets Ingested**:
```python
# For each table in specified schema(s):
{
    "table_name": "SALES_METRICS",
    "schema_name": "ANALYTICS",
    "database_name": "PROD_DW",
    "description": "Daily sales metrics by region and product",
    "columns": [
        {"name": "DATE", "type": "DATE", "description": "Transaction date"},
        {"name": "REGION", "type": "VARCHAR", "description": "Sales region"},
        {"name": "REVENUE", "type": "NUMBER", "description": "Total revenue in USD"},
        {"name": "UNITS_SOLD", "type": "NUMBER", "description": "Units sold"}
    ],
    "row_count": 1500000,
    "sample_queries": [
        "SELECT * FROM ANALYTICS.SALES_METRICS WHERE DATE >= CURRENT_DATE - 30",
        "SELECT REGION, SUM(REVENUE) FROM ANALYTICS.SALES_METRICS GROUP BY REGION"
    ]
}
```

**Vector Store Chunk Format**:
```python
{
    "chunk_id": "sf_table_ANALYTICS_SALES_METRICS",
    "document_id": "snowflake_tables",
    "content": """
        Table: ANALYTICS.SALES_METRICS
        Description: Daily sales metrics by region and product

        Columns:
        - DATE (DATE): Transaction date
        - REGION (VARCHAR): Sales region
        - REVENUE (NUMBER): Total revenue in USD
        - UNITS_SOLD (NUMBER): Units sold

        Example queries:
        - Get last 30 days: SELECT * FROM ANALYTICS.SALES_METRICS WHERE DATE >= CURRENT_DATE - 30
        - Revenue by region: SELECT REGION, SUM(REVENUE) FROM ANALYTICS.SALES_METRICS GROUP BY REGION
    """,
    "metadata": {
        "type": "snowflake_table_metadata",
        "database": "PROD_DW",
        "schema": "ANALYTICS",
        "table": "SALES_METRICS",
        "row_count": 1500000,
        "columns": ["DATE", "REGION", "REVENUE", "UNITS_SOLD"]
    }
}
```

#### Step 3: SQL Generation Service

**New Service** (`services/sql_generator.py`):
```python
class SQLGenerator:
    """
    Generates SQL queries from natural language using LLM.

    Uses Snowflake Cortex to translate user intent + table metadata
    into executable SQL.
    """

    def generate_sql(
        self,
        user_query: str,
        table_metadata: List[Dict],
        history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Generate SQL from natural language.

        Args:
            user_query: User's question in natural language
            table_metadata: Relevant table/column info from vector search
            history: Optional conversation history

        Returns:
            {
                "sql": "SELECT ...",
                "explanation": "This query calculates...",
                "tables_used": ["ANALYTICS.SALES_METRICS"],
                "confidence": 0.95
            }
        """

    def _build_sql_generation_prompt(
        self,
        user_query: str,
        table_metadata: List[Dict]
    ) -> str:
        """Build prompt for LLM SQL generation"""

    def validate_and_sanitize(self, sql: str) -> str:
        """Ensure SQL is safe (no mutations, etc.)"""
```

**SQL Generation Prompt Template**:
```
You are a Snowflake SQL expert. Generate a SQL query based on the user's question.

AVAILABLE TABLES:
Table: ANALYTICS.SALES_METRICS
Columns: DATE (DATE), REGION (VARCHAR), REVENUE (NUMBER), UNITS_SOLD (NUMBER)
Description: Daily sales metrics by region and product

USER QUESTION: "What was our revenue last quarter?"

INSTRUCTIONS:
1. Generate a SELECT query (no INSERT/UPDATE/DELETE/DROP)
2. Use proper table.column syntax
3. Include appropriate WHERE clauses, aggregations, GROUP BY
4. Add ORDER BY and LIMIT if relevant
5. Return only the SQL query

SQL:
```

#### Step 4: Query Execution & Formatting

**Enhanced RAG Service** (`services/rag_service.py`):
```python
def answer_with_enterprise_data(
    self,
    query: str,
    history: Optional[List[Dict]] = None
) -> Dict:
    """
    Answer query using enterprise Snowflake data.

    Workflow:
    1. Vector search to find relevant tables
    2. Generate SQL using LLM
    3. Execute SQL against enterprise Snowflake
    4. Format results for Slack
    5. Include SQL query in response for transparency
    """

    # Step 1: Find relevant tables
    table_chunks = self.vector_store.search(query, top_k=3)
    table_metadata = [chunk for chunk in table_chunks
                     if chunk["metadata"]["type"] == "snowflake_table_metadata"]

    # Step 2: Generate SQL
    sql_result = self.sql_generator.generate_sql(query, table_metadata)

    # Step 3: Execute query
    data = self.enterprise_sf.execute_query(sql_result["sql"])

    # Step 4: Format results
    formatted = self._format_query_results(data, sql_result)

    return {
        "answer": formatted,
        "sql": sql_result["sql"],
        "tables_used": sql_result["tables_used"],
        "row_count": len(data)
    }
```

**Result Formatting**:
```python
def _format_query_results(self, data: List[Dict], sql_info: Dict) -> str:
    """Format SQL query results for Slack"""

    if not data:
        return "No results found."

    # Detect result type
    if len(data) == 1 and len(data[0]) == 1:
        # Single value (e.g., SUM, COUNT)
        return f"Result: {list(data[0].values())[0]}"

    elif len(data) <= 10:
        # Small result set - show all rows as table
        return self._format_as_table(data)

    else:
        # Large result set - show summary + top rows
        return self._format_as_summary(data)
```

#### Step 5: Query Detection Keywords

**Enhanced RAG Service**:
```python
def should_use_enterprise_data(self, query: str) -> bool:
    """Detect queries about enterprise data"""

    query_lower = query.lower()

    enterprise_keywords = [
        # Metrics
        "revenue", "sales", "metrics", "kpi", "performance",

        # Time-based
        "last month", "last quarter", "ytd", "this year",
        "last week", "yesterday", "today",

        # Aggregations
        "total", "sum", "average", "count", "how many",

        # Comparisons
        "compare", "vs", "versus", "trend", "growth",

        # Business terms (customize for your firm)
        "pipeline", "forecast", "bookings", "churn",
        "customers", "products", "regions"
    ]

    return any(keyword in query_lower for keyword in enterprise_keywords)
```

## Response Format Examples

### Example 1: Simple Aggregation

```
You: @Elli What was our total revenue last quarter?

Elli: Based on enterprise data:

      Total Revenue (Q4 2025): $12,450,000

      📊 Query Details:
      • Tables: ANALYTICS.SALES_METRICS
      • Rows: 1 result
      • SQL: SELECT SUM(REVENUE) FROM ANALYTICS.SALES_METRICS
             WHERE DATE >= '2025-10-01' AND DATE < '2026-01-01'
```

### Example 2: Breakdown Results

```
You: @Elli Show me revenue by region last month

Elli: Revenue by Region (December 2025):

      • North America: $4,250,000
      • Europe: $3,180,000
      • Asia Pacific: $2,920,000
      • Latin America: $1,100,000

      Total: $11,450,000

      📊 Query Details:
      • Tables: ANALYTICS.SALES_METRICS
      • Rows: 4 results
      • SQL: SELECT REGION, SUM(REVENUE) as TOTAL
             FROM ANALYTICS.SALES_METRICS
             WHERE DATE >= '2025-12-01' AND DATE < '2026-01-01'
             GROUP BY REGION
             ORDER BY TOTAL DESC
```

### Example 3: Time Series

```
You: @Elli What's our revenue trend over the last 6 months?

Elli: Revenue Trend (Last 6 Months):

      Jul 2025: $3,200,000
      Aug 2025: $3,450,000
      Sep 2025: $3,600,000
      Oct 2025: $3,800,000
      Nov 2025: $4,100,000
      Dec 2025: $4,250,000

      Growth: +32.8% (Jul → Dec)

      📊 Query Details:
      • Tables: ANALYTICS.SALES_METRICS
      • Rows: 6 results
```

## Security & Governance

### Data Access Controls

1. **Schema Allowlist**:
   ```bash
   ENTERPRISE_DATA_ALLOWED_SCHEMAS=PUBLIC,ANALYTICS,SALES
   # Users can only query these schemas
   ```

2. **Query Validation**:
   ```python
   FORBIDDEN_KEYWORDS = [
       "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
       "ALTER", "CREATE", "GRANT", "REVOKE"
   ]

   def validate_query(sql: str) -> bool:
       sql_upper = sql.upper()
       return not any(kw in sql_upper for kw in FORBIDDEN_KEYWORDS)
   ```

3. **Row Limits**:
   ```python
   ENTERPRISE_DATA_QUERY_LIMIT=1000  # Max rows returned
   ```

4. **Snowflake Role-Based Access**:
   - Use service account with READ-ONLY role
   - Respects Snowflake row-level security policies
   - No data mutation capabilities

### Query Logging & Auditing

```python
def log_query_execution(
    user_id: str,
    query: str,
    sql: str,
    tables: List[str],
    row_count: int,
    success: bool
):
    """Log all enterprise data queries for audit"""

    log_entry = {
        "timestamp": datetime.now(),
        "user_id": user_id,
        "natural_language_query": query,
        "generated_sql": sql,
        "tables_accessed": tables,
        "rows_returned": row_count,
        "success": success
    }

    # Store in audit table or log file
```

## Testing Strategy

### Mock Mode

1. **Mock Table Metadata**:
   ```python
   def _mock_table_metadata():
       return [
           {
               "table": "ANALYTICS.SALES_METRICS",
               "columns": ["DATE", "REGION", "REVENUE"],
               "description": "Sales data"
           }
       ]
   ```

2. **Mock SQL Execution**:
   ```python
   def _mock_execute_query(sql: str) -> List[Dict]:
       # Return sample data based on SQL patterns
       if "SUM(REVENUE)" in sql:
           return [{"SUM": 12450000}]
       elif "GROUP BY REGION" in sql:
           return [
               {"REGION": "North America", "TOTAL": 4250000},
               {"REGION": "Europe", "TOTAL": 3180000}
           ]
   ```

### Real Mode Testing

1. Test with non-production Snowflake environment first
2. Use READ-ONLY credentials
3. Test query validation (try forbidden keywords)
4. Test row limit enforcement
5. Verify audit logging

## Implementation Checklist

**Phase 1 - Foundation**:
- [ ] Create `EnterpriseSnowflake` service
- [ ] Add enterprise Snowflake connection configuration
- [ ] Implement metadata fetching from `INFORMATION_SCHEMA`
- [ ] Create metadata ingestion CLI tool
- [ ] Test connection and metadata retrieval

**Phase 2 - SQL Generation**:
- [ ] Create `SQLGenerator` service
- [ ] Build SQL generation prompts
- [ ] Implement query validation
- [ ] Add mock SQL generation for testing
- [ ] Test SQL generation with sample queries

**Phase 3 - Query Execution**:
- [ ] Implement query execution with limits
- [ ] Add result formatting (single value, table, summary)
- [ ] Implement error handling
- [ ] Add query logging/auditing
- [ ] Test with real Snowflake data

**Phase 4 - RAG Integration**:
- [ ] Enhance RAG service with enterprise data path
- [ ] Add enterprise query detection keywords
- [ ] Update listeners to route enterprise queries
- [ ] Format responses with SQL transparency
- [ ] Test end-to-end workflow

**Phase 5 - Documentation**:
- [ ] Update README with enterprise data examples
- [ ] Document security model
- [ ] Create user guide for enterprise queries
- [ ] Add troubleshooting guide

## Questions to Answer

Before implementation, we need to clarify:

1. **Snowflake Environment**:
   - What's your Snowflake account identifier?
   - Which warehouse should Elli use for queries?
   - Which databases/schemas contain queryable data?

2. **Use Cases**:
   - What are the top 5 questions users will ask?
   - What tables/views should be prioritized?
   - Any sensitive data that should be excluded?

3. **Security**:
   - Do you have a READ-ONLY service account?
   - Are there row-level security policies in place?
   - Who should have access to enterprise queries?

4. **Data Characteristics**:
   - How large are your tables (row counts)?
   - How fresh does data need to be (real-time vs daily)?
   - Any complex joins or transformations needed?

5. **Governance**:
   - Do you need approval workflow for queries?
   - Should queries be logged for audit?
   - Any compliance requirements (GDPR, SOC2, etc.)?

## Next Steps

1. **Discovery Session**: Discuss your Snowflake environment and use cases
2. **Prototype**: Build with 1-2 tables to validate approach
3. **Iterate**: Refine SQL generation and result formatting
4. **Expand**: Add more tables and query patterns
5. **Production**: Deploy with monitoring and audit logs

---

**Status**: Planning Complete - Ready for Discovery Session
**Estimated Effort**: 800-1200 lines of code across 4-5 new services
**Timeline**: 2-3 implementation sessions after discovery
