import os
import time
from typing import Optional
from services.logger import logger
from services.metrics import metrics


def _load_private_key(key_path: str, passphrase: Optional[str] = None):
    """
    Load RSA private key from file for Snowflake key-pair authentication.

    Args:
        key_path: Path to the private key file (PKCS8 format)
        passphrase: Optional passphrase if key is encrypted

    Returns:
        Private key bytes for Snowflake connector
    """
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    with open(key_path, "rb") as key_file:
        p_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend()
        )

    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )


class AIService:
    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        account: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
    ):
        """
        Initialize AI service with Snowflake Cortex integration.

        Supports two authentication methods:
        1. Key-pair authentication (recommended): Set SNOWFLAKE_PRIVATE_KEY_PATH
        2. Password authentication: Set SNOWFLAKE_PASSWORD

        Args:
            user: Snowflake username (optional, defaults to env var)
            password: Snowflake password (optional, defaults to env var)
            account: Snowflake account identifier (optional, defaults to env var)
            warehouse: Snowflake warehouse (optional, defaults to env var)
            database: Snowflake database (optional, defaults to env var)
            schema: Snowflake schema (optional, defaults to env var)
            role: Snowflake role (optional, defaults to env var)
            private_key_path: Path to RSA private key file (optional, defaults to env var)
            private_key_passphrase: Passphrase for encrypted key (optional, defaults to env var)
        """
        self.user = user or os.environ.get("SNOWFLAKE_USER")
        self.password = password or os.environ.get("SNOWFLAKE_PASSWORD")
        self.account = account or os.environ.get("SNOWFLAKE_ACCOUNT")
        self.warehouse = warehouse or os.environ.get("SNOWFLAKE_WAREHOUSE")
        self.database = database or os.environ.get("SNOWFLAKE_DATABASE")
        self.schema = schema or os.environ.get("SNOWFLAKE_SCHEMA")
        self.role = role or os.environ.get("SNOWFLAKE_ROLE")
        self.private_key_path = private_key_path or os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
        self.private_key_passphrase = private_key_passphrase or os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

        # Try to initialize Snowflake connection
        self.connection = None
        self.is_mock = True

        # Check for required credentials (user, account, warehouse) + auth method (key or password)
        has_base_creds = all([self.user, self.account, self.warehouse])
        has_key_auth = self.private_key_path and os.path.exists(self.private_key_path)
        has_password_auth = bool(self.password)

        if has_base_creds and (has_key_auth or has_password_auth):
            try:
                import snowflake.connector

                # Build connection parameters
                conn_params = {
                    "user": self.user,
                    "account": self.account,
                    "warehouse": self.warehouse,
                    "database": self.database,
                    "schema": self.schema,
                    "role": self.role,
                }

                # Use key-pair auth if available (preferred), otherwise password
                if has_key_auth:
                    logger.info("Using key-pair authentication for Snowflake", service="ai")
                    conn_params["private_key"] = _load_private_key(
                        self.private_key_path,
                        self.private_key_passphrase
                    )
                else:
                    logger.info("Using password authentication for Snowflake", service="ai")
                    conn_params["password"] = self.password

                self.connection = snowflake.connector.connect(**conn_params)
                self.is_mock = False
                logger.info("Connected to Snowflake Cortex", service="ai", mode="real")
            except ImportError as e:
                if "cryptography" in str(e):
                    logger.warning(
                        "cryptography package not installed, required for key-pair auth",
                        service="ai"
                    )
                else:
                    logger.warning(
                        "snowflake-connector-python not installed, using mock mode",
                        service="ai"
                    )
            except FileNotFoundError:
                logger.error(
                    f"Private key file not found: {self.private_key_path}",
                    service="ai"
                )
            except Exception as e:
                logger.error(
                    f"Could not connect to Snowflake: {e}",
                    service="ai",
                    error=str(e)
                )
                logger.log_error(e, context={"service": "ai", "method": "__init__"})
        else:
            missing = []
            if not self.user:
                missing.append("SNOWFLAKE_USER")
            if not self.account:
                missing.append("SNOWFLAKE_ACCOUNT")
            if not self.warehouse:
                missing.append("SNOWFLAKE_WAREHOUSE")
            if not has_key_auth and not has_password_auth:
                missing.append("SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PASSWORD")

            logger.info(
                f"Snowflake credentials incomplete (missing: {', '.join(missing)}), using mock mode",
                service="ai",
                mode="mock"
            )

    def get_response(self, user_query: str, history: list = None) -> str:
        """
        Get AI response from Snowflake Cortex or mock fallback with conversation context.

        Args:
            user_query: The user's question or request
            history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            AI-generated response string
        """
        if not self.is_mock and self.connection:
            try:
                start_time = time.time()
                # Execute Cortex Complete function
                cursor = self.connection.cursor()

                # Construct the prompt with conversation history
                system_prompt = "You are Elli, a helpful enterprise assistant."

                # Build conversation context from history
                conversation_context = ""
                if history:
                    conversation_context = "\n\nConversation History:\n"
                    for msg in history:
                        role = "User" if msg["role"] == "user" else "Assistant"
                        conversation_context += f"{role}: {msg['content']}\n"
                    conversation_context += "\n"

                # Combine system prompt, history, and current query
                full_prompt = f"{system_prompt}{conversation_context}\nCurrent Query: {user_query}\n\nAnswer:"

                # Execute the Cortex COMPLETE function
                query = """
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'llama3-70b',
                        %s
                    ) as response
                """

                cursor.execute(query, (full_prompt,))
                result = cursor.fetchone()
                cursor.close()

                duration_ms = (time.time() - start_time) * 1000

                if result and result[0]:
                    logger.log_api_call(
                        service="snowflake",
                        method="cortex.complete",
                        duration_ms=duration_ms,
                        success=True,
                        context={
                            "model": "llama3-70b",
                            "query": user_query[:100],
                            "has_history": bool(history)
                        }
                    )
                    metrics.record_api_call("snowflake", "cortex.complete", duration_ms, True)
                    return result[0]
                else:
                    logger.warning("Snowflake Cortex returned empty response", service="ai")
                    metrics.record_api_call("snowflake", "cortex.complete", duration_ms, False)
                    return self._get_mock_response(user_query, history)

            except Exception as e:
                logger.log_error(e, context={
                    "service": "ai",
                    "method": "get_response",
                    "query": user_query[:100]
                })
                metrics.record_error("ai", type(e).__name__)
                return self._get_mock_response(user_query, history)
        else:
            # Mock mode fallback
            logger.debug(f"Mock AI response for query: {user_query[:100]}", service="ai", mode="mock")
            return self._get_mock_response(user_query, history)

    def _get_mock_response(self, user_query: str, history: list = None) -> str:
        """
        Generate context-aware mock AI response for testing without Snowflake credentials.

        Args:
            user_query: The user's question
            history: Optional conversation history for context awareness

        Returns:
            Mock response string
        """
        # Extract context from conversation history
        context_entities = set()
        if history:
            for msg in history:
                content = msg.get("content", "").lower()
                # Extract common entities from history
                if "acme" in content:
                    context_entities.add("Acme Corp")
                if "techstart" in content:
                    context_entities.add("TechStart Inc")
                if "global systems" in content:
                    context_entities.add("Global Systems")

        # Simple keyword-based mock responses with context awareness
        query_lower = user_query.lower()

        # Check for context-dependent queries (e.g., "update it", "tell me more")
        if history and any(
            pronoun in query_lower
            for pronoun in ["it", "them", "that", "this", "those"]
        ):
            if context_entities:
                entity_list = ", ".join(context_entities)
                return (
                    f"Based on our conversation, I assume you're referring to **{entity_list}**.\n\n"
                    "I can help you with that! For Salesforce updates, try:\n"
                    f"'Update {list(context_entities)[0]} to Closed Won'\n\n"
                    "*This is a context-aware mock response from Elli's brain 🧠 - "
                    "Connect to Snowflake Cortex for real AI insights!*"
                )

        if "revenue" in query_lower or "sales" in query_lower:
            return (
                "I analyzed your request about revenue data.\n\n"
                "According to the **Snowflake Data Warehouse** (mock data), "
                "Q3 revenue is up 15% compared to last quarter, with strong "
                "performance in the enterprise segment. 📊\n\n"
                "*This is a mock response from Elli's brain 🧠 - "
                "Connect to Snowflake Cortex for real AI insights!*"
            )
        elif "customer" in query_lower or "client" in query_lower:
            return (
                "I can help you with customer information.\n\n"
                "Our top customers this quarter include Acme Corp, TechStart Inc, "
                "and Global Systems. Customer satisfaction scores are averaging 4.2/5.0. 😊\n\n"
                "*This is a mock response from Elli's brain 🧠 - "
                "Connect to Snowflake Cortex for real AI insights!*"
            )
        elif "help" in query_lower or "what can you do" in query_lower:
            return (
                "👋 I'm Elli, your enterprise assistant!\n\n"
                "I can help you with:\n"
                "• Updating Salesforce opportunities (try: 'Update Acme Corp to Closed Won')\n"
                "• Answering questions about your data\n"
                "• Providing insights from your data warehouse\n"
                "• Understanding context from our conversation thread\n\n"
                "*This is a mock response - Connect to Snowflake Cortex for real AI insights!*"
            )
        else:
            context_note = ""
            if history:
                context_note = " I've reviewed our conversation history for context."

            return (
                f"I analyzed your request: *'{user_query}'*.{context_note}\n\n"
                "According to the **Snowflake Data Warehouse** (mock data), "
                "I found relevant information that might help answer your question. "
                "The data suggests positive trends across key metrics. 📈\n\n"
                "*This is a mock response from Elli's brain 🧠 - "
                "Connect to Snowflake Cortex for real AI insights!*"
            )

    def close(self):
        """Close the Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Snowflake connection closed", service="ai")

    def __del__(self):
        """Cleanup connection on deletion."""
        self.close()
