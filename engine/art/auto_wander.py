"""Scene for: wander. A winding old-town lane at golden hour with a slow walker."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad

S = 1600
INK = (34, 32, 44)


class Wander:
    WORD = "wander"

    def __init__(self):
        random.seed(85)
        img = vgrad(S, S, [(0, (196, 170, 220)), (0.4, (250, 200, 170)), (0.6, (252, 226, 190)), (1, (252, 226, 190))])
        d = ImageDraw.Draw(img, "RGBA")
        for k in range(8):
            rr = 300 * (1 - k / 8)
            d.ellipse([800 - rr, 520 - rr, 800 + rr, 520 + rr], fill=(255, 226, 160) + (22,))
        d.ellipse([720, 440, 880, 600], fill=(255, 220, 150))
        # far roofs silhouette
        x = 0
        while x < 1600:
            w = random.uniform(80, 160)
            h = random.uniform(560, 680)
            d.rectangle([x, h, x + w, 900], fill=(200, 160, 180))
            d.polygon([(x - 6, h), (x + w / 2, h - 50), (x + w + 6, h)], fill=(180, 140, 164))
            x += w
        # lane: winding cobbled path
        def lane(s):
            return 800 + 120 * math.sin(s * 3.2 + 0.4) * (1 - s), 900 + 700 * s, 40 + 520 * s ** 1.4
        L, R = [], []
        for s in np.linspace(0, 1, 30):
            c, y, w = lane(s)
            L.append((c - w, y)); R.append((c + w, y))
        d.polygon(L + R[::-1], fill=(222, 196, 170))
        for s in np.linspace(0.05, 1, 16):
            c, y, w = lane(s)
            for k in range(-4, 5):
                cx = c + k * w / 4.5 + (s * 37 % 1) * 20
                r = 8 + 22 * s
                d.ellipse([cx - r, y - r * 0.45, cx + r, y + r * 0.45], outline=(196, 166, 140), width=3)
        self.lane = lane
        # houses on both sides, near ones bigger
        cols = [(232, 150, 120), (246, 210, 140), (150, 180, 196), (220, 170, 196), (180, 200, 150), (240, 190, 160)]
        for side in (-1, 1):
            for j, s in enumerate([0.12, 0.3, 0.55, 0.85]):
                c, y, w = lane(s)
                hw = 120 + 280 * s
                hh = 260 + 560 * s
                if side < 0:
                    x1 = c - w - 10; x0 = x1 - hw
                else:
                    x0 = c + w + 10; x1 = x0 + hw
                top = y - hh
                col = cols[(j * 2 + (side > 0)) % len(cols)]
                d.rectangle([x0, top, x1, y + 20], fill=col, outline=INK, width=6)
                d.polygon([(x0 - 20, top), ((x0 + x1) / 2, top - 70 - 90 * s), (x1 + 20, top)], fill=(170, 84, 70), outline=INK)
                ww = 24 + 50 * s
                for wx in np.linspace(x0 + hw * 0.25, x1 - hw * 0.25, 2):
                    for wy in (top + hh * 0.2, top + hh * 0.5):
                        d.rectangle([wx - ww / 2, wy, wx + ww / 2, wy + ww * 1.4], fill=(255, 230, 170), outline=INK, width=4)
                        d.rectangle([wx - ww / 2 - 6, wy + ww * 1.4, wx + ww / 2 + 6, wy + ww * 1.4 + 10], fill=(110, 160, 90))
                dx = x1 - hw * 0.3 if side < 0 else x0 + hw * 0.3
                d.rounded_rectangle([dx - ww * 0.55, y + 20 - ww * 2, dx + ww * 0.55, y + 20], 10, fill=(120, 80, 60), outline=INK, width=4)
        self.base = img
        # string of lanterns across the lane
        self.lan = []
        for s in np.linspace(0, 1, 9):
            x = 260 + s * 1080
            y = 300 + 120 * math.sin(math.pi * s)
            self.lan.append((x, y))
        self.birds = [(random.uniform(0, 1), random.uniform(120, 300), random.uniform(0, 6)) for _ in range(4)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        # birds
        for ph, y, k in self.birds:
            x = ((ph + t * 0.02) % 1.0) * 1800 - 100
            yy = y + 14 * math.sin(t * 1.4 + k)
            w = 16 + 8 * math.sin(t * 5 + k)
            d.line([(x - 30, yy - w * 0.6), (x, yy), (x + 30, yy - w * 0.6)], fill=(90, 70, 110), width=6)
        # lanterns swaying
        d.line([(200, 260)] + self.lan + [(1400, 260)], fill=INK, width=5)
        for i, (x, y) in enumerate(self.lan):
            sw = 10 * math.sin(t * 1.2 + i)
            lx, ly = x + sw, y + 50
            d.line([(x, y), (lx, ly - 30)], fill=INK, width=4)
            a = 0.7 + 0.3 * math.sin(t * 2 + i * 1.7)
            d.ellipse([lx - 50, ly - 50, lx + 50, ly + 60], fill=(255, 210, 130, int(80 * a)))
            col = (230, 80, 70) if i % 2 else (250, 170, 60)
            d.ellipse([lx - 26, ly - 32, lx + 26, ly + 36], fill=col, outline=INK, width=4)
            d.rectangle([lx - 12, ly - 38, lx + 12, ly - 30], fill=INK)
        # walker wandering down the lane, drifting side to side
        p = (t * 0.025) % 1.0
        s = 0.25 + p * 0.6
        c, y, w = self.lane(s)
        x = c + w * 0.35 * math.sin(t * 0.4)
        sc = 0.5 + 1.1 * s
        step = math.sin(t * 4)
        d.ellipse([x - 40 * sc, y - 10 * sc, x + 40 * sc, y + 10 * sc], fill=(150, 120, 110, 120))
        d.line([(x, y - 80 * sc), (x - 22 * sc * step, y)], fill=INK, width=int(14 * sc))
        d.line([(x, y - 80 * sc), (x + 22 * sc * step, y)], fill=INK, width=int(14 * sc))
        d.rounded_rectangle([x - 34 * sc, y - 210 * sc, x + 34 * sc, y - 70 * sc], int(26 * sc), fill=(110, 90, 170), outline=INK, width=max(3, int(5 * sc)))
        d.ellipse([x - 26 * sc, y - 270 * sc, x + 26 * sc, y - 216 * sc], fill=INK)
        # straw hat
        d.ellipse([x - 48 * sc, y - 262 * sc, x + 48 * sc, y - 240 * sc], fill=(240, 210, 140), outline=INK, width=max(2, int(4 * sc)))
        d.ellipse([x - 24 * sc, y - 286 * sc, x + 24 * sc, y - 246 * sc], fill=(240, 210, 140), outline=INK, width=max(2, int(4 * sc)))
        return img
