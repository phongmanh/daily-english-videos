"""Decide what today's post is, render it, and write out/meta.json.

18:00 cycle (repeats): 5 x word Short  ->  long video (those 5 words)
12:00 review (every day, --kind review): 3 words already posted, alternating
      "Do you remember?" (recall) and an A/B/C quiz.

Usage:
  python scripts/make_video.py                 # automatic: next item in the cycle
  python scripts/make_video.py --kind word --word cozy
  python scripts/make_video.py --kind quiz --words stroll,sip,doze,soothing,linger
  python scripts/make_video.py --kind long --words stroll,sip,doze,soothing,linger
  python scripts/make_video.py --kind review                 # today's 12:00 review
  python scripts/make_video.py --kind story --story rainy-evening

Stories (stories/<name>.json, order in stories/queue.json) go out in the 12:00 slot on Sundays,
once every word in the story has already been posted. A story is recorded as a review post
with style "story", so the rest of the pipeline treats it like any other 12:00 post.
"""
import argparse, json, os, random, sys
from datetime import datetime, timedelta, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BATCH = 5
from scripts.captions import word_meta, quiz_meta, long_meta, review_meta, story_meta
VN = timezone(timedelta(hours=7))

def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)

def word(w):
    return load(f"words/{w}.json")

def plan():
    """Return ("word", "<w>") | ("long", [words]) | (None, reason). (The quiz now lives in the 12:00 review.)"""
    pub = load("state/published.json")["published"]
    last = max([i for i, e in enumerate(pub) if e.get("kind") in ("long", "batch_closed")] or [-1])
    since = pub[last + 1:]
    batch = [e["word"] for e in since if e.get("kind", "word") == "word"]
    posted = {e["word"] for e in pub if e.get("kind", "word") == "word" and "word" in e}
    queue = [w for w in load("words/queue.json")["queue"] if w not in posted]
    if len(batch) < BATCH:
        if queue:
            return "word", queue[0]
        if len(batch) >= 3:          # queue ran dry: still finish the cycle with what we have
            return "long", batch
        return None, "Queue is empty: add words to words/queue.json"
    return "long", batch[:BATCH]

def story(name):
    return load(f"stories/{name}.json")

def next_story(public_words):
    """First story in the queue that hasn't been posted and only uses words that are already public."""
    pub = load("state/published.json")["published"]
    done = {e.get("story") for e in pub if e.get("style") == "story"}
    for name in load("stories/queue.json")["queue"]:
        if name in done:
            continue
        if all(l["word"] in public_words for l in story(name)["lines"]):
            return name
    return None

def plan_review(day=None):
    """Sunday: the next ready story, if any. Otherwise pick 3 words that are already public,
    mostly recent ones. Even days: recall, odd days: quiz."""
    day = day or datetime.now(VN).date()
    now = datetime.now(VN)
    pub = load("state/published.json")["published"]
    seen = []
    for e in pub:
        if e.get("kind", "word") != "word" or "word" not in e:
            continue
        at = e.get("publish_at")
        if at and datetime.fromisoformat(at) > now:      # not public yet (e.g. today's 18:00 word)
            continue
        if e["word"] not in seen:
            seen.append(e["word"])
    if len(seen) < 3:
        return None, "Need at least 3 posted words for a review"
    if day.weekday() == 6:
        name = next_story(set(seen))
        if name:
            return "story", name
    pool = seen[-10:]
    rng = random.Random(day.toordinal())
    style = "recall" if day.toordinal() % 2 == 0 else "quiz"
    if style == "quiz":
        return style, rng.sample(pool, min(5, len(pool)))
    return style, rng.sample(pool, 2)   # 2 words keeps it under 40 s (Instagram limit)

def meta_word(wd):
    return {"kind": "word", "word": wd["word"], "words": [wd["word"]], **word_meta(wd)}

def meta_quiz(words, qs):
    return {"kind": "quiz", "words": [w["word"] for w in words], **quiz_meta(words),
            "answers": [q["answer"]["word"] for q in qs]}

