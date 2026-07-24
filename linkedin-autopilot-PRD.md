# LinkedIn Autopilot — Complete Product Requirements Document

**Owner:** You (Pune-based)
**Version:** 1.1 — Carousel design system added from reference slides
**Status:** Ready for implementation

---

## Table of Contents

1. What This Is
2. What This Is Not
3. User Experience — The Daily Flow
4. System Architecture
5. Data Flow Pipeline
6. Component Specifications
7. Personality System — The Locked Layer
8. Source Map & Scraping Rules
9. Scoring & Filtering Logic
10. Telegram Bot Conversation Design
11. Post Format Specifications
12. Carousel & Image Generation
13. LinkedIn Posting Logic
14. Hosting & Deployment
15. Environment & Secrets
16. Project File Structure
17. Test Suite
18. Open Questions & Decisions Log

---

## 1. What This Is

A fully automated daily LinkedIn content pipeline with a single human checkpoint — you, on Telegram, every morning.

The system wakes up before you do. It scrapes the internet for the most relevant tech and AI stories from the last 24 hours — global launches, India ecosystem moves, tools people can use today. It scores and ranks them. It sends you the top 3 on Telegram at 7:00 AM IST. You pick one, optionally add your angle in text or voice. It generates a post in your voice, suggests a format, and waits for your go-ahead. You say post. It posts to LinkedIn. Done. Your total time: under 3 minutes.

If you don't reply within 2 hours, it sends one reminder. If still no reply, it skips the day, logs it, and tries again tomorrow.

The only cost in the entire system is the LLM API call — approximately ₹0.80 per day on Groq's free tier, which is effectively zero.

---

## 2. What This Is Not

- Not a content farm. One post per day. Quality over quantity.
- Not fully autonomous. You are always the final voice. The system writes, you approve.
- Not a generic LinkedIn tool. Every configuration decision — tone, sources, scoring weights, format rules — is hard-coded to your specific taste and geography.
- Not expensive. Except the optional LLM API (Groq free tier covers this), everything runs on free infrastructure.

---

## 3. User Experience — The Daily Flow

This is the ground truth. Everything in the architecture serves this flow.

```
07:00 AM IST
System sends Telegram message:

────────────────────────────────────────
good morning. here are today's picks.

reply: [number] + your take (text or voice note)
format suggestion is included — you can override.
────────────────────────────────────────

1. 🔧 mistral just dropped a 7b model that beats gpt-4 on code
   [hackernews] | trending 800pts | 3h ago
   format suggestion: carousel (benchmark comparison)
   https://mistral.ai/news/...

2. 🇮🇳 bangalore-based startup raises $12m to build ai for bharat languages
   [inc42] | fresh | 1h ago
   format suggestion: text post
   https://inc42.com/...

3. 🔧 open-source tool that turns any figma file into react code
   [show hn] | 600pts | 5h ago
   format suggestion: image pair (before/after)
   https://github.com/...

reply 'skip' to skip today.
────────────────────────────────────────
```

**You reply:** `2, this matters because most ai tools are still built assuming english fluency — that's a massive gap for 600m people`

OR you send a voice note saying the same thing.

```
07:04 AM IST
System replies on Telegram:

────────────────────────────────────────
got it. here's your post:

most ai products still assume english fluency.
a bangalore startup just raised $12m to fix that,
building ai specifically for indian languages at scale.
600 million people just became part of the conversation.
https://inc42.com/...

format: text post
────────────────────────────────────────
reply 'post' to publish
reply 'edit [what to change]' to tweak
reply 'carousel' or 'image' to switch format
────────────────────────────────────────
```

**You reply:** `post`

```
07:05 AM IST
LinkedIn post published.
System replies: ✓ posted. check it here: https://linkedin.com/feed/update/...
```

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RENDER.COM (free tier)                   │
│                     runs as a background worker                 │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ SCHEDULER│───▶│ SCRAPER  │───▶│  SCORER  │───▶│GENERATOR │  │
│  │ (cron)   │    │          │    │          │    │(Groq API)│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                       │         │
│                                                       ▼         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   TELEGRAM BOT                           │   │
│  │  sends brief → receives your reply → handles voice note  │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                          │                            │
│         ▼                          ▼                            │
│  ┌──────────────┐          ┌──────────────┐                     │
│  │ GROQ WHISPER │          │  CAROUSEL /  │                     │
│  │ (if voice)   │          │  IMAGE GEN   │                     │
│  └──────────────┘          └──────────────┘                     │
│                                   │                            │
│                                   ▼                            │
│                        ┌──────────────────┐                    │
│                        │  LINKEDIN POSTER │                    │
│                        │  (official API)  │                    │
│                        └──────────────────┘                    │
│                                   │                            │
│                                   ▼                            │
│                        ┌──────────────────┐                    │
│                        │   LOGGER / STATE │                    │
│                        │   (local JSON)   │                    │
│                        └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### External Services

| Service | Purpose | Cost |
|---|---|---|
| Groq API | LLM (post generation) + Whisper (voice transcription) | Free tier |
| Telegram Bot API | Your daily interface | Free |
| LinkedIn API | Publishing posts | Free |
| Render.com | Hosting the worker | Free tier |
| HN Firebase API | Hacker News data | Free |
| Reddit JSON API | Reddit data | Free (with limits) |
| RSS feeds | India news + product launches | Free |
| Product Hunt RSS | Daily AI launches | Free |
| GitHub Trending | Trending repos | Free (scrape) |

