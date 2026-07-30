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
    TOOL_LAUNCH_KEYWORDS, BENCHMARK_KEYWORDS, OPPORTUNITY_BONUS,
    OPPORTUNITY_KEYWORDS, TIER1_OPPORTUNITY_BONUS, TIER1_COMPANY_KEYWORDS
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

    # Mix pass: ensure 1 Opportunity, 1 India, 1 General
    top3 = _mix_pass(scored)

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
    s["is_opportunity"] = any(kw in text for kw in OPPORTUNITY_KEYWORDS)

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
    if s["is_opportunity"]:
        is_tier1 = any(kw in text for kw in TIER1_COMPANY_KEYWORDS)
        if s["india_relevant"] or is_tier1:
            bonuses += OPPORTUNITY_BONUS
            if is_tier1:
                bonuses += TIER1_OPPORTUNITY_BONUS
                log.info(f"Tier 1 opportunity detected: {s.get('title')[:30]}")
            else:
                log.info(f"India opportunity detected: {s.get('title')[:30]}")
        else:
            # Demote niche opportunities so they don't dominate the mix pass
            s["is_opportunity"] = False

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
# MIX PASS
# ─────────────────────────────────────────────────────────────────

def _mix_pass(scored: list[dict]) -> list[dict]:
    """
    Ensure a true mix of content in the top 3:
    1. Highest scoring Opportunity (if exists)
    2. Highest scoring India story (if exists)
    3. Highest scoring General/Tool story
    """
    top3 = []
    picked_ids = set()

    # 1. Opportunity
    for s in scored:
        if s.get("is_opportunity") and s["id"] not in picked_ids:
            top3.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass: added opportunity '{s['title'][:40]}'")
            break

    # 2. India
    for s in scored:
        if s.get("india_relevant") and s["id"] not in picked_ids:
            top3.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass: added India story '{s['title'][:40]}'")
            break

    # 3. General AI/Tool (must NOT be an opportunity)
    for s in scored:
        if len(top3) >= 3:
            break
        if s["id"] not in picked_ids and not s.get("is_opportunity"):
            top3.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass: added general/tool story '{s['title'][:40]}'")
            break
            
    # 4. Fallback (if we somehow still don't have 3, take highest remaining)
    for s in scored:
        if len(top3) >= 3:
            break
        if s["id"] not in picked_ids:
            top3.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass: added fallback story '{s['title'][:40]}'")

    # Sort so the absolute highest score is shown first
    top3.sort(key=lambda x: x.get("final_score", 0), reverse=True)
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
