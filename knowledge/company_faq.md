# Frequently Asked Questions

## Product Questions

### What is Elli?
Elli is an enterprise AI and workflow automation platform that works through Slack. It combines intelligent workflow automation with AI-powered assistance to help teams work faster and smarter.

### How is Elli different from a regular chatbot?
Unlike simple chatbots that follow scripted responses, Elli uses advanced AI (large language models) to understand context, remember conversations, and retrieve information from your company's knowledge base. It also executes real workflows like updating Salesforce, not just answering questions.

### What integrations does Elli support?
Currently, Elli integrates with:
- Slack (primary interface)
- Salesforce (CRM operations)
- Snowflake (data warehouse queries)

Additional integrations coming in 2026: Microsoft Teams, HubSpot, Google Workspace, and more.

### Can Elli work with our custom internal tools?
Yes! Enterprise tier customers can use our REST API to build custom integrations with internal tools. Our engineering team can also build custom integrations as part of Enterprise contracts.

### How long does implementation take?
Typical implementation timeline is 30 days from contract signing to full production deployment:
- Week 1: Kickoff and requirements gathering
- Week 2: Configuration and integration setup
- Week 3: User training
- Week 4: Go-live and monitoring

## Pricing Questions

### How much does Elli cost?
Elli offers three pricing tiers:
- **Standard**: $49/user/month (billed annually)
- **Professional**: $99/user/month (billed annually)
- **Enterprise**: Custom pricing based on your needs

Volume discounts available for 100+ users.

### Is there a free trial?
Yes! We offer a 14-day free trial with no credit card required. Trial includes up to 10 users and access to Professional tier features.

### What payment methods do you accept?
We accept:
- Credit cards (Visa, Mastercard, Amex)
- ACH bank transfers
- Wire transfers (for international customers)
- Purchase orders (for Enterprise customers)

### What are your payment terms?
- Standard customers: Net 30 for established accounts
- New customers: 50% upfront, 50% on delivery
- Early payment discount: 2% off if paid within 10 days
- Enterprise: Custom terms available

### Can we pay monthly instead of annually?
Yes, monthly billing is available at a 20% premium. For example, Professional tier is $99/month when billed annually, or $119/month when billed monthly.

## Technical Questions

### Is my data secure?
Yes. Elli is SOC 2 Type II certified and complies with GDPR, CCPA, and other data protection regulations. All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We conduct regular security audits and penetration testing.

### Where is data stored?
By default, data is stored in AWS US-East region. Enterprise customers can choose:
- AWS US-West
- AWS EU (Frankfurt)
- Private cloud in your infrastructure
- On-premises deployment

### Can Elli access our Salesforce data?
Elli only accesses Salesforce data that you explicitly grant permission to. You control access using Salesforce security settings and profiles. Elli never stores Salesforce data - it queries in real-time.

### What happens if Elli goes down?
We maintain 99.9% uptime SLA for Enterprise customers. In the rare event of downtime:
- Your existing systems (Slack, Salesforce) continue working normally
- Elli workflows are queued and automatically retry when service is restored
- We provide status updates via status.elli-platform.com

### Does Elli require installing software?
No! Elli is a cloud-based SaaS platform. You simply add the Elli app to your Slack workspace. No software installation or maintenance required (unless you choose on-premises deployment).

## Usage Questions

### How do I update a Salesforce opportunity with Elli?
Simply type a natural language command in Slack:
- "Update Acme Corp to Closed Won"
- "Set TechStart stage to Negotiation"

Elli will search for the opportunity, confirm it found the right one, and open a form for you to review and submit the update.

### Can Elli answer questions about our internal documents?
Yes! With RAG (Retrieval Augmented Generation) enabled, Elli can search your knowledge base and provide answers with source citations. You upload documents to the knowledge base, and Elli indexes them for semantic search.

### What types of questions can I ask Elli?
Elli can answer:
- Product information ("What are our payment terms?")
- Company policies ("What's our vacation policy?")
- Data queries ("What was Q3 revenue?")
- Salesforce questions ("What's the status of the Acme deal?")
- How-to questions ("How do I close a deal?")

### Does Elli remember previous conversations?
Yes! Elli maintains context within Slack threads. If you ask "Who is Acme Corp?" and then say "Update it to Closed Won", Elli understands "it" refers to Acme Corp.

