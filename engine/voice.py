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

def short_track(W):
    """Narration for one Short. W is a word dict from words/<word>.json."""
    tr = Track(0.5)
    tr.add("hook", say("Today's word:"), 0.25)
    tr.add("word", say(W["ph"], ph=True), 0.8)
    tr.add("listen", say("Listen."), 0.4)
    for j, s in enumerate(W["syl"]):
        tr.add(f"syl{j}", say(s, speed=SLOW, ph=True), 0.45)
    tr.gap(0.15)
    tr.add("word", say(W["ph"], speed=SLOW, ph=True), 0.55)
    tr.add("word", say(W["ph"], ph=True), 0.8)
    tr.add("note", say(W["note_say"]), 0.8)
    tr.add("turn_say", say("Your turn."), 0.3)
    st = tr.t
    tr.gap(2.2)
    tr.marks["turn"] = [[round(st, 3), round(tr.t, 3)]]
    tr.add("word", say(W["ph"], ph=True), 0.9)
    tr.add("meaning", say("It means: " + W["mean_say"]), 0.7)
    tr.add("example", say("For example: " + W["ex_say"]), 0.8)
    tr.add("follow", say("Follow for a new word every day!"), 0.0)
    audio, dur = tr.render(1.5)
    return audio, dur, tr.marks
