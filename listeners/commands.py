"""
Slash command handlers for Elli.

Handles commands like:
- /company - Company context lookup from Salesforce and knowledge base
- /ask-deal-agent - Query the Snowflake Cortex Analyst DEAL_AGENT
"""

import time
from slack_bolt import App
from services.logger import logger
from services.metrics import metrics
from services.company_aggregator import CompanyAggregator
from services.cortex_analyst_service import cortex_analyst


def register_command_listeners(app: App):
    """Register all slash command handlers."""

    # Initialize aggregator (uses singleton services internally)
    aggregator = CompanyAggregator()

    # Register /company command (uses aggregator)
    register_company_command(app, aggregator)

    # ==========================================
    # DEAL AGENT COMMAND
    # ==========================================

    @app.command("/ask-deal-agent")
    def handle_ask_deal_agent(ack, body, client, respond):
        """
        Handle /ask-deal-agent slash command.

        Sends a question to the Snowflake Cortex Analyst DEAL_AGENT
        and returns the response with any generated SQL.

        Usage: /ask-deal-agent What deals are closing this month?
        """
        ack()

        user_id = body["user_id"]
        channel_id = body["channel_id"]
        question = body.get("text", "").strip()

        if not question:
            respond(
                text="Please provide a question. Usage: `/ask-deal-agent What deals are closing this month?`",
                response_type="ephemeral"
            )
            return

        logger.info(
            f"Deal Agent query from user {user_id}: {question[:100]}",
            service="commands",
            user_id=user_id,
            command="ask-deal-agent"
        )

        start_time = time.time()

        # Send initial "thinking" message
        respond(
            text="🔍 Querying Deal Agent...",
            response_type="in_channel"
        )

        # Query the Cortex Analyst
        response = cortex_analyst.query(question)

        duration_ms = (time.time() - start_time) * 1000

        # Build response blocks
        blocks = _build_deal_agent_response_blocks(question, response)

        # Log the query
        logger.log_query(
            user_id=user_id,
            channel_id=channel_id,
            query=question,
            query_type="cortex_analyst",
            duration_ms=duration_ms,
            success=response.success,
            sources_used=["cortex_analyst_deal_agent"]
        )
        metrics.record_query_time(duration_ms)

        # Post the response
        client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=f"Deal Agent Response: {response.text[:100]}..."
        )

        # If there are suggestions, add them as a follow-up
        if response.suggestions:
            suggestion_text = "*💡 Try asking:*\n" + "\n".join(
                f"• {s}" for s in response.suggestions[:3]
            )
            client.chat_postMessage(
                channel=channel_id,
                text=suggestion_text,
                thread_ts=None  # In main channel
            )


