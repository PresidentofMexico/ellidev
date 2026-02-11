# Elli Architecture Documentation

## System Overview

Elli is a hybrid Slack bot that combines deterministic workflow automation with AI assistance using a two-layer routing approach.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Slack User                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Slack API (Socket Mode)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                         app.py                               │
│                   (Entry Point & Router)                     │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐         ┌──────────────────────┐
│   Layer 1: Workflows │         │   Layer 2: AI        │
│   (Regex Matching)   │         │   (Fallback)         │
└──────────┬───────────┘         └──────────┬───────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐         ┌──────────────────────┐
│   /listeners/        │         │   /listeners/        │
│   messages.py        │         │   mentions.py        │
└──────────┬───────────┘         └──────────┬───────────┘
           │                               │
           ▼                               ▼
┌──────────────────────┐         ┌──────────────────────┐
│   /workflows/        │         │   /services/         │
│   salesforce.py      │         │   ai_service.py      │
└──────────┬───────────┘         └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│   /services/         │
│   sf_client.py       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Salesforce API     │
└──────────────────────┘
```

## Layer 1: Workflow Automation (Phase 2)

### Message Flow - Smart Salesforce Update

```
User sends: "Update Acme Corp to Closed Won"
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ listeners/messages.py                                    │
│                                                          │
│ @app.message(regex: "update (.+?) to (discovery|...)")  │
│   │                                                      │
│   ├─> Extract: company_name = "Acme Corp"               │
│   ├─> Extract: target_stage = "Closed Won"              │
│   └─> Call: handle_smart_update(client, user_id, ...)   │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ workflows/salesforce.py                                  │
│                                                          │
│ handle_smart_update(client, user_id, company, stage)    │
│   │                                                      │
│   ├─> Initialize: sf_client = SalesforceClient()        │
│   ├─> Search: opportunities = sf_client.search(...)     │
│   │                                                      │
│   ├─> IF len(opportunities) == 0:                       │
│   │     └─> Send: "Not found" message                   │
│   │                                                      │
│   ├─> ELIF len(opportunities) == 1:                     │
│   │     └─> Send: Auto-display with button              │
│   │                                                      │
│   └─> ELSE (multiple):                                  │
│       └─> Send: Disambiguation dropdown                 │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ services/sf_client.py                                    │
│                                                          │
│ search_opportunities(company_name)                       │
│   │                                                      │
│   ├─> IF has_credentials:                               │
│   │     ├─> Connect to Salesforce                       │
│   │     ├─> Execute SOQL:                               │
│   │     │   "SELECT Id, Name, StageName, CloseDate      │
│   │     │    FROM Opportunity                           │
│   │     │    WHERE Name LIKE '%{company}%'              │
│   │     │    LIMIT 5"                                   │
│   │     └─> Return: real results                        │
│   │                                                      │
│   └─> ELSE:                                             │
│       └─> Return: mock_search_opportunities()           │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  Return Results │
                 └────────────────┘
```

### User Interaction Flow

```
Single Result Flow:
─────────────────
User: "Update TechStart to Negotiation"
  ↓
Bot: "✅ I found 1 opportunity..."
     [TechStart Inc - Pilot]
     [📝 Update to Negotiation] ← Button
  ↓
User: Clicks button
  ↓
Bot: Opens pre-filled modal
     • Name: "TechStart Inc - Pilot" (pre-filled)
     • Stage: "Negotiation" (pre-selected)
     • ID: stored in private_metadata
  ↓
User: Submits modal
  ↓
Bot: "✅ Success! Updated TechStart Inc to Negotiation"


Multiple Results Flow:
─────────────────────
User: "Update Acme Corp to Closed Won"
  ↓
Bot: "🔍 I found 2 opportunities..."
     [Select an opportunity ▼]
     • Acme Corp - Q1 Expansion
     • Acme Corp - Enterprise Deal
  ↓
User: Selects from dropdown
  ↓
Bot: Opens pre-filled modal
  ↓
User: Submits
  ↓
Bot: "✅ Success! Updated [Name] to Closed Won"


No Results Flow:
────────────────
User: "Update XYZ Corp to Discovery"
  ↓
Bot: "🔍 I couldn't find any opportunities for 'XYZ Corp'..."
  ↓
