"""TikTok: send each video to your TikTok inbox as a draft (Content Posting API, "Upload").

TikTok only lets apps post publicly after a full review, so we use the lighter "upload a draft"
permission (video.upload): the video lands in your TikTok app as a notification, you open it,
paste the caption and tap Post. Captions for the latest videos are on
https://phongmanh.github.io/daily-english-videos/tiktok.html (copy buttons).

  python scripts/tiktok.py send out/meta.json

Secrets: TT_CLIENT_KEY, TT_CLIENT_SECRET, TT_REFRESH_TOKEN (from scripts/get_tiktok_token.py),
TT_TOKEN_KEY (also printed by that script). TikTok may give a new refresh token each time we
refresh; it is saved encrypted (with TT_TOKEN_KEY) in state/tiktok_token.enc so the next run uses it.
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://open.tiktokapis.com/v2"
TOKEN_FILE = os.path.join(ROOT, "state", "tiktok_token.enc")
CAPTIONS = os.path.join(ROOT, "docs", "tiktok.json")
HASHTAGS = "#learnenglish #englishvocabulary #tienganh #hoctienganh #dailyenglish"


def write_output(key, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"{key}={value}\n")


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(os.environ["TT_TOKEN_KEY"].encode())


def load_refresh_token():
    if os.path.exists(TOKEN_FILE) and os.environ.get("TT_TOKEN_KEY"):
        try:
            return _fernet().decrypt(open(TOKEN_FILE, "rb").read()).decode()
        except Exception as e:
            print(f"::warning::Could not read state/tiktok_token.enc ({e}); using TT_REFRESH_TOKEN")
    return os.environ["TT_REFRESH_TOKEN"]


def access_token():
    r = requests.post(f"{API}/oauth/token/", timeout=60, data={
        "client_key": os.environ["TT_CLIENT_KEY"], "client_secret": os.environ["TT_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": load_refresh_token()})
    d = r.json()
    if "access_token" not in d:
        sys.exit(f"TikTok login failed: {d}. Run scripts/get_tiktok_token.py again and update TT_REFRESH_TOKEN.")
    if d.get("refresh_token") and os.environ.get("TT_TOKEN_KEY"):
        open(TOKEN_FILE, "wb").write(_fernet().encrypt(d["refresh_token"].encode()))
    return d["access_token"]


def api(token, path, body):
    r = requests.post(f"{API}{path}", json=body, timeout=60,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    d = r.json()
    err = d.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(f"{err.get('code')}: {err.get('message')}")
    return d["data"]


def caption(meta):
    """TikTok drafts have no caption field, so we keep a ready-to-paste caption on the website."""
    lines = [l for l in meta.get("facebook_description", "").splitlines() if not l.startswith("#")]
    text = "\n".join(lines).strip()
    return (text[:2000] + "\n\n" + HASHTAGS).strip()


def save_caption(meta, publish_at):
    items = json.load(open(CAPTIONS, encoding="utf-8")) if os.path.exists(CAPTIONS) else []
    items.insert(0, {"made": datetime.now(timezone.utc).isoformat(timespec="minutes"), "publish_at": publish_at,
                     "kind": meta["kind"], "style": meta.get("style", ""), "words": meta["words"],
                     "title": meta.get("title", "").replace(" #shorts", ""), "caption": caption(meta)})
    json.dump(items[:14], open(CAPTIONS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cmd_send(a):
    meta = json.load(open(a.meta, encoding="utf-8"))
    path, size = meta["video"], os.path.getsize(meta["video"])
    token = access_token()
    try:
        # one chunk up to 64 MB (all our videos are far smaller)
        d = api(token, "/post/publish/inbox/video/init/",
                {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}})
    except RuntimeError as e:
        if "spam_risk_too_many_pending_share" in str(e):
            msg = "TikTok skipped: 5 drafts are already waiting in your TikTok inbox. Post or delete them in the app."
            print(f"::warning::{msg}"); write_output("tiktok_skipped", msg); return
        raise
    with open(path, "rb") as f:
        r = requests.put(d["upload_url"], data=f, timeout=900, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": f"bytes 0-{size - 1}/{size}"})
    if r.status_code not in (200, 201):
        sys.exit(f"TikTok upload failed: {r.status_code} {r.text[:300]}")
    pid = d["publish_id"]
    status = "?"
    for _ in range(40):                               # wait up to ~3 min for TikTok to process it
        time.sleep(5)
        s = api(token, "/post/publish/status/fetch/", {"publish_id": pid})
        status = s.get("status", "?")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if status == "FAILED":
            sys.exit(f"TikTok processing failed: {s.get('fail_reason')}")
    print(f"TikTok: {status} ({pid})")
    save_caption(meta, a.publish_at)
    write_output("tiktok_id", pid)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send"); s.add_argument("meta"); s.add_argument("--publish-at", default="")
    a = ap.parse_args()
    {"send": cmd_send}[a.cmd](a)
