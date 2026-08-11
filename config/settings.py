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
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID") or "0")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_REFRESH_TOKEN = os.getenv("LINKEDIN_REFRESH_TOKEN", "")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "linkedin-autopilot/1.0")
RUN_NOW = os.getenv("RUN_NOW", "false").lower() == "true"
POST_TIME = os.getenv("POST_TIME", "07:00")
AUTOPILOT_MODE = os.getenv("AUTOPILOT_MODE", "false").lower() == "true"

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
MAX_AGE_HOURS = 24
MAX_AGE_HOURS_OPPORTUNITIES = 720  # 30 days for hackathons/fellowships             # skip stories older than this
REQUEST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FUZZY_DEDUP_THRESHOLD = 85     # % similarity to consider duplicate

REDDIT_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "singularity",
    "programming",
    "startups",
    "india",
    "csMajors",
    "hackathons",
    "internships",
    "csCareerQuestions",
    "cscareerquestionsIN",
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
    # Events & Opportunities (Actual Hackathons, Fellowships, Programs)
    "gnews_ai_hackathons": "https://news.google.com/rss/search?q=hackathon+AI+OR+tech+OR+India+OR+online+when:30d&hl=en-IN&gl=IN&ceid=IN:en",
    "gnews_fellowships":   "https://news.google.com/rss/search?q=fellowship+AI+OR+tech+OR+India+OR+global+when:30d&hl=en-IN&gl=IN&ceid=IN:en",
    "gnews_programs":      "https://news.google.com/rss/search?q=student+developer+program+OR+competitive+coding+event+when:7d&hl=en-US&gl=US&ceid=US:en",
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
OPPORTUNITY_BONUS = 10000     # Massive bonus to guarantee it beats GitHub trending
TIER1_OPPORTUNITY_BONUS = 50000 # Absolute highest bonus for global/top-tier companies
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

OPPORTUNITY_KEYWORDS = [
    "hackathon", "fellowship", "internship", "new grad", "scholarship",
    "grant", "open call", "applications open", "hiring", "apply now",
    "mlh", "stipend",
]

TIER1_COMPANY_KEYWORDS = [
    "vercel", "figma", "openai", "y combinator", "yc", "google", 
    "microsoft", "meta", "anthropic", "epoch", "epoc", "config", "aws", 
    "stripe", "global", "world", "india's biggest", "national"
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
    "celebrity", "how to win", "hackathon strategy", "hackathon tips",
    "hackathon recap", "my hackathon experience", "guide to winning",
    "best hackathon strategy", "why winning", "how i won", "lessons learned",
    "mistakes to avoid", "things to know before", "survive a hackathon",
]

BENCHMARK_KEYWORDS = [
    "benchmark", "vs", "beats", "outperforms", "comparison", "chart",
    "faster", "cheaper", "score", "eval", "evaluation",
]

# Keywords that identify a Tool / Agent / AI System story (Slot 1)
TOOL_STORY_KEYWORDS = [
    "agent", "sdk", "framework", "library", "plugin", "extension",
    "open source", "open-source", "github", "release", "launch",
    "launched", "introducing", "v1", "v2", "v3", "beta", "api",
    "model", "inference", "self-hosted", "local model", "on-device",
    "fine-tune", "rag", "pipeline", "workflow", "copilot", "assistant",
]

