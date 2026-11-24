"""Pick the next word in the queue (or --word X), render its Short, and write out/meta.json.

Usage:  python scripts/make_short.py [--word cozy] [--out out]
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.short import render_short

EMOJI = {"serene": "🌅", "cozy": "☕", "breeze": "🍃", "drowsy": "🌙", "unwind": "🌴",
         "stroll": "🌳", "sip": "☕", "doze": "😴", "soothing": "🪷", "linger": "🌇"}

def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)

def next_word():
    queue = load("words/queue.json")["queue"]
    done = {p["word"] for p in load("state/published.json")["published"]}
    for w in queue:
        if w not in done:
            return w
    return None

def metadata(wd):
    w = wd["word"]
    title = f"{w} – how to pronounce it {EMOJI.get(w, '✨')} #shorts #learnenglish"
    desc = (f"{w} {wd['ipa']} ({wd['pos']}) – {wd['vi']}\n\n"
            f"Meaning: {wd['meaning']}\n"
            f"Example: {wd['example']}\n\n"
            f"Listen, repeat out loud, and comment your own sentence! 👇\n"
            f"Học từ vựng tiếng Anh mỗi ngày.\n\n"
            f"#LearnEnglish #EnglishVocabulary #EnglishPronunciation #HocTiengAnh #TuVungTiengAnh #shorts")
    tags = ["learn english", "english vocabulary", "english pronunciation", w, f"how to pronounce {w}",
            "học tiếng anh", "từ vựng tiếng anh", "phát âm tiếng anh"]
    fb = (f"{w} {wd['ipa']} – {wd['vi']} {EMOJI.get(w, '✨')}\n"
          f"{wd['meaning']}\n\"{wd['example']}\"\n\n"
          f"Listen and repeat! Comment your own sentence 👇\n"
          f"#LearnEnglish #HocTiengAnh #TuVungTiengAnh")
    return {"word": w, "title": title[:100], "description": desc, "tags": tags, "facebook_description": fb}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word")
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    a = ap.parse_args()
    word = a.word or next_word()
    if not word:
        print("Queue is empty: add words to words/queue.json", file=sys.stderr)
        sys.exit(2)
    os.makedirs(a.out, exist_ok=True)
    wd = load(f"words/{word}.json")
    video = os.path.join(a.out, f"{word}.mp4")
    seed = sum(map(ord, word))
    dur = render_short(wd, video, music_seed=seed, preview_png=os.path.join(a.out, f"{word}.png"))
    meta = metadata(wd)
    meta.update({"video": video, "duration": dur})
    with open(os.path.join(a.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"Rendered {word}: {dur:.1f}s -> {video}")

if __name__ == "__main__":
    main()
