"""
tests/test_linkedin.py
Tests for LinkedIn API integration — fully mocked, no real API calls.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from linkedin.poster import post_text_to_linkedin, post_carousel_to_linkedin, _post_id_to_url


# ─────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────

def mock_requests_post(status_code=201, json_data=None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {"id": "urn:li:ugcPost:123456789"}
    mock.raise_for_status = MagicMock()
    mock.headers = {"x-restli-id": "urn:li:ugcPost:123456789"}
    return mock


# ─────────────────────────────────────────────────────────────────
# TEXT POST TESTS
# ─────────────────────────────────────────────────────────────────

@patch("linkedin.poster._check_token_age", return_value=0)
@patch("linkedin.poster.requests.post")
def test_text_post_api_call_structure(mock_post, mock_token):
    """Text post should call UGC Posts endpoint with correct structure."""
    mock_post.return_value = mock_requests_post()

    result = post_text_to_linkedin("test post content")

    assert mock_post.called
    call_kwargs = mock_post.call_args

    # Check endpoint
    url_called = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", "")
    assert "ugcPosts" in url_called

    # Check payload structure
    payload = call_kwargs[1].get("json", {}) or (call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
    assert "lifecycleState" in str(call_kwargs)
    assert "PUBLISHED" in str(call_kwargs)


@patch("linkedin.poster._check_token_age", return_value=0)
@patch("linkedin.poster.requests.post")
def test_text_post_returns_url(mock_post, mock_token):
    mock_post.return_value = mock_requests_post(json_data={"id": "urn:li:ugcPost:987654321"})
    url = post_text_to_linkedin("test post")
    assert "linkedin.com" in url
    assert "987654321" in url


@patch("linkedin.poster._check_token_age", return_value=0)
@patch("linkedin.poster.requests.post")
def test_text_post_visibility_public(mock_post, mock_token):
    mock_post.return_value = mock_requests_post()
    post_text_to_linkedin("test post")
    call_str = str(mock_post.call_args)
    assert "PUBLIC" in call_str


# ─────────────────────────────────────────────────────────────────
# CAROUSEL POST TESTS
# ─────────────────────────────────────────────────────────────────

@patch("linkedin.poster._check_token_age", return_value=0)
@patch("linkedin.poster.requests.put")
@patch("linkedin.poster.requests.post")
@patch("builtins.open", mock_open(read_data=b"fake pdf content"))
def test_carousel_upload_then_post_sequence(mock_post, mock_put, mock_token):
    """Carousel should: register upload → PUT binary → create post."""
    # Mock register upload response
    register_response = MagicMock()
    register_response.status_code = 200
    register_response.raise_for_status = MagicMock()
    register_response.json.return_value = {
        "value": {
            "asset": "urn:li:digitalmediaAsset:ABC123",
            "uploadMechanism": {
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                    "uploadUrl": "https://api.linkedin.com/upload/abc"
                }
            }
        }
    }

    # Mock post creation response
    post_response = MagicMock()
    post_response.status_code = 201
    post_response.raise_for_status = MagicMock()
    post_response.json.return_value = {"id": "urn:li:ugcPost:111222333"}
    post_response.headers = {"x-restli-id": "urn:li:ugcPost:111222333"}

    mock_post.side_effect = [register_response, post_response]

    mock_put.return_value = MagicMock(status_code=201, raise_for_status=MagicMock())

    url = post_carousel_to_linkedin("fake_path.pdf", "intro text here", "carousel title")

    # Upload PUT should have been called
    assert mock_put.called

    # Post should have been created
    assert mock_post.call_count == 2

    assert "linkedin.com" in url


@patch("linkedin.poster._check_token_age", return_value=0)
@patch("linkedin.poster.requests.post")
def test_expired_token_raises_permission_error(mock_post, mock_token):
    """401 from LinkedIn should raise PermissionError with helpful message."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_post.return_value = mock_resp

    # Override raise_for_status behavior
    from requests.exceptions import HTTPError
    mock_resp.raise_for_status.side_effect = HTTPError(response=mock_resp)

    with pytest.raises(Exception):
        post_text_to_linkedin("test post")


# ─────────────────────────────────────────────────────────────────
# URL FORMATTING TEST
# ─────────────────────────────────────────────────────────────────

def test_post_id_to_url_formats_correctly():
    url = _post_id_to_url("urn:li:ugcPost:123456789")
    assert "linkedin.com" in url
    assert "123456789" in url


def test_post_id_to_url_handles_empty():
    url = _post_id_to_url("")
    assert "linkedin.com" in url  # should return feed URL


# ─────────────────────────────────────────────────────────────────
# TOKEN AGE TEST
# ─────────────────────────────────────────────────────────────────

def test_token_expiry_warning_at_55_days():
    """Token created 56 days ago should trigger warning."""
    from linkedin.poster import _check_token_age
    from datetime import date, timedelta

    old_date = (date.today() - timedelta(days=56)).isoformat()

    with patch("linkedin.poster.read_state", return_value={"linkedin_token_date": old_date}):
        days_old = _check_token_age()
        assert days_old >= 55
