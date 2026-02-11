"""
Cortex Agent Service - Integration with Snowflake Cortex Agents.

This service provides programmatic access to Snowflake Cortex Agent objects
via the REST API. Cortex Agents (like DEAL_AGENT) are intelligent agent objects
that can orchestrate multiple tools including Cortex Analyst for structured
data queries with semantic models.

Authentication supports two methods (in priority order):
1. PAT (Programmatic Access Token) - Simplest setup, token expires
2. JWT key-pair - More secure, no expiration, requires key management

API Documentation:
- Cortex Agents Run API: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
- Cortex Agents REST API: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-rest-api
- Authentication: https://docs.snowflake.com/en/developer-guide/sql-api/authenticating
"""

import os
import time
import hashlib
import requests
from typing import Optional
from dataclasses import dataclass
from services.logger import logger
from services.metrics import metrics

# JWT libraries for key-pair authentication
try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


@dataclass
class AnalystResponse:
    """Structured response from Cortex Analyst."""
    request_id: str
    text: str
    sql: Optional[str] = None
    suggestions: Optional[list] = None
    warnings: Optional[list] = None
    model_name: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def has_sql(self) -> bool:
        """Check if response includes a SQL query."""
        return self.sql is not None and len(self.sql) > 0

    def format_for_slack(self) -> str:
        """Format the response for Slack display."""
        parts = []

        if self.text:
            parts.append(self.text)

        if self.sql:
            parts.append(f"\n```sql\n{self.sql}\n```")

        if self.suggestions:
            parts.append("\n💡 **Follow-up suggestions:**")
            for suggestion in self.suggestions[:3]:
                parts.append(f"• {suggestion}")

        if self.warnings:
            parts.append("\n⚠️ **Warnings:**")
            for warning in self.warnings[:2]:
                parts.append(f"• {warning}")

        return "\n".join(parts)


