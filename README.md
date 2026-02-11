# Elli - Enterprise AI + Workflow Slack Bot

> **Version**: 0.3.0 (Production Deployment Release)

## Overview

Elli is a hybrid Slack application that combines deterministic workflow automation with AI-powered assistance. It integrates with **Snowflake Cortex Agents** for deal/pipeline analytics and provides intelligent responses using Snowflake Cortex AI.

### Key Features (v0.2)

- **`/ask-deal-agent`** - Query deal/pipeline data via Snowflake Cortex Agents (DEAL_AGENT)
- **`/company`** - Aggregated company context from Salesforce and knowledge base
- **Deal Creation from Slack** - Create Salesforce opportunities directly from deal messages in threads
- **Salesforce OAuth** - Production-ready authentication with automatic token refresh
- **AI-Powered Chat** - Conversational AI using Snowflake Cortex with RAG
- **Conversation Memory** - Thread-aware context with long-term semantic memory

### Architecture

**Layer 1 (Slash Commands)**: Direct integrations
- `/ask-deal-agent` - Snowflake Cortex Agent for deal analytics
- `/company` - Company context aggregation

**Layer 2 (Workflows)**: Pattern-based triggers for specific actions
- Entity extraction from natural language (e.g., "Update Acme Corp to Closed Won")
- Smart Salesforce opportunity search and updates
- Pre-filled modals with opportunity data

**Layer 3 (AI Fallback)**: Intelligent responses powered by Snowflake Cortex
- Real LLM integration using `llama3-70b`
- RAG with vector search and knowledge base
- Context-aware responses with conversation memory

## Tech Stack

- **Python**: 3.11+
- **Framework**: Slack Bolt (Socket Mode)
- **AI**: Snowflake Cortex (llama3-70b) + Cortex Agents
- **Analytics**: Snowflake Cortex Analyst (DEAL_AGENT)
- **CRM**: Salesforce API (simple-salesforce)
- **Environment**: python-dotenv

## Project Structure

```
/elli
├── app.py                  # Entry point
├── requirements.txt        # Dependencies
├── .env                    # Environment variables (gitignored)
├── AGENTS.md              # Coding guidelines & breadcrumbs
├── CHANGELOG.md           # Version history
├── README.md              # This file
├── /docs                  # Documentation
│   ├── ARCHITECTURE.md
│   ├── CI_CD.md
│   ├── CONTRIBUTING.md
│   ├── PHASE2_SUMMARY.md
│   └── TESTING_GUIDE.md
├── /listeners             # Event routing
│   ├── messages.py        # Workflow triggers (Layer 1)
│   └── mentions.py        # AI handlers (Layer 2)
├── /workflows             # Business logic
│   └── salesforce.py      # Salesforce workflows
└── /services              # External integrations
    ├── ai_service.py      # Snowflake Cortex client
    └── sf_client.py       # Salesforce API client
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your credentials:

```bash
# Required: Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token

# Optional: Snowflake Cortex (for AI features)
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_WAREHOUSE=your-warehouse

