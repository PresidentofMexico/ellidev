# Semantic Memory User Guide

**Feature**: Semantic Memory (Phase 5.2)
**Version**: 0.5.1
**Status**: Production Ready

## What is Semantic Memory?

Semantic Memory gives Elli the ability to **remember and reference past conversations** beyond the immediate thread history. Think of it as Elli's long-term memory - it automatically summarizes conversations and can recall relevant discussions when you ask about them later.

### Three Layers of Context

Elli now has three layers of memory to provide comprehensive, context-aware responses:

| Layer | Scope | Retention | Example |
|-------|-------|-----------|---------|
| **Thread History** | Last 5 messages | Current session | "Update it" (references previous message) |
| **Semantic Memory** | Past conversations | 30 days (configurable) | "What did we discuss last week?" |
| **Knowledge Base** | Company documents | Permanent | "What are our payment terms?" |

## How It Works

### Auto-Summarization

Every 10 messages (by default), Elli automatically:
1. Reviews the conversation thread
2. Generates a structured summary with:
   - Main topic
   - Key entities (companies, people, products)
   - Important points discussed
   - Conversation category
3. Stores the summary for later retrieval

**You don't need to do anything** - this happens automatically in the background.

### Memory Retrieval

When you ask questions that reference past conversations, Elli:
1. Detects that you're asking about history
2. Searches through past conversation summaries
3. Finds the most relevant memories based on:
   - **Semantic similarity** (50%) - How well it matches your query
   - **Recency** (30%) - More recent conversations score higher
   - **User match** (20%) - Your own conversations are prioritized
4. Includes relevant memories in the response with dates

## Usage Examples

### Example 1: Referencing Past Discussions

```
You: @Elli What did we discuss about Acme Corp last week?

Elli: Based on our past conversations, we discussed the following:

      We reviewed their Q4 renewal opportunity valued at $250K.
      You mentioned they were interested in expanding to our Enterprise tier.
      The decision maker is Sarah Johnson, VP of Operations.

      💭 Relevant Past Conversations:
      • Discussion about Acme Corp renewal opportunity (from 2026-01-07)
      • Enterprise tier pricing inquiry (from 2026-01-08)
```

### Example 2: Following Up on Previous Topics

```
You: @Elli Remember when you mentioned the new pricing structure?

Elli: Yes! In our conversation from 2026-01-10, we discussed the new tiered
      pricing structure that goes into effect next quarter.

      💭 Relevant Past Conversations:
      • New pricing structure rollout discussion (from 2026-01-10)
```

### Example 3: Status Updates

```
You: @Elli What's the status of the TechStart deal?

Elli: Based on our previous discussions, TechStart was in the negotiation
      phase with a deal value of $180K. You mentioned they needed custom
      integration support.

      💭 Relevant Past Conversations:
      • TechStart deal progress update (from 2026-01-09)
```

## Memory Detection Keywords

Elli automatically searches memories when your query contains phrases like:

- "What did we discuss..."
- "You mentioned..."
- "You said..."
- "Earlier..."
- "Before..."
- "Last time..."
- "Previous..."
- "Remember..."
- "Recall..."
- "What was the status of..."
- "Tell me about..." (when referring to past conversations)

## Configuration

Semantic Memory is configured through environment variables in your `.env` file.

### Basic Configuration

```bash
# Enable or disable semantic memory
SEMANTIC_MEMORY_ENABLED=true

# How often to create summaries (every N messages)
MEMORY_SUMMARY_INTERVAL=10

# How far back to search for memories (in days)
MEMORY_SEARCH_DAYS_BACK=30

# How many memories to include in responses
MEMORY_TOP_K=2
```

### Configuration Options Explained

#### `SEMANTIC_MEMORY_ENABLED`
- **Default**: `true`
- **Options**: `true` or `false`
- **Description**: Master switch for semantic memory feature
- **When to disable**: If you want Elli to only use thread history and knowledge base

