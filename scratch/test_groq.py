import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, r"d:\ANTIGRAVITY\linkedin-autopilot")
load_dotenv()

from generator.generator import _call_groq

try:
    print("Testing Groq...")
    response = _call_groq("Say hello in one word.")
    print("Response:", response)
except Exception as e:
    print("Groq failed:", e)
