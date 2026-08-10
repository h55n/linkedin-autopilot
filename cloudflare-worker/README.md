# Cloudflare Worker — Telegram → GitHub Actions Bridge

This tiny worker is the **missing piece** that makes the whole system work.

## What It Does

```
You reply on Telegram
       ↓
Telegram sends webhook POST to CF Worker URL
       ↓
CF Worker calls GitHub API → triggers bot-session.yml
       ↓
GitHub Actions runs the bot, processes your message, replies
```

## One-Time Setup (~5 minutes)

### 1. Create a GitHub Fine-Grained PAT

Go to: **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**

- Repository: `linkedin-autopilot` (your repo only)
- Permissions: **Actions → Read and Write**
- Copy the token — you won't see it again

### 2. Create a Cloudflare Worker

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) (free account, no card needed)
2. Click **Workers & Pages → Create application → Create Worker**
3. Name it: `linkedin-autopilot-bridge`
4. Paste the contents of `index.js` into the editor
5. Click **Deploy**
6. Copy the Worker URL: `https://linkedin-autopilot-bridge.<your-subdomain>.workers.dev`

### 3. Set Environment Variables

In your Cloudflare Worker → **Settings → Variables**:

| Variable | Value |
|---|---|
| `GITHUB_TOKEN` | The PAT you created in step 1 |
| `GITHUB_OWNER` | Your GitHub username |
| `GITHUB_REPO` | `linkedin-autopilot` |
| `TELEGRAM_SECRET` | Any random string (e.g. `mysecret123`) |

### 4. Register the Webhook with Telegram

Run this in your browser or curl (replace values):

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://linkedin-autopilot-bridge.<your-subdomain>.workers.dev&secret_token=mysecret123
```

You should get: `{"ok":true,"result":true,"description":"Webhook was set"}`

### 5. Verify

Send your bot a message. Go to GitHub → Actions tab → you should see a `Bot Session` run appear within seconds.

### To Reset / Remove Webhook (if switching back to polling)

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
```

## Environment Variables Needed in GitHub Secrets

Make sure these are all set in your repo → **Settings → Secrets and variables → Actions**:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GROQ_API_KEY`
- `GIST_TOKEN`
- `GIST_ID`
- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_PERSON_URN`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `MISTRAL_API_KEY` (optional — fallback LLM)
- `NVIDIA_NIM_API_KEY` (optional — primary LLM)
