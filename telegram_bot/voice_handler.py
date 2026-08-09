"""
telegram_bot/voice_handler.py
Downloads Telegram voice notes (.ogg) and transcribes via Groq Whisper.
"""

import os
import tempfile
import requests
from groq import Groq
from utils.logger import get_logger, log_error
from config.settings import GROQ_API_KEY, GROQ_WHISPER_MODEL, TELEGRAM_BOT_TOKEN

log = get_logger("voice_handler")
_client = None


def _get_groq_client():
    global _client
    if _client is None:
        key = GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY is not set in environment")
        _client = Groq(api_key=key)
    return _client


def transcribe_voice(file_id: str) -> str | None:
    """
    Download a Telegram voice file and transcribe it via Groq Whisper.
    Returns the transcribed text, or None on failure.
    """
    try:
        # Step 1: Get file path from Telegram
        ogg_path = _download_voice(file_id)
        if not ogg_path:
            return None

        # Step 2: Transcribe with Whisper
        text = _transcribe_file(ogg_path)

        # Step 3: Cleanup
        try:
            os.remove(ogg_path)
        except OSError:
            pass

        log.info(f"Voice transcribed: '{text[:80]}...' " if len(text) > 80 else f"Voice transcribed: '{text}'")
        return text

    except Exception as e:
        log_error("Voice transcription failed", e)
        return None


def _download_voice(file_id: str) -> str | None:
    """Download the .ogg file from Telegram servers. Returns local path."""
    # Get file info
    resp = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
        params={"file_id": file_id},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        log.warning(f"Telegram getFile failed: {data}")
        return None

    file_path = data["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    # Download to temp file
    dl_resp = requests.get(download_url, timeout=30, stream=True)
    dl_resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    for chunk in dl_resp.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()

    log.debug(f"Voice file downloaded: {tmp.name}")
    return tmp.name


def _transcribe_file(file_path: str) -> str:
    """Send audio file to Groq Whisper for transcription."""
    client = _get_groq_client()
    with open(file_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(file_path), f, "audio/ogg"),
            model=GROQ_WHISPER_MODEL,
            language="en",
        )
    return transcription.text.strip()
