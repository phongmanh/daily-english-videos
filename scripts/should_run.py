"""Exit-code-free check used by the workflow: prints run=true/false to GITHUB_OUTPUT.

Two daily slots: SLOT=word (18:00 post: word Short or weekly video) and SLOT=review (12:00 post).
Each slot has several scheduled runs (GitHub sometimes drops one). Only the first one that
finds no post of that slot made today (Vietnam date) does the work. Manual runs always go ahead.
"""
import json, os
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
event = os.environ.get("EVENT", "")
slot = os.environ.get("SLOT", "word")
kinds = {"review"} if slot == "review" else {"word", "quiz", "long"}
today = datetime.now(VN).date()
run = True
if event == "schedule":
    pub = json.load(open(os.path.join(ROOT, "state", "published.json"), encoding="utf-8"))["published"]
    for e in pub:
        made = e.get("made_at")
        if e.get("kind", "word") in kinds and made and datetime.fromisoformat(made).astimezone(VN).date() == today:
            run = False
            break
print(f"event={event} slot={slot} today(VN)={today} run={run}")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"run={'true' if run else 'false'}\n")
