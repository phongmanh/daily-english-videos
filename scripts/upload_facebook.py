"""Publish out/meta.json's video as a Reel on a Facebook Page (Reels Publishing API).

Needs env: FB_PAGE_ID, FB_PAGE_TOKEN (a Page access token)
Usage: python scripts/upload_facebook.py out/meta.json [--publish-at 2026-11-25T18:00:00+07:00]
       Without --publish-at the Reel is published right away.
"""
import argparse, json, os, sys, time
from datetime import datetime
import requests

API = "https://graph.facebook.com/v25.0"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("--publish-at")
    a = ap.parse_args()
    meta = json.load(open(a.meta, encoding="utf-8"))
    page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]

    r = requests.post(f"{API}/{page}/video_reels", data={"upload_phase": "start", "access_token": token}, timeout=60)
    r.raise_for_status()
    video_id = r.json()["video_id"]

    size = os.path.getsize(meta["video"])
    with open(meta["video"], "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/video-upload/v25.0/{video_id}",
                          headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
                          data=f, timeout=600)
    r.raise_for_status()

    data = {"upload_phase": "finish", "video_id": video_id, "access_token": token,
            "description": meta["facebook_description"]}
    if a.publish_at:
        ts = int(datetime.fromisoformat(a.publish_at).timestamp())
        if ts - time.time() > 15 * 60:
            data.update({"video_state": "SCHEDULED", "scheduled_publish_time": str(ts)})
        else:
            data["video_state"] = "PUBLISHED"
    else:
        data["video_state"] = "PUBLISHED"
    r = requests.post(f"{API}/{page}/video_reels", data=data, timeout=120)
    if not r.ok:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    print(f"Facebook Reel OK: video {video_id} ({data['video_state']})")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"facebook_id={video_id}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        print(f"Missing secret {e}. See SETUP.md.", file=sys.stderr); sys.exit(1)