With Phase 5 semantic memory (coming soon), Elli will remember conversations across days and weeks.

### Can multiple team members use Elli simultaneously?
Yes! Elli is designed for concurrent multi-user access. Each user has their own conversation context, and all interactions are logged for audit purposes.

## Administrative Questions

### How do I add new users?
Administrators can add users through:
1. Slack workspace settings (add members to your workspace)
2. Elli admin portal (assign licenses and permissions)

New users automatically get access once added to both systems.

### Can I control what Elli has access to?
Yes! Administrators can configure:
- Which Slack channels Elli can monitor
- Which Salesforce objects Elli can read/write
- Which knowledge base documents are accessible
- User roles and permissions

### How do I add documents to the knowledge base?
1. Create markdown (.md) files with your content
2. Place them in the `/knowledge` directory
3. Run the ingestion script: `python scripts/ingest_knowledge.py`

Documents are automatically chunked, embedded, and indexed for search.

### Can I see usage analytics?
Yes! The admin dashboard shows:
- Number of queries per day/week/month
- Most common questions asked
- Response time metrics
- User adoption rates
- Workflow completion rates

## Support Questions

### How do I get help if something isn't working?
Contact support through:
- **Email**: support@elli-platform.com
- **Slack**: Message your dedicated support channel (Enterprise tier)
- **Phone**: 1-800-ELLI-AI1 (Enterprise tier only)
- **Knowledge Base**: help.elli-platform.com

### What's included in support?
- **Standard tier**: Email support, 48-hour response time
- **Professional tier**: Email + live chat, 24-hour response time
- **Enterprise tier**: 24/7 phone support, dedicated team, 4-hour response time

### Can I request new features?
Yes! We maintain a public roadmap and accept feature requests. Enterprise customers get priority feature development and can sponsor custom features.

### Do you offer training?
Yes! All tiers include:
- Self-paced online training modules
- Documentation and video tutorials
- Weekly office hours (Professional and Enterprise)
- On-site training (Enterprise only, additional cost)

## Compliance Questions

### Is Elli GDPR compliant?
Yes. Elli is fully GDPR compliant. We provide data processing agreements (DPA), support data subject access requests (DSAR), and offer data deletion on request.

### Is Elli HIPAA compliant?
Yes. For Healthcare customers, we offer HIPAA-compliant deployments with signed Business Associate Agreements (BAA). Contact our Enterprise sales team for details.

### Can I get a SOC 2 report?
Yes. We maintain SOC 2 Type II certification. Enterprise customers can request our SOC 2 report under NDA.

### What about data residency requirements?
We support data residency in multiple regions:
- United States (AWS US-East, US-West)
- European Union (AWS Frankfurt)
- Custom regions available for Enterprise customers

## Migration Questions

### Can I migrate from a competitor to Elli?
Yes! We offer migration assistance for customers switching from other platforms. Our team will help you:
- Export data from your existing system
- Configure equivalent workflows in Elli
- Train your team on the new platform
- Run parallel systems during transition

### How long does migration take?
Typical migration timeline is 4-6 weeks, depending on complexity. Enterprise customers get dedicated migration support.

### Will I lose historical data?
No. We can import historical data from your previous system, including:
- Past conversations and interactions
- Knowledge base documents
- Workflow execution logs
- User preferences and settings

## General Questions

### Who uses Elli?
Elli is used by companies of all sizes across industries:
- **Technology**: SaaS companies, startups, tech enterprises
- **Finance**: Banks, insurance companies, investment firms
- **Manufacturing**: Supply chain, operations teams
- **Healthcare**: Hospital administration, medical device companies
- **Consulting**: Professional services firms

### What's your uptime guarantee?
- Standard tier: Best effort, no SLA
- Professional tier: 99.5% uptime SLA
- Enterprise tier: 99.9% uptime SLA with credits for downtime

### Can I cancel anytime?
- Monthly plans: Cancel anytime, effective end of current billing period
- Annual plans: Cancel with 30 days notice, no refund for remaining months
- Enterprise contracts: Per contract terms (typically 30-90 day notice)

### Do you offer discounts for nonprofits?
Yes! Nonprofit organizations and educational institutions receive 25% off all pricing tiers. Contact sales@elli-platform.com with proof of nonprofit status.
