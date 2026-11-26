"""Backup scene for a word that has no illustration of its own (for example, when the
auto-generated drawing for a new word failed its checks). Uses the word's own colors, so it
still matches the rest of the Short: a soft sky, a low sun, rolling hills and drifting light."""
import json, math, os, random
from PIL import ImageDraw
from engine.common import vgrad, glow

S = 1600
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class GenericScene:
    # No WORD attribute on purpose: get_art() uses this only when a word has no scene.

    def __init__(self, word):
        try:
            with open(os.path.join(ROOT, "words", f"{word}.json"), encoding="utf-8") as f:
                wd = json.load(f)
            bg, acc = tuple(wd["bg"]), tuple(wd["accent"])
        except (OSError, KeyError, ValueError):
            bg, acc = (240, 226, 210), (120, 96, 150)
        rnd = random.Random(sum(map(ord, word)))
        light = _mix(bg, (255, 255, 255), 0.35)
        deep = _mix(acc, (30, 28, 40), 0.35)
        img = vgrad(S, S, [(0, _mix(acc, light, 0.55)), (0.55, light), (1, _mix(bg, acc, 0.25))])
        self.sun = (rnd.uniform(380, 1220), rnd.uniform(380, 560))
        img = glow(img, self.sun, 260, _mix(light, (255, 240, 200), 0.6), 0.75)
        d = ImageDraw.Draw(img, "RGBA")
        sx, sy = self.sun
        d.ellipse([sx - 110, sy - 110, sx + 110, sy + 110], fill=_mix(light, (255, 246, 222), 0.7))
        for k, (base, amp, col) in enumerate([(980, 90, _mix(acc, light, 0.45)),
                                              (1140, 70, _mix(acc, deep, 0.2)),
                                              (1320, 60, deep)]):
            ph, fr = rnd.uniform(0, 6), rnd.uniform(1.2, 2.2)
            pts = [(x, base - amp * math.sin(x / S * math.pi * fr + ph)) for x in range(0, S + 1, 40)]
            d.polygon([(0, S)] + pts + [(S, S)], fill=col)
        self.base = img
        self.dots = [(rnd.uniform(0, S), rnd.uniform(150, 900), rnd.uniform(8, 26), rnd.uniform(0, 6))
                     for _ in range(28)]
        self.light = light

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, r, ph in self.dots:
            xx = (x + 14 * t) % (S + 80) - 40
            yy = y + 18 * math.sin(t * 0.7 + ph)
            a = int(70 + 60 * math.sin(t * 1.1 + ph))
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=self.light + (a,))
        return img
