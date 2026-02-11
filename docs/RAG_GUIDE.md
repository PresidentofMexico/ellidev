# RAG User Guide

## What is RAG?

**RAG (Retrieval Augmented Generation)** allows Elli to search your company's knowledge base and use that information to answer questions accurately with source citations.

Think of RAG as giving Elli access to your company's documentation, so she can answer questions like:
- "What are our payment terms?"
- "How do I onboard a new customer?"
- "What features are in the Professional tier?"

## How It Works

```
1. You ask a question: "What is our pricing?"
2. Elli searches the knowledge base for relevant information
3. Elli reads the top matching documents
4. Elli generates an answer based on what she found
5. Elli cites her sources with relevance scores
```

## Getting Started

### 1. Check if RAG is Enabled

Ask Elli a knowledge question:
```
@Elli What are our payment terms?
```

If RAG is working, you'll see:
- A detailed answer based on your documents
- A "📚 Sources:" section at the bottom
- Document names with relevance percentages

### 2. Add Your Documents

#### Create Markdown Files

Place `.md` files in the `/knowledge` directory:
```
/knowledge
├── product_info.md
├── sales_playbook.md
├── company_policies.md
└── faq.md
```

#### Document Format

Use this structure:
```markdown
# Document Title

## Section 1

Your content here. Be specific and detailed.

## Section 2

More content...
```

**Tips for Good Documents:**
- Use clear headers (`##` for sections)
- Write in complete sentences
- Include specific details (numbers, dates, names)
- Avoid abbreviations without explanation
- Use bullet points for lists

### 3. Ingest Documents

Run the ingestion script:
```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

You'll see output like:
```
✅ Found 4 markdown file(s)
📄 Reading: knowledge/product_info.md
📄 Reading: knowledge/sales_playbook.md
...
✅ Generated 67 chunks
💾 Ingesting into vector store...
✅ Ingestion complete!
```

### 4. Test It Out

Ask Elli questions about your documents:
```
@Elli What is our pricing?
@Elli How do I close a deal?
@Elli What are the product features?
```

## Usage Examples

### Product Questions

**Question:**
```
@Elli What is included in the Professional tier?
```

**Response:**
```
Based on our knowledge base, the Professional tier includes:

• Unlimited automated workflows
• Advanced AI assistant with 20,000 queries/month
• Custom workflow builder
• Priority support
• 50 GB knowledge base storage
• Advanced analytics dashboard

Pricing: $99 per user/month (billed annually)

📚 Sources:
• Product Info (Relevance: 96%)
```

### Sales Questions

**Question:**
```
@Elli How should I handle a pricing objection?
```

**Response:**
```
Based on the sales playbook, here's how to handle pricing objections:

Focus on total value, not just cost. Our customers see 60% time savings
on manual tasks, which typically pays for Elli within 6 months. The
Professional tier includes unlimited workflows while competitors charge
per automation.

Ask: "What specific ROI metrics matter most to your team?"

📚 Sources:
• Sales Playbook (Relevance: 92%)
```

### Policy Questions

**Question:**
```
@Elli What is our refund policy?
```

**Response:**
```
According to our company policies:

We offer a 30-day money-back guarantee for all new customers. If you're
not satisfied within the first 30 days, we'll provide a full refund,
no questions asked.

For annual contracts, pro-rated refunds are available within the first
90 days.

📚 Sources:
• Company Faq (Relevance: 89%)
• Product Info (Relevance: 75%)
```

## Advanced Usage

### Custom Chunking

Control how documents are split:

```bash
# Larger chunks for more context (800 tokens)
python scripts/ingest_knowledge.py --path ./knowledge --chunk-size 800

# More overlap for better continuity (100 tokens)
python scripts/ingest_knowledge.py --path ./knowledge --overlap 100

