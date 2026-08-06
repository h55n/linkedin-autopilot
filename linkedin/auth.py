"""
linkedin/auth.py
LinkedIn OAuth 2.0 token management helpers.
"""

import os
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from utils.logger import get_logger

log = get_logger("linkedin.auth")

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ["openid", "profile", "w_member_social"]

# These come from your LinkedIn developer app
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorization complete. You can close this tab.</h2>")

    def log_message(self, *args):
        pass  # suppress server logs


def get_access_token(client_id: str = None, client_secret: str = None) -> dict:
    """
    Run the OAuth 2.0 PKCE flow:
    1. Open browser to LinkedIn auth page
    2. Capture redirect with auth code
    3. Exchange for access token
    Returns a dict with access_token and refresh_token.
    """
    global _auth_code
    _auth_code = None

    cid = client_id or CLIENT_ID
    csecret = client_secret or CLIENT_SECRET

    if not cid or not csecret:
        raise ValueError(
            "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env\n"
            "Create your app at: https://www.linkedin.com/developers/apps"
        )

    # Build auth URL
    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "linkedin_autopilot_auth",
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    print(f"\nOpening LinkedIn auth in browser...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")
    import os
    if not os.environ.get("HEADLESS_OAUTH_MODE"):
        webbrowser.open(auth_url)

    # Spin up local server to catch callback
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    print("Waiting for authorization... (complete in browser)")
    server.handle_request()

    if not _auth_code:
        raise ValueError("No authorization code received")

    # Exchange code for token
    token_resp = requests.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": cid,
            "client_secret": csecret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)

    print(f"\n✓ Access token obtained (expires in {expires_in // 86400} days)")
    return {"access_token": access_token, "refresh_token": refresh_token}

def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """
    Use a refresh token to get a new access token.
    Returns a dict with the new access_token and possibly a new refresh_token.
    """
    if not refresh_token:
        raise ValueError("No refresh token provided")

    token_resp = requests.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    token_resp.raise_for_status()
    return token_resp.json()


def get_person_urn(access_token: str) -> str:
    """Fetch the authenticated user's LinkedIn person URN."""
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    sub = data.get("sub", "")
    return f"urn:li:person:{sub}"
