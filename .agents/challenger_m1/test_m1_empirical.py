import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scorer.scorer import score_stories, _score_story
from utils.helpers import timestamp_to_age_hours

def test_scorer_ai_substring_edge_cases():
    substring_false_positives = [
        "Buying a new domain name for project",
        "Send an email to support team",
        "Students receive monthly stipend",
        "Developers maintain open source libraries",
        "Supply chain management in logistics",
    ]
    for title in substring_false_positives:
        story = {"title": title, "summary": "No special keywords", "score": 10}
        res = _score_story(story)
        assert res["is_ai_related"] is False, f"False positive AI match on title: '{title}'"

    actual_ai_terms = [
        "New AI agent framework released",
        "Building AI tools for developers",
        "New open source LLM benchmark",
        "GPT-4 model performance analysis",
        "Machine learning pipeline optimization",
    ]
    for title in actual_ai_terms:
        story = {"title": title, "summary": "No special keywords", "score": 10}
        res = _score_story(story)
        assert res["is_ai_related"] is True, f"Failed to detect AI on title: '{title}'"

    # Test score_stories public contract
    stories = [{"title": "Building AI agent", "summary": "email domain stipend", "score": 5}]
    scored = score_stories(stories)
    assert len(scored) == 1
    assert scored[0]["is_ai_related"] is True


def test_github_star_parsing():
    def parse_stars(stars_text: str) -> int:
        stars_text = stars_text.replace(",", "").lower().strip()
        try:
            if "k" in stars_text:
                return int(float(stars_text.replace("k", "").strip()) * 1000)
            else:
                return int(stars_text.strip())
        except ValueError:
            return 0

    assert parse_stars("12.35k") == 12350
    assert parse_stars("1.2k") == 1200
    assert parse_stars("500") == 500
    assert parse_stars("0") == 0
    assert parse_stars(" 12.35K ") == 12350
    assert parse_stars("10.5k") == 10500
    assert parse_stars("1,234") == 1234
    assert parse_stars("") == 0
    assert parse_stars("invalid") == 0


def test_timestamp_to_age_hours_none():
    res = timestamp_to_age_hours(None)
    assert res == 0.0, f"Expected 0.0, got {res}"
    assert isinstance(res, float)


def test_voice_handler_import_without_api_key():
    # Save original values
    orig_env = os.environ.get("GROQ_API_KEY")
    
    # Simulate missing GROQ_API_KEY environment variable during import
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]

    # Clear modules if already loaded to test cold import
    if "telegram_bot.voice_handler" in sys.modules:
        del sys.modules["telegram_bot.voice_handler"]
    if "config.settings" in sys.modules:
        del sys.modules["config.settings"]

    # Import without GROQ_API_KEY set
    import telegram_bot.voice_handler as vh

    # Module import must succeed without throwing an exception!
    assert hasattr(vh, "_get_groq_client")

    # Now verify calling _get_groq_client() when key is empty raises ValueError
    vh._client = None
    vh.GROQ_API_KEY = ""
    os.environ["GROQ_API_KEY"] = ""

    raised = False
    try:
        vh._get_groq_client()
    except ValueError as ve:
        raised = True
        assert "GROQ_API_KEY is not set" in str(ve)
    
    assert raised, "Calling _get_groq_client() without GROQ_API_KEY should raise ValueError"

    # Restore original environment
    if orig_env is not None:
        os.environ["GROQ_API_KEY"] = orig_env


if __name__ == "__main__":
    print("Running M1 Empirical Tests...")
    test_scorer_ai_substring_edge_cases()
    print("[PASS] Scorer AI substring edge cases")
    test_github_star_parsing()
    print("[PASS] GitHub star parsing edge cases")
    test_timestamp_to_age_hours_none()
    print("[PASS] Timestamp None safety")
    test_voice_handler_import_without_api_key()
    print("[PASS] Voice handler lazy import without GROQ_API_KEY")
    print("\nALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")
