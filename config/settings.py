"""
config/settings.py
All configuration, weights, prompts, and constants.
This is the single source of truth — nothing is hard-coded elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────
# SECRETS (from .env)
# ─────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID") or "0")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "linkedin-autopilot/1.0")
RUN_NOW = os.getenv("RUN_NOW", "false").lower() == "true"
POST_TIME = os.getenv("POST_TIME", "07:00")

# ─────────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────────

TIMEZONE = "Asia/Kolkata"
REMINDER_AFTER_MINUTES = 60    # send reminder 1h after brief
SKIP_AFTER_MINUTES = 120       # skip day 2h after brief

# ─────────────────────────────────────────────────────────────────
# GROQ / LLM
# ─────────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"
MISTRAL_MODEL = "mistral-large-latest"
NVIDIA_NIM_MODEL = "meta/llama-3.1-70b-instruct"
GROQ_TEMPERATURE = 0.72
GROQ_MAX_TOKENS_TEXT = 600
GROQ_MAX_TOKENS_CAROUSEL = 900
GROQ_WHISPER_MODEL = "whisper-large-v3"

# ─────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10           # seconds per HTTP request
HN_RATE_LIMIT_MS = 50          # ms between HN item fetches
REDDIT_RATE_LIMIT_MS = 500     # ms between subreddit fetches
HN_MIN_SCORE = 100             # skip HN stories below this
HN_TOP_LIMIT = 60              # fetch top N HN stories
REDDIT_MIN_SCORE = 200         # skip Reddit posts below this (most subs)
REDDIT_STARTUPS_MIN_SCORE = 150
REDDIT_TOP_PER_SUB = 10
GITHUB_TRENDING_TOP = 5
MAX_AGE_HOURS = 24             # skip stories older than this
REQUEST_USER_AGENT = "LinkedInAutopilot/1.0"
FUZZY_DEDUP_THRESHOLD = 85     # % similarity to consider duplicate

REDDIT_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "singularity",
    "programming",
    "startups",
    "india",
]

RSS_FEEDS = {
    # India
    "inc42":     "https://inc42.com/feed/",
    "yourstory": "https://yourstory.com/feed",
    "entrackr":  "https://entrackr.com/feed/",
    "ettech":    "https://economictimes.indiatimes.com/tech/rss.cms",
    # Global AI / Tech
    "techcrunch_ai":  "https://techcrunch.com/category/artificial-intelligence/feed/",
    "venturebeat_ai": "https://venturebeat.com/category/ai/feed/",
    "betalist":       "https://betalist.com/feed",
}

PRODUCT_HUNT_RSS = "https://www.producthunt.com/feed"

# ─────────────────────────────────────────────────────────────────
# SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────────

UPVOTE_WEIGHT = 1.0

RECENCY_MULTIPLIERS = {
    (0, 2):   3.0,
    (2, 6):   2.0,
    (6, 12):  1.5,
    (12, 24): 1.0,
    (24, 999): 0.5,
}

INDIA_BONUS = 30
TOOL_LAUNCH_BONUS = 25
AI_KEYWORD_BONUS = 20
BOOST_KEYWORD_BONUS = 5       # per keyword hit
SHOW_HN_RAW_BONUS = 50        # added to raw score before formula
COMMENT_HIGH_MULTIPLIER = 1.3   # comments > 200
COMMENT_MID_MULTIPLIER = 1.15   # comments 100-200
COMMENT_HIGH_THRESHOLD = 200
COMMENT_MID_THRESHOLD = 100

NOISE_PENALTY = 0.2            # multiply final score by this

# ─────────────────────────────────────────────────────────────────
# KEYWORD LISTS
# ─────────────────────────────────────────────────────────────────

INDIA_KEYWORDS = [
    "india", "indian", "bangalore", "bengaluru", "mumbai", "pune",
    "delhi", "hyderabad", "chennai", "kolkata", "startup india",
    "bharat", "rupee", "inr", "sebi", "rbi", "meity", "nasscom",
    "inc42", "yourstory", "entrackr",
]

TOOL_LAUNCH_KEYWORDS = [
    "launch", "launched", "release", "released", "introducing", "announce",
    "announcing", "new tool", "open source", "open-source", "github",
    "show hn", "api", "sdk", "v2", "v3", "beta", "now available",
]

AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "mistral", "llama",
    "machine learning", "deep learning", "neural", "transformer",
    "model", "inference", "fine-tuning", "rag", "agent", "multimodal",
    "diffusion", "embedding", "vector", "openai", "anthropic", "groq",
    "hugging face", "langchain", "pytorch", "tensorflow",
]

BOOST_KEYWORDS = [
    "free", "open source", "faster", "cheaper", "beats", "outperforms",
    "benchmark", "state of the art", "sota", "real-time", "local",
    "on-device", "privacy", "self-hosted",
]

NOISE_KEYWORDS = [
    "nft", "crypto", "bitcoin", "blockchain", "web3", "metaverse",
    "celebrity",
]

BENCHMARK_KEYWORDS = [
    "benchmark", "vs", "beats", "outperforms", "comparison", "chart",
    "faster", "cheaper", "score", "eval", "evaluation",
]

# ─────────────────────────────────────────────────────────────────
# LINKEDIN
# ─────────────────────────────────────────────────────────────────

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_TOKEN_WARNING_DAYS = 55   # warn when token is this old
LINKEDIN_TOKEN_MAX_DAYS = 60       # LinkedIn's hard limit

# Path to store token creation date
LINKEDIN_TOKEN_DATE_FILE = "state/linkedin_token_date.txt"

# ─────────────────────────────────────────────────────────────────
# CAROUSEL
# ─────────────────────────────────────────────────────────────────

CAROUSEL_CANVAS_SIZE = 1080
CAROUSEL_MARGIN = 80
CAROUSEL_CONTENT_SIZE = 920       # 1080 - 2*80
CAROUSEL_MAX_SLIDES = 5
CAROUSEL_MAX_WORDS_PER_SLIDE = 60

CAROUSEL_COLORS = {
    "cover_bg":      "#d4e4d0",
    "content_bg":    "#f7f4ef",
    "cta_bg":        "#f0ebe3",
    "primary_text":  "#1a1a2e",
    "body_text":     "#3a3a3a",
    "muted_text":    "#6b7c6b",
    "highlight_green": "#c8e6c0",
    "highlight_yellow": "#fef08a",
    "coral":         "#f07a5a",
    "white":         "#ffffff",
}

CAROUSEL_FONTS = {
    "headline_path":  "carousel/assets/fonts/Caprasimo-Regular.ttf",
    "body_path":      "carousel/assets/fonts/Inter-Regular.ttf",
    "semibold_path":  "carousel/assets/fonts/Inter-SemiBold.ttf",
    "headline_size":  72,
    "headline_size_content": 52,
    "subheadline_size": 30,
    "body_size":      30,
    "label_size":     18,
    "footer_size":    16,
    "slide_num_size": 18,
}

# (Handle is intentionally omitted from slides)

# Font download URLs (for README / setup script)
FONT_DOWNLOAD_URLS = {
    "Inter-Regular.ttf": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2",
    "Inter-SemiBold.ttf": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fAZ9hiJ-Ek-_EeA.woff2",
    "Caprasimo-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caprasimo/Caprasimo-Regular.ttf",
}

# ─────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────

STATE_FILE = "state/today.json"
DAILY_LOG_FILE = "logs/daily_log.json"
STREAK_FILE = "logs/streak.json"
ERROR_LOG_FILE = "logs/errors.log"
CAROUSEL_OUTPUT_DIR = "carousel/output"

# ─────────────────────────────────────────────────────────────────
# PERSONALITY PROMPT — LOCKED. NEVER MODIFY PER-REQUEST.
# ─────────────────────────────────────────────────────────────────

PERSONALITY_PROMPT = """you are a ghostwriter for a specific person. here is everything you know about them:

