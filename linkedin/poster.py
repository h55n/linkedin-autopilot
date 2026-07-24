"""
linkedin/poster.py
Posts to LinkedIn via the official UGC Posts API (v2).
Handles text posts and PDF carousel uploads.
"""

import os
import time
import requests
from utils.logger import get_logger, log_error
from config.settings import (
    LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN, LINKEDIN_API_BASE,
    LINKEDIN_TOKEN_WARNING_DAYS, LINKEDIN_TOKEN_DATE_FILE,
)

log = get_logger("linkedin")


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def post_text_to_linkedin(post_text: str) -> str:
    """
    Publish a text-only LinkedIn post.
    Returns the LinkedIn post URL.
    """
    _check_token_age()

    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = _api_post("/ugcPosts", payload)
    post_id = resp.get("id", "")
    url = _post_id_to_url(post_id)
    log.info(f"Text post published: {url}")
    return url


def post_carousel_to_linkedin(pdf_path: str, intro_text: str, headline: str = "carousel") -> str:
    """
    Upload a PDF and publish a carousel LinkedIn post.
    Returns the LinkedIn post URL.
    """
    _check_token_age()

    # Step 1: Register upload
    asset_urn = _upload_pdf(pdf_path)

    # Step 2: Create post referencing the asset
    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": intro_text},
                "shareMediaCategory": "DOCUMENT",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
                        "title": {"text": headline},
                    }
                ],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = _api_post("/ugcPosts", payload)
    post_id = resp.get("id", "")
    url = _post_id_to_url(post_id)
    log.info(f"Carousel post published: {url}")
    return url


# ─────────────────────────────────────────────────────────────────
# PDF UPLOAD
# ─────────────────────────────────────────────────────────────────

def _upload_pdf(pdf_path: str) -> str:
    """Upload a PDF to LinkedIn and return the asset URN."""
    # Step 1a: Register upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-document"],
            "owner": LINKEDIN_PERSON_URN,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }

    resp = _api_post("/assets?action=registerUpload", register_payload)
    upload_url = (
        resp.get("value", {})
        .get("uploadMechanism", {})
        .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
        .get("uploadUrl", "")
    )
    asset_urn = resp.get("value", {}).get("asset", "")

    if not upload_url or not asset_urn:
        raise ValueError(f"LinkedIn upload registration failed: {resp}")

    # Step 1b: Upload the actual PDF binary
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        data=pdf_bytes,
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream",
        },
        timeout=60,
    )
    upload_resp.raise_for_status()
    log.info(f"PDF uploaded: {asset_urn}")
    return asset_urn


# ─────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────

def _api_post(endpoint: str, payload: dict) -> dict:
    url = f"{LINKEDIN_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code == 401:
        raise PermissionError("LinkedIn token expired or invalid — run scripts/refresh_linkedin_token.py")
    resp.raise_for_status()

    try:
        return resp.json()
    except Exception:
        return {"id": resp.headers.get("x-restli-id", "")}


def _post_id_to_url(post_id: str) -> str:
    if not post_id:
        return "https://www.linkedin.com/feed/"
    # Extract the numeric part from urn:li:ugcPost:XXXXXXX
    num = post_id.split(":")[-1]
    return f"https://www.linkedin.com/feed/update/urn:li:ugcPost:{num}/"


# ─────────────────────────────────────────────────────────────────
# TOKEN AGE CHECK
# ─────────────────────────────────────────────────────────────────

def _check_token_age() -> int:
    """Check token age and log warning if approaching expiry. Returns days old."""
    if not os.path.exists(LINKEDIN_TOKEN_DATE_FILE):
        return 0

    try:
        with open(LINKEDIN_TOKEN_DATE_FILE) as f:
            date_str = f.read().strip()
        from datetime import date
        token_date = date.fromisoformat(date_str)
        days_old = (date.today() - token_date).days

        if days_old >= LINKEDIN_TOKEN_WARNING_DAYS:
            log.warning(
                f"LinkedIn token is {days_old} days old — expires in "
                f"{60 - days_old} days. Run scripts/refresh_linkedin_token.py"
            )
            return days_old
    except Exception as e:
        log.debug(f"Could not check token age: {e}")

    return 0


def record_token_date():
    """Record today as the token creation date (call after refreshing token)."""
    from datetime import date
    os.makedirs(os.path.dirname(LINKEDIN_TOKEN_DATE_FILE), exist_ok=True)
    with open(LINKEDIN_TOKEN_DATE_FILE, "w") as f:
        f.write(date.today().isoformat())
    log.info("LinkedIn token date recorded")