def _build_deal_agent_response_blocks(question: str, response) -> list:
    """Build Slack blocks for Deal Agent response."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🤖 Deal Agent Response",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Question:* {question[:200]}",
                }
            ],
        },
        {"type": "divider"},
    ]

    # Main response text (Slack has 3000 char limit per block)
    if response.text:
        text = response.text
        # Slack section blocks have a 3000 character limit
        max_length = 2900  # Leave room for truncation message
        if len(text) > max_length:
            text = text[:max_length] + "\n\n_...response truncated due to length_"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        })

    # SQL query if present (also respect 3000 char limit)
    if response.sql:
        sql_text = response.sql
        if len(sql_text) > 2800:
            sql_text = sql_text[:2800] + "\n-- ...truncated"
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Generated SQL:*\n```sql\n{sql_text}\n```",
            },
        })

    # Warnings if any
    if response.warnings:
        warning_text = "\n".join(f"• {w}" for w in response.warnings[:3])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *Warnings:*\n{warning_text}",
            },
        })

    # Footer with metadata
    footer_parts = []
    if response.model_name:
        footer_parts.append(f"Model: {response.model_name}")
    if response.request_id and response.request_id not in ["mock-pipeline", "mock-deals", "mock-revenue", "mock-general", "disabled", "error", "timeout"]:
        footer_parts.append(f"Request ID: {response.request_id[:12]}...")

    if footer_parts:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": " | ".join(footer_parts),
                }
            ],
        })

    # Mock mode indicator
    if cortex_analyst.is_mock:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_🧪 Mock mode - configure CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH for real data_",
                }
            ],
        })

    return blocks


def register_company_command(app: App, aggregator: CompanyAggregator):
    """Register the /company slash command handler."""

    @app.command("/company")
    def handle_company_command(ack, body, client):
        """
        Handle /company slash command.

        Returns aggregated company context including:
        - Salesforce account info
        - Open opportunities
        - Key contacts
        - Knowledge base context
        - Financial summary (placeholder)
        - Portfolio exposure (placeholder)
        """
        ack()

        user_id = body["user_id"]
        channel_id = body["channel_id"]
        company_name = body.get("text", "").strip()

        if not company_name:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="Please provide a company name. Usage: `/company Acme Corp`"
            )
            return

        logger.info(
            f"Company lookup requested: {company_name}",
            service="commands",
            user_id=user_id,
            company=company_name
        )

        # Get aggregated company data
        context = aggregator.get_company_context(company_name)

        # Build response blocks
        blocks = _build_company_response_blocks(company_name, context)

        # Post response to channel (visible to all)
        client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=f"Company context for {company_name}"
        )


def _build_company_response_blocks(company_name: str, context: dict) -> list:
    """Build Slack blocks for company context response."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Company Context: {company_name}",
            },
        },
        {"type": "divider"},
    ]

    # Account Information
    account = context.get("account")
    if account:
        account_text = (
            f"*Industry:* {account.get('Industry', 'N/A')}\n"
            f"*Website:* {account.get('Website', 'N/A')}\n"
            f"*Phone:* {account.get('Phone', 'N/A')}\n"
            f"*Location:* {account.get('BillingCity', 'N/A')}, {account.get('BillingState', 'N/A')}"
        )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Account Information*\n{account_text}",
            },
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Account Information*\n_No account found in Salesforce_",
            },
        })

    blocks.append({"type": "divider"})

    # Open Opportunities
    opportunities = context.get("opportunities", [])
    if opportunities:
        opp_lines = []
        total_value = 0
        for opp in opportunities[:5]:  # Limit to 5
            amount = opp.get("Amount", 0) or 0
            total_value += amount
            amount_str = f"${amount:,}" if amount else "TBD"
            opp_lines.append(
                f"- *{opp['Name']}*: {opp['StageName']} | {amount_str} | Close: {opp['CloseDate']}"
            )

        opp_text = "\n".join(opp_lines)
        if len(opportunities) > 5:
            opp_text += f"\n_...and {len(opportunities) - 5} more_"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Open Opportunities* ({len(opportunities)} total, ${total_value:,} pipeline)\n{opp_text}",
            },
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Open Opportunities*\n_No opportunities found_",
            },
        })

    blocks.append({"type": "divider"})

    # Key Contacts
    contacts = context.get("contacts", [])
    if contacts:
        contact_lines = []
        for contact in contacts[:3]:  # Limit to 3
            contact_lines.append(
                f"- *{contact['Name']}* ({contact.get('Title', 'N/A')}) - {contact.get('Email', 'N/A')}"
            )

        contact_text = "\n".join(contact_lines)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Contacts*\n{contact_text}",
            },
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Key Contacts*\n_No contacts found_",
            },
        })

    blocks.append({"type": "divider"})

    # Knowledge Base Context
    kb_context = context.get("knowledge_base", [])
    if kb_context:
        kb_lines = []
        for item in kb_context[:3]:  # Limit to 3
            # Truncate content preview
            content = item.get("content", "")[:150]
            if len(item.get("content", "")) > 150:
                content += "..."
            kb_lines.append(f"- {content}")

        kb_text = "\n".join(kb_lines)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Knowledge Base*\n{kb_text}",
            },
        })

    # Financial Summary (placeholder)
    financials = context.get("financials")
    if financials:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Financial Summary*\n{financials}",
            },
        })

    # Portfolio Exposure (placeholder)
    exposure = context.get("portfolio_exposure")
    if exposure:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Portfolio Exposure*\n{exposure}",
            },
        })

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "_Data aggregated from Salesforce and knowledge base_",
            }
        ],
    })

    return blocks
