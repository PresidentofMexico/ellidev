import re
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Any
from slack_bolt import App
from services.logger import logger
from services.deal_parser import parse_deal_message, ParsedDeal
from workflows.salesforce import (
    open_create_opportunity_modal,
    handle_create_submission,
)


# ==========================================
# DEAL CREATION STATE TRACKING WITH TTL
# ==========================================

# Session timeout in seconds (15 minutes)
SESSION_TTL_SECONDS = 15 * 60

# Cleanup interval in seconds (run cleanup every 5 minutes)
CLEANUP_INTERVAL_SECONDS = 5 * 60

SESSION_EXPIRED_MSG = "Sorry, your deal creation session expired. Please start again with `add new deal: [Company]`"


@dataclass
class DealSession:
    """Represents a deal creation session with TTL tracking."""
    company: str
    channel_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    strategy: Optional[str] = None
    security_type: Optional[str] = None
    stage: Optional[str] = None
    close_date: Optional[str] = None
    amount: Optional[int] = None
    deal_source: Optional[str] = None
    sponsor: Optional[str] = None
    step: Any = 1  # Can be int or str like "custom_amount"
    # Business unit derived from channel (for RecordType assignment)
    business_unit: Optional[str] = None
    record_type_id: Optional[str] = None

    def is_expired(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> bool:
        """Check if the session has expired based on last activity."""
        return (time.time() - self.last_activity) > ttl_seconds

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "company": self.company,
            "strategy": self.strategy,
            "security_type": self.security_type,
            "stage": self.stage,
            "close_date": self.close_date,
            "amount": self.amount,
            "deal_source": self.deal_source,
            "sponsor": self.sponsor,
            "step": self.step,
            "channel_id": self.channel_id,
            "business_unit": self.business_unit,
            "record_type_id": self.record_type_id,
        }