# Both together
python scripts/ingest_knowledge.py --path ./knowledge --chunk-size 800 --overlap 100
```

**When to adjust:**
- **Larger chunks (800)**: Long-form content, tutorials, detailed explanations
- **Smaller chunks (300)**: FAQs, short reference docs, bullet-point lists
- **More overlap (100)**: Content where context matters (stories, procedures)
- **Less overlap (25)**: Independent items (FAQ, glossary, price lists)

### Ingesting Single Files

Update just one document:
```bash
python scripts/ingest_knowledge.py --path ./knowledge/product_info.md
```

### Recursive Scanning

Scan subdirectories:
```
/knowledge
├── products/
│   ├── platform.md
│   └── integrations.md
├── sales/
│   ├── playbook.md
│   └── objections.md
```

```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

## Configuration

### Environment Variables

Edit your `.env` file:

```bash
# Enable or disable RAG
RAG_ENABLED=true

# Number of document chunks to use per query (1-10)
RAG_TOP_K=3

# Chunk size in tokens (200-1000)
RAG_CHUNK_SIZE=500

# Overlap between chunks in tokens (0-200)
RAG_CHUNK_OVERLAP=50
```

### Tuning RAG_TOP_K

- **RAG_TOP_K=1**: Fast, minimal context, may miss details
- **RAG_TOP_K=3**: Balanced (recommended)
- **RAG_TOP_K=5**: More context, slower, higher token cost
- **RAG_TOP_K=10**: Maximum context, slow, expensive

**Recommendation**: Start with 3, increase if answers lack detail

### Disabling RAG

To disable RAG and use regular AI:
```bash
RAG_ENABLED=false
```

Restart Elli:
```bash
python app.py
```

## Best Practices

### Document Organization

**✅ Do:**
- Organize by topic: `/knowledge/products/`, `/knowledge/sales/`
- Use descriptive filenames: `pricing-tiers.md`, not `doc1.md`
- Keep documents focused on one topic each
- Update regularly as information changes

**❌ Don't:**
- Mix unrelated topics in one file
- Use generic names like `info.md`
- Duplicate content across multiple files
- Include outdated information

### Writing Knowledge Base Docs

**✅ Do:**
- Write complete sentences
- Include specific details (numbers, dates, names)
- Use headers to organize content
- Provide examples and use cases
- Answer "who, what, when, where, why, how"

**❌ Don't:**
- Use vague language ("it depends", "usually", "sometimes")
- Write in incomplete sentences or fragments
- Skip important context
- Use jargon without explanation

### Content Structure

**Good Example:**
```markdown
# Payment Terms

## Standard Terms
Customers with established credit receive Net 30 payment terms,
meaning payment is due within 30 days of the invoice date.

## New Customer Terms
New customers are required to pay 50% upfront at contract signing,
with the remaining 50% due upon delivery.

## Early Payment Discount
We offer a 2% discount for payments received within 10 days of
the invoice date.
```

**Bad Example:**
```markdown
# Payments

Net 30 or 50/50 for new customers. Discount if early.
```

### Updating Documents

When you update a document:

1. Edit the markdown file
2. Re-run ingestion for that file:
   ```bash
   python scripts/ingest_knowledge.py --path ./knowledge/your-file.md
   ```
3. Test with a question

**Note**: Old chunks are not automatically deleted. For a clean slate, manually delete from vector store (see Troubleshooting).

## Query Types

### Questions RAG Handles Well

**Information Queries:**
- "What is [topic]?"
- "What are [items]?"
- "Tell me about [subject]"

**Procedural Questions:**
- "How do I [action]?"
- "How to [task]?"
- "What are the steps to [process]?"

**Definitional Questions:**
- "Explain [concept]"
- "Describe [feature]"
- "Define [term]"

**Policy/Rule Questions:**
- "What is our policy on [topic]?"
- "What are the rules for [situation]?"
- "Can I [action]?"

### Questions RAG May Not Handle

**Opinion-Based:**
- "What's the best [option]?" (unless docs state it)
- "Should I [decision]?" (unless policy covers it)

**Current Data:**
- "What's the current revenue?" (use real-time integrations instead)
- "How many deals closed today?"

**Creative Tasks:**
- "Write me a [content type]" (use regular AI)
- "Generate ideas for [topic]"

