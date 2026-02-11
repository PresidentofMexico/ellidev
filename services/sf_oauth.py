"""
Salesforce OAuth Web Server Flow Handler.

Provides SSO-compatible OAuth authentication with refresh token support.
This allows Elli to maintain a persistent Salesforce connection without
requiring session ID updates.

Usage:
    1. First run: Opens browser for SSO login, stores refresh token
    2. Subsequent runs: Uses refresh token to get new access tokens automatically
"""

import os
import webbrowser
import urllib.parse
import http.server
import socketserver
import threading
import time
import json
import hashlib
import base64
import secrets
from typing import Optional
from dataclasses import dataclass
import requests
from services.logger import logger


# OAuth configuration
CALLBACK_PORT = int(os.environ.get("SF_OAUTH_CALLBACK_PORT", "8080"))
CALLBACK_PATH = "/callback"
# Allow override for production deployments (default to localhost for development)
CALLBACK_URL = os.environ.get(
    "SF_OAUTH_CALLBACK_URL",
    f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"
)

# Salesforce OAuth endpoints
SF_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
SF_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"

# For custom domains (like eldridge.my.salesforce.com)
SF_CUSTOM_AUTH_URL = "https://{domain}/services/oauth2/authorize"
SF_CUSTOM_TOKEN_URL = "https://{domain}/services/oauth2/token"


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code verifier and code challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate a random code verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(64)

    # Create code challenge using SHA256
    code_challenge_digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).rstrip(b'=').decode()

    return code_verifier, code_challenge