#### `MEMORY_SUMMARY_INTERVAL`
- **Default**: `10`
- **Range**: Any positive integer
- **Description**: Number of messages before creating a summary
- **Recommendations**:
  - `5-10`: Good for detailed conversations, more frequent summaries
  - `10-15`: Balanced (recommended for most use cases)
  - `15-20`: Less frequent, better for high-volume channels

#### `MEMORY_SEARCH_DAYS_BACK`
- **Default**: `30`
- **Range**: Any positive integer
- **Description**: How many days of conversation history to search
- **Recommendations**:
  - `7`: One week (for fast-paced teams)
  - `30`: One month (recommended default)
  - `90`: Three months (for long-term projects)
  - `180+`: Six months or more (for strategic initiatives)

#### `MEMORY_TOP_K`
- **Default**: `2`
- **Range**: 1-5 recommended
- **Description**: Number of past conversations to reference in responses
- **Recommendations**:
  - `1`: Minimal context, fastest
  - `2`: Balanced (recommended)
  - `3-5`: More comprehensive, but may clutter responses

## Best Practices

### 1. Use Descriptive Queries

✅ **Good**: "What did we discuss about the Acme Corp renewal?"
❌ **Less Effective**: "What did we talk about?"

More specific queries help Elli find the most relevant memories.

### 2. Reference Timeframes

✅ **Good**: "What was the status last week?"
✅ **Good**: "You mentioned something earlier today about pricing"

Timeframe references help narrow down the search.

### 3. Use Entity Names

✅ **Good**: "Remind me about the TechStart deal"
✅ **Good**: "What did Sarah say about the integration?"

Mentioning specific companies, people, or products improves accuracy.

### 4. Thread Continuity

For best results, keep related conversations in the same thread. This helps Elli:
- Build better summaries
- Maintain context
- Track conversation flow

## Understanding Memory Citations

When Elli references past conversations, you'll see citations like:

```
💭 Relevant Past Conversations:
• Discussion about Acme Corp renewal opportunity (from 2026-01-07)
```

This tells you:
- **Topic**: What was discussed
- **Date**: When the conversation happened
- **Relevance**: Elli chose this because it's most relevant to your query

## Privacy & Data

### User-Specific Memories

- Memories are filtered by user ID
- You primarily see your own past conversations
- Other users' conversations are scored lower in relevance

### Data Retention

- Memories are stored for the duration specified in `MEMORY_SEARCH_DAYS_BACK`
- Older memories are still stored but not retrieved (based on date filtering)
- Currently, there's no automatic deletion (planned for future)

### What Gets Summarized

Elli summarizes:
- ✅ User questions and Elli's responses
- ✅ Key decisions and action items
- ✅ Important entities (companies, people, products)
- ✅ Main topics and conversation flow

Elli does NOT store:
- ❌ Full message content (only summaries)
- ❌ Sensitive data intentionally (though summaries may reference it)
- ❌ System messages or metadata

## Troubleshooting

### "Elli isn't remembering past conversations"

**Check**:
1. Is `SEMANTIC_MEMORY_ENABLED=true` in your `.env` file?
2. Have you had at least 10 messages in the thread? (Summaries only created at intervals)
3. Is your query within the `MEMORY_SEARCH_DAYS_BACK` window?
4. Are you using memory detection keywords in your query?

**Solution**: Try asking explicitly: "Remember when we discussed [topic]?"

### "Elli is referencing irrelevant memories"

**Cause**: The relevance scoring may be finding loose semantic matches.

**Solution**:
- Be more specific in your query
- Reference specific entities or dates
- Reduce `MEMORY_TOP_K` to 1 for more focused responses

### "Summaries are too frequent/infrequent"

**Solution**: Adjust `MEMORY_SUMMARY_INTERVAL`:
- Increase number for less frequent summaries
- Decrease number for more frequent summaries

### "Memory citations are missing dates"

**Cause**: This may happen if the memory was created before the timestamp format was standardized.

**Solution**: This is expected for very old memories. New memories will always have dates.

## Technical Details

### Storage

- Memories are stored in the same vector store as the knowledge base
- They use the metadata type `"conversation_memory"` to differentiate from documents
- Searchable via semantic similarity (embeddings)

