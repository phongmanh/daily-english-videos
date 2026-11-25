"""Instagram Reels via the Instagram Content Publishing API (Facebook Login / Page token).

Instagram's API can't schedule posts, so this works in two steps:
  prepare  (night runs): upload the video into a media container, add it to
           state/pending_instagram.json. If the publish time is already close, publish right away.
  publish  (11:47 and 17:47 runs): publish every saved container that is due within 30 minutes
           and record it in state/published.json.

Needs env: FB_PAGE_ID, FB_PAGE_TOKEN (Page token with instagram_basic + instagram_content_publish).
Optional env: IG_AI_LABEL=true|false (default true) – adds Instagram's "AI info" label.

Usage:
  python scripts/instagram.py prepare out/meta.json --publish-at 2026-11-25T18:00:00+07:00
  python scripts/instagram.py publish
"""
import argparse, json, os, sys, time
from datetime import datetime
import requests

V = "v25.0"
API = f"https://graph.facebook.com/{V}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "state", "pending_instagram.json")
PUBLISHED = os.path.join(ROOT, "state", "published.json")

def token():
    return os.environ["FB_PAGE_TOKEN"]

def check(r):
    if not r.ok:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    return r.json()

def ig_user_id():
    r = requests.get(f"{API}/{os.environ['FB_PAGE_ID']}",
                     params={"fields": "instagram_business_account", "access_token": token()}, timeout=30)
    data = check(r)
    acc = data.get("instagram_business_account")
    if not acc:
        sys.exit("No Instagram account is linked to this Facebook Page (or the token lacks instagram_basic). See SETUP.md.")
    return acc["id"]

def create_container(ig, caption):
    data = {"media_type": "REELS", "upload_type": "resumable", "caption": caption,
            "share_to_feed": "true", "access_token": token()}
    if os.environ.get("IG_AI_LABEL", "true").lower() == "true":
        data["is_ai_generated"] = "true"
    r = requests.post(f"{API}/{ig}/media", data=data, timeout=60)
    if not r.ok and "is_ai_generated" in data and "is_ai_generated" in r.text:
        print("::warning::is_ai_generated not accepted; creating the container without it", file=sys.stderr)
        data.pop("is_ai_generated")
        r = requests.post(f"{API}/{ig}/media", data=data, timeout=60)
    return check(r)["id"]

def upload(container, path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/ig-api-upload/{V}/{container}",
                          headers={"Authorization": f"OAuth {token()}", "offset": "0", "file_size": str(size)},
                          data=f, timeout=900)
    check(r)

def wait_ready(container, max_wait=900):
    t0 = time.time()
    while True:
        r = requests.get(f"{API}/{container}", params={"fields": "status_code,status", "access_token": token()}, timeout=30)
        d = check(r)
        code = d.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram container {code}: {d.get('status')}")
        if time.time() - t0 > max_wait:
            sys.exit(f"Instagram container still {code} after {max_wait}s")
        time.sleep(15)

def publish_container(ig, container):
    wait_ready(container)
    r = requests.post(f"{API}/{ig}/media_publish", data={"creation_id": container, "access_token": token()}, timeout=60)
    return check(r)["id"]

def load_pending():
    if not os.path.exists(PENDING):
        return []
    p = json.load(open(PENDING, encoding="utf-8"))
    return p if isinstance(p, list) else [p]

def save_pending(items):
    if items:
        json.dump(items, open(PENDING, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif os.path.exists(PENDING):
        os.remove(PENDING)

def record(meta_kind, words, media_id, publish_at=None):
    data = json.load(open(PUBLISHED, encoding="utf-8"))
    for e in reversed(data["published"]):
        if meta_kind == "word":
            same = e.get("word") == words[0]
        elif meta_kind == "review":
            same = e.get("words") == words and e.get("publish_at") == publish_at
        else:
            same = e.get("words") == words
        if e.get("kind", "word") == meta_kind and same:
            e["instagram_id"] = media_id
            break
    json.dump(data, open(PUBLISHED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def write_output(key, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"{key}={value}\n")

def cmd_prepare(a):
    meta = json.load(open(a.meta, encoding="utf-8"))
    ig = ig_user_id()
    container = create_container(ig, meta["facebook_description"])
    upload(container, meta["video"])
    print(f"Instagram: video uploaded to container {container}")
    due = a.publish_at and datetime.fromisoformat(a.publish_at).timestamp() - time.time() < 30 * 60
    if not a.publish_at or due:
        media = publish_container(ig, container)
        print(f"Instagram Reel published now: {media}")
        write_output("instagram_id", media)
        write_output("instagram_pending", "")
        return
    items = load_pending()
    items.append({"ig_user_id": ig, "container": container, "kind": meta["kind"], "words": meta["words"],
                  "publish_at": a.publish_at, "created": int(time.time())})
    save_pending(items)
    print(f"Instagram: will publish at {a.publish_at} (Publish Instagram run)")
    write_output("instagram_pending", container)

def cmd_publish(a):
    items = load_pending()
    if not items:
        print("Nothing waiting for Instagram.")
        return
    keep, done, errors = [], [], []
    for p in items:
        if time.time() - p["created"] > 23 * 3600:
            errors.append(f"{p['kind']} {'-'.join(p['words'])}: older than 23 hours (Instagram expires it); re-run with platforms=instagram")
            continue
        due = not p.get("publish_at") or datetime.fromisoformat(p["publish_at"]).timestamp() - time.time() < 30 * 60
        if not due:
            keep.append(p)
            continue
        try:
            media = publish_container(p["ig_user_id"], p["container"])
        except (SystemExit, requests.HTTPError) as e:
            errors.append(f"{p['kind']} {'-'.join(p['words'])}: {e}")
            continue
        record(p["kind"], p["words"], media, p.get("publish_at"))
        done.append("-".join(p["words"]))
        print(f"Instagram Reel published: {media} ({p['kind']}: {', '.join(p['words'])})")
        write_output("instagram_id", media)
    save_pending(keep)
    write_output("label", " + ".join(done) or "nothing due")
    if keep:
        print(f"Still waiting: {len(keep)} (later run)")
    if errors:
        sys.exit("Instagram problems:\n" + "\n".join(errors))

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare"); pr.add_argument("meta"); pr.add_argument("--publish-at")
    sub.add_parser("publish")
    a = ap.parse_args()
    try:
        cmd_prepare(a) if a.cmd == "prepare" else cmd_publish(a)
    except KeyError as e:
        sys.exit(f"Missing secret {e}. See SETUP.md.")

if __name__ == "__main__":
    main()