@dataclass
class OAuthTokens:
    """OAuth token data."""
    access_token: str
    refresh_token: str
    instance_url: str
    token_type: str = "Bearer"
    issued_at: Optional[float] = None


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to capture OAuth callback with authorization code."""

    authorization_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        """Handle the OAuth callback GET request."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == CALLBACK_PATH:
            query_params = urllib.parse.parse_qs(parsed.query)

            if "code" in query_params:
                OAuthCallbackHandler.authorization_code = query_params["code"][0]
                self._send_success_response()
            elif "error" in query_params:
                OAuthCallbackHandler.error = query_params.get("error_description", ["Unknown error"])[0]
                self._send_error_response(OAuthCallbackHandler.error)
            else:
                self._send_error_response("No authorization code received")
        else:
            self.send_response(404)
            self.end_headers()

    def _send_success_response(self):
        """Send success HTML response."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Elli - Salesforce Connected</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>Salesforce Connected Successfully!</h1>
            <p>You can close this window and return to your terminal.</p>
            <p>Elli is now connected to Salesforce.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str):
        """Send error HTML response."""
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Elli - Salesforce Connection Failed</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>Connection Failed</h1>
            <p>Error: {error}</p>
            <p>Please try again or check your Salesforce Connected App configuration.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class SalesforceOAuth:
    """
    Salesforce OAuth Web Server Flow handler.

    Handles the full OAuth flow including:
    - Browser-based authorization
    - Token exchange
    - Refresh token storage
    - Access token refresh
    """

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        instance_url: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize OAuth handler.

        Args:
            consumer_key: OAuth Connected App consumer key
            consumer_secret: OAuth Connected App consumer secret
            instance_url: Salesforce instance URL (for custom domains)
            refresh_token: Existing refresh token (if available)
        """
        self.consumer_key = consumer_key or os.environ.get("SF_CONSUMER_KEY")
        self.consumer_secret = consumer_secret or os.environ.get("SF_CONSUMER_SECRET")
        self.instance_url = instance_url or os.environ.get("SF_INSTANCE_URL")
        self.refresh_token = refresh_token or os.environ.get("SF_REFRESH_TOKEN")

        # Determine auth/token URLs based on instance
        if self.instance_url and "my.salesforce.com" in self.instance_url:
            # Extract domain for custom My Domain URLs
            domain = urllib.parse.urlparse(self.instance_url).netloc
            self.auth_url = SF_CUSTOM_AUTH_URL.format(domain=domain)
            self.token_url = SF_CUSTOM_TOKEN_URL.format(domain=domain)
        else:
            self.auth_url = SF_AUTH_URL
            self.token_url = SF_TOKEN_URL

        self.tokens: Optional[OAuthTokens] = None

    def has_valid_credentials(self) -> bool:
        """Check if we have the minimum credentials needed for OAuth."""
        return bool(self.consumer_key and self.consumer_secret)

    def has_refresh_token(self) -> bool:
        """Check if we have a refresh token."""
        return bool(self.refresh_token)

    def get_access_token(self) -> Optional[OAuthTokens]:
        """
        Get a valid access token.

        If we have a refresh token, use it to get a new access token.
        Otherwise, initiate the full OAuth flow.

        Returns:
            OAuthTokens if successful, None otherwise
        """
        if self.refresh_token:
            tokens = self._refresh_access_token()
            if tokens:
                return tokens
            # Refresh failed, fall through to full auth
            logger.warning(
                "Refresh token failed, initiating full OAuth flow",
                service="salesforce_oauth"
            )

        # Need full OAuth flow
        return self._initiate_oauth_flow()

    def _initiate_oauth_flow(self) -> Optional[OAuthTokens]:
        """
        Initiate the full OAuth Web Server Flow with PKCE.

        1. Generate PKCE code verifier and challenge
        2. Start local callback server
        3. Open browser for user to authorize
        4. Capture authorization code
        5. Exchange code for tokens (with code verifier)
        6. Store refresh token
        """
        if not self.has_valid_credentials():
            logger.error(
                "Cannot initiate OAuth: missing consumer key or secret",
                service="salesforce_oauth"
            )
            return None

        # Reset handler state
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None

        # Generate PKCE code verifier and challenge
        code_verifier, code_challenge = generate_pkce_pair()

        # Build authorization URL with PKCE
        auth_params = {
            "response_type": "code",
            "client_id": self.consumer_key,
            "redirect_uri": CALLBACK_URL,
            "scope": "api refresh_token",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"

        logger.info(
            "Starting OAuth flow with PKCE - opening browser for authorization",
            service="salesforce_oauth"
        )
        print("\n" + "=" * 60)
        print("SALESFORCE AUTHORIZATION REQUIRED")
        print("=" * 60)
        print("\nA browser window will open for you to log in to Salesforce.")
        print("After logging in, you'll be redirected back to authorize Elli.")
        print("\nIf the browser doesn't open automatically, visit this URL:")
        print(f"\n{auth_url}\n")
        print("=" * 60 + "\n")

        # Start callback server in background thread
        server = None
        server_thread = None
        try:
            # Create server with reuse address option
            socketserver.TCPServer.allow_reuse_address = True
            server = socketserver.TCPServer(("", CALLBACK_PORT), OAuthCallbackHandler)
            server_thread = threading.Thread(target=server.handle_request)
            server_thread.daemon = True
            server_thread.start()

            # Open browser
            webbrowser.open(auth_url)

            # Wait for callback (timeout after 120 seconds)
            timeout = 120
            start_time = time.time()
            while server_thread.is_alive() and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                if OAuthCallbackHandler.authorization_code or OAuthCallbackHandler.error:
                    break

            if OAuthCallbackHandler.error:
                logger.error(
                    f"OAuth authorization failed: {OAuthCallbackHandler.error}",
                    service="salesforce_oauth"
                )
                return None

            if not OAuthCallbackHandler.authorization_code:
                logger.error(
                    "OAuth authorization timed out",
                    service="salesforce_oauth"
                )
                return None

            # Exchange authorization code for tokens (with PKCE code verifier)
            return self._exchange_code_for_tokens(OAuthCallbackHandler.authorization_code, code_verifier)

        except Exception as e:
            logger.log_error(e, context={"service": "salesforce_oauth", "method": "_initiate_oauth_flow"})
            return None
        finally:
            if server:
                server.server_close()

    def _exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Optional[OAuthTokens]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier (required if PKCE was used in authorization)

        Returns:
            OAuthTokens if successful, None otherwise
        """
        try:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.consumer_key,
                "client_secret": self.consumer_secret,
                "redirect_uri": CALLBACK_URL,
            }

            # Add PKCE code verifier if provided
            if code_verifier:
                token_data["code_verifier"] = code_verifier

            response = requests.post(self.token_url, data=token_data)
            response.raise_for_status()

            data = response.json()

            tokens = OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                instance_url=data["instance_url"],
                token_type=data.get("token_type", "Bearer"),
                issued_at=float(data.get("issued_at", time.time() * 1000)) / 1000,
            )

            self.tokens = tokens
            self.refresh_token = tokens.refresh_token
            self.instance_url = tokens.instance_url

            # Save refresh token to .env file
            if tokens.refresh_token:
                self._save_refresh_token(tokens.refresh_token, tokens.instance_url)

            logger.info(
                "OAuth token exchange successful",
                service="salesforce_oauth",
                instance_url=tokens.instance_url
            )

            return tokens

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Token exchange failed: {e}",
                service="salesforce_oauth"
            )
            return None
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(
                f"Invalid token response: {e}",
                service="salesforce_oauth"
            )
            return None

    def _refresh_access_token(self) -> Optional[OAuthTokens]:
        """
        Use refresh token to get a new access token.

        Returns:
            OAuthTokens if successful, None otherwise
        """
        if not self.refresh_token:
            return None

        try:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.consumer_key,
                "client_secret": self.consumer_secret,
            }

            response = requests.post(self.token_url, data=token_data)
            response.raise_for_status()

            data = response.json()

            tokens = OAuthTokens(
                access_token=data["access_token"],
                refresh_token=self.refresh_token,  # Refresh token doesn't change
                instance_url=data.get("instance_url", self.instance_url),
                token_type=data.get("token_type", "Bearer"),
                issued_at=float(data.get("issued_at", time.time() * 1000)) / 1000,
            )

            self.tokens = tokens
            self.instance_url = tokens.instance_url

            logger.info(
                "Access token refreshed successfully",
                service="salesforce_oauth",
                instance_url=tokens.instance_url
            )

            return tokens

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Token refresh failed: {e}",
                service="salesforce_oauth"
            )
            return None

    def _save_refresh_token(self, refresh_token: str, instance_url: str):
        """
        Save refresh token to .env file.

        Args:
            refresh_token: The refresh token to save
            instance_url: The Salesforce instance URL
        """
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

        try:
            # Read existing .env content
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            # Update or add refresh token and instance URL
            new_lines = []
            found_refresh = False
            found_instance = False

            for line in lines:
                # Skip old session ID if present
                if line.startswith("SF_SESSION_ID="):
                    new_lines.append(f"# {line}")  # Comment out old session ID
                    continue

                if line.startswith("SF_REFRESH_TOKEN="):
                    new_lines.append(f"SF_REFRESH_TOKEN={refresh_token}\n")
                    found_refresh = True
                elif line.startswith("SF_INSTANCE_URL="):
                    new_lines.append(f"SF_INSTANCE_URL={instance_url}\n")
                    found_instance = True
                else:
                    new_lines.append(line)

            # Add if not found
            if not found_refresh:
                # Find the Salesforce section or add after OAuth comments
                insert_idx = len(new_lines)
                for i, line in enumerate(new_lines):
                    if "SF_CONSUMER_KEY" in line or "SF_CONSUMER_SECRET" in line:
                        insert_idx = i + 1
                        break
                new_lines.insert(insert_idx, f"SF_REFRESH_TOKEN={refresh_token}\n")

            if not found_instance:
                # Add after refresh token
                for i, line in enumerate(new_lines):
                    if "SF_REFRESH_TOKEN" in line:
                        new_lines.insert(i + 1, f"SF_INSTANCE_URL={instance_url}\n")
                        break

            # Write back
            with open(env_path, "w") as f:
                f.writelines(new_lines)

            logger.info(
                "Saved refresh token to .env file",
                service="salesforce_oauth"
            )
            print("\nRefresh token saved to .env file.")
            print("Future runs will use this token automatically.\n")

        except Exception as e:
            logger.warning(
                f"Could not save refresh token to .env: {e}",
                service="salesforce_oauth"
            )
            print(f"\nCould not save refresh token automatically.")
            print(f"Please add this line to your .env file manually:")
            print(f"\nSF_REFRESH_TOKEN={refresh_token}\n")
