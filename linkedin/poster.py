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
    LINKEDIN_ACCESS_TOKEN, LINKEDIN_REFRESH_TOKEN, LINKEDIN_PERSON_URN, LINKEDIN_API_BASE,
    LINKEDIN_TOKEN_WARNING_DAYS, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
)
from utils.helpers import read_state, update_state

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


def post_image_to_linkedin(image_path: str, post_text: str) -> str:
    """
    Upload an image and publish an image LinkedIn post.
    Returns the LinkedIn post URL.
    """
    _check_token_age()

    # Step 1: Register upload
    asset_urn = _upload_image(image_path)

    # Step 2: Create post referencing the asset
    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
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
    log.info(f"Image post published: {url}")
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


def _upload_image(image_path: str) -> str:
    """Upload an image to LinkedIn and return the asset URN."""
    # Step 1a: Register upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
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
        raise ValueError(f"LinkedIn image upload registration failed: {resp}")

    # Step 1b: Upload the actual image binary
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        data=image_bytes,
        headers={
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream",
        },
        timeout=60,
    )
    upload_resp.raise_for_status()
    log.info(f"Image uploaded: {asset_urn}")
    return asset_urn


# ─────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────

def _api_post(endpoint: str, payload: dict) -> dict:
    url = f"{LINKEDIN_API_BASE}{endpoint}"
    
    # We must read from os.environ to get the freshest token if it was just refreshed in memory
    current_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", LINKEDIN_ACCESS_TOKEN)
    
    headers = {
        "Authorization": f"Bearer {current_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code == 401:
        log.warning("LinkedIn API returned 401. Attempting automatic token refresh...")
        if _attempt_auto_refresh():
            # Retry once
            current_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", LINKEDIN_ACCESS_TOKEN)
            headers["Authorization"] = f"Bearer {current_token}"
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
    if resp.status_code == 401:
        raise PermissionError("LinkedIn token expired and automatic refresh failed. Run scripts/refresh_linkedin_token.py")
        
    resp.raise_for_status()

    try:
        return resp.json()
    except Exception:
        return {"id": resp.headers.get("x-restli-id", "")}


def _post_id_to_url(post_id: str) -> str:
    if not post_id:
        return "https://www.linkedin.com/feed/"
    # Use the raw URN (could be urn:li:share:XXXX or urn:li:ugcPost:XXXX)
    return f"https://www.linkedin.com/feed/update/{post_id}/"


# ─────────────────────────────────────────────────────────────────
# TOKEN AGE CHECK
# ─────────────────────────────────────────────────────────────────

def _check_token_age() -> int:
    """Check token age and log warning if approaching expiry. Returns days old."""
    state = read_state()
    date_str = state.get("linkedin_token_date")
    
    if not date_str:
        return 0

    try:
        from datetime import date
        token_date = date.fromisoformat(date_str)
        days_old = (date.today() - token_date).days

        if days_old >= LINKEDIN_TOKEN_WARNING_DAYS:
            log.warning(
                f"LinkedIn token is {days_old} days old — expires in "
                f"{60 - days_old} days. Attempting automatic proactive refresh."
            )
            if not _attempt_auto_refresh():
                log.warning("Proactive refresh failed. You may need to run scripts/refresh_linkedin_token.py")
            return days_old
    except Exception as e:
        log.debug(f"Could not check token age: {e}")

    return 0

def _attempt_auto_refresh() -> bool:
    """Try to use the refresh token to get a new access token and save it."""
    from linkedin.auth import refresh_access_token
    from dotenv import set_key
    
    refresh_token = os.environ.get("LINKEDIN_REFRESH_TOKEN", LINKEDIN_REFRESH_TOKEN)
    if not refresh_token or not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        log.warning("Cannot auto-refresh: missing refresh token or client credentials in .env")
        return False
        
    try:
        data = refresh_access_token(LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, refresh_token)
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        
        if not new_access:
            return False
            
        env_file = ".env"
        if not os.path.exists(env_file):
            with open(env_file, "w") as f:
                f.write("")
                
        set_key(env_file, "LINKEDIN_ACCESS_TOKEN", new_access)
        os.environ["LINKEDIN_ACCESS_TOKEN"] = new_access
        
        if new_refresh:
            set_key(env_file, "LINKEDIN_REFRESH_TOKEN", new_refresh)
            os.environ["LINKEDIN_REFRESH_TOKEN"] = new_refresh
            
        record_token_date()
        log.info("Successfully auto-refreshed LinkedIn token")
        return True
    except Exception as e:
        log_error("Auto-refresh failed", e)
        return False


def record_token_date():
    """Record today as the token creation date (call after refreshing token)."""
    from datetime import date
    update_state(linkedin_token_date=date.today().isoformat())
    log.info("LinkedIn token date recorded to state")