# Optional: Salesforce OAuth (for CRM features)
SF_CONSUMER_KEY=your-connected-app-consumer-key
SF_CONSUMER_SECRET=your-connected-app-consumer-secret
SF_REFRESH_TOKEN=your-oauth-refresh-token
SF_INSTANCE_URL=https://your-instance.my.salesforce.com
```

**Note**: App works in mock mode without Snowflake/Salesforce credentials for testing.

### 3. Run the Bot

```bash
python app.py
```

## Features

### ✅ Phase 1: Modular Architecture (Complete)
- Separated concerns: Listeners → Workflows → Services
- Clean project structure
- CI/CD pipeline ready

### ✅ Phase 2: Smart Salesforce Integration (Complete)
- Natural language entity extraction
- Intelligent opportunity search (0/1/multiple result handling)
- Pre-filled modals with real Salesforce data
- Real API integration with mock fallback

### ✅ Phase 3: Snowflake Cortex AI (Complete)
- Real LLM responses using `llama3-70b`
- App mention and DM handling
- Enhanced mock mode with keyword detection
- Graceful fallback without credentials

### ✅ Phase 4: Conversation Memory (Complete)
- Thread-aware context with 5-message history
- Pronoun resolution ("update it" references previous context)
- Entity extraction from conversation history
- Context-aware prompting for both real and mock modes

### ✅ Phase 5.1: RAG with Vector Search (Complete)
- Retrieval Augmented Generation (RAG) for knowledge-based queries
- Vector store with Snowflake Cortex (with mock fallback)
- Document chunking and semantic search
- Source citation in AI responses
- CLI tool for knowledge base ingestion

### ✅ Phase 5.2: Semantic Memory (Complete)
- Long-term conversation memory beyond thread history
- Auto-summarization every N messages (configurable interval)
- Semantic search across past conversations
- Relevance scoring with recency and user match
- Memory citations in responses with dates

### ✅ Phase 5.3: Salesforce RAG Integration (Complete)
- Live Salesforce data integrated into knowledge base
- Hybrid search across documents and CRM records
- Semantic search over opportunities, accounts, and contacts
- Enhanced source citations distinguishing documents vs Salesforce records
- CLI tool for on-demand Salesforce data sync

### ✅ Phase 7: Logging and Monitoring (Complete)
- Structured logging with JSON output for production monitoring
- Query audit trail tracking all user interactions
- Performance metrics (response times, API latency, error rates)
- Comprehensive error tracking with full context
- Service-level logging across all components
- Metrics collection with p50/p95/p99 statistics

### ✅ Phase 8: Unit Tests and Integration Tests (Complete)
- Comprehensive test framework with pytest
- Unit tests for all core services (logger, metrics, RAG, AI, Salesforce)
- Integration tests for end-to-end flows
- Code coverage tracking (>70% target)
- Mock mode testing for all services
- Shared test fixtures and utilities

### ✅ Phase 9.1: Cortex Agent Integration (Complete - v0.1 MVP)
- `/ask-deal-agent` slash command for deal/pipeline analytics
- Snowflake Cortex Agents REST API integration
- SSE (Server-Sent Events) streaming response parsing
- Dual authentication: PAT (simple) and JWT key-pair (secure)
- Proper event-type parsing (`response.text.delta` vs `response.thinking.delta`)
- Mock mode for development without credentials

### ✅ Phase 10: Salesforce Integration (Complete - v0.2)
- Salesforce OAuth Web Server Flow with automatic token refresh
- Deal creation from Slack threads with "Add new deal" button
- Deal message parsing (company, sponsor, source, strategy, security type)
- Account lookup with TBD fallback for Deal Source and Primary Sponsor
- Custom Salesforce fields: Strategy__c, Security_Type__c, Deal_Source_Account__c, Primary_Sponsor__c
- Pre-filled modals with parsed deal data

### ✅ Phase 13: Production Deployment (Complete - v0.3)
- Production hardening (graceful shutdown, health checks, startup validation)
- Channel-based Opportunity RecordType mapping
- Azure Container Instance deployment infrastructure
- Dockerfile improvements with proper HEALTHCHECK
- Environment-based channel → business unit → RecordTypeId configuration

## Usage Examples

### Deal Agent Queries (NEW in v0.1)

```
/ask-deal-agent What deals are closing this month?
```
```
🤖 Deal Agent Response

Question: What deals are closing this month?

Based on the deal data, there are 5 deals closing this month:
• Acme Corp Renewal - $250K (Negotiation)
• TechStart Expansion - $180K (Proposal)
...
```

```
/ask-deal-agent Give me the top 10 companies by EBITDA
```
```
🤖 Deal Agent Response

Here are the companies with the top 10 highest latest adjusted EBITDA LTM values:

| Company | EBITDA |
|---------|--------|
| Alera   | $552K  |
...
```

### Smart Salesforce Updates

```
You: Update Acme Corp to Closed Won
Elli: 🔍 Searching for opportunities...
      ✅ I found 2 opportunities for 'Acme Corp'. Which one?
      [Dropdown with options]
```

### Deal Creation from Threads (NEW in v0.2)

```
[In a deal discussion thread]
User: ThreeSixty Group - New Deal
      Originator: Houlihan Lokey
      Sponsor: AEA Investors
      Stage: Initial interest

Elli: [Add new deal] button appears

[User clicks button]
Elli: 📝 Create New Opportunity modal opens with:
      - Company: ThreeSixty Group (pre-filled)
      - Deal Source: Houlihan Lokey (auto-lookup)
      - Sponsor: AEA Investors LLC (auto-lookup)
      - Stage: Initial Interest (pre-selected)
```

### AI Questions

```
You: @Elli What was our Q3 revenue?
Elli: 👀 Let me check on that...
      According to the Snowflake Data Warehouse...
```

### Thread-Aware Conversations (NEW in Phase 4)

```
You: @Elli Who is Acme Corp?
Elli: Acme Corp is one of our top customers...

