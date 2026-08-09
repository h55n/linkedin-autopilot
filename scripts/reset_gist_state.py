"""scripts/reset_gist_state.py — Reset the Gist state to idle so the pipeline can re-run."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

os.environ["STATE_BACKEND"] = "gist"
from utils.helpers import write_state, read_state

state = read_state()
print("Current Gist state:")
print("  date   :", state.get("date"))
print("  status :", state.get("status"))

write_state({
    "date": None,
    "picks": [],
    "status": "idle",
    "sent_at": None,
    "selected_story": None,
    "user_angle": None,
    "current_draft": None,
    "current_format": None,
    "current_carousel_data": None,
    "linkedin_url": None,
    "past_urls": state.get("past_urls", []),
})

state2 = read_state()
print("Reset done. New status:", state2.get("status"))
