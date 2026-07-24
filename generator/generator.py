"""
generator/generator.py
All LLM calls go through here. Uses Groq API.
Handles text posts, carousel JSON, image captions, and morning brief formatting.
"""

import json
import re
from groq import Groq
from utils.logger import get_logger, log_error
from utils.helpers import age_label, format_source_label, format_score_label, emoji_for_story
from generator.prompts import (
    build_text_post_prompt,
    build_carousel_prompt,
    build_image_caption_prompt,
    build_edit_prompt,
)
from config.settings import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS_TEXT, GROQ_MAX_TOKENS_CAROUSEL,
)

log = get_logger("generator")
client = Groq(api_key=GROQ_API_KEY)


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def generate_post(story: dict, post_type: str = "text", angle: str = None) -> dict:
    """
    Generate a LinkedIn post for the given story.

    Args:
        story: story dict from scraper/scorer
        post_type: "text" | "carousel" | "image"
        angle: optional user-provided perspective

    Returns:
        {
            "post_type": str,
            "post_text": str,          # for text/image
            "carousel_data": dict,     # for carousel (raw JSON from LLM)
            "intro_text": str,         # for carousel (LinkedIn caption)
        }
    """
    log.info(f"Generating {post_type} post for: {story['title'][:60]}")

    if post_type == "carousel":
        return _generate_carousel(story, angle)
    elif post_type == "image":
        return _generate_image_caption(story, angle)
    else:
        return _generate_text_post(story, angle)


def generate_post_with_edit(
    original_post: str,
    edit_instruction: str,
    story: dict,
    post_type: str = "text",
) -> dict:
    """Regenerate a post applying an edit instruction."""
    prompt = build_edit_prompt(original_post, edit_instruction, story, post_type)
    text = _call_groq(prompt, max_tokens=GROQ_MAX_TOKENS_TEXT)
    return {
        "post_type": post_type,
        "post_text": _clean_text_post(text),
        "carousel_data": None,
        "intro_text": None,
    }


def generate_morning_brief(picks: list[dict]) -> str:
    """
    Format the morning Telegram message with the top 3 picks.
    This does NOT call the LLM — it's pure formatting.
    """
    lines = [
        "good morning. here are today's picks.\n",
        "reply: [number] + your take (text or voice note)",
        "format suggestion is included — you can override.\n",
        "─" * 40,
    ]

    format_labels = {
        "text": "text post",
        "carousel": "carousel",
        "image": "image pair (before/after)",
    }

    for i, story in enumerate(picks[:3], start=1):
        emoji = emoji_for_story(story)
        title = story["title"].lower()
        source = format_source_label(story.get("source", ""))
        score = story.get("score", 0)
        age = age_label(story.get("age_hours", 0))
        fmt = format_labels.get(story.get("format_suggestion", "text"), "text post")
        url = story.get("url", "")

        score_label = format_score_label(score, story.get("source", ""))
        freshness = "trending" if score > 500 else "fresh" if story.get("age_hours", 99) < 3 else ""

        lines.append(
            f"{i}. {emoji} {title}\n"
            f"   [{source}] | {freshness + ' ' if freshness else ''}{score_label} | {age}\n"
            f"   format suggestion: {fmt}\n"
            f"   {url}"
        )

    lines.append("\n" + "─" * 40)
    lines.append("reply 'skip' to skip today.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# INTERNAL GENERATORS
# ─────────────────────────────────────────────────────────────────

def _generate_text_post(story: dict, angle: str = None) -> dict:
    prompt = build_text_post_prompt(story, angle)
    text = _call_groq(prompt, max_tokens=GROQ_MAX_TOKENS_TEXT)
    return {
        "post_type": "text",
        "post_text": _clean_text_post(text),
        "carousel_data": None,
        "intro_text": None,
    }


def _generate_image_caption(story: dict, angle: str = None) -> dict:
    prompt = build_image_caption_prompt(story, angle)
    text = _call_groq(prompt, max_tokens=GROQ_MAX_TOKENS_TEXT)
    return {
        "post_type": "image",
        "post_text": _clean_text_post(text),
        "carousel_data": None,
        "intro_text": None,
    }


def _generate_carousel(story: dict, angle: str = None) -> dict:
    prompt = build_carousel_prompt(story, angle)
    raw = _call_groq(prompt, max_tokens=GROQ_MAX_TOKENS_CAROUSEL)

    carousel_data = _parse_carousel_json(raw)

    if carousel_data is None:
        log.warning("Carousel JSON parse failed — retrying once")
        raw2 = _call_groq(prompt, max_tokens=GROQ_MAX_TOKENS_CAROUSEL)
        carousel_data = _parse_carousel_json(raw2)

    if carousel_data is None:
        log.warning("Carousel parse failed twice — falling back to text post")
        return _generate_text_post(story, angle)

    # Enforce max 5 slides
    slides = carousel_data.get("slides", [])
    if len(slides) > 5:
        carousel_data["slides"] = slides[:5]

    intro_text = carousel_data.get("intro_text", story["title"].lower())

    return {
        "post_type": "carousel",
        "post_text": intro_text,
        "carousel_data": carousel_data,
        "intro_text": intro_text,
    }


# ─────────────────────────────────────────────────────────────────
# GROQ API CALL
# ─────────────────────────────────────────────────────────────────

def _call_groq(prompt: str, max_tokens: int = 600) -> str:
    """Call Groq LLM and return the text response."""
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=GROQ_TEMPERATURE,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        log_error("Groq API call failed", e)
        raise


# ─────────────────────────────────────────────────────────────────
# TEXT CLEANUP
# ─────────────────────────────────────────────────────────────────

def _clean_text_post(text: str) -> str:
    """Strip common LLM preamble patterns."""
    # Remove wrapping quotes
    text = text.strip('"').strip("'")
    # Remove "Here's your post:" type preambles
    patterns = [
        r"^here'?s (your|the) post:?\s*",
        r"^linkedin post:?\s*",
        r"^post:?\s*",
        r"^\*\*.*?\*\*\s*",   # bold headers
    ]
    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    return text.strip()


def _parse_carousel_json(raw: str) -> dict | None:
    """Extract and parse JSON from LLM response."""
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
        # Validate structure
        if "slides" not in data or not isinstance(data["slides"], list):
            return None
        for slide in data["slides"]:
            if "heading" not in slide:
                return None
        return data
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