---

## 5. Data Flow Pipeline

Every step is sequential. A failure at any step logs and exits gracefully — it never silently corrupt state.

```
STEP 1 — SCRAPE (07:00 AM IST)
├── Hacker News top stories (filtered: score > 100)
├── Reddit hot posts from r/artificial, r/MachineLearning,
│   r/singularity, r/programming, r/startups, r/india
├── Product Hunt RSS (AI category filter)
├── RSS feeds: Inc42, YourStory, Entrackr, ET Tech,
│   TechCrunch AI, VentureBeat AI, TheresAnAI, BetaList
└── GitHub Trending (top 5 repos)
         │
         ▼
STEP 2 — DEDUPLICATE
├── Remove duplicate URLs (strip query params)
├── Remove near-duplicate titles (fuzzy match, 85% threshold)
└── Remove stories older than 24 hours
         │
         ▼
STEP 3 — SCORE
├── Base score from upvotes/engagement
├── Recency multiplier (fresher = higher)
├── India keyword bonus (+30)
├── Tool/launch keyword bonus (+25)
├── AI keyword bonus (+20)
├── Boost keyword bonus (+5 per keyword hit)
└── Noise keyword penalty (×0.2)
         │
         ▼
STEP 4 — DIVERSITY PASS
├── Rank all stories by final score
├── Check if at least 1 India story is in top 3
├── If not, replace lowest-scoring pick with top India story
└── Output: top 3 stories with format suggestion for each
         │
         ▼
STEP 5 — FORMAT SUGGESTION
├── Story is a tool launch + has GitHub URL → suggest image pair
├── Story has benchmark/comparison data → suggest carousel
├── Story is India news, opinion-heavy → suggest text post
└── Attach suggestion to each story (user can override)
         │
         ▼
STEP 6 — TELEGRAM BRIEF
├── Format morning message (see UX section)
├── Send to TELEGRAM_CHAT_ID
├── Save state: {date, picks, status: "waiting", sent_at: timestamp}
└── Start 2-hour countdown timer
         │
         ▼
STEP 7 — WAIT FOR YOUR REPLY (up to 2 hours)
├── Telegram bot is always listening (polling loop)
├── On reply → parse: story number + angle text
├── If voice note → download .ogg → Groq Whisper → extract text angle
├── If no reply at 1h mark → send one reminder
├── If no reply at 2h mark → log "skipped", exit for today
└── On 'skip' reply → log "user skipped", exit
         │
         ▼
STEP 8 — GENERATE POST
├── Feed story + your angle into Groq LLM
├── Use locked personality prompt (see Section 7)
├── Generate in requested format (text / carousel / image caption)
└── Send draft back to you on Telegram
         │
         ▼
STEP 9 — YOUR APPROVAL
├── On 'post' → proceed to Step 10
├── On 'edit [instruction]' → regenerate with edit note, loop back
├── On 'carousel' / 'image' / 'text' → regenerate in new format
└── On 'cancel' → log "user cancelled", exit
         │
         ▼
STEP 10 — GENERATE ASSETS (if needed)
├── Text post → no assets needed
├── Carousel → generate PDF (up to 5 slides as 1080×1080 images → PDF)
└── Image pair → placeholder instruction (you attach screenshots manually)
         │
         ▼
STEP 11 — PUBLISH TO LINKEDIN
├── Text post → LinkedIn API: POST /ugcPosts (text only)
├── Carousel → LinkedIn API: upload PDF → attach to post
├── Confirm publish, get post URL
└── Send confirmation to Telegram: ✓ posted → [url]
         │
         ▼
STEP 12 — LOG
├── Write to logs/daily_log.json:
│   {date, story_picked, format, post_text, linkedin_url, your_angle}
└── Increment streak counter (for your own motivation)
```

---

## 6. Component Specifications

### 6.1 Scheduler (`scheduler.py`)
- Uses `APScheduler` with `Asia/Kolkata` timezone
- One job: runs `main_pipeline()` at 07:00 every day
- Separate job: reminder check at 08:00 (1 hour after brief)
- Separate job: skip check at 09:00 (2 hours after brief)
- State is persisted in `state/today.json` to survive restarts

### 6.2 Scraper (`scraper/scraper.py`)
- Each source is an independent function — a failure in one does not affect others
- All functions return the same dict schema (see below)
- Rate limiting: 50ms sleep between HN item fetches, 500ms between Reddit subreddits
- Timeout: 10 seconds per request, fail gracefully

**Story dict schema (universal across all sources):**
```python
{
  "id": str,               # hash of URL
  "source": str,           # "hackernews", "reddit/r/artificial", "inc42", etc.
  "title": str,            # clean title (no "Show HN:", no "Ask HN:")
  "url": str,              # canonical URL to the actual content
  "discussion_url": str,   # HN/Reddit discussion thread URL (optional)
  "summary": str,          # short description (max 400 chars, plain text)
  "score": int,            # raw upvote/engagement score from source
  "comments": int,         # comment count
  "timestamp": int,        # unix timestamp of publication
  "is_tool_launch": bool,  # True if this is a product/tool launch
  "region": str,           # "india" or "global"
  # Added by scorer:
  "final_score": float,
  "age_hours": float,
  "india_relevant": bool,
  "is_ai_related": bool,
  "format_suggestion": str  # "text" | "carousel" | "image"
}
```

