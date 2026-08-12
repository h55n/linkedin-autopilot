"""
scorer/scorer.py
Pure scoring function — no external calls, runs instantly.
Takes a list of story dicts, returns the top 3 ranked + annotated.
"""

import re
from utils.logger import get_logger
from utils.helpers import timestamp_to_age_hours
from config.settings import (
    UPVOTE_WEIGHT, RECENCY_MULTIPLIERS,
    INDIA_BONUS, TOOL_LAUNCH_BONUS, AI_KEYWORD_BONUS,
    BOOST_KEYWORD_BONUS, COMMENT_HIGH_MULTIPLIER, COMMENT_MID_MULTIPLIER,
    COMMENT_HIGH_THRESHOLD, COMMENT_MID_THRESHOLD, NOISE_PENALTY,
    INDIA_KEYWORDS, AI_KEYWORDS, BOOST_KEYWORDS, NOISE_KEYWORDS,
    TOOL_LAUNCH_KEYWORDS, BENCHMARK_KEYWORDS, OPPORTUNITY_BONUS,
    OPPORTUNITY_KEYWORDS, TIER1_OPPORTUNITY_BONUS, TIER1_COMPANY_KEYWORDS,
    HACKATHON_KEYWORDS, TOOL_STORY_KEYWORDS,
)

log = get_logger("scorer")


def _match_keyword(kw: str, text: str) -> bool:
    """Check if keyword matches as a full word in text using word boundaries."""
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE))