[End]
```

## Module Responsibilities

### `/app.py` - Entry Point
**Responsibility**: Initialize Slack app, register listeners, start server

```python
Concerns:
- Load environment variables
- Initialize Slack app
- Register listener modules
- Start Socket Mode handler
- Error handling for missing tokens
```

### `/listeners/` - Event Routing

#### `messages.py` - Workflow Triggers
**Responsibility**: Pattern matching and entity extraction

```python
Concerns:
- Register regex patterns
- Extract entities from messages
- Route to appropriate workflows
- Handle button/dropdown interactions
- NO business logic
```

#### `mentions.py` - AI Fallback
**Responsibility**: Handle app mentions and DMs

```python
Concerns:
- Detect app mentions
- Filter out workflow keywords
- Route to AI service
- Handle DM vs channel routing
```

### `/workflows/` - Business Logic

#### `salesforce.py` - Salesforce Workflows
**Responsibility**: Salesforce-specific business logic

```python
Concerns:
- Search result handling (0/1/multiple)
- Modal generation (pre-fill logic)
- User interaction flows
- Message formatting
- Calling service layer
- NO direct API calls
```

### `/services/` - External Integrations

#### `sf_client.py` - Salesforce API Client
**Responsibility**: Salesforce API communication

```python
Concerns:
- API authentication
- SOQL query execution
- Opportunity CRUD operations
- Error handling
- Mock fallback for testing
- NO UI logic
```

#### `ai_service.py` - AI Service Client
**Responsibility**: LLM communication (future)

```python
Concerns:
- LLM API calls
- Prompt formatting
- Response parsing
- RAG integration (future)
```

## Data Flow - Phase 2 Smart Update

### 1. Message Received
```
Slack → app.py → listeners/messages.py
```

### 2. Entity Extraction
```
listeners/messages.py
  Input:  "Update Acme Corp to Closed Won"
  Regex:  r"update\s+(.+?)\s+to\s+(discovery|negotiation|closed won)"
  Output: company="Acme Corp", stage="Closed Won"
```

### 3. Workflow Invocation
```
listeners/messages.py → workflows/salesforce.py
  Call: handle_smart_update(client, user_id, "Acme Corp", "Closed Won")
```

### 4. Service Call
```
workflows/salesforce.py → services/sf_client.py
  Call: sf_client.search_opportunities("Acme Corp")
  Returns: [
    {Id: "006xxx", Name: "Acme Corp - Q1", StageName: "Discovery", ...},
    {Id: "006yyy", Name: "Acme Corp - Enterprise", StageName: "Negotiation", ...}
  ]
```

### 5. Result Handling
```
workflows/salesforce.py
  IF 0 results:   → Send "not found" message
  IF 1 result:    → Send auto-display with button
  IF multiple:    → Send disambiguation dropdown
```

### 6. User Action
```
User clicks button/dropdown
  ↓
listeners/messages.py (action handler)
  ↓
workflows/salesforce.py
  Call: open_salesforce_modal(..., prefill_opp_id, prefill_opp_name, prefill_stage)
```

### 7. Modal Submission
```
User submits modal
  ↓
listeners/messages.py (view handler)
  ↓
workflows/salesforce.py
  Call: handle_salesforce_submission(client, user_id, view)
  ↓
services/sf_client.py
  Call: update_opportunity_stage(opp_id, opp_name, new_stage)
  ↓
Salesforce API (if credentials available)
```

## Configuration Flow

```
.env file
  ↓
python-dotenv loads
  ↓
os.environ
  ↓
Services read on initialization:
  • SalesforceClient() reads SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN
  • App() reads SLACK_BOT_TOKEN, SLACK_APP_TOKEN
  ↓
Graceful fallback if missing:
  • Salesforce: Use mock mode
  • Slack: Error and exit
```

## Error Handling Strategy

### Level 1: Service Layer
```python
try:
    # Salesforce API call
except SalesforceAPIError:
    # Log error
    # Return mock data or empty list
```

### Level 2: Workflow Layer
```python
if not results:
    # Send user-friendly "not found" message
elif service_error:
    # Send "try again later" message
```

### Level 3: Listener Layer
```python
try:
    # Call workflow
except Exception as e:
    # Log error
    # Send generic error message
    # Don't crash bot
```

## Security Architecture

### Secrets Management
```
.env (gitignored)
  ↓
Environment Variables
  ↓
Service Initialization
  ↓
In-Memory Only (never logged)
```

### API Authentication
```
Salesforce:
  Username + Password + Security Token
  ↓
  OAuth 2.0 session
  ↓
  Time-limited access token

Slack:
  Bot Token (xoxb-...)
  App Token (xapp-...)
  ↓
  Socket Mode connection
```

## Scalability Considerations

### Current Architecture (Socket Mode)
- ✅ Good for: Development, internal use, small teams
- ❌ Limited: Single process, no load balancing

### Future Architecture (HTTP Mode)
- Multiple worker processes
- Load balancer
- Message queue for async processing
- Redis for session management

## Testing Architecture

### Mock Mode (No Credentials)
```
User Request
  ↓
Listener (real)
  ↓
Workflow (real)
  ↓
Service (mock) ← Uses _mock_search_opportunities()
  ↓
Returns hardcoded data
```

### Real Mode (With Credentials)
```
User Request
  ↓
Listener (real)
  ↓
Workflow (real)
  ↓
Service (real) ← Connects to Salesforce API
  ↓
Returns real Salesforce data
```

## Performance Characteristics

### Layer 1 (Workflows)
- Regex matching: <1ms
- Entity extraction: <1ms
- Workflow routing: <10ms

### Layer 2 (AI) - Future
- LLM API call: 500-3000ms
- Depends on model and prompt length

### Service Layer
- Mock mode: <10ms
- Real Salesforce API: 200-1000ms
- Depends on network and data volume

---

**Document Version**: 2.0
**Last Updated**: 2026-01-14
**Phase**: 2 - Smart Salesforce Integration Complete
