"""
generator/prompts.py
All prompt templates as constants. Never construct prompts dynamically.
"""

from config.settings import PERSONALITY_PROMPT


def build_text_post_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating a text post."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE (incorporate this perspective):\n{angle}\n"

    full_text_section = f"FULL ARTICLE TEXT (use this for depth and accuracy):\n{story['full_text'][:2000]}\n" if story.get('full_text') else ""

    return f"""{PERSONALITY_PROMPT}

---

TASK: Act as a world-class conversion copywriter. Synthesize the story and the user's angle into a highly engaging, thought-provoking narrative that provides unique value to the reader. 

COPYWRITING RULES:
- Clarity Over Cleverness: Be clear, direct, and easy to understand.
- Benefits Over Features: Focus on what the news means for the reader's outcomes.
- Simple over complex: Use simple verbs ("use" not "utilize").
- Active over passive voice.
- Show, don't tell: Describe outcomes rather than using adverbs.
- Engage the reader: Use rhetorical questions or analogies when helpful.
- Avoid sensationalism, buzzwords, and fluff. Provide real substance.
- Highlight Numbers: People love data. Extract and prominently feature impressive numbers, metrics, funding amounts, or statistics.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
SOURCE: {story.get('source', '')}
REGION: {story.get('region', 'global')}
{full_text_section}
{angle_section}
OUTPUT RULES:
- Return ONLY the post text. No preamble, no "here's the post:", no quotes around it.
- 2 to 4 short punchy paragraphs/sentences.
- CRITICAL: Separate each sentence/paragraph with an empty line (double newline, \n\n) for proper LinkedIn readability.
- Write in normal sentence case: capitalize first word, proper nouns, brand names, and acronyms. Do NOT write in all-lowercase.
- Introduce the URL on its own line at the very end. CRITICAL: Extract and provide the ACTUAL official project, hackathon, event, or company website link mentioned in the text, NOT just the news source link. Vary the Call To Action naturally and conversationally (e.g., "Official link here: ", "Apply here: ", "Check out the project: ", etc.) followed by the extracted official URL (or the STORY URL if no official link exists).
"""


def build_carousel_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating carousel slide JSON."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE:\n{angle}\n"

    full_text_section = f"FULL ARTICLE TEXT (use this for depth and accuracy):\n{story['full_text'][:2000]}\n" if story.get('full_text') else ""

    return f"""{PERSONALITY_PROMPT}

---

TASK: Write carousel slide content for the story below.
Return ONLY valid JSON. No markdown, no backticks, no explanation.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
{full_text_section}
{angle_section}
JSON FORMAT (return exactly this structure):
{{
  "intro_text": "one sentence hook for the linkedin post caption",
  "slides": [
    {{
      "type": "cover",
      "category_label": "BUSINESS",
      "heading": "5 words max, Title Case",
      "subheading": "10 words max, Sentence case"
    }},
    {{
      "type": "content",
      "heading": "5 words max, Sentence case",
      "body": "40 words max. CRITICAL: Separate each sentence/paragraph with double newlines (\\n\\n).",
      "highlight_phrase": "optional: a key phrase from body to highlight"
    }},
    {{
      "type": "content",
      "heading": "5 words max, Sentence case",
      "body": "40 words max. CRITICAL: Separate each sentence/paragraph with double newlines (\\n\\n)."
    }},
    {{
      "type": "cta",
      "heading": "5 words max, Sentence case",
      "body": "40 words max. CRITICAL: Separate each sentence/paragraph with double newlines (\\n\\n).",
      "highlight_phrase": "the single most important takeaway"
    }}
  ]
}}

RULES:
- Maximum 5 slides total (including cover).
- No em dashes, no exclamation marks, no hashtags.
- Each slide body: write 30 to 50 words of rich, explanatory detail. Do not write one-liners.
- intro_text: 1 sentence, creates curiosity gap.
- IMPORTANT: the `body` fields MUST contain double newlines (`\\n\\n`) to separate sentences into short paragraphs.
- Do NOT use all lowercase. Use natural Title Case for cover headings, and Sentence case for subheadings and body text.
- CRITICAL JSON RULE: Output ONLY the raw JSON object. NO markdown code fences (no ```json or ```). NO introductory text like "Here is the JSON". Start your response exactly with {{ and end exactly with }}.
"""


