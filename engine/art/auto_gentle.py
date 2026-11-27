"""Scene for: gentle. Curtains sway softly at an open window over a calm garden."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad

S = 1600
INK = (34, 32, 44)


class Gentle:
    WORD = "gentle"

    def __init__(self):
        random.seed(52)
        # wall
        img = vgrad(S, S, [(0, (226, 238, 232)), (1, (204, 224, 214))])
        d = ImageDraw.Draw(img, "RGBA")
        self.win = (380, 250, 1220, 1110)
        x0, y0, x1, y1 = self.win
        view = vgrad(x1 - x0, y1 - y0, [(0, (168, 214, 236)), (0.55, (226, 242, 240)), (0.56, (160, 206, 150)), (1, (120, 180, 120))])
        vd = ImageDraw.Draw(view, "RGBA")
        for k in range(8):
            rr = 140 * (1 - k / 8)
            vd.ellipse([620 - rr, 170 - rr, 620 + rr, 170 + rr], fill=(255, 250, 220) + (22,))
        vd.ellipse([570, 120, 670, 220], fill=(255, 246, 206))
        vw, vh = view.size
        vd.polygon([(0, vh * 0.6)] + [(x, vh * 0.56 - 40 * math.sin(x / 160 + 1)) for x in range(0, vw + 1, 20)] + [(vw, vh), (0, vh)], fill=(140, 196, 132))
        for tx, ty, s in [(150, 520, 1.0), (650, 500, 0.8), (420, 560, 0.6)]:
            vd.rectangle([tx - 10 * s, ty - 120 * s, tx + 10 * s, ty], fill=(110, 84, 60))
            for ox, oy, r in [(0, -170, 80), (-55, -120, 60), (55, -125, 62)]:
                vd.ellipse([tx + (ox - r) * s, ty + (oy - r) * s, tx + (ox + r) * s, ty + (oy + r) * s], fill=(84, 150, 96))
        for _ in range(40):
            fx, fy = random.uniform(0, vw), random.uniform(vh * 0.7, vh)
            vd.ellipse([fx - 7, fy - 7, fx + 7, fy + 7], fill=random.choice([(255, 255, 255), (250, 210, 220), (255, 230, 140)]))
        img.paste(view, (x0, y0))
        d.rectangle([x0 - 30, y0 - 30, x1 + 30, y1 + 30], outline=(250, 250, 246), width=40)
        d.rectangle([x0 - 50, y0 - 50, x1 + 50, y1 + 50], outline=INK, width=6)
        d.rectangle([x0 - 10, y0 - 10, x1 + 10, y1 + 10], outline=INK, width=6)
        # sill
        d.rounded_rectangle([x0 - 110, y1 + 30, x1 + 110, y1 + 90], 12, fill=(250, 250, 246), outline=INK, width=6)
        # cup and small plant on sill
        d.rounded_rectangle([470, y1 - 60, 590, y1 + 30], 20, fill=(246, 214, 170), outline=INK, width=6)
        d.arc([560, y1 - 40, 630, y1 + 10], -90, 90, fill=INK, width=6)
        d.polygon([(1000, y1 - 70), (1120, y1 - 70), (1100, y1 + 30), (1020, y1 + 30)], fill=(230, 150, 120), outline=INK)
        for k in range(5):
            a = math.radians(-150 + k * 30)
            lx, ly = 1060 + 100 * math.cos(a), y1 - 70 + 100 * math.sin(a)
            d.line([(1060, y1 - 70), (lx, ly)], fill=(70, 130, 80), width=7)
            d.ellipse([lx - 22, ly - 14, lx + 22, ly + 14], fill=(96, 168, 98))
        # floor
        d.rectangle([0, 1380, 1600, 1600], fill=(186, 206, 196))
        d.line([(0, 1380), (1600, 1380)], fill=(160, 186, 174), width=10)
        # curtain rod
        d.rounded_rectangle([200, 170, 1400, 196], 12, fill=(120, 96, 80), outline=INK, width=5)
        d.ellipse([180, 160, 226, 206], fill=(120, 96, 80), outline=INK, width=5)
        d.ellipse([1374, 160, 1420, 206], fill=(120, 96, 80), outline=INK, width=5)
        self.base = img

    def curtain(self, d, t, side):
        top, bot = 196, 1330
        outer = 230 if side < 0 else 1370
        full = 400 if side < 0 else -400
        n = 30
        tie = 0.6
        left, right = [], []
        for i in range(n + 1):
            s = i / n
            y = top + (bot - top) * s
            sway = s ** 1.5 * (40 * math.sin(t * 0.9 + side) + 18 * math.sin(t * 1.7 + 2 * side))
            # width: full at the top, gathered at the tie, flaring a little below it
            if s < tie:
                f = 1 - 0.75 * (s / tie) ** 1.3
            else:
                f = 0.25 + 0.35 * ((s - tie) / (1 - tie)) ** 0.8
            ow = sway * 0.3 * (s > tie)
            left.append((outer + ow, y))
            right.append((outer + full * f + sway * (s > tie) + 0.4 * sway * (s <= tie), y))
        d.polygon(left + right[::-1], fill=(250, 244, 232, 235))
        for fr in (0.25, 0.5, 0.75):
            pts = [(l[0] + (r[0] - l[0]) * fr, l[1]) for l, r in zip(left, right)]
            d.line(pts, fill=(226, 212, 196, 220), width=6)
        d.line(left + right[::-1] + [left[0]], fill=INK, width=5)
        k = int(n * tie)
        lx, rx, y = left[k][0], right[k][0], left[k][1]
        d.rounded_rectangle([min(lx, rx) - 6, y - 16, max(lx, rx) + 6, y + 16], 12, fill=(110, 170, 150), outline=INK, width=4)

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        x0, y0, x1, y1 = self.win
        # a floating feather drifting across the window
        p = (t * 0.035) % 1.0
        fx = x0 + 60 + p * (x1 - x0 - 120)
        fy = y0 + 260 + 120 * math.sin(p * 6.3) + 30 * math.sin(t * 1.3)
        ang = 0.6 * math.sin(t * 1.1)
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for s in np.linspace(-1, 1, 14):
            pts.append((s * 90, 0))
        spine = [(fx + px * ca, fy + px * sa) for px, _ in pts]
        for i, (px, _) in enumerate(pts):
            h = 26 * math.sqrt(max(0, 1 - (px / 90) ** 2))
            for sgn in (-1, 1):
                ex, ey = px + 18, sgn * h
                d.line([(fx + px * ca, fy + px * sa), (fx + ex * ca - ey * sa, fy + ex * sa + ey * ca)], fill=(255, 255, 255, 230), width=6)
        d.line(spine, fill=(200, 190, 180), width=4)
        # light motes in the sunbeam
        for k in range(14):
            q = (t * 0.05 + k / 14) % 1.0
            mx = 560 + k * 37 + 30 * math.sin(t * 0.7 + k)
            my = 1300 - q * 600
            a = int(160 * math.sin(math.pi * q))
            d.ellipse([mx - 5, my - 5, mx + 5, my + 5], fill=(255, 250, 220, a))
        self.curtain(d, t, -1)
        self.curtain(d, t, 1)
        return img
