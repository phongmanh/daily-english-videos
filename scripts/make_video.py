"""Decide what today's post is, render it, and write out/meta.json.

Cycle (repeats): 5 x word Short  ->  quiz Short (those 5 words)  ->  long video (those 5 words)

Usage:
  python scripts/make_video.py                 # automatic: next item in the cycle
  python scripts/make_video.py --kind word --word cozy
  python scripts/make_video.py --kind quiz --words stroll,sip,doze,soothing,linger
  python scripts/make_video.py --kind long --words stroll,sip,doze,soothing,linger
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BATCH = 5
EMOJI = {"serene": "🌅", "cozy": "☕", "breeze": "🍃", "drowsy": "🌙", "unwind": "🌴",
         "stroll": "🌳", "sip": "☕", "doze": "😴", "soothing": "🪷", "linger": "🌇"}
TAGS = ["learn english", "english vocabulary", "english pronunciation", "học tiếng anh",
        "từ vựng tiếng anh", "phát âm tiếng anh"]
HASHTAGS = "#LearnEnglish #EnglishVocabulary #EnglishPronunciation #HocTiengAnh #TuVungTiengAnh"

def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)

def word(w):
    return load(f"words/{w}.json")

def plan():
    """Return ("word", "<w>") | ("quiz", [words]) | ("long", [words]) | (None, reason)."""
    pub = load("state/published.json")["published"]
    last = max([i for i, e in enumerate(pub) if e.get("kind") in ("long", "batch_closed")] or [-1])
    since = pub[last + 1:]
    batch = [e["word"] for e in since if e.get("kind", "word") == "word"]
    quiz_done = any(e.get("kind") == "quiz" for e in since)
    posted = {e["word"] for e in pub if e.get("kind", "word") == "word" and "word" in e}
    queue = [w for w in load("words/queue.json")["queue"] if w not in posted]
    if len(batch) < BATCH:
        if queue:
            return "word", queue[0]
        if len(batch) >= 3:          # queue ran dry: still finish the cycle with what we have
            return ("long", batch) if quiz_done else ("quiz", batch)
        return None, "Queue is empty: add words to words/queue.json"
    return ("long", batch[:BATCH]) if quiz_done else ("quiz", batch[:BATCH])

def meta_word(wd):
    w = wd["word"]; e = EMOJI.get(w, "✨")
    return {"kind": "word", "word": w, "words": [w],
            "title": f"{w} – how to pronounce it {e} #shorts #learnenglish"[:100],
            "description": f"{w} {wd['ipa']} ({wd['pos']}) – {wd['vi']}\n\nMeaning: {wd['meaning']}\n"
                           f"Example: {wd['example']}\n\nListen, repeat out loud, and comment your own sentence! 👇\n"
                           f"Học từ vựng tiếng Anh mỗi ngày.\n\n{HASHTAGS} #shorts",
            "tags": TAGS + [w, f"how to pronounce {w}"],
            "facebook_description": f"{w} {wd['ipa']} – {wd['vi']} {e}\n{wd['meaning']}\n\"{wd['example']}\"\n\n"
                                    f"Listen and repeat! Comment your own sentence 👇\n#LearnEnglish #HocTiengAnh #TuVungTiengAnh"}

def meta_quiz(words, qs):
    names = [w["word"] for w in words]
    return {"kind": "quiz", "words": names,
            "title": "English vocabulary quiz 🧠 Can you get 3/3? #shorts #learnenglish",
            "description": f"Quick quiz on this week's words: {', '.join(names)}.\n"
                           f"Comment your score! 👇\nKiểm tra từ vựng tuần này – bạn được mấy điểm?\n\n{HASHTAGS} #quiz #shorts",
            "tags": TAGS + ["english quiz", "vocabulary quiz"] + names,
            "facebook_description": f"Quiz time! 🧠 Can you get 3/3?\nThis week's words: {', '.join(names)}\n"
                                    f"Comment your score 👇\n#LearnEnglish #HocTiengAnh #EnglishQuiz",
            "answers": [q["answer"]["word"] for q in qs]}

def meta_long(words, chapters):
    names = [w["word"] for w in words]
    chap = "\n".join(f"{int(s // 60)}:{int(s % 60):02d} {label}" for s, label in chapters)
    return {"kind": "long", "words": names,
            "title": f"{len(words)} English Words This Week | {', '.join(names)}"[:100],
            "description": f"Learn this week's {len(words)} English words — with pronunciation, meaning, and examples.\n"
                           f"Học {len(words)} từ vựng tiếng Anh tuần này: phát âm, nghĩa và ví dụ.\n\n{chap}\n\n"
                           f"Listen, repeat out loud, and comment your own sentence below 👇\n\n{HASHTAGS}",
            "tags": TAGS + names,
            "facebook_title": f"{len(words)} English words this week",
            "facebook_description": f"This week's {len(words)} words 🌿 {', '.join(names)}\n"
                                    f"Pronunciation, meaning and examples. Listen and repeat!\n\n{chap}\n\n#LearnEnglish #HocTiengAnh"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["auto", "word", "quiz", "long"], default="auto")
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
    else:
        arg = a.words.split(",") if a.words else plan()[1]

    if kind == "word":
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
