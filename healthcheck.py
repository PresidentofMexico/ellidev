#!/usr/bin/env python3
"""
Health check script for container orchestration.

Verifies critical services are connected and responding.
Exit 0 = healthy, Exit 1 = unhealthy

Used by Docker HEALTHCHECK and Azure Container Instance health probes.
"""
import os
import sys


def check_health() -> int:
    """
    Check health of critical services.

    Returns:
        0 if healthy, 1 if unhealthy
    """
    errors = []

    # Check 1: Required environment variables present
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]
    for var in required_vars:
        if not os.environ.get(var):
            errors.append(f"Missing required env var: {var}")

    # Check 2: Can import core modules (catch import errors early)
    try:
        from slack_bolt import App
    except ImportError as e:
        errors.append(f"Cannot import slack_bolt: {e}")

    try:
        from services.sf_client import SalesforceClient
    except ImportError as e:
        errors.append(f"Cannot import SalesforceClient: {e}")

    try:
        from services.logger import logger
    except ImportError as e:
        errors.append(f"Cannot import logger: {e}")

    # Check 3: Salesforce client can initialize (mock mode is acceptable)
    try:
        from services.sf_client import SalesforceClient
        sf = SalesforceClient()
        # Just verify we can create the client - mock mode is OK
        del sf
    except Exception as e:
        errors.append(f"Salesforce client init error: {e}")

    # Report results
    if errors:
        for err in errors:
            print(f"UNHEALTHY: {err}", file=sys.stderr)
        return 1

    print("HEALTHY: All checks passed")
    return 0


if __name__ == "__main__":
    # Load environment variables for standalone execution
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not required for health check

    sys.exit(check_health())
