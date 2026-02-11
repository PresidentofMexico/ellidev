# Phase 6: Additional Salesforce Workflows - Implementation Plan

**Version**: 0.7.0 (Planned)
**Status**: Planning
**Agent**: Claude Code (Sonnet 4.5)

## Overview

Phase 6 expands Salesforce workflow automation beyond opportunity updates to include:
1. **Creating new opportunities** via natural language
2. **Searching and displaying contacts** with interactive results
3. **Creating new contacts** with smart defaults
4. **Account lookups** with related opportunities
5. **Pipeline reporting** with stage-based summaries

## Goals

1. **Opportunity Creation**: "Create opportunity for Acme Corp worth $100K"
2. **Contact Search**: "Who are the contacts at TechStart?" → List with action buttons
3. **Contact Creation**: "Add Sarah Johnson at Acme Corp as VP Sales"
4. **Account Overview**: "Show me details for Global Systems" → Account + related opportunities
5. **Pipeline View**: "What's in my pipeline?" → Stage breakdown with totals

## Features

### 6.1: Create Opportunity Workflow

**Purpose**: Allow users to create opportunities via natural language

**Trigger Patterns**:
- "Create opportunity for [Company] worth [$Amount]"
- "Add deal for [Company] at [Stage] stage"
- "New opportunity: [Company] - [Name]"

**Implementation**:
```python
# listeners/messages.py
@app.message(re.compile(r"create opportunity|add deal|new opportunity", re.IGNORECASE))
def trigger_create_opportunity(message, say, client):
    # Extract: company, amount, stage, name
    # Open modal with pre-filled fields
    # On submission: Create SF opportunity via API
```

**Modal Fields**:
- Opportunity Name (required)
- Account (search/autocomplete)
- Amount (optional)
- Close Date (date picker, default: +30 days)
- Stage (dropdown, default: Discovery)
- Description (optional text area)

**Success Response**:
```
✅ Created opportunity "Acme Corp Renewal - $250K"
   Stage: Discovery
   Close Date: 2026-02-15

   View in Salesforce: [Link]
```

### 6.2: Contact Search Workflow

**Purpose**: Search and display contacts with action buttons

**Trigger Patterns**:
- "Who are the contacts at [Company]?"
- "Find contacts for [Company]"
- "Show me contacts at [Company]"
- "Contacts for [Company]"

**Implementation**:
```python
def handle_contact_search(company_name):
    # Search Salesforce contacts by account name
    # Return interactive message with buttons:
    # [Email Contact] [View in SF] [Add to Opportunity]
```

**Response Format**:
```
🔍 Contacts at Acme Corp:

1. Sarah Johnson
   Title: VP of Operations
   Email: sjohnson@acmecorp.example.com
   Phone: (555) 123-4567
   [Email] [View in Salesforce]

2. Michael Smith
   Title: Director of IT
   Email: msmith@acmecorp.example.com
   Phone: (555) 123-4568
   [Email] [View in Salesforce]

Found 2 contacts
```

### 6.3: Create Contact Workflow

**Purpose**: Add new contacts to Salesforce

**Trigger Patterns**:
- "Add [Name] at [Company] as [Title]"
- "Create contact: [Name], [Title] at [Company]"
- "New contact for [Company]: [Name]"

**Implementation**:
- Extract name, company, title from message
- Open modal with pre-filled fields
- On submission: Create SF contact via API

**Modal Fields**:
- First Name (required)
- Last Name (required)
- Account (search/autocomplete)
- Title (optional)
- Email (optional)
- Phone (optional)

### 6.4: Account Overview Workflow

**Purpose**: Display account details with related opportunities

**Trigger Patterns**:
- "Show me [Company]"
- "Account details for [Company]"
- "Tell me about [Company]"

**Implementation**:
```python
def handle_account_overview(company_name):
    account = sf_client.get_account_by_name(company_name)
    opportunities = sf_client.get_opportunities_by_account(account_id)
    contacts = sf_client.get_contacts_by_account(account_id)

    # Format rich message with sections:
    # - Account info (industry, website, phone)
    # - Open opportunities (with stages/amounts)
    # - Key contacts (primary contact highlighted)
```

**Response Format**:
```
🏢 Global Systems

Industry: Manufacturing
Website: https://globalsystems.example.com
Employees: 50,000
Location: Chicago, IL

💼 Open Opportunities (2):
  • Global Systems New Contract - $420K (Discovery)
  • Global Systems Expansion - $180K (Proposal)
  Total Pipeline: $600K

👥 Key Contacts (3):
  • Jennifer Martinez (CTO) - Primary Contact
  • David Lee (VP Engineering)
  • Amy Chen (Director of Operations)

[View Full Account in Salesforce]
```

### 6.5: Pipeline Reporting Workflow

**Purpose**: Show user's pipeline breakdown by stage

