import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from telegram_bot.bot import _parse_pick

picks = [
    {
        "title": "Nvidia NIM is a game-changer for AI deployment",
        "summary": "Nvidia has launched NIM, making it easier than ever to deploy AI models on their hardware with optimal performance."
    },
    {
        "title": "Groq LPU speed breaks records",
        "summary": "Groq's language processing units are achieving unprecedented tokens per second."
    },
    {
        "title": "Mistral releases new open weight model",
        "summary": "A highly capable 8x22B mixture of experts model has been released by Mistral."
    }
]

tests = [
    "2",
    "2. make it funny",
    "I want the one about Groq",
    "Let's go with the Mistral story, and focus on the open source angle.",
    "Nvidia NIM looks good",
    "Can you do the first one? Make it sound professional.",
    "None of these look good to me."
]

print("Testing _parse_pick with LLM fallback:")
for t in tests:
    result = _parse_pick(t, picks)
    print(f"Input: '{t}'")
    print(f"Result: {result}\n")