def meta_long(words, chapters):
    return {"kind": "long", "words": [w["word"] for w in words], **long_meta(words, chapters)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["auto", "word", "quiz", "long", "review", "story"], default="auto")
    ap.add_argument("--style", choices=["recall", "quiz"], help="for --kind review (default: by date)")
    ap.add_argument("--story", help="for --kind story: stories/<name>.json (empty = next ready story)")
    ap.add_argument("--word")
    ap.add_argument("--words", help="comma-separated, for quiz/long")
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    kind, arg = a.kind, None
    if kind == "auto":
        if a.word:
            kind, arg = "word", a.word
        else:
            kind, arg = plan()
            if kind is None:
                print(arg, file=sys.stderr); sys.exit(2)
    elif kind == "word":
        arg = a.word or plan()[1]
    elif kind == "story":
        kind, style, arg = "review", "story", a.story
        if not arg:
            pub = load("state/published.json")["published"]
            arg = next_story({e["word"] for e in pub if e.get("kind", "word") == "word" and "word" in e})
            if not arg:
                print("No story ready: add one to stories/queue.json (all its words must be posted)", file=sys.stderr); sys.exit(2)
    elif kind == "review":
        style, arg = plan_review()
        if style is None:
            print(arg, file=sys.stderr); sys.exit(2)
        if a.style:
            style = a.style
            if not isinstance(arg, list):          # today was a story day, but a word review was asked for
                arg = plan_review(datetime.now(VN).date() - timedelta(days=1))[1]
        if a.words:
            arg = a.words.split(",")
    else:
        arg = a.words.split(",") if a.words else plan()[1]

    if kind == "review" and style == "story":
        from engine.story import render_story
        st = story(arg)
        words = [word(l["word"]) for l in st["lines"]]
        video = os.path.join(a.out, "story.mp4")
        dur, _ = render_story(st, words, video, music_seed=sum(map(ord, arg)),
                              preview_png=os.path.join(a.out, "story.png"))
        meta = {"kind": "review", "style": "story", "story": arg, "words": [w["word"] for w in words],
                **story_meta(st, words)}
    elif kind == "review":
        words = [word(w) for w in arg]
        seed = datetime.now(VN).date().toordinal()
        if style == "recall":
            from engine.recall import render_recall
            words = words[:2]
            video = os.path.join(a.out, "review.mp4")
            dur = render_recall(words, video, seed=seed, preview_png=os.path.join(a.out, "review.png"))
        else:
            from engine.quiz import render_quiz
            video = os.path.join(a.out, "review.mp4")
            dur, qs = render_quiz(words, video, seed=seed, preview_png=os.path.join(a.out, "review.png"))
            words = [q["answer"] for q in qs] + [w for w in words if w not in [q["answer"] for q in qs]]
        meta = {"kind": "review", "style": style, "words": [w["word"] for w in words], **review_meta(style, words)}
    elif kind == "word":
        from engine.short import render_short
        wd = word(arg)
        video = os.path.join(a.out, f"{arg}.mp4")
        dur = render_short(wd, video, music_seed=sum(map(ord, arg)), preview_png=os.path.join(a.out, f"{arg}.png"))
        meta = meta_word(wd)
    elif kind == "quiz":
        from engine.quiz import render_quiz
        words = [word(w) for w in arg]
        video = os.path.join(a.out, "quiz.mp4")
        seed = sum(map(ord, "".join(arg)))
        dur, qs = render_quiz(words, video, seed=seed, preview_png=os.path.join(a.out, "quiz.png"))
        meta = meta_quiz(words, qs)
    else:
        from engine.long import render_long
        words = [word(w) for w in arg]
        video = os.path.join(a.out, "weekly.mp4")
        dur, chapters = render_long(words, video, seed=len(arg) + sum(map(ord, arg[0])))
        meta = meta_long(words, chapters)
        from engine.thumbnail import make_long_thumbnail
        meta["thumbnail"] = make_long_thumbnail(words, os.path.join(a.out, "weekly_thumbnail.png"))
    meta.update({"video": video, "duration": round(dur, 2)})
    with open(os.path.join(a.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"Rendered {kind}: {meta['words']} ({dur:.1f}s) -> {video}")

if __name__ == "__main__":
    main()