**Trigger Patterns**:
- "What's in my pipeline?"
- "Show my pipeline"
- "Pipeline report"
- "My opportunities"

**Implementation**:
```python
def handle_pipeline_report(user_id):
    # Get opportunities owned by user (via Slack→SF user mapping)
    # Group by stage
    # Calculate totals per stage
    # Format as breakdown
```

**Response Format**:
```
📊 Your Pipeline Report

Discovery (3 deals):
  • Acme Corp Renewal - $250K
  • TechStart Expansion - $180K
  • NewCo Initial - $100K
  Subtotal: $530K

Proposal (2 deals):
  • Global Systems Expansion - $420K
  • StartupXYZ - $75K
  Subtotal: $495K

Negotiation (1 deal):
  • Enterprise Inc Renewal - $600K
  Subtotal: $600K

📈 Total Pipeline: $1,625K (6 opportunities)
```

## Technical Architecture

### File Structure

```
/workflows
├── salesforce.py           # MODIFIED: Add new workflow handlers
└── salesforce_create.py    # NEW: Opportunity/contact creation logic

/listeners
├── messages.py             # MODIFIED: Add new trigger patterns
└── mentions.py             # No changes

/services
├── sf_client.py            # MODIFIED: Add create methods, search methods
└── user_mapping.py         # NEW: Map Slack users to SF users (future)
```

### New SF Client Methods

**File**: `services/sf_client.py`

```python
class SalesforceClient:
    # Existing methods...

    def create_opportunity(self, data: Dict) -> Dict:
        """Create new opportunity in Salesforce"""

    def create_contact(self, data: Dict) -> Dict:
        """Create new contact in Salesforce"""

    def search_contacts_by_account(self, account_name: str) -> List[Dict]:
        """Find contacts for given account"""

    def get_account_details(self, account_name: str) -> Dict:
        """Get account with related opps and contacts"""

    def get_opportunities_by_owner(self, owner_id: str) -> List[Dict]:
        """Get opportunities for specific owner (for pipeline)"""
```

## Implementation Steps

### Step 1: Enhance SF Client

Add CRUD operations:
- `create_opportunity()` - POST to Opportunity object
- `create_contact()` - POST to Contact object
- `search_contacts_by_account()` - Query contacts by account name
- `get_account_details()` - Query account with SOQL joins
- `get_opportunities_by_owner()` - Query opportunities by owner ID

### Step 2: Create Opportunity Workflow

1. Add trigger pattern to `listeners/messages.py`
2. Extract company, amount, stage from message
3. Search for account (reuse existing search logic)
4. Open modal with pre-filled fields
5. Handle submission in `workflows/salesforce.py`
6. Call `sf_client.create_opportunity()`
7. Send success message with SF link

### Step 3: Contact Search Workflow

1. Add trigger pattern to `listeners/messages.py`
2. Extract company name
3. Call `sf_client.search_contacts_by_account()`
4. Format results with action buttons
5. Handle button clicks (email mailto:, SF link)

### Step 4: Create Contact Workflow

1. Add trigger pattern to `listeners/messages.py`
2. Extract name, company, title
3. Open modal with pre-filled fields
4. Handle submission
5. Call `sf_client.create_contact()`
6. Send success message

### Step 5: Account Overview Workflow

1. Add trigger pattern to `listeners/messages.py`
2. Extract company name
3. Call `sf_client.get_account_details()`
4. Format rich message with sections
5. Include action buttons

### Step 6: Pipeline Report Workflow

1. Add trigger pattern to `listeners/messages.py`
2. Get Slack user ID from message
3. Map to Salesforce owner ID (hardcoded for Phase 6.1, proper mapping in 6.2)
4. Call `sf_client.get_opportunities_by_owner()`
5. Group by stage, calculate totals
6. Format as breakdown

## Configuration

### Environment Variables

No new configuration needed. Reuses existing:
- `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN` from Phase 2

### Future Enhancement (Phase 6.2)

User mapping configuration:
```bash
# User Mapping (Phase 6.2)
SF_USER_MAPPING='{"U12345":"sf_user_id_1","U67890":"sf_user_id_2"}'
```

## Testing Strategy

### Mock Mode Testing

Create mock implementations:
- `_mock_create_opportunity()` - Returns fake opportunity ID
- `_mock_create_contact()` - Returns fake contact ID
- `_mock_search_contacts()` - Returns sample contacts
- `_mock_get_account_details()` - Returns sample account with opps

### Real Mode Testing

1. Test create opportunity with real SF account
2. Verify opportunity appears in Salesforce
3. Test contact search returns real contacts
4. Test create contact adds to Salesforce
5. Verify account overview shows real data

## Usage Examples

### Example 1: Create Opportunity

```
You: Create opportunity for Acme Corp worth $100K
Elli: 🔍 Searching for Acme Corp...
      ✅ Found account: Acme Corp

      [Modal opens with pre-filled fields]

You: [Fills in details and submits]
Elli: ✅ Created opportunity "Acme Corp Q1 Renewal - $100K"
      Stage: Discovery
      Close Date: 2026-02-15

      View in Salesforce: https://...
```