def _has_any_keyword(text: str, keywords: list[str]) -> bool:
    """Check if any keyword in keywords matches text as a full word."""
    return any(_match_keyword(kw, text) for kw in keywords)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many keywords match text as full words."""
    return sum(1 for kw in keywords if _match_keyword(kw, text))


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def score_stories(stories: list[dict]) -> list[dict]:
    """Score all stories using word-boundary keyword matching and return annotated copies."""
    if not stories:
        return []
    return [_score_story(s) for s in stories]


def rank_and_pick(stories: list[dict]) -> list[dict]:
    """
    Score and rank stories, apply diversity pass, attach format suggestion.
    Returns top 3 stories, fully annotated.
    """
    if not stories:
        log.warning("scorer received empty story list")
        return []

    # Score every story
    scored = score_stories(stories)

    # Sort descending
    scored.sort(key=lambda s: s["final_score"], reverse=True)

    # Mix pass: ensure 1 Opportunity, 1 India, 1 General
    top5 = _mix_pass(scored)

    # Attach format suggestion
    for story in top5:
        story["format_suggestion"] = suggest_format(story)

    log.info(f"Top 5 picks: {[s['title'][:50] for s in top5]}")
    return top5


# ─────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────

def _score_story(story: dict) -> dict:
    """Compute final_score and attach metadata flags. Mutates a copy."""
    s = dict(story)  # don't mutate the original

    text = f"{s.get('title', '')} {s.get('summary', '')}".lower()

    # ── Detect flags ──────────────────────────────────────────────
    s["india_relevant"] = _has_any_keyword(text, INDIA_KEYWORDS)
    s["is_ai_related"] = _has_any_keyword(text, AI_KEYWORDS)
    s["is_opportunity"] = _has_any_keyword(text, OPPORTUNITY_KEYWORDS)

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
        is_tier1 = _has_any_keyword(text, TIER1_COMPANY_KEYWORDS)
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

    boost_hits = _count_keyword_hits(text, BOOST_KEYWORDS)
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
    if _has_any_keyword(text, NOISE_KEYWORDS):
        final *= NOISE_PENALTY

    s["final_score"] = round(final, 2)
    return s


def _recency_multiplier(age_hours: float) -> float:
    for (lo, hi), mult in RECENCY_MULTIPLIERS.items():
        if lo <= age_hours < hi:
            return mult
    return 0.5



def _is_fellowship_story(story: dict) -> bool:
    """
    Returns True if the story is about a fellowship, scholarship, or grant.
    """
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    return "fellowship" in text or "scholarship" in text or "grant" in text

# ─────────────────────────────────────────────────────────────────
# MIX PASS HELPERS
# ─────────────────────────────────────────────────────────────────

def _is_tool_story(story: dict) -> bool:
    """
    Returns True if the story looks like a tool / agent / AI system launch.
    Matches GitHub trending, ProductHunt, and keyword-heavy tool stories.
    """
    source = story.get("source", "").lower()
    if source in ("github_trending", "producthunt"):
        return True
    if story.get("is_tool_launch"):
        return True
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    return _has_any_keyword(text, TOOL_STORY_KEYWORDS)


def _is_hackathon_story(story: dict) -> bool:
    """
    Returns True if the story is about an *active* hackathon (not a recap/tips piece).
    Noise keywords (strategy, tips, recap) are already penalised by the scorer.
    """
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    # Must match at least one hackathon keyword
    if not _has_any_keyword(text, HACKATHON_KEYWORDS):
        return False
    # Reject stories that are clearly noise (recap/tips) even if hackathon word appears
    noise_patterns = [
        "recap", "tips", "strategy", "how to win", "how i won",
        "lessons learned", "mistakes", "survive", "guide to",
    ]
    if any(p in text for p in noise_patterns):
        return False
    return True



def _is_fellowship_story(story: dict) -> bool:
    """
    Returns True if the story is about a fellowship, scholarship, or grant.
    """
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    return "fellowship" in text or "scholarship" in text or "grant" in text

# ─────────────────────────────────────────────────────────────────
# MIX PASS

# ─────────────────────────────────────────────────────────────────

def _mix_pass(scored: list[dict]) -> list[dict]:
    """
    Enforce exactly 5 content slots:
    1. Fellowship (India or global)
    2. Hackathon 1 (India or online)
    3. Hackathon 2
    4. AI / Tech News or Tool 1
    5. AI / Tech News or Tool 2
    """
    top5 = []
    picked_ids = set()

    # Slot 1: Fellowship
    for s in scored:
        if _is_fellowship_story(s) and s["id"] not in picked_ids:
            top5.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass slot 1 (Fellowship): '{s['title'][:50]}'")
            break

    # Slot 2 & 3: Hackathons
    hackathon_count = 0
    for s in scored:
        if _is_hackathon_story(s) and s["id"] not in picked_ids:
            top5.append(s)
            picked_ids.add(s["id"])
            hackathon_count += 1
            log.info(f"Mix pass slot {1 + hackathon_count} (Hackathon): '{s['title'][:50]}'")
            if hackathon_count >= 2:
                break

    # Slot 4 & 5: Tech News / Tools
    news_count = 0
    for s in scored:
        if s["id"] not in picked_ids and not _is_hackathon_story(s) and not _is_fellowship_story(s):
            top5.append(s)
            picked_ids.add(s["id"])
            news_count += 1
            log.info(f"Mix pass slot {1 + hackathon_count + news_count} (News/Tool): '{s['title'][:50]}'")
            if news_count >= 2:
                break

    # Fallback: if any slots came up empty (e.g. no hackathons found), fill up to 5 with best remaining
    for s in scored:
        if len(top5) >= 5:
            break
        if s["id"] not in picked_ids:
            top5.append(s)
            picked_ids.add(s["id"])
            log.info(f"Mix pass fallback: '{s['title'][:50]}'")

    # Present in score order (highest score first) so the brief feels natural
    top5.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return top5


# ─────────────────────────────────────────────────────────────────
# FORMAT SUGGESTION
# ─────────────────────────────────────────────────────────────────

def suggest_format(story: dict) -> str:
    """
    Suggest a LinkedIn format based on story characteristics.
    Returns: "text" | "carousel"

    "image" is intentionally excluded from auto-suggestions.
    Users can still switch to image manually by typing 'image' in Telegram.
    """
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()

    # Tool/Agent/GitHub stories → carousel (richer visual format)
    if _is_tool_story(story):
        return "carousel"

    # Benchmark / comparison stories → carousel (data shows better than text)
    if _has_any_keyword(text, BENCHMARK_KEYWORDS):
        return "carousel"

    # Everything else (news, fellowships, hackathons) → clean text post
    return "text"