class CortexAnalystService:
    """
    Service for interacting with Snowflake Cortex Analyst agents via REST API.

    Supports two authentication methods (checked in priority order):

    1. PAT (Programmatic Access Token) - SIMPLEST
       - Generate in Snowsight: Settings → Authentication → Programmatic Access Tokens
       - Set CORTEX_ANALYST_PAT=<your-token>
       - Token expires (90 days typical), requires regeneration

    2. JWT Key-Pair - MORE SECURE
       - Generate RSA key pair: openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8
       - Extract public key: openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
       - Assign to Snowflake user: ALTER USER elli_service_account SET RSA_PUBLIC_KEY='...'
       - Set SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8
       - No expiration, but requires key rotation per security policy

    Environment Variables:
    - CORTEX_ANALYST_ENABLED: Enable/disable Cortex Analyst (default: false)
    - CORTEX_ANALYST_PAT: Programmatic Access Token (simplest option)
    - SNOWFLAKE_USER: Snowflake username (required for key-pair auth)
    - SNOWFLAKE_PRIVATE_KEY_PATH: Path to RSA private key file (for key-pair auth)
    - SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: Optional passphrase for encrypted key
    - CORTEX_ANALYST_ACCOUNT: Snowflake account (e.g., ara18269)
    - CORTEX_ANALYST_REGION: Snowflake region (e.g., east-us-2.azure)
    - CORTEX_ANALYST_AGENT: Agent name (e.g., DEAL_AGENT)
    - CORTEX_ANALYST_DATABASE: Database containing semantic model (e.g., DEV_CURATE)
    - CORTEX_ANALYST_SCHEMA: Schema containing semantic model (e.g., CORE)
    """

    # JWT token lifetime (Snowflake max is 59 seconds for key-pair auth)
    JWT_LIFETIME_SECONDS = 59

    def __init__(
        self,
        enabled: Optional[bool] = None,
        pat: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
        user: Optional[str] = None,
        account: Optional[str] = None,
        region: Optional[str] = None,
        agent: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        """
        Initialize Cortex Analyst service with PAT or JWT key-pair authentication.

        Authentication is checked in priority order:
        1. PAT (simplest) - if CORTEX_ANALYST_PAT is set
        2. Key-pair (more secure) - if SNOWFLAKE_PRIVATE_KEY_PATH is set
        3. Mock mode - if neither is configured

        Args:
            enabled: Enable/disable the service (defaults to env var)
            pat: Programmatic Access Token (defaults to env var)
            private_key_path: Path to RSA private key file (defaults to env var)
            private_key_passphrase: Passphrase for encrypted key (defaults to env var)
            user: Snowflake username for JWT (defaults to env var)
            account: Snowflake account identifier (defaults to env var)
            region: Snowflake region (defaults to env var)
            agent: Cortex Analyst agent name (defaults to env var)
            database: Database containing the semantic model (defaults to env var)
            schema: Schema containing the semantic model (defaults to env var)
        """
        self.enabled = enabled if enabled is not None else os.environ.get(
            "CORTEX_ANALYST_ENABLED", "false"
        ).lower() == "true"

        # PAT authentication (simplest option - checked first)
        self.pat = pat or os.environ.get("CORTEX_ANALYST_PAT")

        # JWT key-pair authentication config (fallback option)
        self.private_key_path = private_key_path or os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
        self.private_key_passphrase = private_key_passphrase or os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
        self.user = user or os.environ.get("SNOWFLAKE_USER")

        # Cortex Analyst specific config
        self.account = account or os.environ.get("CORTEX_ANALYST_ACCOUNT")
        self.region = region or os.environ.get("CORTEX_ANALYST_REGION", "east-us-2.azure")
        self.agent = agent or os.environ.get("CORTEX_ANALYST_AGENT", "DEAL_AGENT")
        self.database = database or os.environ.get("CORTEX_ANALYST_DATABASE", "DEV_CURATE")
        self.schema = schema or os.environ.get("CORTEX_ANALYST_SCHEMA", "CORE")

        # Cached private key (loaded once for key-pair auth)
        self._private_key = None

        # Auth method tracking: 'pat', 'keypair', or None (mock)
        self.auth_method = None

        # Build the REST API base URL
        # Format: https://<account>.<region>.snowflakecomputing.com
        if self.account and self.region:
            self.base_url = f"https://{self.account}.{self.region}.snowflakecomputing.com"
            # Cortex Agents Run API endpoint (for agent objects like DEAL_AGENT)
            # Format: /api/v2/databases/{database}/schemas/{schema}/agents/{name}:run
            self.api_endpoint = (
                f"{self.base_url}/api/v2/databases/{self.database}/schemas/{self.schema}"
                f"/agents/{self.agent}:run"
            )
        else:
            self.base_url = None
            self.api_endpoint = None

        # Build qualified account name for JWT (account.region format)
        self.qualified_account = None
        if self.account and self.region:
            # Convert region format: east-us-2.azure -> EAST_US_2_AZURE
            region_normalized = self.region.upper().replace("-", "_").replace(".", "_")
            self.qualified_account = f"{self.account.upper()}.{region_normalized}"

        # Validate configuration and determine auth method
        self.is_mock = True
        if self.enabled:
            self._configure_authentication()
        else:
            logger.info(
                "Cortex Analyst disabled",
                service="cortex_analyst",
                mode="disabled"
            )

    def _configure_authentication(self) -> None:
        """Configure authentication method based on available credentials."""
        # Priority 1: PAT (simplest)
        if self.pat:
            if not self.account:
                logger.warning(
                    "CORTEX_ANALYST_ACCOUNT not set - Cortex Analyst will use mock mode",
                    service="cortex_analyst"
                )
                return

            self.auth_method = "pat"
            self.is_mock = False
            logger.info(
                f"Cortex Analyst initialized for agent {self.agent}",
                service="cortex_analyst",
                mode="real",
                auth="pat",
                agent=self.agent,
                database=self.database,
                schema=self.schema
            )
            return

        # Priority 2: Key-pair JWT
        if self.private_key_path:
            if not JWT_AVAILABLE:
                logger.warning(
                    "PyJWT/cryptography not installed - Cortex Analyst will use mock mode. "
                    "Install with: pip install PyJWT cryptography",
                    service="cortex_analyst"
                )
                return

            if not self.user:
                logger.warning(
                    "SNOWFLAKE_USER not set - Cortex Analyst will use mock mode",
                    service="cortex_analyst"
                )
                return

            if not self.account:
                logger.warning(
                    "CORTEX_ANALYST_ACCOUNT not set - Cortex Analyst will use mock mode",
                    service="cortex_analyst"
                )
                return

            if not os.path.exists(self.private_key_path):
                logger.warning(
                    f"Private key file not found: {self.private_key_path} - Cortex Analyst will use mock mode",
                    service="cortex_analyst"
                )
                return

            # Try to load the private key
            if self._load_private_key():
                self.auth_method = "keypair"
                self.is_mock = False
                logger.info(
                    f"Cortex Analyst initialized for agent {self.agent}",
                    service="cortex_analyst",
                    mode="real",
                    auth="jwt_keypair",
                    agent=self.agent,
                    database=self.database,
                    schema=self.schema
                )
            else:
                logger.warning(
                    "Failed to load private key - Cortex Analyst will use mock mode",
                    service="cortex_analyst"
                )
            return

        # No credentials configured
        logger.warning(
            "No authentication configured (set CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH) - "
            "Cortex Analyst will use mock mode",
            service="cortex_analyst"
        )

    def _load_private_key(self) -> bool:
        """Load the RSA private key from file. Returns True on success."""
        if not JWT_AVAILABLE:
            return False

        try:
            with open(self.private_key_path, "rb") as key_file:
                key_data = key_file.read()

            passphrase = None
            if self.private_key_passphrase:
                passphrase = self.private_key_passphrase.encode()

            self._private_key = serialization.load_pem_private_key(
                key_data,
                password=passphrase,
                backend=default_backend()
            )

            logger.debug(
                f"Loaded private key from {self.private_key_path}",
                service="cortex_analyst"
            )
            return True

        except Exception as e:
            logger.log_error(e, context={
                "service": "cortex_analyst",
                "method": "_load_private_key",
                "key_path": self.private_key_path
            })
            return False

    def _generate_jwt_token(self) -> Optional[str]:
        """Generate a short-lived JWT token for Snowflake authentication."""
        if not JWT_AVAILABLE or not self._private_key:
            return None

        try:
            # Get public key fingerprint for key ID (kid)
            public_key = self._private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo
            )
            sha256_hash = hashlib.sha256(public_key_bytes).digest()
            import base64
            public_key_fp = "SHA256:" + base64.b64encode(sha256_hash).decode("utf-8")

            # Build JWT claims
            now = int(time.time())
            claims = {
                "iss": f"{self.qualified_account}.{self.user.upper()}",
                "sub": f"{self.qualified_account}.{self.user.upper()}",
                "iat": now,
                "exp": now + self.JWT_LIFETIME_SECONDS
            }

            # Generate the token
            token = jwt.encode(
                claims,
                self._private_key,
                algorithm="RS256",
                headers={"kid": public_key_fp}
            )

            return token

        except Exception as e:
            logger.log_error(e, context={
                "service": "cortex_analyst",
                "method": "_generate_jwt_token"
            })
            return None

    def _get_auth_headers(self) -> dict:
        """Get authentication headers based on configured auth method."""
        if self.auth_method == "pat":
            return {
                "Authorization": f"Bearer {self.pat}",
                "Content-Type": "application/json",
                "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN"
            }
        elif self.auth_method == "keypair":
            token = self._generate_jwt_token()
            if not token:
                return {}
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT"
            }
        else:
            return {}

    def query(
        self,
        question: str,
        conversation_history: Optional[list] = None,
        timeout: int = 60
    ) -> AnalystResponse:
        """
        Send a question to the Cortex Analyst agent.

        Args:
            question: Natural language question about the data
            conversation_history: Optional list of previous Q&A for context
            timeout: Request timeout in seconds (default: 60)

        Returns:
            AnalystResponse with the agent's response
        """
        if not self.enabled:
            return AnalystResponse(
                request_id="disabled",
                text="Cortex Analyst is not enabled. Set CORTEX_ANALYST_ENABLED=true to enable.",
                success=False,
                error="Service disabled"
            )

        if self.is_mock:
            return self._get_mock_response(question)

        return self._query_api(question, conversation_history, timeout)

    def _query_api(
        self,
        question: str,
        conversation_history: Optional[list],
        timeout: int
    ) -> AnalystResponse:
        """Execute the actual API call to Cortex Agent."""
        start_time = time.time()

        try:
            # Build request body for Cortex Agents Run API
            # Ref: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ]
            }

            # Add conversation history if provided
            if conversation_history:
                # Prepend previous messages
                for hist_item in conversation_history:
                    request_body["messages"].insert(0, {
                        "role": hist_item.get("role", "user"),
                        "content": [
                            {
                                "type": "text",
                                "text": hist_item.get("content", "")
                            }
                        ]
                    })

            # Make the API call with JWT authentication
            headers = self._get_auth_headers()
            if not headers:
                return AnalystResponse(
                    request_id="auth_error",
                    text="Failed to generate authentication token. Check private key configuration.",
                    success=False,
                    error="JWT token generation failed"
                )

            # Cortex Agents API returns Server-Sent Events (SSE) stream
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                json=request_body,
                timeout=timeout,
                stream=True  # Enable streaming for SSE
            )

            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # Parse the SSE stream response
                return self._parse_sse_response(response, duration_ms)
            else:
                error_msg = f"API error: {response.status_code} - {response.text[:500]}"
                logger.error(
                    error_msg,
                    service="cortex_analyst",
                    status_code=response.status_code,
                    endpoint=self.api_endpoint
                )
                metrics.record_api_call("cortex_analyst", "query", duration_ms, False)
                metrics.record_error("cortex_analyst", f"HTTP_{response.status_code}")

                return AnalystResponse(
                    request_id="error",
                    text=f"Sorry, I encountered an error querying the Deal Agent: {response.status_code}",
                    success=False,
                    error=error_msg
                )

        except requests.exceptions.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Cortex Analyst request timed out after {timeout}s",
                service="cortex_analyst"
            )
            metrics.record_api_call("cortex_analyst", "query", duration_ms, False)
            metrics.record_error("cortex_analyst", "Timeout")

            return AnalystResponse(
                request_id="timeout",
                text="Sorry, the request timed out. Please try a simpler question.",
                success=False,
                error="Request timeout"
            )

        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_error(e, context={
                "service": "cortex_analyst",
                "method": "query",
                "question": question[:100]
            })
            metrics.record_api_call("cortex_analyst", "query", duration_ms, False)
            metrics.record_error("cortex_analyst", type(e).__name__)

            return AnalystResponse(
                request_id="error",
                text="Sorry, I couldn't connect to the Deal Agent. Please try again later.",
                success=False,
                error=str(e)
            )

    def _parse_sse_response(self, response, duration_ms: float) -> AnalystResponse:
        """Parse the Server-Sent Events (SSE) stream from Cortex Agents API.

        The Cortex Agent streams events with distinct types:
        - "response.thinking.delta" - streaming reasoning tokens (internal thinking)
        - "response.text.delta" - streaming answer tokens (final answer to user)
        - "response" - final aggregated response containing complete output

        We collect ONLY the text.delta events (the final answer), ignoring thinking.
        Per Snowflake docs: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
        """
        import json

        text_parts = []
        sql_statement = None
        suggestions = None
        warnings = []
        request_id = "unknown"
        model_name = None
        event_count = 0
        current_event_type = None

        # Collect text delta parts (the actual answer)
        answer_text_parts = []

        try:
            # Read the SSE stream line by line
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                # SSE format has two line types:
                # "event: response.text.delta" - event type
                # "data: {json}" - event data
                if line.startswith("event: "):
                    current_event_type = line[7:].strip()
                    continue

                if line.startswith("data: "):
                    json_str = line[6:]  # Remove "data: " prefix
                elif line.startswith("{"):
                    json_str = line  # Plain JSON
                else:
                    continue

                # Handle [DONE] marker
                if json_str.strip() == "[DONE]":
                    break

                try:
                    event_data = json.loads(json_str)
                    event_count += 1

                    # Extract request_id if present
                    if "request_id" in event_data:
                        request_id = event_data["request_id"]

                    # Check for model info in metadata
                    metadata = event_data.get("response_metadata", {})
                    if "model_names" in metadata and metadata["model_names"]:
                        model_name = metadata["model_names"][0]

                    # Check for warnings
                    if "warnings" in event_data:
                        for w in event_data["warnings"]:
                            if isinstance(w, dict):
                                warnings.append(w.get("message", str(w)))
                            else:
                                warnings.append(str(w))

                    # Process based on event type
                    if current_event_type == "response.text.delta":
                        # This is the final answer text - collect it
                        text = event_data.get("text", "")
                        if text:
                            answer_text_parts.append(text)

                    elif current_event_type == "response":
                        # Final aggregated response - extract content if we don't have it
                        content = event_data.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get("type") == "text":
                                        # Only use if we didn't get streaming text
                                        if not answer_text_parts:
                                            answer_text_parts.append(item.get("text", ""))
                                    elif item.get("type") == "tool_results":
                                        # Check for SQL in tool results
                                        tool_content = item.get("content", [])
                                        for tc in tool_content:
                                            if isinstance(tc, dict) and tc.get("type") == "sql":
                                                sql_statement = tc.get("statement", "")

                    # Skip thinking events - we don't need them
                    # current_event_type == "response.thinking.delta"

                except json.JSONDecodeError:
                    continue

            # Log summary
            logger.info(
                f"SSE parsing complete: {event_count} events, {len(answer_text_parts)} text parts",
                service="cortex_analyst",
                request_id=request_id
            )

        except Exception as e:
            logger.log_error(e, context={
                "service": "cortex_analyst",
                "method": "_parse_sse_response"
            })
            return AnalystResponse(
                request_id="parse_error",
                text="Sorry, I had trouble parsing the Deal Agent response.",
                success=False,
                error=str(e)
            )

        # Combine the answer text parts (these are the streamed final answer tokens)
        final_text = "".join(answer_text_parts).strip()

        if not final_text:
            logger.warning(
                f"No text.delta events found in {event_count} events",
                service="cortex_analyst"
            )
            debug_info = f"\n\n_Debug: Received {event_count} events but no response.text.delta events._"
            final_text = f"The Deal Agent processed your request but returned no text response.{debug_info}"

        logger.log_api_call(
            service="cortex_analyst",
            method="query",
            duration_ms=duration_ms,
            success=True,
            context={
                "request_id": request_id,
                "has_sql": sql_statement is not None,
                "model": model_name,
                "agent": self.agent
            }
        )
        metrics.record_api_call("cortex_analyst", "query", duration_ms, True)

        return AnalystResponse(
            request_id=request_id,
            text=final_text,
            sql=sql_statement,
            suggestions=suggestions,
            warnings=warnings if warnings else None,
            model_name=model_name,
            success=True
        )

    def _find_final_answer_in_events(self, events: list) -> str:
        """Find the final user-facing answer from the list of SSE events.

        The Cortex Agent streams events in this order:
        1. Thinking/planning events (internal reasoning)
        2. Tool execution events (SQL generation, etc.)
        3. Final answer event (what the user should see)

        The final answer typically starts with phrases like "Based on..." or "Here are..."
        and contains the actual data/results the user asked for.
        """
        if not events:
            return ""

        # Phrases that indicate this is NOT the final answer (status/thinking)
        # Used to skip over thinking messages when searching for the answer start
        skip_phrases_anywhere = [
            "Query ID:",
            "Planning the next steps",
            "Choosing data sources",
            "Getting additional context",
            "Running CORTEX_ANALYST",
            "Streaming SQL",
            "Interpreting question",
            "Generating SQL",
            "Postprocessing SQL",
            "Reviewing the results",
            "Rethinking the plan",
            "Forming the answer",
            "Executing SQL",
            "The user is asking",
            "I need to",
            "I should",
            "Let me ",
            "I'll ",
            "I'm going to",
            "semantic model",
        ]

        # Stricter set of phrases that indicate the agent went BACK to thinking
        # after starting an answer. These should only stop concatenation.
        # Note: "Looking at", "I can see", "From the data" removed - they can appear in answers
        stop_after_answer_phrases = [
            "Planning the next steps",
            "Choosing data sources",
            "Running CORTEX_ANALYST",
            "Rethinking the plan",
            "I need to",
            "I should",
            "Let me ",
            "I'll ",
            "I'm going to",
        ]

        # Phrases that indicate this IS the final answer (must start with)
        answer_phrases = [
            "Based on",
            "Here are",
            "The following",
            "I found",
            "There are",
            "The results show",
            "The data shows",
            "According to",
            "Deals with",
            "No deals",
            "The deals",
        ]

        # First, extract text from all events - checking multiple possible structures
        all_messages = []
        for event in events:
            text = self._extract_text_from_event(event)
            if text:
                all_messages.append(text)

        # Log what we found
        logger.info(
            f"Extracted {len(all_messages)} text messages from {len(events)} events",
            service="cortex_analyst"
        )

        if not all_messages:
            # Log event structures for debugging
            sample_keys = []
            for e in events[:5]:
                if isinstance(e, dict):
                    sample_keys.append(str(list(e.keys())))
            logger.warning(
                f"No text extracted. Sample event keys: {sample_keys}",
                service="cortex_analyst"
            )
            return ""

        # First pass: Find the LAST answer phrase start, then concatenate from there to end
        # Search in reverse to find the final answer (agent may answer multiple times)
        answer_start_index = -1
        matched_phrase = ""

        for i in range(len(all_messages) - 1, -1, -1):
            message = all_messages[i].strip()

            # Skip empty or very short messages
            if len(message) < 20:
                continue

            # Skip if this is a thinking/status message
            if any(phrase in message for phrase in skip_phrases_anywhere):
                continue

            # Check if this STARTS with an answer phrase
            for phrase in answer_phrases:
                if message.startswith(phrase):
                    answer_start_index = i
                    matched_phrase = phrase
                    break

            if answer_start_index >= 0:
                break  # Found the last answer start

        if answer_start_index >= 0:
            # Concatenate from answer start to end (or until agent goes back to thinking)
            answer_parts = []
            for j in range(answer_start_index, len(all_messages)):
                msg = all_messages[j].strip()
                if not msg:
                    continue
                # Stop only if we hit a clear "back to thinking" phrase
                # Use the stricter list to avoid breaking on normal answer content
                if any(phrase in msg for phrase in stop_after_answer_phrases):
                    break
                answer_parts.append(msg)

            final_answer = "\n".join(answer_parts)
            logger.info(
                f"Found final answer starting with '{matched_phrase}' ({len(final_answer)} chars, {len(answer_parts)} parts)",
                service="cortex_analyst"
            )
            return final_answer

        # Second pass: if no answer-phrase match, find longest clean message
        logger.debug("No answer-phrase match, trying longest clean message", service="cortex_analyst")

        longest_clean = ""
        for message in all_messages:
            message = message.strip()
            if len(message) <= len(longest_clean):
                continue

            # Check if it has any skip phrases
            has_skip = any(phrase in message for phrase in skip_phrases_anywhere)
            if not has_skip and len(message) > 100:
                longest_clean = message

        if longest_clean:
            logger.info(
                f"Using longest clean message ({len(longest_clean)} chars)",
                service="cortex_analyst"
            )
            return longest_clean

        logger.warning("Could not find suitable final answer", service="cortex_analyst")
        return ""

    def _extract_text_from_event(self, event: dict) -> str:
        """Extract text content from an SSE event, checking multiple possible structures.

        Cortex Agents API can return text in various formats:
        - event["message"] - simple string message
        - event["delta"]["content"] - streaming delta format
        - event["choices"][0]["delta"]["content"] - OpenAI-style format
        - event["content"][0]["text"] - content array format
        """
        if not isinstance(event, dict):
            return ""

        # Try direct "message" field (simple string)
        if "message" in event and isinstance(event["message"], str):
            return event["message"]

        # Try "delta.content" (streaming format)
        delta = event.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            # Check for text in content array
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        return item.get("text", "")

        # Try "choices[0].delta.content" (OpenAI-style)
        choices = event.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                delta = choice.get("delta", {})
                if isinstance(delta, dict):
                    content = delta.get("content")
                    if isinstance(content, str):
                        return content

        # Try "content" array directly
        content = event.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")

        # Try "text" directly
        if "text" in event and isinstance(event["text"], str):
            return event["text"]

        return ""

    def _extract_final_answer(self, full_text: str) -> str:
        """Extract the final answer from the agent's full response stream.

        The Cortex Agent streams its entire thinking process including:
        - "Planning the next steps"
        - "Choosing data sources to use"
        - "Running CORTEX_ANALYST_SV_DEAL_TOOL"
        - Internal reasoning
        - Final answer to the user

        This method filters out the thinking and returns only the final answer.
        """
        # Phrases that indicate thinking/planning (not the final answer)
        thinking_phrases = [
            "Planning the next steps",
            "Choosing data sources",
            "Getting additional context",
            "Running CORTEX_ANALYST",
            "Streaming SQL",
            "Interpreting question",
            "Generating SQL",
            "Postprocessing SQL",
            "Reviewing the results",
            "Rethinking the plan",
            "Query ID:",
            "I need to",
            "I should",
            "I'll ",
            "Let me ",
            "Looking at the semantic model",
            "The user is asking",
            "This requires querying",
            "Since the result is empty",
        ]

        # Split into paragraphs/sentences
        lines = full_text.split('\n')
        final_lines = []
        skip_until_next_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line is thinking/planning
            is_thinking = False
            for phrase in thinking_phrases:
                if phrase.lower() in line.lower():
                    is_thinking = True
                    break

            # Also skip lines that look like status updates (short, no punctuation)
            if line in ["Done", "DoneDone"]:
                continue

            if not is_thinking:
                # This might be part of the final answer
                # Look for lines that start with "Based on" or similar conclusion phrases
                conclusion_starters = [
                    "Based on",
                    "The query",
                    "There are currently",
                    "I found",
                    "Here are",
                    "The results show",
                    "According to",
                    "The data shows",
                    "No deals",
                    "The following",
                ]
                for starter in conclusion_starters:
                    if line.startswith(starter):
                        final_lines.append(line)
                        break

        # If we found conclusion lines, use them
        if final_lines:
            # Deduplicate (agent often repeats itself)
            seen = set()
            unique_lines = []
            for line in final_lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            return "\n\n".join(unique_lines)

        # Fallback: try to find the last paragraph that looks like an answer
        paragraphs = full_text.split('\n\n')
        for para in reversed(paragraphs):
            para = para.strip()
            # Skip if it's clearly thinking
            if any(phrase.lower() in para.lower() for phrase in thinking_phrases[:10]):
                continue
            # Skip if too short (likely a status update)
            if len(para) < 50:
                continue
            return para

        # Last resort: return the last 500 chars
        return full_text[-500:] if len(full_text) > 500 else full_text

    def _extract_content_item(self, content: dict) -> dict:
        """Extract text, sql, and suggestions from a content item."""
        result = {"text": None, "sql": None, "suggestions": None}

        if not isinstance(content, dict):
            return result

        content_type = content.get("type")

        if content_type == "text":
            result["text"] = content.get("text", "")
        elif content_type == "sql":
            result["sql"] = content.get("statement", "")
        elif content_type == "suggestions":
            result["suggestions"] = content.get("suggestions", [])
        elif content_type == "tool_results":
            # Tool results contain nested content
            tool_content = content.get("content", [])
            for tc in tool_content:
                if isinstance(tc, dict):
                    if tc.get("type") == "text":
                        result["text"] = tc.get("text", "")
                    elif tc.get("type") == "json":
                        # JSON results - format as text
                        json_data = tc.get("json", {})
                        if json_data:
                            import json
                            result["text"] = json.dumps(json_data, indent=2)

        return result

    def _extract_content(self, content: dict, text_parts: list, sql_statement, suggestions):
        """Legacy helper - extract content and append to lists."""
        extracted = self._extract_content_item(content)
        if extracted.get("text"):
            text_parts.append(extracted["text"])
        # Note: sql_statement and suggestions are not modified in place
        # This is kept for backward compatibility but the main parsing handles these

    def _parse_response(self, data: dict, duration_ms: float) -> AnalystResponse:
        """Parse a non-streaming API response into an AnalystResponse object."""
        request_id = data.get("request_id", "unknown")
        message = data.get("message", {})
        content_list = message.get("content", [])

        text_parts = []
        sql_statement = None
        suggestions = None

        for content in content_list:
            content_type = content.get("type")
            if content_type == "text":
                text_parts.append(content.get("text", ""))
            elif content_type == "sql":
                sql_statement = content.get("statement", "")
            elif content_type == "suggestions":
                suggestions = content.get("suggestions", [])

        warnings = data.get("warnings", [])
        response_metadata = data.get("response_metadata", {})
        model_names = response_metadata.get("model_names", [])
        model_name = model_names[0] if model_names else None

        logger.log_api_call(
            service="cortex_analyst",
            method="query",
            duration_ms=duration_ms,
            success=True,
            context={
                "request_id": request_id,
                "has_sql": sql_statement is not None,
                "model": model_name,
                "agent": self.agent
            }
        )
        metrics.record_api_call("cortex_analyst", "query", duration_ms, True)

        return AnalystResponse(
            request_id=request_id,
            text="\n".join(text_parts),
            sql=sql_statement,
            suggestions=suggestions,
            warnings=[w.get("message", str(w)) for w in warnings] if warnings else None,
            model_name=model_name,
            success=True
        )

    def _get_mock_response(self, question: str) -> AnalystResponse:
        """Generate a mock response for testing without credentials."""
        logger.debug(
            f"Mock Cortex Analyst response for: {question[:100]}",
            service="cortex_analyst",
            mode="mock"
        )

        question_lower = question.lower()

        # Mock responses based on question keywords
        if "pipeline" in question_lower or "forecast" in question_lower:
            return AnalystResponse(
                request_id="mock-pipeline",
                text=(
                    "Based on the current pipeline data:\n\n"
                    "📊 **Pipeline Summary:**\n"
                    "• Total Pipeline Value: $4.2M\n"
                    "• Deals in Negotiation: 12\n"
                    "• Weighted Forecast: $2.8M\n"
                    "• Expected Close This Quarter: 8 deals\n\n"
                    "*This is a mock response - configure CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH for real data.*"
                ),
                sql="SELECT stage, COUNT(*) as deals, SUM(amount) as value FROM opportunities GROUP BY stage",
                suggestions=[
                    "What deals are at risk?",
                    "Show me deals closing this month",
                    "Which reps have the highest pipeline?"
                ]
            )
        elif "deal" in question_lower or "opportunity" in question_lower:
            return AnalystResponse(
                request_id="mock-deals",
                text=(
                    "Here's an overview of your deals:\n\n"
                    "🎯 **Top Deals:**\n"
                    "1. Acme Corp Expansion - $500K (Negotiation)\n"
                    "2. TechStart Platform License - $350K (Proposal)\n"
                    "3. Global Systems Renewal - $280K (Discovery)\n\n"
                    "*This is a mock response - configure CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH for real data.*"
                ),
                sql="SELECT name, amount, stage FROM opportunities ORDER BY amount DESC LIMIT 10",
                suggestions=[
                    "What's the status of Acme Corp?",
                    "Show deals closing this quarter",
                    "Which deals need attention?"
                ]
            )
        elif "revenue" in question_lower or "sales" in question_lower:
            return AnalystResponse(
                request_id="mock-revenue",
                text=(
                    "Revenue analysis for the current period:\n\n"
                    "💰 **Revenue Metrics:**\n"
                    "• Closed Won YTD: $8.5M\n"
                    "• vs. Target: 94% achieved\n"
                    "• Best Performing Segment: Enterprise (+22%)\n"
                    "• Average Deal Size: $125K\n\n"
                    "*This is a mock response - configure CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH for real data.*"
                ),
                sql="SELECT SUM(amount) as revenue, AVG(amount) as avg_deal FROM opportunities WHERE stage = 'Closed Won'",
                suggestions=[
                    "Show monthly revenue trend",
                    "Which products drive the most revenue?",
                    "Compare this quarter to last"
                ]
            )
        else:
            return AnalystResponse(
                request_id="mock-general",
                text=(
                    f"I analyzed your question: *\"{question}\"*\n\n"
                    "I can help you explore deal data, pipeline metrics, and revenue insights. "
                    "Try asking about:\n"
                    "• Pipeline and forecast\n"
                    "• Specific deals or accounts\n"
                    "• Revenue and sales performance\n"
                    "• Deal stage analysis\n\n"
                    "*This is a mock response - configure CORTEX_ANALYST_PAT or SNOWFLAKE_PRIVATE_KEY_PATH for real data.*"
                ),
                suggestions=[
                    "Show me the current pipeline",
                    "What deals are closing this month?",
                    "How is revenue trending?"
                ]
            )

    def send_feedback(
        self,
        request_id: str,
        positive: bool,
        feedback_message: Optional[str] = None
    ) -> bool:
        """
        Send feedback for a previous analyst response.

        Args:
            request_id: The request_id from a previous query response
            positive: True for thumbs up, False for thumbs down
            feedback_message: Optional detailed feedback

        Returns:
            True if feedback was sent successfully
        """
        if self.is_mock or not self.enabled:
            logger.debug(
                f"Mock feedback: request_id={request_id}, positive={positive}",
                service="cortex_analyst"
            )
            return True

        try:
            feedback_endpoint = f"{self.base_url}/api/v2/cortex/analyst/feedback"

            request_body = {
                "request_id": request_id,
                "positive": positive
            }
            if feedback_message:
                request_body["feedback_message"] = feedback_message

            headers = self._get_auth_headers()
            if not headers:
                logger.warning(
                    "Failed to generate JWT for feedback - skipping",
                    service="cortex_analyst"
                )
                return False

            response = requests.post(
                feedback_endpoint,
                headers=headers,
                json=request_body,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(
                    f"Feedback sent for request {request_id}",
                    service="cortex_analyst",
                    positive=positive
                )
                return True
            else:
                logger.warning(
                    f"Failed to send feedback: {response.status_code}",
                    service="cortex_analyst"
                )
                return False

        except Exception as e:
            logger.log_error(e, context={
                "service": "cortex_analyst",
                "method": "send_feedback",
                "request_id": request_id
            })
            return False


# Singleton instance for global access
cortex_analyst = CortexAnalystService()
