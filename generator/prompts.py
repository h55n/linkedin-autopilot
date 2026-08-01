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
- Introduce the URL on its own line at the very end. Vary the Call To Action naturally and conversationally (e.g., "Read this article to know more: ", "Dive deeper here: ", "Check out the full details: ", etc.) followed by the URL.
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
- Introduce the URL on its own line at the very end. Vary the Call To Action naturally and conversationally (e.g., "Read this article to know more: ", "Dive deeper here: ", "Check out the full details: ", etc.) followed by the URL.
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
