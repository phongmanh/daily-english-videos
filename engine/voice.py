"""Narration with Kokoro (open-source TTS, Apache-2.0). Returns audio + timing marks."""
import os
import numpy as np

MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))
VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
SPEED, SLOW = 0.88, 0.68
SR = 24000
_k = None

def _model():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(os.path.join(MODEL_DIR, "kokoro.onnx"), os.path.join(MODEL_DIR, "voices.bin"))
    return _k

def say(text, speed=SPEED, ph=False):
    a, sr = _model().create(text, voice=VOICE, speed=speed, lang="en-us", is_phonemes=ph)
    assert sr == SR
    return a.astype(np.float32)

class Track:
    def __init__(self, lead):
        self.t = lead; self.parts = []; self.marks = {}
    def add(self, key, a, gap_after=0.0):
        st = self.t
        self.parts.append((st, a))
        self.t += len(a) / SR
        if key:
            self.marks.setdefault(key, []).append([round(st, 3), round(self.t, 3)])
        self.t += gap_after
    def gap(self, s):
        self.t += s
    def render(self, tail):
        dur = round(self.t + tail, 3)
        buf = np.zeros(int(dur * SR) + 10, np.float32)
        for st, a in self.parts:
            i = int(st * SR); buf[i:i + len(a)] += a
        return buf, dur

# Several ways to say each fixed line, so Shorts don't repeat word for word (picked per word).
LINES = {
    "hook": ["Today's word:", "Here's a new word:", "Let's learn this word:", "Word of the day:", "Today, let's say:"],
    "listen": ["Listen.", "Listen carefully.", "Let's break it down.", "Slowly now.", "Listen closely."],
    "vn": ["A tip for Vietnamese speakers.", "Watch out for this.", "A common mistake.", "Be careful here."],
    "turn": ["Your turn.", "Now you try.", "Say it with me.", "Now you.", "Try it out loud."],
    "meaning": ["It means:", "This word means:", "Here's the meaning:", "In simple words:"],
    "example": ["For example:", "Like this:", "You can say:", "Here's an example:"],
    "follow": ["Follow for a new word every day!", "See you tomorrow with a new word!",
               "Follow for one new word every day!", "Come back tomorrow for another word!"],
}

def pick(key, seed):
    opts = LINES[key]
    return opts[(seed + 7 * list(LINES).index(key)) % len(opts)]

def short_track(W):
    """Narration for one Short. W is a word dict from words/<word>.json."""
    seed = sum(map(ord, W["word"]))
    tr = Track(0.5)
    tr.add("hook", say(pick("hook", seed)), 0.25)
    tr.add("word", say(W["ph"], ph=True), 0.8)
    tr.add("listen", say(pick("listen", seed)), 0.4)
    for j, s in enumerate(W["syl"]):
        tr.add(f"syl{j}", say(s, speed=SLOW, ph=True), 0.45)
    tr.gap(0.15)
    tr.add("word", say(W["ph"], speed=SLOW, ph=True), 0.55)
    tr.add("word", say(W["ph"], ph=True), 0.8)
    tr.add("note", say(W["note_say"]), 0.8)
    if W.get("vn_tip_say"):
        tr.add("vntip", say(pick("vn", seed) + " " + W["vn_tip_say"]), 0.8)
    tr.add("turn_say", say(pick("turn", seed)), 0.3)
    st = tr.t
    tr.gap(2.2)
    tr.marks["turn"] = [[round(st, 3), round(tr.t, 3)]]
    tr.add("word", say(W["ph"], ph=True), 0.9)
    tr.add("meaning", say(pick("meaning", seed) + " " + W["mean_say"]), 0.7)
    tr.add("example", say(pick("example", seed) + " " + W["ex_say"]), 0.8)
    tr.add("follow", say(pick("follow", seed)), 0.0)
    audio, dur = tr.render(1.5)
    return audio, dur, tr.marks

NUM = ["one", "two", "three", "four", "five"]

