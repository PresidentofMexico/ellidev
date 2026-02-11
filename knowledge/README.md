# Knowledge Base

This directory contains documents that Elli uses to answer questions through RAG (Retrieval Augmented Generation).

## Document Guidelines

### Format
- Use Markdown (.md) format for all documents
- Include clear headers (## for sections)
- Use bullet points for lists
- Keep paragraphs concise (2-4 sentences)

### Content Structure
Each document should have:
1. **Title**: Clear, descriptive H1 header
2. **Overview**: Brief summary of the topic
3. **Sections**: Organized content with H2/H3 headers
4. **Examples**: Practical examples where applicable

### Chunking Considerations
- Documents will be split into ~500 token chunks
- Each chunk should be self-contained when possible
- Use descriptive section headers (they provide context for chunks)

### Best Practices
- **Be Specific**: Include concrete details, numbers, dates
- **Use Examples**: Real-world scenarios help the AI understand context
- **Avoid Ambiguity**: Be explicit about policies, procedures, terms
- **Update Regularly**: Keep information current

## Document Types

### Product Documentation
Information about your products, features, capabilities, and technical specifications.

### Sales Playbooks
Sales processes, methodologies, objection handling, competitive intelligence.

### Company Policies
HR policies, security guidelines, expense policies, time-off procedures.

### FAQ Documents
Common questions and answers from customers, employees, or stakeholders.

## Ingesting Documents

After adding or modifying documents, run the ingestion script:

```bash
python scripts/ingest_knowledge.py --path ./knowledge --recursive
```

This will:
1. Scan all .md files in the directory
2. Chunk documents into ~500 token segments
3. Generate embeddings using Snowflake Cortex
4. Store in the vector database

## Example Document

See [product_info.md](product_info.md) for a sample document structure.