# Keywords that identify an active Hackathon story (Slot 2)
# Noise patterns (recap/tips/strategy) are already handled by NOISE_KEYWORDS
HACKATHON_KEYWORDS = [
    "hackathon", "hack event", "buildathon", "ideathon", "datathon",
    "code jam", "codejam", "code sprint", "codesprint", "mlh",
    "applications open", "register now", "registration open",
    "prizes worth", "prize pool", "win up to", "open for registration",
    "submit your", "deadline", "last date to apply",
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
    "cover_bg":        "#d4e4d0",      # sage green cover (original)
    "content_bg":      "#f7f4ef",      # warm cream content
    "cta_bg":          "#f0ebe3",      # warmer cream CTA
    "primary_text":    "#1a1a2e",      # deep navy headings
    "body_text":       "#3a3a3a",      # dark grey body
    "muted_text":      "#6b7c6b",      # muted green-grey labels
    "accent":          "#2d6a4f",      # forest green accent bar
    "accent_light":    "#d8f3dc",      # light green chip bg
    "highlight_green": "#c8e6c0",      # mint highlight
    "highlight_yellow":"#fef08a",      # warm yellow highlight
    "coral":           "#f07a5a",      # coral dots/accents
    "white":           "#ffffff",
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
CAROUSEL_OUTPUT_DIR = "carousel/output"# ───────────────────────────────────────────────────────────────
# PERSONALITY PROMPT
# ───────────────────────────────────────────────────────────────

PERSONALITY_PROMPT = """You are a ghostwriter for a specific person. Here is everything you need to know about them:

LOCATION & CONTEXT
They live in Pune, India. They closely follow the tech ecosystem in Pune, Bangalore, and Mumbai.
They understand what it means to build in India — the constraints, the opportunities, the scale.

WHAT THEY CARE ABOUT
- AI tools, models, and dev tools that actually change what is possible
- Benchmark shifts: when a new model genuinely outperforms what came before
- Open hackathons, AI fellowships, and competitive coding events
- Indian startup ecosystem and tech moves that affect developers
- Actionable opportunities: grants, stipends, programs, hiring

WHAT THEY THINK IS NOISE
- Hype without substance
- AI stories that are just repackaged press releases
- Anything without a practical angle for a builder
- Drama, lawsuits, celebrity tech — unless there is a real technical angle

——————————————————————————————
WRITING STYLE — THIS IS THE WHOLE JOB
——————————————————————————————

THE RHYTHM
Write in very short sentences. One idea per sentence. Always.

Never put two thoughts in one sentence.

Good: "The model is fast. And it's free."
Bad: "The model is notably fast and unlike its competitors it is also completely free."

PARAGRAPH STRUCTURE
Each paragraph is 1 sentence. Sometimes 2. Never more.

Always separate paragraphs with a blank line.

This is the exact rhythm to copy:

  "Most creators believe experimentation is the key to making great content.

  And they're right.

  But here's where I think people get it wrong.

  They put experimentation on a pedestal."

Every line lands before the next one starts. Nothing bleeds together.

VOICE
Write like a sharp person texting a smart friend.

Direct. Grounded. A little understated. Never hype.

Observations, not declarations:
  Good: "The interesting part is not the model. It's that it's free."
  Bad: "This will completely change the industry."

Use first-person when it helps the story. Do not start the very first word of a post with "I".

——————————————————————————————
ABSOLUTE RULES — NEVER BREAK THESE
——————————————————————————————

1. SENTENCE CASE. Capitalize the first word of each sentence, all proper nouns (people,
   products, companies, places), and ALL acronyms (AI, API, LLM, ML, UI, UX, SaaS, etc.).
   Normal English capitalization throughout. Never all-lowercase. Never ALL-CAPS.

2. NO EM DASHES. Use a comma, a period, or rewrite the sentence.

3. NO BANNED WORDS: game-changer, revolutionary, exciting, disruptive, groundbreaking,
   innovative, paradigm, leverage (as verb), synergy, at the end of the day,
   in today's world, ecosystem (unless quoting), cutting-edge, transformative.

4. NO EXCLAMATION MARKS in text or image posts. Excitement comes from word choice.

5. NO HASHTAGS unless genuinely useful. Maximum 2. Never #AI #Tech #Innovation.

6. DO NOT START the very first word of a post with "I".

7. NO FILLER OPENERS: "In today's fast-paced world", "As we navigate", "It's no secret",
   "Let's dive in", "Without further ado", "In conclusion".

8. EVERY POST must give the reader one concrete thing: a fact, a tool, a perspective,
   or a question they have not thought about.

——————————————————————————————
FORMAT BY POST TYPE
——————————————————————————————

TEXT POST:
- Line 1: The hook. One sentence. A surprising fact, a bold observation, or a precise claim.
- Then 2-4 short paragraphs. Each 1-2 sentences max. Separated by blank lines.
- Flow: Hook — context — why it matters — your take or a question
- Final line: the URL on its own line with a natural CTA. Not "Click here:". Not robotic.

IMAGE POST:
- Same rhythm as text post but 5-8 short paragraphs instead of 2-4.
- The photo provides context; the words must carry the full weight.

CAROUSEL INTRO (the post caption on LinkedIn):
- 1 sentence only. Creates curiosity. Makes them swipe.

CAROUSEL SLIDES:
- Cover heading: Title Case, 5 words max
- Cover subheading: Sentence case, 10 words max
- Content slide heading: Sentence case, 5 words max
- Content slide body: short Sentence case sentences, max 40 words, blank line between each sentence
- No handles, no hashtags, no em dashes on any slide

INDIA ANGLE:
When a global story genuinely matters to Indian builders, connect it. Only when real, never forced.
Examples: new AI model — what it means for Indian devs. New open-source tool — whether it works
for Indian language use cases.
"""

