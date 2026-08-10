/**
 * cloudflare-worker/index.js
 *
 * Telegram → GitHub Actions webhook bridge.
 *
 * Flow:
 *   1. Telegram sends POST to this worker URL (set as the bot webhook)
 *   2. Worker verifies the secret token header
 *   3. Worker calls GitHub API to dispatch bot-session.yml with the payload
 *   4. GitHub Actions runs the bot session, processes the message, replies
 *
 * Environment Variables (set in CF Worker dashboard):
 *   GITHUB_TOKEN     — Fine-grained PAT with "Actions: write" permission
 *   GITHUB_OWNER     — Your GitHub username (e.g. "h55n")
 *   GITHUB_REPO      — Your repo name (e.g. "linkedin-autopilot")
 *   TELEGRAM_SECRET  — Any random string; set same in Telegram setWebhook call
 */

export default {
  async fetch(request, env) {
    // Only accept POST
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // Verify Telegram secret token (prevents unauthorized calls)
    const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (env.TELEGRAM_SECRET && secretHeader !== env.TELEGRAM_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("Bad Request: invalid JSON", { status: 400 });
    }

    // Dispatch to GitHub Actions bot-session workflow
    const githubUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/bot-session.yml/dispatches`;

    const response = await fetch(githubUrl, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "linkedin-autopilot-webhook-bridge/1.0",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          telegram_payload: JSON.stringify(body),
        },
      }),
    });

    if (response.ok || response.status === 204) {
      return new Response("OK", { status: 200 });
    } else {
      const text = await response.text();
      console.error(`GitHub dispatch failed: ${response.status} — ${text}`);
      return new Response("GitHub dispatch failed", { status: 502 });
    }
  },
};
