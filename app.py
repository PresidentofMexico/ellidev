import os
import re
import signal
import sys

# CRITICAL: Load environment variables BEFORE any other imports
# This ensures services that read env vars at import time get the correct values
from dotenv import load_dotenv
load_dotenv()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from listeners.messages import register_message_listeners
from listeners.mentions import register_mention_listeners
from listeners.commands import register_command_listeners
from services.logger import logger


# ==========================================
# GRACEFUL SHUTDOWN HANDLING
# ==========================================
def handle_shutdown(signum, frame):
    """
    Handle graceful shutdown on SIGTERM/SIGINT.

    Called when Azure Container Instance stops or restarts the container,
    or when the user presses Ctrl+C locally.
    """
    signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(
        f"Shutdown signal received ({signal_name}), initiating graceful shutdown",
        service="app",
        signal=signal_name
    )
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# ==========================================
# STARTUP VALIDATION
# ==========================================
def validate_startup_requirements():
    """
    Validate all required configuration is present before starting.

    Fails fast with clear error messages if critical configuration is missing.
    Warns about optional configuration that affects functionality.
    """
    errors = []
    warnings = []

    # Critical: Slack tokens (required for bot to function)
    if not os.environ.get("SLACK_BOT_TOKEN"):
        errors.append("SLACK_BOT_TOKEN is required")
    if not os.environ.get("SLACK_APP_TOKEN"):
        errors.append("SLACK_APP_TOKEN is required")

    # Optional: Salesforce credentials (has mock mode fallback)
    sf_oauth = all([
        os.environ.get("SF_CONSUMER_KEY"),
        os.environ.get("SF_CONSUMER_SECRET"),
        os.environ.get("SF_REFRESH_TOKEN"),
    ])
    sf_session = all([
        os.environ.get("SF_SESSION_ID"),
        os.environ.get("SF_INSTANCE_URL"),
    ])

    if not sf_oauth and not sf_session:
        warnings.append("No Salesforce credentials found - deal creation will use mock mode")

    # Optional: Snowflake credentials (has mock mode fallback)
    sf_base = all([
        os.environ.get("SNOWFLAKE_USER"),
        os.environ.get("SNOWFLAKE_ACCOUNT"),
        os.environ.get("SNOWFLAKE_WAREHOUSE"),
    ])
    sf_auth = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH") or os.environ.get("SNOWFLAKE_PASSWORD")

    if not (sf_base and sf_auth):
        warnings.append("Snowflake credentials incomplete - AI service will use mock mode")

    # Optional: Cortex Analyst (has mock mode fallback)
    if os.environ.get("CORTEX_ANALYST_ENABLED", "").lower() == "true":
        if not os.environ.get("CORTEX_ANALYST_PAT") and not os.environ.get("CORTEX_ANALYST_PRIVATE_KEY_PATH"):
            warnings.append("Cortex Analyst enabled but no credentials - will use mock mode")

    # Log warnings
    for warning in warnings:
        logger.warning(warning, service="app", phase="startup")

    # Fail on errors
    if errors:
        for error in errors:
            logger.error(f"Startup validation failed: {error}", service="app", phase="startup")
        raise SystemExit(1)

    logger.info(
        "Startup validation passed",
        service="app",
        phase="startup",
        warnings_count=len(warnings)
    )

# Initialize the app with your bot token and socket mode token
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Register Listeners
register_message_listeners(app)
register_mention_listeners(app)
register_command_listeners(app)

# ==========================================
# 🚀 START THE APP
# ==========================================
if __name__ == "__main__":
    # Validate configuration before starting
    validate_startup_requirements()

    logger.info("Elli is starting...", service="app", phase="startup")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()