def build_image_caption_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating a full LinkedIn post for an image post."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE (incorporate this perspective strongly):\n{angle}\n"

    full_text_section = f"FULL ARTICLE TEXT (use this for depth and accuracy):\n{story['full_text'][:2500]}\n" if story.get('full_text') else ""

    return f"""{PERSONALITY_PROMPT}

---

TASK: Act as a world-class LinkedIn copywriter. Write a FULL, COMPLETE, highly engaging LinkedIn post for the story below. This is an image post — the photo provides visual context, but your words must do the heavy lifting. Write for maximum reach and impact.

COPYWRITING RULES:
- Hook first: Open with a single line that stops the scroll. A surprising fact, a bold claim, or a punchy question.
- Benefits Over Features: Focus on what this means for the reader — not just what happened.
- Simple over complex: Use simple verbs. Short sentences. Short paragraphs.
- Active over passive voice.
- Show, don't tell: Describe outcomes and implications rather than just announcing the news.
- Use rhetorical questions or analogies to make abstract ideas concrete.
- Avoid sensationalism, buzzwords, and fluff. Provide real, meaty substance.
- Highlight Numbers: Extract and prominently feature impressive stats, metrics, funding amounts, dates, or benchmarks.
- Build tension, then release it: set up a problem, then reveal the insight.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
{full_text_section}
{angle_section}
OUTPUT RULES:
- Return ONLY the post text. No preamble, no "here's the post:", no quotes.
- Write 5 to 8 short paragraphs. Each paragraph is 1–3 sentences max.
- Structure: Hook → Context → Why it matters → Key insight or data → What readers should do or think.
- CRITICAL: Separate every paragraph with a blank line (double newline, \n\n). LinkedIn needs this for readability.
- Write in normal sentence case: capitalize first word, proper nouns, brand names, and acronyms (AI, API, ML, etc.). Do NOT write in all-lowercase.
- End with the URL on its own line. CRITICAL: Provide the ACTUAL official project/event/company URL from the article text, NOT just the news source link. Vary the CTA naturally (e.g. "full details here:", "check it out:", "apply here:", "read the full announcement:") followed by the URL.
"""


def build_edit_prompt(original_post: str, edit_instruction: str, story: dict, post_type: str) -> str:
    """Prompt for editing/regenerating a post with a specific instruction."""
    return f"""{PERSONALITY_PROMPT}

---

TASK: Revise this LinkedIn {post_type} post based on the edit instruction.

ORIGINAL POST:
{original_post}

EDIT INSTRUCTION:
{edit_instruction}

STORY CONTEXT:
Title: {story['title']}
URL: {story.get('url', '')}

OUTPUT RULES:
- Return ONLY the revised post text. No preamble.
- Apply the edit instruction faithfully, thinking like a copywriter.
- Keep all writing rules (normal sentence case, no em dashes, no exclamation marks for text posts).
"""

def build_intent_parser_prompt(text: str, picks: list[dict]) -> str:
    """Prompt for parsing natural language story pick + format + angle."""
    picks_context = ""
    for i, p in enumerate(picks, 1):
        picks_context += f"{i}. Title: {p.get('title', '')}\nSuggested format: {p.get('format_suggestion', 'text')}\nSummary: {p.get('summary', '')}\n\n"

    return f"""
TASK: You are an intent parser. The user was presented with 5 story options and replied with natural language.
Extract: which story (1, 2, 3, 4, or 5) they picked, any format preference, and any custom angle/opinion.

STORY OPTIONS:
{picks_context}
USER'S REPLY:
{text}

FORMAT VALUES: "image" | "carousel" | "text"
Format keywords to recognise:
- "image", "with image", "post image", "with a photo" → "image"
- "carousel", "slides", "swipe" → "carousel"
- "text", "text only", "no image", "just text" → "text"
- If no format is mentioned → null (caller will use default)

OUTPUT RULES:
- Return ONLY valid JSON, no markdown, no backticks, no explanations.
- JSON must have exactly three keys: "story_num", "angle", "format".
- "story_num": integer 1-5, or null if cannot determine.
- "angle": the user's perspective/opinion as a string, or null if none given.
- "format": "image", "carousel", "text", or null.
"""


def build_action_intent_prompt(text: str) -> str:
    """Prompt to classify user intent when reviewing a draft post."""
    return f"""
TASK: The user has been shown a draft LinkedIn post and replied with a message.
Classify their intent into one of exactly four actions.

USER'S REPLY:
{text}

ACTIONS:
- "post" — they want to publish as-is. Keywords: post, publish, go, yes, looks good, send it, perfect, approved, do it, post it.
- "edit" — they want changes. Keywords: edit, change, make it, fix, shorter, longer, different, tone, tweak, rewrite, rephrase, update.
- "switch" — they want a different format. Keywords: carousel, image, text, switch, use instead, change format.
- "cancel" — they want to abandon this post. Keywords: cancel, drop it, nevermind, forget it, stop, no.

OUTPUT RULES:
- Return ONLY valid JSON, no markdown, no backticks, no explanations.
- JSON must have exactly two keys: "action" and "detail".
- "action": one of "post", "edit", "switch", "cancel", or null if truly unclear.
- "detail": for "edit" → the edit instruction string. For "switch" → the format string ("image"/"carousel"/"text"). Otherwise null.
"""