def quiz_track(questions):
    """questions: list of {"answer": word dict, "options": [word dicts], "correct": index}.
    Kept under 40 s (Instagram refuses longer Reels): the options are shown, not read out."""
    tr = Track(0.4)
    tr.add("intro", say("Quiz time!"), 0.4)
    for qi, q in enumerate(questions):
        tr.add(f"q{qi}", say(f"{NUM[qi].capitalize()}. Which word means: {q['answer']['mean_say']}"), 0.1)
        for oi in range(len(q["options"])):          # options pop in one after another (no speech)
            tr.marks[f"q{qi}_l{oi}"] = [[round(tr.t + 0.2 * oi, 3), round(tr.t + 0.2 * oi, 3)]]
        st = tr.t
        tr.gap(3.0)
        tr.marks[f"q{qi}_count"] = [[round(st, 3), round(tr.t, 3)]]
        tr.marks[f"q{qi}_ans"] = [[round(tr.t, 3), round(tr.t, 3)]]
        tr.add(f"q{qi}_word", say(q["answer"]["ph"], ph=True), 0.7)
    tr.add("outro", say("How many did you get?"), 0.0)
    audio, dur = tr.render(1.4)
    return audio, dur, tr.marks

def recall_track(words):
    """Review Short: show a word we already learned, the viewer recalls the meaning, then reveal.
    Use 2 words to stay under 40 s (Instagram refuses longer Reels)."""
    tr = Track(0.4)
    tr.add("intro", say("Do you still remember these words?"), 0.4)
    for i, W in enumerate(words):
        tr.marks[f"w{i}"] = [[round(tr.t, 3), round(tr.t, 3)]]
        tr.add(f"w{i}_word", say(W["ph"], ph=True), 0.3)
        tr.add(f"w{i}_ask", say("What does it mean?"), 0.1)
        st = tr.t
        tr.gap(3.0)
        tr.marks[f"w{i}_count"] = [[round(st, 3), round(tr.t, 3)]]
        tr.add(f"w{i}_mean", say("It means: " + W["mean_say"]), 0.35)
        tr.add(f"w{i}_ex", say(W["ex_say"]), 0.35)
        tr.add(f"w{i}_rep2", say(W["ph"], ph=True), 0.8)
    tr.add("outro", say("How many did you remember?"), 0.0)
    audio, dur = tr.render(1.4)
    return audio, dur, tr.marks

def long_tracks(words, intro="Here are this week's five words. Listen, and repeat after me."):
    """Returns {scene name: (audio, dur, marks)} for title, w0..wN, review, outro."""
    out = {}
    tr = Track(0.6)
    tr.add("intro", say("Relax, and learn English."), 0.75)
    tr.add("sub", say(intro), 0.0)
    out["title"] = (*tr.render(1.2), tr.marks)
    for i, W in enumerate(words):
        tr = Track(0.8)
        tr.add("label", say(f"Word {i + 1}."), 0.35)
        tr.add("word", say(W["ph"], ph=True), 0.9)
        tr.add("listen", say("Listen."), 0.45)
        for j, s in enumerate(W["syl"]):
            tr.add(f"syl{j}", say(s, speed=SLOW, ph=True), 0.5)
        tr.gap(0.2)
        tr.add("word", say(W["ph"], speed=SLOW, ph=True), 0.6)
        tr.add("word", say(W["ph"], ph=True), 0.9)
        tr.add("note", say(W["note_say"]), 0.9)
        tr.add("turn_say", say("Now you. Say it with me."), 0.4)
        tr.add("word", say(W["ph"], ph=True), 0.3)
        st = tr.t
        tr.gap(2.6)
        tr.marks["turn"] = [[round(st, 3), round(tr.t, 3)]]
        tr.add("word", say(W["ph"], ph=True), 1.2)
        art = "an" if W["pos"][0] in "aeiou" else "a"
        tr.add("pos", say(f"It's {art} {W['pos']}."), 0.75)
        tr.add("meaning", say("It means: " + W["mean_say"]), 0.75)
        tr.add("example", say("For example: " + W["ex_say"]), 0.75)
        tr.add("tip", say("Tip: " + W["tip_say"]), 0.0)
        out[f"w{i}"] = (*tr.render(1.6), tr.marks)
    tr = Track(0.5)
    tr.add("head", say("Let's review. Repeat each word after me."), 1.0)
    for i, W in enumerate(words):
        tr.add(f"r{i}", say(W["ph"], ph=True), 1.8)
    out["review"] = (*tr.render(0.4), tr.marks)
    tr = Track(0.5)
    tr.add("l1", say("Great job! Try using one of these words today."), 0.75)
    tr.add("l2", say("See you next time."), 0.0)
    out["outro"] = (*tr.render(2.0), tr.marks)
    return out
