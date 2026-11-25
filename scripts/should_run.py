"""Exit-code-free check used by the workflow: prints run=true/false to GITHUB_OUTPUT.

Scheduled runs fire several times a night (GitHub sometimes drops a scheduled run).
Only the first one that finds no post made today (Vietnam date) does the work.
Manual runs always go ahead.
"""
import json, os
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
event = os.environ.get("EVENT", "")
today = datetime.now(VN).date()
run = True
if event == "schedule":
    pub = json.load(open(os.path.join(ROOT, "state", "published.json"), encoding="utf-8"))["published"]
    for e in pub:
        made = e.get("made_at")
        if made and datetime.fromisoformat(made).astimezone(VN).date() == today:
            run = False
            break
print(f"event={event} today(VN)={today} run={run}")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"run={'true' if run else 'false'}\n")
