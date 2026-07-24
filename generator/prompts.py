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

    return f"""{PERSONALITY_PROMPT}

---

TASK: Write a LinkedIn text post about the story below.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
SOURCE: {story.get('source', '')}
REGION: {story.get('region', 'global')}
{angle_section}
OUTPUT RULES:
- Return ONLY the post text. No preamble, no "here's the post:", no quotes around it.
- 2 to 3 sentences. Hard limit. No more.
- All lowercase, no em dashes, no exclamation marks.
- Include the URL naturally in sentence 3 if it's a tool/product launch.
- Max 700 characters total.
"""


def build_carousel_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating carousel slide JSON."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE:\n{angle}\n"

    return f"""{PERSONALITY_PROMPT}

---

TASK: Write carousel slide content for the story below.
Return ONLY valid JSON. No markdown, no backticks, no explanation.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
{angle_section}
JSON FORMAT (return exactly this structure):
{{
  "intro_text": "one sentence hook for the linkedin post caption",
  "slides": [
    {{
      "type": "cover",
      "category_label": "AI TOOLS",
      "heading": "5 words max, all lowercase",
      "subheading": "10 words max, all lowercase"
    }},
    {{
      "type": "content",
      "heading": "5 words max, all lowercase",
      "body": "40 words max, all lowercase",
      "highlight_phrase": "optional: a key phrase from body to highlight"
    }},
    {{
      "type": "content",
      "heading": "5 words max, all lowercase",
      "body": "40 words max, all lowercase"
    }},
    {{
      "type": "cta",
      "heading": "5 words max, all lowercase",
      "body": "40 words max, all lowercase",
      "highlight_phrase": "the single most important takeaway"
    }}
  ]
}}

RULES:
- Maximum 5 slides total (including cover).
- All text lowercase except acronyms (GPT, API, LLM, etc.).
- No em dashes, no exclamation marks, no hashtags.
- Each slide body: max 40 words.
- intro_text: 1 sentence, creates curiosity gap.
"""


def build_image_caption_prompt(story: dict, angle: str = None) -> str:
    """Prompt for generating an image pair caption."""
    angle_section = ""
    if angle:
        angle_section = f"\nYOUR ANGLE:\n{angle}\n"

    return f"""{PERSONALITY_PROMPT}

---

TASK: Write a LinkedIn caption for an image pair post about the story below.

STORY TITLE: {story['title']}
STORY URL: {story.get('url', '')}
STORY SUMMARY: {story.get('summary', '')}
{angle_section}
OUTPUT RULES:
- Return ONLY the caption text. No preamble.
- 1 to 2 sentences.
- All lowercase, no em dashes, no exclamation marks.
- Assume the reader might not look at the images — the caption must make sense alone.
- Include the URL.
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
- Apply the edit instruction faithfully.
- Keep all writing rules (lowercase, no em dashes, max 3 sentences for text posts).
"""