### Example 2: Contact Search

```
You: Who are the contacts at TechStart?
Elli: 🔍 Contacts at TechStart Inc:

      1. Michael Chen
         Title: VP of Engineering
         Email: mchen@techstart.io
         Phone: (555) 234-5678
         [Email] [View in Salesforce]

      2. Lisa Wang
         Title: CTO
         Email: lwang@techstart.io
         Phone: (555) 234-5679
         [Email] [View in Salesforce]

      Found 2 contacts
```

### Example 3: Account Overview

```
You: Show me Global Systems
Elli: 🏢 Global Systems

      Industry: Manufacturing
      Employees: 50,000
      Location: Chicago, IL

      💼 Open Opportunities (1):
        • Global Systems New Contract - $420K (Discovery)

      👥 Key Contacts (1):
        • Jennifer Martinez (CTO)

      [View Full Account in Salesforce]
```

### Example 4: Pipeline Report

```
You: What's in my pipeline?
Elli: 📊 Your Pipeline Report

      Discovery (2):
        • Acme Corp - $250K
        • TechStart - $180K
        Subtotal: $430K

      Negotiation (1):
        • Global Systems - $420K
        Subtotal: $420K

      📈 Total: $850K (3 opportunities)
```

## Design Decisions

### Decision 1: Modal vs Direct Creation

**Options**:
- A) Always show modal (more control, explicit)
- B) Direct creation for simple cases, modal for complex

**Decision**: Option A for Phase 6.1
- Predictable UX
- Allows review before creation
- Can enhance with direct creation in 6.2

### Decision 2: User Mapping

**Options**:
- A) Hardcoded mapping (simple, limited)
- B) Environment variable mapping (flexible, manual setup)
- C) Slack user field mapping (automatic, requires SF setup)

**Decision**: Option B for Phase 6.1
- Simple to implement
- Flexible for testing
- Can migrate to Option C in 6.2

### Decision 3: Contact Search Results

**Options**:
- A) Plain text list
- B) Interactive buttons (email, view SF)
- C) Full modal with all contact details

**Decision**: Option B
- Balance between simplicity and functionality
- Action buttons provide quick access
- Expandable to Option C later if needed

## Backward Compatibility

✅ **No Breaking Changes**:
- All new workflows are additive
- Existing Phase 1-5.3 functionality unchanged
- New trigger patterns don't conflict with existing
- Mock mode fallbacks for all new features

## Success Metrics

### Functional Completeness

- [ ] Create opportunity workflow implemented
- [ ] Contact search workflow implemented
- [ ] Create contact workflow implemented
- [ ] Account overview workflow implemented
- [ ] Pipeline report workflow implemented
- [ ] Enhanced SF client with CRUD methods
- [ ] Mock mode for all new features
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
| API rate limits | Medium | Batch operations, cache where possible |
| User mapping complexity | Medium | Start with hardcoded mapping, enhance later |
| Modal validation | Low | Client-side + server-side validation |
| Permission errors | Medium | Graceful error messages, check permissions |

## Future Enhancements (Phase 6.2+)

1. **Automatic User Mapping**: Use Slack profile fields or SF integration
2. **Direct Creation**: Skip modal for simple "Create opp for X worth $Y" commands
3. **Bulk Operations**: "Create 5 opportunities from this list"
4. **Advanced Filters**: Pipeline by date range, stage, amount
5. **Forecast Reports**: Win probability, weighted pipeline
6. **Activity Logging**: Log all Slack→SF interactions

## Dependencies

**No New Dependencies**: Reuses existing infrastructure
- ✅ `simple-salesforce` - Already installed (Phase 2)
- ✅ `services/sf_client.py` - Extend existing client

## Timeline Estimate

| Task | Estimated Lines | Complexity |
|------|----------------|------------|
| SF client enhancements | 200 lines | Medium |
| Create opportunity workflow | 150 lines | Medium |
| Contact search workflow | 100 lines | Low |
| Create contact workflow | 150 lines | Medium |
| Account overview workflow | 120 lines | Medium |
| Pipeline report workflow | 100 lines | Medium |
| Mock implementations | 150 lines | Low |
| Documentation | 200 lines | Low |
| **Total** | **1,170 lines** | **Medium** |

## Ready to Plan

Planning complete. Ready for user approval to begin implementation.

**Next Step**: Await user approval, then implement workflows in order:
1. SF client enhancements (foundation)
2. Create opportunity (most requested)
3. Contact search (quick win)
4. Create contact (natural extension)
5. Account overview (comprehensive)
6. Pipeline report (power feature)

---

**Created by**: Claude Code (Sonnet 4.5)
**Date**: 2026-01-14
**Status**: Planning Complete - Awaiting Approval ✅
