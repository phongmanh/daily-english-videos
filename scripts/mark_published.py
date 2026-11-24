"""Record a posted word in state/published.json so it is not posted again."""
import argparse, json, os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("word")
ap.add_argument("--youtube", default="")
ap.add_argument("--facebook", default="")
ap.add_argument("--publish-at", default="")
a = ap.parse_args()
p = os.path.join(ROOT, "state", "published.json")
data = json.load(open(p, encoding="utf-8"))
data["published"].append({"word": a.word, "youtube_id": a.youtube, "facebook_id": a.facebook,
                          "publish_at": a.publish_at, "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Recorded", a.word)
