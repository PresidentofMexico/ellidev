# Testing Guide - Phase 2: Smart Salesforce Integration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `slack_bolt==1.18.0`
- `slack_sdk==3.27.1`
- `python-dotenv==1.0.0`
- `simple-salesforce==1.12.6` (NEW)

### 2. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Add your Slack credentials (required):
```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
```

**Optional**: Add Salesforce credentials for real API testing:
```bash
SF_USERNAME=your-username@company.com
SF_PASSWORD=your-password
SF_SECURITY_TOKEN=your-security-token
```

If you don't add Salesforce credentials, the app will use **mock mode** automatically.

### 3. Run the Bot

```bash
python app.py
```

You should see:
```
⚠️ Salesforce credentials not found in environment. Using mock mode.
⚡️ Elli is running!
```

## Testing Scenarios

### Scenario 1: Smart Update - Single Result

**Test in Slack:**
```
Update TechStart to Negotiation
```

**Expected Response:**
```
🔍 Searching for opportunities matching 'TechStart'...

✅ I found 1 opportunity for 'TechStart':

TechStart Inc - Pilot
Current Stage: Discovery
Close Date: 2026-02-28

[📝 Update to Negotiation] (clickable button)
```

**Action**: Click the button to open pre-filled modal
- Opportunity name: "TechStart Inc - Pilot"
- Stage: Pre-selected to "Negotiation"

### Scenario 2: Smart Update - Multiple Results

**Test in Slack:**
```
Update Acme Corp to Closed Won
```

**Expected Response:**
```
🔍 Searching for opportunities matching 'Acme Corp'...

🔍 I found 2 opportunities for 'Acme Corp'. Which one would you like to update?

[Select an opportunity ▼]
```

**Dropdown options:**
- Acme Corp - Q1 Expansion (Discovery)
- Acme Corp - Enterprise Deal (Negotiation)

**Action**: Select one from dropdown to open pre-filled modal

### Scenario 3: Smart Update - No Results

**Test in Slack:**
```
Update NonExistent Corp to Discovery
```

**Expected Response:**
```
🔍 Searching for opportunities matching 'NonExistent Corp'...

🔍 I couldn't find any opportunities for 'NonExistent Corp'.
Please check the spelling or try a different search term.
```

### Scenario 4: Alternative Pattern

**Test in Slack:**
```
Set Global Systems stage to Discovery
```

**Expected Response:**
```
🔍 Searching for opportunities matching 'Global Systems'...

✅ I found 1 opportunity for 'Global Systems':

Global Systems - Migration
Current Stage: Closed Won
Close Date: 2026-01-15

[📝 Update to Discovery] (clickable button)
```

### Scenario 5: Legacy Fallback

**Test in Slack:**
```
update salesforce
```

**Expected Response:**
```
👋 @YourName, let's update that opportunity.

[📝 Open Update Form] (button)
```

**Action**: Click button to open blank modal (no pre-fill)

## Mock Data Available

When running in mock mode, the following opportunities are available:

| Company | Opportunity Name | Current Stage | Close Date |
|---------|------------------|---------------|------------|
| Acme Corp | Acme Corp - Q1 Expansion | Discovery | 2026-03-31 |
| Acme Corp | Acme Corp - Enterprise Deal | Negotiation | 2026-04-15 |
| TechStart | TechStart Inc - Pilot | Discovery | 2026-02-28 |
| Global Systems | Global Systems - Migration | Closed Won | 2026-01-15 |

## Supported Stage Values

The following stages are recognized in natural language:
- `discovery` / `Discovery`
- `negotiation` / `Negotiation`
- `closed won` / `Closed Won`

## Testing Real Salesforce API

### Prerequisites

1. Salesforce account with API access
2. Security token (reset from Salesforce settings if needed)
3. Opportunities in your Salesforce org

### Setup

Add to `.env`:
```bash
SF_USERNAME=your-username@company.com
SF_PASSWORD=your-password
SF_SECURITY_TOKEN=your-security-token
```

### Expected Console Output

```
✅ Connected to Salesforce API
⚡️ Elli is running!
```

### Testing Real Queries

Try searching for actual opportunities in your org:
```
Update [Your Company Name] to Negotiation
```

The bot will search your real Salesforce data and return actual opportunities.

### Successful Update Console Output

When you submit the modal:
```
✅ SALESFORCE API: Updated 'Company Name - Deal' (ID: 006xxx) to stage 'Negotiation'
```

### Error Handling

If there's an API error:
```
❌ Error updating Salesforce: [error details]
```

The user receives:
```
❌ Error: Could not update 'Company Name'. Please check the opportunity name and try again.
```

## Troubleshooting

### Issue: "simple-salesforce not installed"

**Solution:**
```bash
pip install simple-salesforce==1.12.6
```

### Issue: "Could not connect to Salesforce"

**Possible causes:**
1. Incorrect username/password
2. Missing or incorrect security token
3. IP restrictions on Salesforce org
4. User doesn't have API access

**Solution:**
- Verify credentials in `.env`
- Reset security token from Salesforce
- Check Salesforce login history for blocked attempts
- Contact Salesforce admin for API access

### Issue: "No opportunities found" (in real mode)

**Possible causes:**
1. No opportunities match the search term
2. User doesn't have permission to view opportunities
3. Search term is too specific

**Solution:**
- Try broader search terms
- Check Salesforce permissions
- Verify opportunities exist in your org

### Issue: Bot doesn't respond

**Possible causes:**
1. Message listener not matching pattern
2. Bot not in channel
3. Slack tokens expired

**Solution:**
- Check pattern syntax (must include stage name)
- Invite bot to channel with `/invite @Elli`
- Verify tokens in `.env`

## Advanced Testing

### Test Modal Pre-fill

1. Send: `Update Acme Corp to Closed Won`
2. Select "Acme Corp - Q1 Expansion" from dropdown
3. Verify modal opens with:
   - ✅ Opportunity name: "Acme Corp - Q1 Expansion"
   - ✅ Stage: Pre-selected to "Closed Won"
4. Change stage to "Negotiation"
5. Submit
6. Verify confirmation message

### Test Case Insensitivity

These should all work:
- `update acme corp to closed won`
- `UPDATE ACME CORP TO CLOSED WON`
- `Update Acme Corp to Closed Won`

### Test Stage Variations

These should all work:
- `Update Acme Corp to closed won`
- `Update Acme Corp to Closed Won`
- `Update Acme Corp to CLOSED WON`

## Performance Testing

### Response Times

Expected response times in mock mode:
- Entity extraction: <100ms
- Search: <50ms (in-memory)
- Total: <200ms

Expected response times with real Salesforce API:
- Entity extraction: <100ms
- Search: 200-1000ms (API call)
- Update: 200-1000ms (API call)

### Load Testing

For production, test with:
- Multiple concurrent users
- Rapid-fire requests
- Large result sets (>5 opportunities)

## Next Steps

After verifying Phase 2 works:
1. Test all scenarios above ✅
2. Try with real Salesforce credentials
3. Document any issues found
4. Ready for Phase 3 implementation

## Feedback & Issues

Found a bug? Document:
1. What command you sent
2. Expected behavior
3. Actual behavior
4. Console logs
5. Error messages

---

**Last Updated**: 2026-01-14
**Phase**: 2 - Smart Salesforce Integration