### 6.3 Scorer (`scorer/scorer.py`)
- Pure function: takes list of story dicts, returns ranked list
- No external API calls — runs instantly
- Fully configurable via `config/settings.py`
- Diversity pass runs after initial ranking

### 6.4 Generator (`generator/generator.py`)
- All LLM calls go to Groq API
- Model: `llama-3.3-70b-versatile` (best quality on Groq free tier)
- Temperature: 0.72 (creative but not erratic)
- Max tokens: 600 for text posts, 900 for carousel JSON
- Personality prompt is a constant — never constructed dynamically
- Carousel output is always JSON — parsed and validated before sending to you
- On JSON parse failure: regenerate once, then fallback to text post

### 6.5 Telegram Bot (`telegram_bot/bot.py`)
- Uses `python-telegram-bot` library (polling mode, not webhook — simpler on free hosting)
- Maintains conversation state in `state/today.json`
- Handles exactly these user intents:
  - `[1|2|3]` — pick a story
  - `[1|2|3] [text]` — pick + angle
  - Voice note — download + transcribe + extract angle
  - `post` — approve and publish
  - `edit [instruction]` — regenerate with note
  - `carousel` / `image` / `text` — switch format
  - `skip` — skip today
  - `cancel` — cancel after draft
  - `status` — what's the system doing right now
  - `log` — show last 7 days of posts
- Ignores all messages from anyone except TELEGRAM_CHAT_ID (security)

### 6.6 Voice Handler (`telegram_bot/voice_handler.py`)
- Downloads the .ogg file from Telegram's servers
- Sends to Groq Whisper large-v3
- Returns transcribed text
- Logs both the original voice note path and the transcription
- If Whisper fails: asks you to resend as text (graceful fallback)

### 6.7 Carousel Generator (`carousel/carousel_gen.py`)
- Uses `Pillow` (Python image library) — no external design tools, no Canva, no APIs
- Each slide: 1080×1080px square canvas
- All fonts loaded from `assets/fonts/` — system never uses OS fallback fonts
- Required font files:
  - `assets/fonts/CooperBT-Bold.ttf` — headline font (primary)
  - `assets/fonts/PlayfairDisplay-Bold.ttf` — headline fallback if Cooper BT missing
  - `assets/fonts/Inter-Regular.ttf` — body text
  - `assets/fonts/Inter-SemiBold.ttf` — labels, highlighted text
- Slide rendering order: cover → content slides → opinion/CTA slide
- All slides exported as individual PNGs → compiled into single PDF via `img2pdf` or `Pillow PDF mode`
- Max 5 slides enforced: if LLM returns more than 5, truncate silently
- Margin system: 80px on all sides, content zone 920×920px centered
- Background colors by slide type:
  - Cover: `#d4e4d0` (sage green)
  - Content: `#f7f4ef` (warm cream)
  - Final CTA: `#f0ebe3` (slightly warmer cream)
- Text colors: headline `#1a1a2e`, body `#3a3a3a`, muted `#6b7c6b`
- Accent: coral `#f07a5a` for bullet dots and arrow icons
- Highlights: green `#c8e6c0` (default), yellow `#fef08a` (final CTA only)
- Highlight rendering: draw rounded rectangle behind the phrase, then draw text on top
- Bullet rendering: draw filled circle in coral, then text in green highlight box beside it
- Arrow rendering: draw `→` glyph in coral, then plain body text beside it
- Slide number: top-left of content slides only (not cover), Inter Regular 18px, `#aaaaaa`
- Footer: bottom-center of content slides, Inter Regular 16px, `#aaaaaa`, your handle
- Cover: no slide number, no footer
- Text wrapping: Pillow `textbbox` for measuring, manual word-wrap to enforce 60-word max
- Vertical centering: calculate total content block height, center it within content zone