You: Update it to Closed Won
Elli: Based on our conversation, I assume you're referring to Acme Corp.
      [Opens Salesforce update modal]
```

### Direct Messages

```
You: (DM) How do I update a deal?
Elli: I can help you with Salesforce updates!
      Try: 'Update [Company] to [Stage]'
```

### RAG-Powered Knowledge Queries (NEW in Phase 5.1)

```
You: @Elli What are our payment terms?
Elli: Based on our knowledge base, here are our standard payment terms:

      • Net 30 for customers with established credit
      • 50% upfront, 50% on delivery for new customers
      • Early payment discount: 2% if paid within 10 days

      📚 Sources:
      • Product Info (Relevance: 95%)
      • Sales Playbook (Relevance: 87%)
```

### Semantic Memory Retrieval (NEW in Phase 5.2)

```
You: @Elli What did we discuss about Acme Corp last week?
Elli: Based on our past conversations, we discussed the following:

      We reviewed their Q4 renewal opportunity valued at $250K.
      You mentioned they were interested in expanding to our Enterprise tier.

      💭 Relevant Past Conversations:
      • Discussion about Acme Corp renewal opportunity (from 2026-01-07)
      • Enterprise tier pricing inquiry (from 2026-01-08)
```

### Salesforce RAG Queries (NEW in Phase 5.3)

```
You: @Elli What deals are in negotiation stage?
Elli: Based on current Salesforce data:

      • Acme Corp Renewal - $250K, closes 2026-02-15
      • TechStart Expansion - $180K, closes 2026-02-28

      📚 Sources:
      • Acme Corp Renewal - $250,000 (Negotiation) [Salesforce] (Relevance: 95%)
      • TechStart Expansion - $180,000 (Proposal) [Salesforce] (Relevance: 89%)
```

```
You: @Elli Who should I contact at TechStart?
Elli: The primary contact at TechStart is:

      Michael Chen, VP of Engineering
      Email: mchen@techstart.io

      📚 Sources:
      • Michael Chen, VP Engineering [Salesforce Contact] (Relevance: 97%)
      • TechStart Inc [Salesforce Account] (Relevance: 85%)
```

## Development

### Running Tests

```bash
make test
```

### Code Formatting

```bash
make format
```

### Ingesting Knowledge Base

```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

### Syncing Salesforce Data

```bash
python scripts/ingest_salesforce.py
python scripts/ingest_salesforce.py --objects opportunities,accounts
python scripts/ingest_salesforce.py --limit 50
```

### Docker

```bash
make docker-build
make docker-run
```

## Documentation

- **[AGENTS.md](AGENTS.md)** - Coding guidelines and breadcrumbs for AI agents
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and data flows
- **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** - Contribution guidelines
- **[docs/CI_CD.md](docs/CI_CD.md)** - CI/CD pipeline documentation
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing scenarios and instructions

## Roadmap

### Completed (v0.3)
- ✅ **Phase 1**: Modular refactoring
- ✅ **Phase 2**: Entity extraction & smart Salesforce search
- ✅ **Phase 3**: Snowflake Cortex AI integration
- ✅ **Phase 4**: Conversation memory & context awareness
- ✅ **Phase 5.1**: RAG with vector search and knowledge base
- ✅ **Phase 5.2**: Semantic memory (long-term conversation summaries)
- ✅ **Phase 5.3**: Salesforce RAG integration (hybrid search with CRM data)
- ✅ **Phase 7**: Logging and monitoring (structured logging, metrics, audit trail)
- ✅ **Phase 8**: Unit tests and integration tests (pytest framework, 70%+ coverage)
- ✅ **Phase 9.1**: Cortex Agent integration (DEAL_AGENT via REST API)
- ✅ **Phase 10**: Salesforce OAuth & deal creation from Slack threads
- ✅ **Phase 12**: Azure deployment infrastructure (CI/CD pipeline, Key Vault integration)
- ✅ **Phase 13**: Production deployment (hardening, channel-based Opportunity types)

### Planned (Post-Pilot)
- 📋 **Phase 9.2**: Snowflake enterprise data integration (financial data, portfolio exposure)
- 📋 **Phase 11**: LevPro integration
- ⏸️ **Phase 6**: Additional Salesforce workflows (TABLED)

## License

Enterprise Internal Use

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## Support

For issues or questions, check [AGENTS.md](AGENTS.md) for context or create an issue.

---

**Current Version**: 0.3.0
**Last Updated**: 2026-02-03
**Status**: v0.3 Released - Production Deployment with Channel-Based Opportunity Types
