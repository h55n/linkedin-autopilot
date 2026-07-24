"""
scorer/scorer.py
Pure scoring function — no external calls, runs instantly.
Takes a list of story dicts, returns the top 3 ranked + annotated.
"""

from utils.logger import get_logger
from utils.helpers import timestamp_to_age_hours
from config.settings import (
    UPVOTE_WEIGHT, RECENCY_MULTIPLIERS,
    INDIA_BONUS, TOOL_LAUNCH_BONUS, AI_KEYWORD_BONUS,
    BOOST_KEYWORD_BONUS, COMMENT_HIGH_MULTIPLIER, COMMENT_MID_MULTIPLIER,
    COMMENT_HIGH_THRESHOLD, COMMENT_MID_THRESHOLD, NOISE_PENALTY,
    INDIA_KEYWORDS, AI_KEYWORDS, BOOST_KEYWORDS, NOISE_KEYWORDS,
    TOOL_LAUNCH_KEYWORDS, BENCHMARK_KEYWORDS,
)

log = get_logger("scorer")


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def rank_and_pick(stories: list[dict]) -> list[dict]:
    """
    Score and rank stories, apply diversity pass, attach format suggestion.
    Returns top 3 stories, fully annotated.
    """
    if not stories:
        log.warning("scorer received empty story list")
        return []

    # Score every story
    scored = [_score_story(s) for s in stories]

    # Sort descending
    scored.sort(key=lambda s: s["final_score"], reverse=True)

    # Diversity pass: ensure at least one India story in top 3
    top3 = _diversity_pass(scored)

    # Attach format suggestion
    for story in top3:
        story["format_suggestion"] = suggest_format(story)

    log.info(f"Top 3 picks: {[s['title'][:50] for s in top3]}")
    return top3


# ─────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────

def _score_story(story: dict) -> dict:
    """Compute final_score and attach metadata flags. Mutates a copy."""
    s = dict(story)  # don't mutate the original

    text = f"{s.get('title', '')} {s.get('summary', '')}".lower()

    # ── Detect flags ──────────────────────────────────────────────
    s["india_relevant"] = any(kw in text for kw in INDIA_KEYWORDS)
    s["is_ai_related"] = any(kw in text for kw in AI_KEYWORDS)

    if s.get("region") == "india" or s["india_relevant"]:
        s["region"] = "india"
        s["india_relevant"] = True

    # ── Age / recency ─────────────────────────────────────────────
    age_hours = s.get("age_hours") or timestamp_to_age_hours(s.get("timestamp", 0))
    s["age_hours"] = age_hours
    recency = _recency_multiplier(age_hours)

    # ── Base score ────────────────────────────────────────────────
    raw_score = float(s.get("score", 0))
    base = raw_score * UPVOTE_WEIGHT * recency

    # ── Bonuses ───────────────────────────────────────────────────
    bonuses = 0.0
    if s["india_relevant"]:
        bonuses += INDIA_BONUS
    if s.get("is_tool_launch"):
        bonuses += TOOL_LAUNCH_BONUS
    if s["is_ai_related"]:
        bonuses += AI_KEYWORD_BONUS

    boost_hits = sum(1 for kw in BOOST_KEYWORDS if kw in text)
    bonuses += boost_hits * BOOST_KEYWORD_BONUS

    # ── Comment velocity multiplier ───────────────────────────────
    comments = s.get("comments", 0)
    if comments > COMMENT_HIGH_THRESHOLD:
        comment_mult = COMMENT_HIGH_MULTIPLIER
    elif comments > COMMENT_MID_THRESHOLD:
        comment_mult = COMMENT_MID_MULTIPLIER
    else:
        comment_mult = 1.0

    final = (base + bonuses) * comment_mult

    # ── Noise penalty ─────────────────────────────────────────────
    if any(kw in text for kw in NOISE_KEYWORDS):
        final *= NOISE_PENALTY

    s["final_score"] = round(final, 2)
    return s


def _recency_multiplier(age_hours: float) -> float:
    for (lo, hi), mult in RECENCY_MULTIPLIERS.items():
        if lo <= age_hours < hi:
            return mult
    return 0.5


# ─────────────────────────────────────────────────────────────────
# DIVERSITY PASS
# ─────────────────────────────────────────────────────────────────

def _diversity_pass(scored: list[dict]) -> list[dict]:
    """
    Ensure at least one India story in the top 3.
    If not, replace the 3rd pick with the top India story (if one exists).
    """
    top3 = scored[:3]

    india_in_top3 = any(s.get("india_relevant") for s in top3)
    if india_in_top3:
        return top3

    # Find the top India story not already in top3
    top3_ids = {s["id"] for s in top3}
    india_stories = [
        s for s in scored
        if s.get("india_relevant") and s["id"] not in top3_ids
    ]

    if india_stories:
        top3[2] = india_stories[0]   # replace 3rd pick
        log.info(f"Diversity pass: inserted India story '{india_stories[0]['title'][:50]}'")

    return top3


# ─────────────────────────────────────────────────────────────────
# FORMAT SUGGESTION
# ─────────────────────────────────────────────────────────────────

def suggest_format(story: dict) -> str:
    """
    Suggest a LinkedIn format based on story characteristics.
    Returns: "text" | "carousel" | "image"
    """
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    url = story.get("url", "").lower()

    if story.get("is_tool_launch") and "github.com" in url:
        return "image"

    if any(kw in text for kw in BENCHMARK_KEYWORDS):
        return "carousel"

    if story.get("india_relevant") and story.get("age_hours", 999) < 12:
        return "text"

    return "text"