LOCATION & CONTEXT
they live in pune, india. they closely follow the tech ecosystem in
pune, bangalore, and mumbai. they understand what it means to build
in india — the constraints, the opportunities, the scale.

WHAT THEY CARE ABOUT
- ai tools and model launches that actually change what's possible
- indian startup ecosystem: funding, launches, policy, people
- developer tools: things that save time or unlock new workflows
- benchmark shifts: when a new model or tool genuinely outperforms what came before
- global tech moves that will hit india in 6-12 months

WHAT THEY THINK IS NOISE
- hype without substance
- ai stories that are just repackaged press releases
- anything without a practical angle for a builder or curious person
- drama, lawsuits, celebrity tech unless there's a real technical angle

WRITING RULES — ABSOLUTE. NEVER BREAK THESE.
1. all lowercase. every word. no exceptions. not even proper nouns.
2. no em dashes (—). if you feel like using one, use a comma or a period instead.
3. no corporate speak. banned words: game-changer, revolutionary, exciting,
   disruptive, groundbreaking, innovative, paradigm, ecosystem (unless quoting),
   leverage (as a verb), synergy, at the end of the day, in today's world.
4. no hashtags unless genuinely useful. maximum 2 if used. never #AI #Tech #Innovation.
5. no exclamation marks in text posts. excitement is shown through word choice, not punctuation.
6. do not start with "i". first word should be the hook.
7. write like you are texting a smart friend who has 10 seconds.
8. every post must give the reader something: knowledge, a tool, a perspective, a question.
   if you cannot identify what the reader gets, do not write the post.

FORMAT RULES BY POST TYPE

plain text post:
- 2 to 4 very short paragraphs/sentences.
- CRITICAL: Separate each sentence/paragraph with an empty line (double newline).
- paragraph 1: the fact or the thing that happened (hook)
- paragraph 2: why it matters or what changed
- paragraph 3: your opinion or a question to make them think
- paragraph 4: attach the link properly on its own line at the very end.

carousel intro text (the text that appears with the carousel on linkedin):
- 1 sentence only. this is the hook that makes them swipe.
- it should create a gap: something they want to know more about.

carousel slides:
- cover slide: heading in Title Case (5 words max), subheading in Sentence case (10 words max).
- content slides: heading in Sentence case (5 words max), body in short Sentence case paragraphs.
- each slide body: max 40 words, separated by double newlines (\n\n) for paragraph breathing room.
- no handles, no hashtags, no em dashes.

image pair caption:
- 1 to 2 sentences.
- explain what the images show and why it matters.
- assume the reader might not look at the images.

INDIA ANGLE
whenever a global story is relevant to india, connect it. not forced —
only when it genuinely matters. examples:
- new ai model → what it means for indian devs/startups who use it
- us policy change → how it affects indian tech companies
- new open-source tool → whether it works for indian language use cases

OPINION STYLE
opinions should feel like observations, not declarations.
good: "the interesting part is not the model — it's that it's free"
bad: "this will completely change the industry"
good: "most people are missing what actually matters here"
bad: "this is a game changer"
"""
