"""One place for every title, description and caption, so all posts look the same.

Every post follows the same shape:
  Title:   <what> – <hook> | Daily English [#shorts]
  Body:    header line · Vietnamese line · details · call to action · schedule line · hashtags
YouTube gets title + body (+ #shorts for Shorts). Facebook/Instagram get the body as the caption.
"""

BRAND = "Daily English"
CTA = "🔁 Listen, repeat out loud, and write your own sentence in the comments!"
SCHEDULE = "📅 New word every day at 6 PM, review at 12 PM · Từ mới lúc 18:00, ôn tập lúc 12:00"
HASHTAGS = "#DailyEnglish #LearnEnglish #EnglishVocabulary #EnglishPronunciation #HocTiengAnh #TuVungTiengAnh"
TAGS = ["daily english", "learn english", "english vocabulary", "english pronunciation",
        "học tiếng anh", "từ vựng tiếng anh", "phát âm tiếng anh"]

def _vi_short(wd):
    return wd["vi"].split(",")[0].strip()

def _sounds_like(wd):
    return "".join(s for s, _ in wd["like"])

def _fit(title, limit=100):
    return title if len(title) <= limit else title[:limit - 1].rstrip() + "…"

def _body(lines, shorts):
    tags = HASHTAGS + (" #shorts" if shorts else "")
    return "\n".join(lines + ["", CTA, SCHEDULE, "", tags])

def word_meta(wd):
    w = wd["word"]
    lines = [f"📖 Word of the Day: {w} {wd['ipa']} ({wd['pos']})",
             f"🇻🇳 {wd['vi']}",
             f"💡 Meaning: {wd['meaning']}",
             f"✏️ Example: {wd['example']}",
             f"🗣️ Sounds like: {_sounds_like(wd)}"]
    return {"title": _fit(f"{w} ({_vi_short(wd)}) – How to Pronounce | {BRAND} #shorts"),
            "description": _body(lines, shorts=True),
            "facebook_description": _body(lines, shorts=False),
            "tags": TAGS + [w, f"how to pronounce {w}", f"{w} meaning", f"{w} nghĩa là gì"]}

def quiz_meta(words):
    names = [w["word"] for w in words]
    lines = ["🧠 Weekly Quiz: Can you get 3/3?",
             "🇻🇳 Kiểm tra từ vựng tuần này – bạn được mấy điểm?",
             f"📝 This week's words: {' · '.join(names)}",
             "💬 Comment your score: 0, 1, 2 or 3!"]
    return {"title": _fit(f"Quiz: {', '.join(names[:3])}… – Can You Get 3/3? | {BRAND} #shorts"),
            "description": _body(lines, shorts=True),
            "facebook_description": _body(lines, shorts=False),
            "tags": TAGS + ["english quiz", "vocabulary quiz"] + names}

def long_meta(words, chapters):
    names = [w["word"] for w in words]
    n = len(words)
    chap = [f"{int(s // 60)}:{int(s % 60):02d} {label}" for s, label in chapters]
    lines = [f"📚 Weekly Review: {n} English words with pronunciation, meaning and examples",
             f"🇻🇳 Ôn tập {n} từ vựng tiếng Anh tuần này: phát âm, nghĩa và ví dụ",
             ""] + [f"• {w['word']} {w['ipa']} – {w['vi']}" for w in words] + ["", "⏱️ Chapters"] + chap
    return {"title": _fit(f"{n} English Words – {', '.join(names)} | {BRAND} Weekly"),
            "description": _body(lines, shorts=False),
            "facebook_title": f"{n} English Words – {BRAND} Weekly",
            "facebook_description": _body(lines, shorts=False),
            "tags": TAGS + names}

def review_meta(style, words):
    """style: 'recall' (do you remember?) or 'quiz' (A/B/C). Posted at 12:00."""
    names = [w["word"] for w in words]
    if style == "recall":
        lines = ["🧠 Daily Review: Do you still remember these words?",
                 "🇻🇳 Ôn tập: bạn còn nhớ nghĩa của những từ này không?", ""] + \
                [f"• {w['word']} {w['ipa']}" for w in words] + \
                ["", "💬 Comment how many you remembered: 0, 1, 2 or 3!"]
        title = f"Do You Remember? {', '.join(names)} – Daily Review | {BRAND} #shorts"
    else:
        lines = ["🧠 Quick Quiz: Can you get 3/3?",
                 "🇻🇳 Ôn tập từ vựng – bạn được mấy điểm?",
                 f"📝 Words: {' · '.join(sorted(names))}",
                 "💬 Comment your score: 0, 1, 2 or 3!"]
        title = f"Quick English Quiz – Can You Get 3/3? | {BRAND} #shorts"
    return {"title": _fit(title),
            "description": _body(lines, shorts=True),
            "facebook_description": _body(lines, shorts=False),
            "tags": TAGS + ["english review", "english quiz", "vocabulary quiz"] + names}