### Relevance Scoring Formula

```
Total Score = (0.5 × Semantic Similarity) + (0.3 × Recency) + (0.2 × User Match)
```

- **Semantic Similarity**: How well the memory matches your query (vector search score)
- **Recency**: Exponential decay with 30-day half-life (recent memories score higher)
- **User Match**: 100% if your memory, 50% if someone else's

### Mock Mode

If you don't have Snowflake credentials:
- Elli uses pattern-based summarization
- Extracts entities using regex
- Categories conversation types via keywords
- Full functionality available for testing

## Integration with Other Features

### Combined with RAG (Knowledge Base)

When you ask a question, Elli can use all three context layers:

```
You: @Elli What are our payment terms for the Acme renewal?

Elli: Based on our knowledge base and past conversations:

      Standard payment terms are Net 30 for established customers.

      For the Acme renewal specifically, we discussed offering:
      • 2% early payment discount
      • Quarterly invoicing option

      📚 Sources:
      • Product Info (Relevance: 95%)

      💭 Relevant Past Conversations:
      • Acme Corp payment terms discussion (from 2026-01-08)
```

### Combined with Thread History

```
Thread:
User: "Who handles the TechStart account?"
Elli: "Sarah Johnson is the primary contact..."

User: "What did we discuss about them last month?"
Elli: "Based on our conversation history and past discussions..."
      [References both thread history AND semantic memory]
```

## FAQ

### Q: How many conversations can Elli remember?

**A**: There's no hard limit. Elli can store and search through unlimited conversations, but only retrieves the most relevant ones based on your query.

### Q: Can I delete specific memories?

**A**: Not yet. Memory deletion is planned for a future release (Phase 5.2.2+).

### Q: Do memories persist if the bot restarts?

**A**: Yes! Memories are stored in the vector store and persist across restarts. However, the message count tracking (which triggers summarization) resets on restart.

### Q: Can Elli remember conversations from before Phase 5.2?

**A**: No. Semantic memory only captures conversations that happened after Phase 5.2 was deployed. Historical conversations before this feature are not summarized.

### Q: Does this work in direct messages?

**A**: Yes! Semantic memory works in both channel mentions (@Elli) and direct messages.

### Q: What happens if I disable semantic memory?

**A**: Elli will fall back to using only thread history (last 5 messages) and the knowledge base. Past memories remain stored but won't be retrieved.

## Getting Started Checklist

- [ ] Ensure `SEMANTIC_MEMORY_ENABLED=true` in your `.env` file
- [ ] Review configuration settings (intervals, search window, top K)
- [ ] Have conversations with Elli (need 10+ messages for first summary)
- [ ] Try asking "What did we discuss earlier?" to test memory retrieval
- [ ] Check for memory citations (💭) in responses
- [ ] Adjust configuration based on your team's needs

## Examples by Use Case

### Sales Teams

```
"What was the status of the Acme deal?"
"Remind me what Sarah mentioned about pricing"
"You said something about Q4 targets earlier"
```

### Support Teams

```
"What issues did we discuss for client XYZ?"
"Recall the resolution we planned for the API timeout"
"What was the previous ticket about?"
```

### Project Teams

```
"What did we decide about the deployment schedule?"
"Remind me of the technical requirements we discussed"
"Status of the integration milestone?"
```

## Related Documentation

- [PHASE5_2_SUMMARY.md](PHASE5_2_SUMMARY.md) - Technical implementation details
- [RAG_GUIDE.md](RAG_GUIDE.md) - Knowledge base and RAG features
- [README.md](../README.md) - Full project documentation
- [CHANGELOG.md](../CHANGELOG.md) - Version history and changes

## Support

If you have questions or issues:
1. Check this guide first
2. Review the [CHANGELOG.md](../CHANGELOG.md) for known issues
3. Check [AGENTS.md](../AGENTS.md) for implementation context
4. Create an issue with details about your problem

---

**Last Updated**: 2026-01-14
**Version**: 0.5.1
**Feature Status**: Production Ready ✅
