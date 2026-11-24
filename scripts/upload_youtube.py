"""Upload out/meta.json's video to YouTube as private, scheduled to go public at --publish-at.

Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Usage: python scripts/upload_youtube.py out/meta.json --publish-at 2026-11-25T18:00:00+07:00
       (omit --publish-at to keep the video private)
"""
import argparse, json, os, sys, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("--publish-at", help="ISO 8601 time with timezone")
    a = ap.parse_args()
    meta = json.load(open(a.meta, encoding="utf-8"))
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    if a.publish_at:
        status["publishAt"] = a.publish_at
    body = {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": status}
    media = MediaFileUpload(meta["video"], mimetype="video/mp4", chunksize=4 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, tries = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 5:
                tries += 1; time.sleep(2 ** tries); continue
            raise
    vid = resp["id"]
    print(f"YouTube upload OK: https://youtu.be/{vid} (status: {resp['status'].get('privacyStatus')}, "
          f"publishAt: {resp['status'].get('publishAt')})")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"youtube_id={vid}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        print(f"Missing secret {e}. See SETUP.md.", file=sys.stderr); sys.exit(1)
