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
- 2 to 4 very short paragraphs/sentences.
- CRITICAL: Separate each sentence/paragraph with an empty line (double newline, \n\n) for proper alignment.
- Follow the lowercase rule from PERSONALITY_PROMPT exactly, ensuring short-form acronyms (AI, AICT, API, etc.) are ALWAYS capitalized.
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
- Each slide body: max 40 words.
- intro_text: 1 sentence, creates curiosity gap.
- IMPORTANT: the `body` fields MUST contain double newlines (`\\n\\n`) to separate sentences into short paragraphs.
- Do NOT use all lowercase. Use natural Title Case for cover headings, and Sentence case for subheadings and body text.
- CRITICAL JSON RULE: Output ONLY the raw JSON object. NO markdown code fences (no ```json or ```). NO introductory text like "Here is the JSON". Start your response exactly with {{ and end exactly with }}.
"""


def build_image_caption_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating an image pair caption."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE:\n{angle}\n"

    full_text_section = f"FULL ARTICLE TEXT (use this for depth and accuracy):\n{story['full_text'][:2000]}\n" if story.get('full_text') else ""

    return f"""{PERSONALITY_PROMPT}

---

TASK: Act as a world-class conversion copywriter. Write a highly engaging and insightful LinkedIn caption for an image pair post about the story below.

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
{full_text_section}
{angle_section}
OUTPUT RULES:
- Return ONLY the caption text. No preamble.
- 2 to 3 very short paragraphs.
- CRITICAL: Separate each paragraph with an empty line (double newline, \n\n) for proper alignment.
- Follow the lowercase rule from PERSONALITY_PROMPT exactly, ensuring short-form acronyms (AI, AICT, API, etc.) are ALWAYS capitalized.
- Assume the reader might not look at the images — the caption must make sense alone.
- Introduce the URL on its own line at the very end. CRITICAL: Extract and provide the ACTUAL official project, hackathon, event, or company website link mentioned in the text, NOT just the news source link. Vary the Call To Action naturally and conversationally (e.g., "Official link here: ", "Apply here: ", "Check out the project: ", etc.) followed by the extracted official URL (or the STORY URL if no official link exists).
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
- Keep all writing rules (mostly lowercase except for acronyms, no em dashes, max 3 sentences for text posts).
"""

def build_intent_parser_prompt(text: str, picks: list[dict]) -> str:
    """Prompt for parsing natural language intent into a story selection."""
    picks_context = ""
    for i, p in enumerate(picks, 1):
        picks_context += f"{i}. Title: {p.get('title', '')}\nFormat: {p.get('format_suggestion', 'unknown')}\nSummary: {p.get('summary', '')}\n\n"

    return f"""
TASK: You are an intent parser. The user was presented with 3 story options and replied with natural language. 
Determine WHICH story (1, 2, or 3) the user selected, and extract any custom angle/opinion they provided.

STORY OPTIONS:
{picks_context}
USER'S REPLY:
{text}

OUTPUT RULES:
- Return ONLY valid JSON, no markdown formatting, no backticks, no explanations.
- The JSON must have two keys: "story_num" and "angle".
- "story_num": an integer (1, 2, or 3). If you cannot determine which story they meant, return null.
- "angle": a string containing the user's specific angle, perspective, or instruction. If they only specified the story without an angle (e.g. "I want the first one"), return null.
"""