**For non-RAG queries**, Elli falls back to regular AI responses.

## Troubleshooting

### Elli isn't using RAG

**Check 1: Is RAG enabled?**
```bash
# In .env
RAG_ENABLED=true
```

**Check 2: Is the knowledge base ingested?**
```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

**Check 3: Does your question match RAG patterns?**
Try: "What is our pricing?" instead of "Tell me something interesting"

### No relevant results found

**Cause**: No documents match your query

**Solutions:**
1. Check your documents actually cover the topic
2. Try different phrasing
3. Lower the relevance threshold (contact admin)
4. Add more documents on the topic

### Sources show low relevance

**Cause**: Documents only partially match the query

**Solutions:**
1. Ask more specific questions
2. Improve document content on that topic
3. Increase RAG_TOP_K to see more results
4. Add dedicated documentation for that topic

### Wrong information in response

**Cause**: Outdated or incorrect source documents

**Solutions:**
1. Update the source markdown files
2. Re-ingest: `python scripts/ingest_knowledge.py --path ./knowledge --recursive`
3. Test again

### Mock mode vs Snowflake mode

**Mock Mode** (no Snowflake credentials):
- Uses keyword-based search
- Less accurate matching
- Good for testing, not production

**Snowflake Mode** (with credentials):
- Uses semantic search (embeddings)
- Much more accurate
- Finds conceptually similar content

**To check mode**: Look for startup messages
```
✅ Connected to Snowflake for vector storage  # Snowflake mode
⚠️ Using mock vector store                    # Mock mode
```

## Statistics

### Check Vector Store Stats

Add this to your Python script:
```python
from services.vector_store import VectorStore

vector_store = VectorStore()
stats = vector_store.get_stats()

print(f"Total chunks: {stats['total_chunks']}")
print(f"Total documents: {stats['total_documents']}")
```

### Example Output

```
Total chunks: 67
Total documents: 4
```

This tells you:
- 67 searchable chunks in the vector store
- From 4 different documents

## FAQs

### How many documents can I add?

**Mock Mode**: Hundreds (limited by memory)
**Snowflake Mode**: Thousands to millions

### How long does ingestion take?

Roughly 1-2 seconds per document in mock mode, longer with Snowflake.

Example: 10 documents (~5,000 words each) = ~30 seconds

### Can I use PDFs or Word docs?

Currently only markdown (`.md`) files are supported.

**Workaround**: Convert to markdown first
- PDFs: Use `pandoc` or online converters
- Word: Save as markdown or use converters

### How do I delete documents?

**Delete from filesystem:**
```bash
rm knowledge/old-doc.md
```

**Delete from vector store:**
```python
from services.vector_store import VectorStore

vector_store = VectorStore()
vector_store.delete_document("old-doc")
```

### Does RAG work with conversation memory?

Yes! Phase 5.1 integrates seamlessly with Phase 4 conversation memory. Elli remembers:
- Previous 5 messages in the thread (Phase 4)
- Relevant knowledge base documents (Phase 5.1)

Example:
```
User: @Elli What is our pricing?
Elli: [RAG response about pricing tiers]

User: What about the Enterprise tier?
Elli: [Uses conversation context + searches knowledge base for Enterprise tier details]
```

## Support

### Getting Help

If RAG isn't working as expected:

1. Check this guide
2. Review [docs/PHASE5_SUMMARY.md](PHASE5_SUMMARY.md) for technical details
3. Check [AGENTS.md](../AGENTS.md) breadcrumbs for implementation context
4. Create an issue with details:
   - Your question to Elli
   - Expected vs actual response
   - RAG configuration (RAG_ENABLED, RAG_TOP_K)
   - Vector store mode (mock or Snowflake)

### Providing Feedback

Help us improve RAG:
- Report inaccurate responses
- Share questions that work well
- Suggest document topics to add
- Report performance issues

---

**Version**: 0.5.0
**Last Updated**: 2026-01-14
**Feature**: RAG with Vector Search (Phase 5.1)
