"""Record a post in state/published.json (reads kind/words from out/meta.json).

If the same post was already recorded (e.g. it went to Facebook first and is now re-run for
YouTube only), the existing entry is updated instead of adding a duplicate.
"""
import argparse, json, os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("meta")
ap.add_argument("--youtube", default="")
ap.add_argument("--facebook", default="")
ap.add_argument("--instagram", default="")
ap.add_argument("--tiktok", default="", help="TikTok publish id (draft sent to the inbox)")
ap.add_argument("--publish-at", default="")
a = ap.parse_args()
meta = json.load(open(a.meta, encoding="utf-8"))
p = os.path.join(ROOT, "state", "published.json")
data = json.load(open(p, encoding="utf-8"))

def same(e):
    if e.get("kind", "word") != meta["kind"]:
        return False
    if meta["kind"] == "review":          # a review is a new post every day
        return e.get("publish_at") == a.publish_at
    return e.get("word") == meta["word"] if meta["kind"] == "word" else e.get("words") == meta["words"]

existing = next((e for e in reversed(data["published"]) if same(e)), None)
if existing:
    if a.youtube:
        existing["youtube_id"] = a.youtube
    if a.facebook:
        existing["facebook_id"] = a.facebook
    if a.instagram:
        existing["instagram_id"] = a.instagram
    if a.tiktok:
        existing["tiktok_id"] = a.tiktok
    print("Updated", meta["kind"], meta["words"])
else:
    entry = {"kind": meta["kind"], "youtube_id": a.youtube, "facebook_id": a.facebook, "instagram_id": a.instagram,
             "publish_at": a.publish_at,
             "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if meta["kind"] == "word":
        entry["word"] = meta["word"]
    else:
        entry["words"] = meta["words"]
    if meta.get("style"):
        entry["style"] = meta["style"]
    if meta.get("story"):
        entry["story"] = meta["story"]
    if a.tiktok:
        entry["tiktok_id"] = a.tiktok
    data["published"].append(entry)
    print("Recorded", meta["kind"], meta["words"])
json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