### 6.8 LinkedIn Poster (`linkedin/poster.py`)
- Uses LinkedIn UGC Posts API (v2)
- Text post: single API call
- Carousel (PDF): two-step — upload asset first, then create post referencing asset ID
- Access token stored in `.env`, refreshed manually every 60 days (LinkedIn's limit)
- On token expiry: sends Telegram message warning you to refresh

### 6.9 Logger (`utils/logger.py`)
- Writes structured JSON to `logs/daily_log.json`
- Each entry: date, story, format, post_text, your_angle, linkedin_url, status
- Also maintains `logs/streak.json`: consecutive posting days
- Logs errors to `logs/errors.log` with full tracebacks

---

## 7. Personality System — The Locked Layer

This is the most important section. This prompt never changes based on context or user input. It is a constant in `config/settings.py`. Every post generation call begins with this exact prompt.

```
SYSTEM PROMPT — LOCKED. DO NOT MODIFY PER-REQUEST.

you are a ghostwriter for a specific person. here is everything you know about them:

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
- 2 to 3 sentences. hard limit.
- sentence 1: the fact or the thing that happened (hook)
- sentence 2: why it matters or what changed
- sentence 3: your opinion, a tool link, or a question to make them think
- if it is a tool launch: include the url naturally in sentence 3

carousel intro text (the text that appears with the carousel on linkedin):
- 1 sentence only. this is the hook that makes them swipe.
- it should create a gap: something they want to know more about.

carousel slides:
- slide 1: the most surprising or counterintuitive fact. large, bold.
- slides 2-3: the substance. what happened, what changed, what it means.
- slide 4-5 (optional): practical takeaway, your opinion, or what to do next.
- each slide: heading (5 words max) + body (40 words max)
- all lowercase except acronyms (GPT, API, etc.)

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
```

---

## 8. Source Map & Scraping Rules

### Global Sources

| Source | Method | Filter | Fetch Limit |
|---|---|---|---|
| Hacker News | Firebase REST API | score > 100, not dead/deleted | top 60 stories |
| Show HN (HN) | Same API | title starts with "Show HN" | included in top 60 |
| Reddit r/artificial | JSON API | score > 200, not stickied | top 10 per sub |
| Reddit r/MachineLearning | JSON API | score > 200 | top 10 |
| Reddit r/singularity | JSON API | score > 200 | top 10 |
| Reddit r/programming | JSON API | score > 200 | top 10 |
| Reddit r/startups | JSON API | score > 150 | top 10 |
| Product Hunt | RSS feed | AI keyword filter | top 10, AI only |
| GitHub Trending | HTML scrape | none | top 5 repos |
| TechCrunch AI | RSS | published < 24h | all recent |
| VentureBeat AI | RSS | published < 24h | all recent |
| TheresAnAI | RSS | published < 24h | all recent |
| BetaList | RSS | published < 24h | all recent |

### India Sources

| Source | Method | Filter | Region |
|---|---|---|---|
| Inc42 | RSS | published < 24h | India |
| YourStory | RSS | published < 24h | India/Bangalore |
| Entrackr | RSS | published < 24h | India |
| ET Tech | RSS | published < 24h | India |

### Scraping Rules

- Max age: 24 hours. Anything older is skipped unless it just went viral (score still rising).
- Timeout: 10s per request. On timeout, log warning and continue.
- Rate limiting: HN 50ms between items, Reddit 500ms between subreddits, RSS feeds no limit.
- User agent: `LinkedInAutopilot/1.0` on all requests.
- Reddit API: use public JSON endpoint first. If rate limited (429), back off 60s and retry once.
- No authentication required for any source in this setup.

---

## 9. Scoring & Filtering Logic

### Score Formula

```
final_score = (raw_score × upvote_weight × recency_multiplier)
            + india_bonus
            + tool_launch_bonus
            + ai_keyword_bonus
            + (boost_keyword_hits × 5)
            + comment_velocity_bonus
            × noise_penalty_multiplier
```

### Recency Multiplier

| Age | Multiplier |
|---|---|
| 0 – 2 hours | 3.0× |
| 2 – 6 hours | 2.0× |
| 6 – 12 hours | 1.5× |
| 12 – 24 hours | 1.0× |
| > 24 hours | 0.5× |

### Bonuses

| Condition | Bonus |
|---|---|
| India keyword in title or summary | +30 |
| Tool/product launch keyword | +25 |
| AI keyword | +20 |
| Per boost keyword hit | +5 |
| Comments > 200 | ×1.3 multiplier |
| Comments 100–200 | ×1.15 multiplier |
| Show HN post | +50 to raw score before formula |

### Noise Penalty

If any noise keyword is found in title + summary: `final_score × 0.2`

Noise keywords: `nft, crypto, bitcoin, blockchain, web3, metaverse, celebrity`

### Diversity Rule

After ranking, check: is at least one India story in the top 3?
If not: replace the 3rd pick with the highest-scoring India story (if one exists).
If no India story exists today: top 3 by score, no change.

### Format Suggestion Logic

```
if is_tool_launch AND has_github_url:
    suggest "image"   ← screenshot of tool + code/output

elif title or summary contains ["benchmark", "vs", "beats", "outperforms",
                                 "comparison", "chart", "faster", "cheaper"]:
    suggest "carousel"  ← data lends itself to slides

elif india_relevant AND is recent:
    suggest "text"    ← opinion post, india angle

else:
    suggest "text"    ← default: keep it simple
```

---

## 10. Telegram Bot Conversation Design

### State Machine

```
IDLE
  │
  │ (07:00 AM cron fires)
  ▼
BRIEF_SENT ──(no reply 1h)──▶ REMINDER_SENT ──(no reply 1h)──▶ SKIPPED
  │
  │ (you reply: "2, here's my take")
  ▼
PROCESSING (transcribe voice if needed → generate post)
  │
  ▼
DRAFT_SENT
  │
  ├──(reply: "post") ──────────────────────────▶ PUBLISHING ──▶ POSTED ──▶ IDLE
  │
  ├──(reply: "edit [note]") ──────────────────▶ PROCESSING (loop)
  │
  ├──(reply: "carousel"/"image"/"text") ──────▶ PROCESSING (loop)
  │
  └──(reply: "cancel") ───────────────────────▶ CANCELLED ──▶ IDLE
```

### Message Templates

**Morning brief:** (shown in Section 3)

**Reminder (1 hour after brief):**
```
hey, still waiting on today's pick. 
which story are you going with? (reply 1, 2, or 3 + your take)
or reply 'skip' to skip today.
```

**Skip confirmation:**
```
ok, skipping today. see you tomorrow at 7.
current streak: [N] days
```

**Draft preview:**
```
────────────────────────────
here's your post:

[generated post text]

format: [text post / carousel / image pair]
────────────────────────────
reply 'post' to publish
reply 'edit [what to change]' to tweak
reply 'carousel' / 'image' / 'text' to switch format
reply 'cancel' to drop it
```

**Posted confirmation:**
```
✓ posted.
https://linkedin.com/feed/update/[id]

streak: [N] days in a row 🔥
```

**Edit request handling:**
```
User: "edit make it sharper and add the github link"
System: [regenerates with edit note appended to prompt]
        [sends new draft in same format as above]
```

---

## 11. Post Format Specifications

### Text Post Rules

- All lowercase
- No em dashes
- 2–3 sentences hard limit
- No hashtags (or max 2 if topic genuinely benefits)
- URL included naturally if tool/product launch
- Max 700 characters (LinkedIn sweet spot for algorithm)
- No line breaks between sentences — single flowing paragraph

**Example output:**
```
mistral just released a 7b model that scores higher than gpt-4 on
humaneval coding benchmarks. the interesting part is not the score —
it's that it runs locally on a macbook. indian devs building on tight
budgets just got a serious option. https://mistral.ai/news/
```

### Carousel Specifications

#### Philosophy
Editorial. Clean. Calm. Each slide should feel like a page from a well-designed newsletter, not a social media graphic. Generous whitespace is the most important design decision — never crowd the slide. Every element earns its place.

#### Canvas
- Size: 1080×1080px per slide (square — LinkedIn native)
- Export: each slide as PNG, then compiled into a single PDF for upload
- Max slides: 5 (enforced in code — never go above this)

#### Typography — Hard-coded, Never Changes

| Element | Font | Weight | Size | Color |
|---|---|---|---|---|
| Category label (cover only) | Inter or system sans-serif | 600 (semibold) | 22px | `#6b7c6b` (muted sage) |
| Main headline | Cooper BT (serif) or Playfair Display as fallback | 700–800 (bold) | 72–90px | `#1a1a2e` (dark navy) |
| Subheadline / intro line | Inter | 400 (regular) | 32px | `#3a3a3a` |
| Body text | Inter | 400 (regular) | 30–34px | `#3a3a3a` |
| Highlighted phrase | Inter | 600 (semibold) | same as body | `#1a1a2e` on pastel highlight bg |
| Bullet label text | Inter | 500 (medium) | 30px | `#1a1a2e` |
| Slide number / footer | Inter | 400 | 18px | `#aaaaaa` (very muted) |

**Font loading rule:** Try to load Cooper BT from `assets/fonts/CooperBT-Bold.ttf`. If unavailable, fall back to Playfair Display (downloadable from Google Fonts, include in assets). Never fall back to a system serif — it will look wrong.

#### Color Palette — Pastel, Calm, Editorial

| Name | Hex | Usage |
|---|---|---|
| Cover background | `#d4e4d0` | Sage green — cover slide only |
| Content background | `#f7f4ef` | Warm off-white/cream — all content slides |
| CTA/opinion background | `#f0ebe3` | Slightly warmer cream — final slide |
| Primary text | `#1a1a2e` | Dark navy — all headlines and bold text |
| Body text | `#3a3a3a` | Dark grey — all paragraph text |
| Muted text | `#6b7c6b` | Category labels, slide numbers, footer |
| Highlight — green | `#c8e6c0` | Key phrase background highlight |
| Highlight — yellow | `#fef08a` | Alternate key phrase highlight (use sparingly) |
| Bullet dot | `#f07a5a` | Coral/orange — list bullet dots |
| Arrow icon | `#f07a5a` | Same coral — for arrow-style bullets |

**Rule:** Never use more than one highlight color per slide. Green is default, yellow only for the single most important takeaway per carousel.

#### Spacing & Layout — The Most Important Part

Every slide uses the same margin system:

```
┌─────────────────────────────────────┐
│                                     │
│   [80px margin — always empty]      │
│                                     │
│   ┌─────────────────────────────┐   │  ← 80px left/right margin
│   │                             │   │
│   │      CONTENT LIVES HERE     │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
│   [80px margin — always empty]      │
│                                     │
└─────────────────────────────────────┘
```

- Outer margin: 80px on all four sides — nothing bleeds to the edge
- Content zone: 920×920px centered within the 1080×1080 canvas
- Vertical alignment: content block centered in the content zone, not top-aligned
- Line spacing: 1.5× font size minimum between lines
- Element spacing: 40px between headline and body, 28px between bullet items
- Never put more than 60 words of text on a single content slide

#### Slide-by-Slide Spec

**Slide 1 — Cover (always this layout)**
```
Background: #d4e4d0 (sage green)

[Optional small icon — leaf or similar, 24px, muted]
[Category label — e.g. "AI TOOLS" or "INDIA TECH" — spaced caps, 22px, #6b7c6b]
                        ↕ 24px gap
[Main headline — Cooper BT Bold, 80–90px, #1a1a2e, centered, max 5 words]
                        ↕ 20px gap
[Subtitle line — Inter Regular, 30px, #3a3a3a, centered, max 10 words]

No slide number on cover. No footer on cover.
```

**Slides 2–4 — Content slides**
```
Background: #f7f4ef (warm cream)

Top-left: slide number (e.g. "02") — Inter 400, 18px, #aaaaaa
                        ↕ 48px
[Headline — Cooper BT Bold, 56–66px, #1a1a2e, centered]
                        ↕ 32px
[Body text — Inter 400, 30px, #3a3a3a, centered, max 40 words]

If bullet list:
  ● [coral dot] [text in green highlight box]
  ● [coral dot] [text in green highlight box]
  ● [coral dot] [text in green highlight box]
  (max 3 bullets per slide)

If highlighted phrase needed:
  Normal body text flows, then key phrase gets
  [yellow or green background box behind just that phrase]

Bottom-center: your handle or name — Inter 400, 16px, #aaaaaa
```

**Final slide — Opinion / CTA**
```
Background: #f0ebe3 (warm cream, slightly different from content slides)

[Headline — "here's one thing to do" or similar — Cooper BT Bold, 54px, #1a1a2e]
                        ↕ 32px
[Body — the practical takeaway — Inter 400, 30px, #3a3a3a]
                        ↕ 24px
[Key action phrase in yellow highlight: "That's your real target." style]

Bottom: your handle — muted, small
```

#### Bullet Point Styling
- Bullet dot: filled circle `●`, coral `#f07a5a`, 20px, vertically centered with text
- Arrow style: `→` in coral for "things to avoid" or "contrast" slides (see reference slide 4)
- Text next to bullet: in a soft green highlight box `#c8e6c0` with 8px horizontal padding, 6px vertical padding, 6px border-radius
- Never use standard markdown bullets — always custom rendered

#### What Never Goes on a Slide
- No gradients
- No drop shadows
- No borders or boxes around the entire slide
- No stock photo backgrounds
- No more than 2 font sizes in use on a single slide
- No more than 60 words total per content slide
- No hashtags
- No exclamation marks (matches your post voice)

### Image Pair

- System does NOT auto-screenshot (this requires a browser)
- System generates the caption text and the instruction
- It tells you in Telegram: "for this post, grab a screenshot of [specific thing] and attach both images when posting, or reply 'text' to switch to a text post"
- Future version: integrate Playwright for auto-screenshot

---

## 12. LinkedIn Posting Logic

### Authentication

- OAuth 2.0: one-time browser flow to get access token
- Token stored in `.env` as `LINKEDIN_ACCESS_TOKEN`
- Expires every 60 days
- System checks token age daily. If > 55 days old: Telegram warning to refresh.
- Refresh script: `python scripts/refresh_linkedin_token.py` — opens browser, walks through flow

### Text Post API Call

```
POST https://api.linkedin.com/v2/ugcPosts
Authorization: Bearer {token}
Content-Type: application/json

{
  "author": "urn:li:person:{PERSON_ID}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "{post_text}"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

### Carousel (PDF) Post

Step 1: Upload PDF as asset
```
POST https://api.linkedin.com/v2/assets?action=registerUpload
→ get uploadUrl and asset URN
PUT {uploadUrl} with PDF binary
```

Step 2: Create post referencing asset
```
POST https://api.linkedin.com/v2/ugcPosts
{
  "shareMediaCategory": "DOCUMENT",
  "media": [{
    "status": "READY",
    "media": "{asset_urn}",
    "title": {"text": "{headline}"}
  }]
}
```

---

## 13. Hosting & Deployment

### Platform: Render.com (free tier)

- Service type: **Background Worker** (not Web Service — no HTTP server needed)
- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`
- Environment variables: set in Render dashboard (not in code)
- Persistent disk: 1GB free — used for logs and state
- Free tier sleeps after 15 minutes of inactivity — but background workers don't sleep (only web services do)

### Alternative: Railway.app (free tier)

- Same setup, slightly different dashboard
- $5/month credit free — enough for this workload

### Why not a VPS?

Cost. Both Render and Railway give enough free compute for a script that runs once a day and processes < 1MB of data. A VPS (DigitalOcean, etc.) would cost ₹500–800/month unnecessarily.

### Keeping it alive

The script runs once daily via APScheduler. Between runs, it's in polling mode (Telegram bot listens). This is not resource-intensive — polling is a lightweight long-poll, not busy-waiting.

---

## 14. Environment & Secrets

All secrets in `.env` file. Never committed to git. Set as environment variables in Render dashboard for production.

```
# .env

# Groq — console.groq.com — free
GROQ_API_KEY=

# Telegram — from @BotFather
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=          # your personal Telegram numeric user ID

# LinkedIn — developers.linkedin.com
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_PERSON_URN=       # urn:li:person:XXXXXXX

# Optional: Reddit (higher rate limits) — reddit.com/prefs/apps
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=linkedin-autopilot/1.0
```

### How to get each key

**Groq API key:**
1. Go to console.groq.com
2. Sign up free
3. API Keys → Create Key
4. Copy into .env

**Telegram Bot Token + Chat ID:**
1. Open Telegram, search @BotFather
2. `/newbot` → follow prompts → copy token
3. Message your new bot once
4. Visit `https://api.telegram.org/bot{TOKEN}/getUpdates`
5. Find `"chat":{"id":XXXXXXXXX}` — that's your TELEGRAM_CHAT_ID

**LinkedIn Access Token:**
1. Go to developers.linkedin.com
2. Create app → add products: "Share on LinkedIn", "Sign In with LinkedIn"
3. Run `python scripts/get_linkedin_token.py` (included in project)
4. Complete OAuth in browser
5. Token copied to .env automatically

**LinkedIn Person URN:**
1. After getting token, run: `python scripts/get_linkedin_urn.py`
2. Prints your URN — copy to .env

---

## 15. Project File Structure

```
linkedin-autopilot/
│
├── main.py                         # entry point — starts scheduler + bot
│
├── config/
│   └── settings.py                 # ALL configuration, weights, prompts
│
├── scraper/
│   ├── scraper.py                  # main scrape_all() function
│   ├── sources/
│   │   ├── hackernews.py           # HN scraper
│   │   ├── reddit.py               # Reddit scraper
│   │   ├── producthunt.py          # Product Hunt RSS
│   │   ├── rss_feeds.py            # India + global RSS
│   │   └── github_trending.py      # GitHub scraper
│   └── deduplicator.py             # URL + fuzzy title dedup
│
├── scorer/
│   └── scorer.py                   # rank_and_pick() + format_suggestion()
│
├── generator/
│   ├── generator.py                # generate_post(), generate_morning_brief()
│   └── prompts.py                  # all prompt templates as constants
│
├── telegram_bot/
│   ├── bot.py                      # main bot, message handlers, state machine
│   ├── voice_handler.py            # voice note download + Groq transcription
│   └── messages.py                 # all message templates as constants
│
├── carousel/
│   ├── carousel_gen.py             # slide generation with Pillow
│   └── assets/
│       └── fonts/
│           └── Inter-Regular.ttf   # font for slides
│
├── linkedin/
│   ├── poster.py                   # post to LinkedIn API
│   └── auth.py                     # token refresh helper
│
├── scripts/
│   ├── get_linkedin_token.py       # one-time OAuth flow
│   ├── get_linkedin_urn.py         # fetch your person URN
│   └── refresh_linkedin_token.py   # refresh expired token
│
├── state/
│   └── today.json                  # current day's pipeline state
│
├── logs/
│   ├── daily_log.json              # history of all posts
│   ├── streak.json                 # posting streak
│   └── errors.log                  # full error tracebacks
│
├── utils/
│   ├── logger.py                   # structured logging setup
│   └── helpers.py                  # shared utilities
│
├── tests/
│   ├── test_scraper.py
│   ├── test_scorer.py
│   ├── test_generator.py
│   ├── test_telegram.py
│   ├── test_linkedin.py
│   └── test_pipeline.py            # end-to-end integration test
│
├── .env.example                    # template — commit this
├── .env                            # your secrets — NEVER commit
├── .gitignore
├── requirements.txt
├── render.yaml                     # Render deployment config
└── README.md                       # setup instructions
```

---

## 16. Test Suite

Each test is independent and runnable with `python -m pytest tests/`.

### Test 1: Scraper Health Check (`test_scraper.py`)

```
test_hackernews_returns_stories
  → call scrape_hackernews()
  → assert len(results) > 0
  → assert all stories have: title, url, score, timestamp
  → assert all scores >= min_score from config

test_reddit_returns_stories
  → call scrape_reddit()
  → assert at least one subreddit returned data
  → assert story dicts have required fields

test_rss_feeds_return_fresh_stories
  → call scrape_rss_feeds()
  → assert all returned stories have timestamp within last 24h

test_deduplication_removes_duplicate_urls
  → feed two stories with same URL
  → assert deduplicate() returns only one

test_deduplication_removes_near_duplicate_titles
  → feed two stories with ~90% similar titles
  → assert deduplicate() returns only one

test_scrape_all_returns_nonempty_list
  → call scrape_all()
  → assert len > 0
  → assert all required fields present
```

### Test 2: Scorer (`test_scorer.py`)

```
test_recent_stories_score_higher_than_old
  → two identical stories, one 1h old, one 20h old
  → assert 1h story has higher final_score

test_india_keyword_adds_bonus
  → story with "bangalore" in title scores higher than identical story without

test_tool_launch_adds_bonus
  → story with is_tool_launch=True scores higher

test_noise_keyword_penalizes_score
  → story with "crypto" in title scores significantly lower

test_diversity_pass_inserts_india_story
  → top 3 picks contain no India stories
  → India story exists with lower score
  → assert rank_and_pick() includes the India story in output

test_format_suggestion_logic
  → tool launch + github URL → suggest "image"
  → story with "benchmark" in title → suggest "carousel"
  → india story, no benchmark → suggest "text"
```

### Test 3: Generator (`test_generator.py`)

```
test_text_post_is_lowercase
  → generate text post for any story
  → assert post_text == post_text.lower()

test_text_post_has_no_em_dashes
  → generate text post
  → assert "—" not in post_text

test_text_post_is_under_3_sentences
  → generate text post
  → split by ". " and assert len <= 3

test_carousel_json_is_valid
  → generate carousel for a story
  → assert result["slides"] is a list
  → assert len(slides) <= 5
  → assert each slide has "heading" and "body"

test_carousel_slides_are_lowercase
  → generate carousel
  → assert all slide text is lowercase

test_voice_transcription_returns_string
  → mock Groq Whisper response
  → assert transcribe_voice() returns non-empty string

test_morning_brief_contains_3_picks
  → generate_morning_brief() with 3 stories
  → assert "1." and "2." and "3." in output
  → assert each story's URL is in output
```

### Test 4: Telegram Bot (`test_telegram.py`)

```
test_bot_ignores_unknown_chat_id
  → simulate message from different chat_id
  → assert bot does not respond

test_story_number_parsed_correctly
  → simulate message "2, here's my take"
  → assert parsed story_number == 2
  → assert parsed angle == "here's my take"

test_story_number_only_parsed_correctly
  → simulate message "1"
  → assert parsed story_number == 1
  → assert parsed angle is None

test_post_command_triggers_publish
  → mock pipeline state = DRAFT_SENT
  → simulate "post" message
  → assert publish_to_linkedin() is called

test_edit_command_triggers_regeneration
  → mock pipeline state = DRAFT_SENT
  → simulate "edit make it shorter"
  → assert generate_post() is called with edit note

test_format_override_works
  → mock pipeline state = DRAFT_SENT, current format = "text"
  → simulate "carousel"
  → assert generate_post() is called with post_type="carousel"

test_skip_command_updates_state
  → simulate "skip"
  → assert state status == "skipped"
  → assert no LinkedIn call made
```

### Test 5: LinkedIn (`test_linkedin.py`)

```
test_text_post_api_call_structure
  → mock LinkedIn API
  → call post_text_to_linkedin("test post")
  → assert API called with correct UGC post structure
  → assert author URN is correct

test_carousel_upload_then_post_sequence
  → mock LinkedIn asset upload
  → mock LinkedIn post creation
  → call post_carousel_to_linkedin(slides=[...])
  → assert upload called first, then post creation
  → assert asset URN passed correctly

test_token_expiry_warning_sent
  → set token_created_date to 56 days ago
  → assert Telegram warning message sent
```

### Test 6: End-to-End Pipeline (`test_pipeline.py`)

```
test_full_pipeline_text_post (integration test)
  → mock all external APIs (HN, Reddit, Groq, Telegram, LinkedIn)
  → run main_pipeline()
  → assert Telegram brief sent
  → simulate user reply "1"
  → assert Groq called for generation
  → simulate "post" reply
  → assert LinkedIn API called
  → assert state status == "posted"
  → assert daily_log.json has new entry

test_pipeline_skips_on_no_reply
  → run main_pipeline()
  → send brief
  → advance clock by 1 hour → assert reminder sent
  → advance clock by 2 hours → assert state == "skipped"
  → assert LinkedIn never called

test_pipeline_handles_scraper_partial_failure
  → mock HN scraper to raise exception
  → assert pipeline continues with Reddit + RSS data
  → assert error logged
  → assert pipeline does not crash
```

### Running Tests

```bash
# all tests
pytest tests/ -v

# single module
pytest tests/test_scraper.py -v

# with coverage report
pytest tests/ --cov=. --cov-report=term-missing

# integration test only
pytest tests/test_pipeline.py -v -s
```

---

## 17. Decisions Log

All decisions made before writing this PRD. These are final.

| Decision | Choice | Reason |
|---|---|---|
| Hosting | Render.com free tier | Zero cost, background workers don't sleep |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, fast, good quality |
| Voice transcription | Groq Whisper large-v3 | Free, 28k seconds/day, fast |
| Your interface | Telegram bot | Easiest mobile experience, free API |
| When system posts | Only after your "post" command | You are always the final approval |
| No reply behavior | Reminder at 1h, skip at 2h | Keeps quality high, no garbage posts |
| Post frequency | Once per day | Quality over quantity |
| Max carousel slides | 5 | Anything more loses people |
| Image screenshot | Manual for now | Auto-screenshot is Phase 2 (Playwright) |
| LinkedIn posting | Official API | Stable, no scraping risk |
| Carousel format | PDF | LinkedIn's native carousel format |
| City coverage | Pune primary, Bangalore primary, Mumbai secondary | Your geography |
| Crypto/Web3 filter | Noise penalty ×0.2 (not hard block) | In case there's a genuinely relevant story |
| Post style | Lowercase, no em dashes, 2-3 sentences | Your brand, hard-coded |
| Carousel headline font | Cooper BT Bold (Playfair Display as fallback) | Matches reference style — editorial, not techy |
| Carousel body font | Inter Regular / SemiBold | Clean, readable at 30px on 1080px canvas |
| Carousel background | Sage green cover (`#d4e4d0`), warm cream content (`#f7f4ef`) | Calm, pastel, editorial — not dark/techy |
| Carousel accent color | Coral `#f07a5a` for bullets/arrows | Warm, not corporate blue |
| Carousel highlight | Green `#c8e6c0` default, yellow `#fef08a` for single hero phrase | Matches reference exactly |
| Carousel margin | 80px all sides — hard rule | Whitespace is the design, never crowd the slide |
| Carousel max words/slide | 60 words hard limit | Forces clarity, matches reference density |
| No gradients/shadows | Hard rule | Keeps slides clean and fast to render |

---

## 18. Build Order

When building, follow this sequence. Each phase is independently testable.

**Phase 1 — Core pipeline (offline)**
Build scraper → scorer → generator. Run locally. Verify output quality before touching Telegram or LinkedIn.

**Phase 2 — Telegram bot**
Add bot, voice handler, state machine. Test entire morning flow end to end on your phone before deployment.

**Phase 3 — LinkedIn posting**
Set up OAuth, test with a draft post (or a test account first), verify carousel PDF upload works.

**Phase 4 — Deployment**
Push to Render, set environment variables, verify cron fires at 7 AM IST, run for 3 days and check logs.

**Phase 5 — Tuning**
After 1 week of posts, review scoring weights and personality prompt based on what content you actually liked vs. skipped.

---

*PRD complete. Ready to build.*
