"""Post out/meta.json's video to a Facebook Page.
Shorts (word/quiz) go up as Reels; the weekly long video goes up as a normal video post.

Needs env: FB_PAGE_ID, FB_PAGE_TOKEN (a Page access token)
Usage: python scripts/upload_facebook.py out/meta.json [--publish-at 2026-11-25T18:00:00+07:00]
       Without --publish-at it is published right away.
"""
import argparse, json, os, sys, time
from datetime import datetime
import requests

V = "v25.0"
API = f"https://graph.facebook.com/{V}"

def schedule_ts(publish_at):
    if not publish_at:
        return None
    ts = int(datetime.fromisoformat(publish_at).timestamp())
    return ts if ts - time.time() > 15 * 60 else None   # Facebook needs at least 10 min ahead

def post_reel(meta, page, token, ts):
    r = requests.post(f"{API}/{page}/video_reels", data={"upload_phase": "start", "access_token": token}, timeout=60)
    r.raise_for_status()
    video_id = r.json()["video_id"]
    size = os.path.getsize(meta["video"])
    with open(meta["video"], "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/video-upload/{V}/{video_id}",
                          headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
                          data=f, timeout=600)
    r.raise_for_status()
    data = {"upload_phase": "finish", "video_id": video_id, "access_token": token,
            "description": meta["facebook_description"]}
    if ts:
        data.update({"video_state": "SCHEDULED", "scheduled_publish_time": str(ts)})
    else:
        data["video_state"] = "PUBLISHED"
    data["is_ai_generated"] = "true"   # Meta requires an AI label for reels with a realistic AI voiceover
    r = requests.post(f"{API}/{page}/video_reels", data=data, timeout=120)
    if not r.ok and "is_ai_generated" in r.text:
        print("::warning::Facebook did not accept is_ai_generated for this Reel - add the AI label in Meta Business Suite", file=sys.stderr)
        data.pop("is_ai_generated")
        r = requests.post(f"{API}/{page}/video_reels", data=data, timeout=120)
    if not r.ok:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    return video_id, data["video_state"]

def post_video(meta, page, token, ts):
    data = {"access_token": token, "title": meta.get("facebook_title", ""), "description": meta["facebook_description"],
            "is_ai_generated": "true"}
    if ts:
        data.update({"published": "false", "scheduled_publish_time": str(ts)})
    def send():
        with open(meta["video"], "rb") as f:
            return requests.post(f"https://graph-video.facebook.com/{V}/{page}/videos", data=data,
                                 files={"source": ("video.mp4", f, "video/mp4")}, timeout=1800)
    r = send()
    if not r.ok and "is_ai_generated" in r.text:
        print("::warning::Facebook did not accept is_ai_generated for this video - add the AI label in Meta Business Suite", file=sys.stderr)
        data.pop("is_ai_generated")
        r = send()
    if not r.ok:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    return r.json()["id"], "SCHEDULED" if ts else "PUBLISHED"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("--publish-at")
    a = ap.parse_args()
    meta = json.load(open(a.meta, encoding="utf-8"))
    page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
    ts = schedule_ts(a.publish_at)
    if meta["kind"] == "long":
        vid, state = post_video(meta, page, token, ts)
    else:
        vid, state = post_reel(meta, page, token, ts)
    print(f"Facebook OK ({'video' if meta['kind'] == 'long' else 'reel'}): {vid} ({state})")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"facebook_id={vid}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        print(f"Missing secret {e}. See SETUP.md.", file=sys.stderr); sys.exit(1)
