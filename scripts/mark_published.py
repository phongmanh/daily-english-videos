"""Record a post in state/published.json (reads kind/words from out/meta.json)."""
import argparse, json, os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("meta")
ap.add_argument("--youtube", default="")
ap.add_argument("--facebook", default="")
ap.add_argument("--publish-at", default="")
a = ap.parse_args()
meta = json.load(open(a.meta, encoding="utf-8"))
entry = {"kind": meta["kind"], "youtube_id": a.youtube, "facebook_id": a.facebook, "publish_at": a.publish_at,
         "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
if meta["kind"] == "word":
    entry["word"] = meta["word"]
else:
    entry["words"] = meta["words"]
p = os.path.join(ROOT, "state", "published.json")
data = json.load(open(p, encoding="utf-8"))
data["published"].append(entry)
json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Recorded", meta["kind"], meta["words"])
