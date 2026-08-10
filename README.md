# LinkedIn Autopilot

A personal, fully automated LinkedIn posting system. It researches trending stories daily, sends you a Telegram brief, and publishes to LinkedIn on your command — in text, image, or carousel format.

## How It Works

```
7:00 AM IST (daily)
  └─ GitHub Actions: morning-pipeline.yml
      └─ scrape → score → pick top 3 → generate brief → send Telegram message

You reply on Telegram (any natural language)
  └─ Telegram webhook → Cloudflare Worker → GitHub Actions: bot-session.yml
      └─ NLP parser → generate post + image (default) → send draft to Telegram

You confirm the draft
  └─ "post" / "looks good" / "go ahead" (any NLP)
      └─ GitHub Actions publishes to LinkedIn
```

## Features

- **Daily research**: Scrapes HN, Reddit, GitHub Trending — scores and picks the best 3 stories for your audience
- **NLP commands**: Reply in plain English. *"I like story 2, post it as carousel"* works.
- **Image by default**: Every post comes with an auto-screenshot attached. Switch to text or carousel anytime.
- **Format options**: Text post | Image post (auto-screenshot) | Carousel PDF
- **Draft review**: See the post before it goes live. Edit, switch format, or cancel.
- **Zero always-on infra**: Runs on GitHub Actions (free tier) + Cloudflare Workers (free tier). No servers, no credit card.

## Architecture

| Component | Technology | Cost |
|---|---|---|
| Daily pipeline | GitHub Actions (cron) | Free |
| Bot responses | GitHub Actions (webhook dispatch) | Free |
| Webhook bridge | Cloudflare Worker | Free |
| State storage | GitHub Gist | Free |
| LLM | Groq (primary), Mistral, Nvidia NIM | Free tiers |

## Setup

### Prerequisites

- GitHub account + this repo forked
- Telegram bot (create via @BotFather)
- LinkedIn Developer App (for the API token)
- Cloudflare account (free, no card needed)
- Groq API key (free at console.groq.com)

### 1. GitHub Secrets

Go to **repo → Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID |
| `GROQ_API_KEY` | From console.groq.com |
| `GIST_TOKEN` | GitHub PAT with `gist` scope |
| `GIST_ID` | ID of a Gist to use as state store |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth token |
| `LINKEDIN_PERSON_URN` | Your LinkedIn person URN |
| `REDDIT_CLIENT_ID` | Reddit API app ID |
| `REDDIT_CLIENT_SECRET` | Reddit API app secret |
| `MISTRAL_API_KEY` | (optional) Mistral AI key |
| `NVIDIA_NIM_API_KEY` | (optional) Nvidia NIM key |

### 2. Create the Gist State Store

```bash
python scripts/setup_gist_state.py
```

### 3. Set Up the Webhook Bridge

See [`cloudflare-worker/README.md`](cloudflare-worker/README.md) for the 5-minute setup. This is the step that makes the bot actually respond to your Telegram messages.

### 4. Install Carousel Fonts (optional)

```bash
python scripts/setup_fonts.py
```

### 5. Get Your LinkedIn Token

```bash
python scripts/get_linkedin_token.py
```

LinkedIn tokens expire every 60 days. Re-run this when the bot warns you.

## Usage

The bot sends you a brief every morning at 7:00 AM IST:

```
good morning. here are today's picks.

reply: [number] + your take (text or voice note)
format suggestion is included — you can override.

────────────────────────────────────────
1. 🤖 openai releases o3-mini for free users
   [hackernews] | trending 2.1k pts | 3h ago
   format suggestion: image post

2. ...
```

### Picking a Story

Reply in any natural language:
- `1` — pick story 1, image (default format)
- `2 my take: this is overhyped` — pick story 2, include your angle
- `I like story 3, make it a carousel` — NLP understood
- `story 1, post it as text only` — override format to text
- `skip` — skip today

### After Draft is Sent

- `post` / `go ahead` / `looks good` — publish to LinkedIn
- `edit make it shorter` / `make it punchier` — regenerate with instruction
- `carousel` / `image` / `text` — switch format
- `cancel` / `drop it` — abandon

### On-Demand Research

```
/research Apple Intelligence announcement — I think they're playing it safe
```

Researches the topic, generates a post, sends for review.

## Local Development

```bash
# Install deps
pip install -r requirements.txt
python -m playwright install chromium

# Copy env
cp .env.example .env
# Fill in your keys

# Run the morning pipeline once
python scripts/run_pipeline.py

# Test bot session with a payload
TELEGRAM_PAYLOAD='{"update_id":1,"message":{"message_id":1,"date":1700000000,"chat":{"id":YOUR_CHAT_ID,"type":"private"},"from":{"id":YOUR_CHAT_ID,"is_bot":false,"first_name":"Test"},"text":"1"}}' python scripts/run_bot_session.py
```

## Files

```
linkedin-autopilot/
├── cloudflare-worker/       # Telegram webhook → GitHub Actions bridge
│   ├── index.js
│   └── README.md
├── telegram_bot/            # Bot message handlers
│   ├── bot.py               # Main handler logic + NLP
│   ├── messages.py          # All Telegram message templates
│   ├── screenshotter.py     # Auto-screenshot for image posts
│   └── voice_handler.py     # Voice note transcription
├── generator/               # LLM post generation
│   ├── generator.py         # All LLM calls
│   └── prompts.py           # All prompt templates
├── scraper/                 # Story research
│   ├── scraper.py           # Main scrape orchestrator
│   ├── researcher.py        # On-demand topic research
│   ├── enricher.py          # Full article text extraction
│   └── deduplicator.py      # Fuzzy dedup
├── scorer/                  # Story ranking
│   └── scorer.py
├── linkedin/                # LinkedIn API
│   ├── poster.py            # Post text/image/carousel
│   └── auth.py
├── carousel/                # Carousel PDF generation
│   └── carousel_gen.py
├── scripts/                 # Utility scripts
│   ├── run_pipeline.py      # GHA: morning pipeline entrypoint
│   ├── run_bot_session.py   # GHA: bot session entrypoint
│   ├── setup_gist_state.py
│   ├── setup_fonts.py
│   └── get_linkedin_token.py
├── .github/workflows/
│   ├── morning-pipeline.yml # Daily 7AM cron
│   └── bot-session.yml      # Per-message webhook handler
└── config/
    └── settings.py          # All config + scoring weights
```