class DealSessionManager:
    """
    Thread-safe manager for deal creation sessions with automatic TTL cleanup.

    Provides session management with:
    - Thread-safe access via lock
    - Automatic expiration of stale sessions
    - Periodic cleanup of expired sessions
    """

    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS):
        self._sessions: dict[str, DealSession] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._last_cleanup = time.time()

    def create_session(self, user_id: str, company: str, channel_id: str) -> DealSession:
        """
        Create a new deal session for a user.

        Automatically looks up the business unit configuration based on the channel,
        which determines the Salesforce RecordType and default field values.

        Args:
            user_id: Slack user ID
            company: Company name for the deal
            channel_id: Channel where the deal was initiated

        Returns:
            The created DealSession with business unit configuration applied
        """
        # Import here to avoid circular dependency
        from config.channel_config import channel_config

        with self._lock:
            self._maybe_cleanup()

            # Get business unit configuration for this channel
            bu_config = channel_config.get_config_for_channel(channel_id)

            # Create session with BU config applied
            session = DealSession(
                company=company,
                channel_id=channel_id,
                business_unit=bu_config.name,
                record_type_id=bu_config.record_type_id,
                # Apply default strategy from BU config if set
                strategy=bu_config.default_fields.get("Strategy__c"),
            )

            self._sessions[user_id] = session
            logger.info(
                f"Created deal session for user {user_id}",
                service="messages",
                user_id=user_id,
                company=company,
                business_unit=bu_config.name,
                record_type_id=bu_config.record_type_id
            )
            return session

    def get_session(self, user_id: str) -> Optional[DealSession]:
        """
        Get a user's active session, if it exists and hasn't expired.

        Args:
            user_id: Slack user ID

        Returns:
            DealSession if active, None if expired or not found
        """
        with self._lock:
            self._maybe_cleanup()
            session = self._sessions.get(user_id)
            if session is None:
                return None
            if session.is_expired(self._ttl_seconds):
                del self._sessions[user_id]
                logger.info(
                    f"Session expired for user {user_id}",
                    service="messages",
                    user_id=user_id
                )
                return None
            session.touch()
            return session

    def update_session(self, user_id: str, **kwargs) -> bool:
        """
        Update fields on an active session.

        Args:
            user_id: Slack user ID
            **kwargs: Fields to update (amount, stage, close_date, step)

        Returns:
            True if session was updated, False if not found/expired
        """
        with self._lock:
            session = self._sessions.get(user_id)
            if session is None or session.is_expired(self._ttl_seconds):
                if session is not None:
                    del self._sessions[user_id]
                return False

            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.touch()
            return True

    def delete_session(self, user_id: str) -> bool:
        """
        Delete a user's session.

        Args:
            user_id: Slack user ID

        Returns:
            True if session was deleted, False if not found
        """
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
                logger.info(
                    f"Deleted deal session for user {user_id}",
                    service="messages",
                    user_id=user_id
                )
                return True
            return False

    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed since last cleanup."""
        now = time.time()
        if (now - self._last_cleanup) < CLEANUP_INTERVAL_SECONDS:
            return

        self._last_cleanup = now
        expired_users = [
            user_id for user_id, session in self._sessions.items()
            if session.is_expired(self._ttl_seconds)
        ]

        for user_id in expired_users:
            del self._sessions[user_id]

        if expired_users:
            logger.info(
                f"Cleaned up {len(expired_users)} expired deal sessions",
                service="messages",
                expired_count=len(expired_users)
            )

    def get_active_session_count(self) -> int:
        """Get the count of active (non-expired) sessions."""
        with self._lock:
            return sum(
                1 for session in self._sessions.values()
                if not session.is_expired(self._ttl_seconds)
            )


# Global session manager instance
deal_sessions = DealSessionManager()


def register_message_listeners(app: App):
    # ==========================================
    # THREAD REPLY: ADD NEW DEAL (PARSE PARENT MESSAGE)
    # ==========================================

    # Pattern: "add new deal" as a thread reply - parses the parent message
    @app.message(re.compile(r"^add new deal$", re.IGNORECASE))
    def trigger_new_deal_from_thread(message, say, client, context):
        """
        Handle 'add new deal' as a thread reply.
        Fetches the parent message, parses it for deal details,
        and opens a pre-filled modal.
        """
        user_id = message["user"]
        channel_id = message["channel"]
        thread_ts = message.get("thread_ts")

        # Check if this is a thread reply
        if not thread_ts:
            # Not a thread reply - show help message
            say(
                "To create a deal from a message, reply to that message in a thread with `add new deal`.\n\n"
                "Or use `add new deal: [Company Name]` to start the guided flow."
            )
            return

        # Fetch the parent message
        try:
            result = client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1,
                inclusive=True
            )

            if not result.get("messages"):
                say("Could not find the parent message. Please try again.")
                return

            parent_message = result["messages"][0]
            parent_text = parent_message.get("text", "")

            if not parent_text or len(parent_text) < 50:
                say("The parent message doesn't appear to contain deal information. Please reply to a deal description message.")
                return

        except Exception as e:
            logger.error(f"Error fetching parent message: {e}", service="messages")
            say("Could not fetch the parent message. Please try again.")
            return

        # Parse the parent message
        say("🔍 Parsing deal information from message...")

        parsed = parse_deal_message(parent_text)

        # Log parsed results
        logger.info(
            "Parsed deal from thread reply",
            service="messages",
            user_id=user_id,
            parsed_data=parsed.to_dict()
        )

        # Check parsing confidence
        if parsed.confidence < 0.2:
            say(
                "⚠️ I couldn't extract enough deal information from this message.\n\n"
                "Please use `add new deal: [Company Name]` to create a deal manually, "
                "or ensure the message contains structured deal information."
            )
            return

        # Show what was parsed and provide button to open modal
        summary_parts = []
        if parsed.opportunity_name:
            summary_parts.append(f"*Opportunity:* {parsed.opportunity_name}")
        if parsed.strategy:
            summary_parts.append(f"*Strategy:* {parsed.strategy}")
        if parsed.security_type:
            summary_parts.append(f"*Security Type:* {parsed.security_type}")
        if parsed.stage:
            summary_parts.append(f"*Stage:* {parsed.stage}")
        if parsed.close_date:
            summary_parts.append(f"*Close Date:* {parsed.close_date}")
        if parsed.amount:
            summary_parts.append(f"*Amount:* ${parsed.amount:,}")
        if parsed.sponsor:
            summary_parts.append(f"*Sponsor:* {parsed.sponsor}")
        if parsed.source:
            summary_parts.append(f"*Deal Source:* {parsed.source}")

        summary_text = "\n".join(summary_parts)
        confidence_pct = int(parsed.confidence * 100)

        # Store parsed data in session for the modal
        session = deal_sessions.create_session(
            user_id,
            parsed.opportunity_name or "New Deal",
            channel_id
        )
        deal_sessions.update_session(
            user_id,
            strategy=parsed.strategy,
            security_type=parsed.security_type,
            stage=parsed.stage,
            close_date=parsed.close_date,
            amount=parsed.amount,
            deal_source=parsed.source,
            sponsor=parsed.sponsor,
            step="parsed"
        )

        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📋 *Parsed Deal Information* ({confidence_pct}% confidence)\n\n{summary_text}",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Create Opportunity"},
                            "action_id": "open_parsed_deal_modal",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Cancel"},
                            "action_id": "cancel_parsed_deal",
                        },
                    ],
                },
            ]
        )

    # Handler for opening modal with parsed data
    @app.action("open_parsed_deal_modal")
    def handle_open_parsed_deal_modal(ack, body, say, client):
        ack()
        user_id = body["user"]["id"]

        session = deal_sessions.get_session(user_id)
        if session is None:
            say(SESSION_EXPIRED_MSG)
            return

        _open_create_modal(client, body["trigger_id"], user_id)

    # Handler for canceling parsed deal
    @app.action("cancel_parsed_deal")
    def handle_cancel_parsed_deal(ack, body, say):
        ack()
        user_id = body["user"]["id"]
        deal_sessions.delete_session(user_id)
        say("Deal creation cancelled.")

    # ==========================================
    # NEW DEAL CREATION TRIGGER (GUIDED FLOW)
    # ==========================================

    # Pattern: "add new deal: [Company]" - starts guided flow
    @app.message(re.compile(r"add new deal:\s*(.+)", re.IGNORECASE))
    def trigger_new_deal(message, say, context):
        user_id = message["user"]
        channel_id = message["channel"]

        # Extract company name from regex match
        # In Slack Bolt, context["matches"] contains the captured group strings directly
        company_name = context["matches"][0].strip()

        # Validate company name length
        if len(company_name) > 255:
            say("Company name is too long. Please use a shorter name (max 255 characters).")
            return

        # Create session with TTL tracking
        deal_sessions.create_session(user_id, company_name, channel_id)

        # Ask first question: Strategy (required field)
        _ask_strategy_question(say, company_name)

    # ==========================================
    # STRATEGY HANDLERS (Step 1)
    # ==========================================

    @app.action(re.compile(r"deal_strategy_(.+)"))
    def handle_deal_strategy(ack, body, say, action):
        ack()
        user_id = body["user"]["id"]
        strategy = action["value"]

        if not deal_sessions.update_session(user_id, strategy=strategy, step=2):
            say(SESSION_EXPIRED_MSG)
            return

        _ask_security_type_question(say)

    # ==========================================
    # SECURITY TYPE HANDLERS (Step 2)
    # ==========================================

    @app.action(re.compile(r"deal_security_type_(.+)"))
    def handle_deal_security_type(ack, body, say, action):
        ack()
        user_id = body["user"]["id"]
        security_type = action["value"]

        if not deal_sessions.update_session(user_id, security_type=security_type, step=3):
            say(SESSION_EXPIRED_MSG)
            return

        _ask_stage_question(say)

    # ==========================================
    # DEAL STAGE HANDLERS (Step 3)
    # ==========================================

    @app.action(re.compile(r"deal_stage_(.+)"))
    def handle_deal_stage(ack, body, say, client, action):
        ack()
        user_id = body["user"]["id"]
        stage = action["value"]

        if not deal_sessions.update_session(user_id, stage=stage, step=4):
            say(SESSION_EXPIRED_MSG)
            return

        _ask_close_date_question(say)

    # ==========================================
    # CLOSE DATE HANDLERS
    # ==========================================

    @app.action(re.compile(r"deal_date_(.+)"))
    def handle_deal_date(ack, body, say, client, action):
        ack()
        user_id = body["user"]["id"]
        date_option = action["value"]

        session = deal_sessions.get_session(user_id)
        if session is None:
            say(SESSION_EXPIRED_MSG)
            return

        # Calculate close date based on option
        today = datetime.now()
        if date_option == "this_month":
            # Last day of current month
            next_month = today.replace(day=28) + timedelta(days=4)
            close_date = (next_month - timedelta(days=next_month.day)).strftime("%Y-%m-%d")
        elif date_option == "next_month":
            # Last day of next month
            next_month = (today.replace(day=28) + timedelta(days=4))
            month_after = next_month.replace(day=28) + timedelta(days=4)
            close_date = (month_after - timedelta(days=month_after.day)).strftime("%Y-%m-%d")
        elif date_option == "this_quarter":
            # End of current quarter
            quarter = (today.month - 1) // 3 + 1
            quarter_end_month = quarter * 3
            quarter_end = today.replace(month=quarter_end_month, day=28) + timedelta(days=4)
            close_date = (quarter_end - timedelta(days=quarter_end.day)).strftime("%Y-%m-%d")
        else:
            close_date = today.strftime("%Y-%m-%d")

        # Store close date
        deal_sessions.update_session(user_id, close_date=close_date)

        # Open modal with pre-filled data
        _open_create_modal(client, body["trigger_id"], user_id)

    @app.action("deal_date_custom")
    def handle_deal_date_custom(ack, body, say):
        ack()
        user_id = body["user"]["id"]

        if not deal_sessions.update_session(user_id, step="custom_date"):
            say(SESSION_EXPIRED_MSG)
            return

        say("Please type the expected close date (e.g., `2026-03-31` or `March 31`):")

    # Handle custom date typed as message
    @app.message(re.compile(r"^\d{4}-\d{2}-\d{2}$"))
    def handle_custom_date_message(message, say, client):
        user_id = message["user"]

        session = deal_sessions.get_session(user_id)
        if session is None:
            return

        if session.step != "custom_date":
            return

        close_date = message["text"]
        deal_sessions.update_session(user_id, close_date=close_date)

        # We need a trigger_id to open modal, but we don't have one from a message
        # So we'll ask user to click a button
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Close date set to *{close_date}*. Click below to review and create the opportunity:",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review & Create Opportunity"},
                            "action_id": "open_create_modal",
                            "style": "primary",
                        }
                    ],
                },
            ]
        )

    @app.action("open_create_modal")
    def handle_open_create_modal(ack, body, say, client):
        ack()
        user_id = body["user"]["id"]

        if deal_sessions.get_session(user_id) is None:
            say(SESSION_EXPIRED_MSG)
            return

        _open_create_modal(client, body["trigger_id"], user_id)

    # ==========================================
    # MODAL SUBMISSION HANDLER
    # ==========================================

    @app.view("sf_create_submission")
    def handle_create_modal_submission(ack, body, view, client):
        ack()
        user_id = body["user"]["id"]
        handle_create_submission(client, user_id, view)

        # Clean up session
        deal_sessions.delete_session(user_id)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _ask_strategy_question(say, company_name: str):
    """Ask the strategy question (Step 1)."""
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📝 Creating a new opportunity for *{company_name}*.\n\n*What strategy is this deal under?*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Corporate Credit"},
                        "action_id": "deal_strategy_Corporate Credit",
                        "value": "Corporate Credit",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "RE Credit"},
                        "action_id": "deal_strategy_RE Credit",
                        "value": "RE Credit",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "RE Equity"},
                        "action_id": "deal_strategy_RE Equity",
                        "value": "RE Equity",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Structured Credit"},
                        "action_id": "deal_strategy_Structured Credit",
                        "value": "Structured Credit",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Other"},
                        "action_id": "deal_strategy_Other",
                        "value": "Other",
                    },
                ],
            },
        ]
    )


def _ask_security_type_question(say):
    """Ask the security type question (Step 2)."""
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*What is the security type?*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Term Loan"},
                        "action_id": "deal_security_type_Term Loan",
                        "value": "Term Loan",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Revolver"},
                        "action_id": "deal_security_type_Revolving Line of Credit",
                        "value": "Revolving Line of Credit",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Bond"},
                        "action_id": "deal_security_type_Bond",
                        "value": "Bond",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Equity"},
                        "action_id": "deal_security_type_Common Equity",
                        "value": "Common Equity",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Other"},
                        "action_id": "deal_security_type_Other",
                        "value": "Other",
                    },
                ],
            },
        ]
    )


def _ask_stage_question(say):
    """Ask the deal stage question (Step 3)."""
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*What stage is this deal in?*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Initial Review"},
                        "action_id": "deal_stage_Initial Review",
                        "value": "Initial Review",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Proposal"},
                        "action_id": "deal_stage_Proposal",
                        "value": "Proposal",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Term Sheet"},
                        "action_id": "deal_stage_Term Sheet",
                        "value": "Term Sheet",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Diligence"},
                        "action_id": "deal_stage_Diligence",
                        "value": "Diligence",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Execution"},
                        "action_id": "deal_stage_Execution",
                        "value": "Execution",
                    },
                ],
            },
        ]
    )


def _ask_close_date_question(say):
    """Ask the close date question."""
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Expected close date?*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "This Month"},
                        "action_id": "deal_date_this_month",
                        "value": "this_month",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Next Month"},
                        "action_id": "deal_date_next_month",
                        "value": "next_month",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "This Quarter"},
                        "action_id": "deal_date_this_quarter",
                        "value": "this_quarter",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Custom"},
                        "action_id": "deal_date_custom",
                        "value": "custom",
                    },
                ],
            },
        ]
    )


def _open_create_modal(client, trigger_id, user_id):
    """Open the opportunity creation modal with pre-filled data."""
    session = deal_sessions.get_session(user_id)

    if session is None:
        # Session expired, use empty defaults
        open_create_opportunity_modal(
            client,
            trigger_id,
            prefill_company="",
            prefill_amount=None,
            prefill_stage="Initial Review",
            prefill_close_date="",
            prefill_strategy=None,
            prefill_security_type=None,
            prefill_deal_source=None,
            prefill_sponsor=None,
            channel_id=None,  # No channel context when session expired
        )
        return

    open_create_opportunity_modal(
        client,
        trigger_id,
        prefill_company=session.company,
        prefill_amount=session.amount,
        prefill_stage=session.stage or "Initial Review",
        prefill_close_date=session.close_date or "",
        prefill_strategy=session.strategy,
        prefill_security_type=session.security_type,
        prefill_deal_source=session.deal_source,
        prefill_sponsor=session.sponsor,
        channel_id=session.channel_id,  # Pass channel for RecordType lookup
    )
