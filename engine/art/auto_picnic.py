"""Scene for: picnic. A checked blanket with a basket and fruit under a leafy tree."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad

S = 1600
INK = (34, 32, 44)


class Picnic:
    WORD = "picnic"

    def __init__(self):
        random.seed(74)
        img = vgrad(S, S, [(0, (170, 214, 240)), (0.45, (232, 244, 240)), (1, (232, 244, 240))])
        d = ImageDraw.Draw(img, "RGBA")
        for k in range(8):
            rr = 230 * (1 - k / 8)
            d.ellipse([1340 - rr, 260 - rr, 1340 + rr, 260 + rr], fill=(255, 244, 200) + (22,))
        d.ellipse([1270, 190, 1410, 330], fill=(255, 236, 160))
        d.polygon([(0, 820)] + [(x, 700 - 70 * math.sin(x / 450 + 0.3)) for x in range(0, 1601, 40)] + [(1600, 1600), (0, 1600)], fill=(160, 206, 130))
        d.polygon([(0, 900)] + [(x, 820 - 40 * math.sin(x / 300 + 2)) for x in range(0, 1601, 40)] + [(1600, 1600), (0, 1600)], fill=(124, 184, 104))
        # tree trunk (leaves are drawn per frame)
        d.polygon([(250, 1100), (330, 1100), (316, 560), (264, 560)], fill=(120, 86, 60), outline=INK)
        d.line([(290, 640), (180, 520)], fill=(120, 86, 60), width=26)
        d.line([(300, 600), (420, 500)], fill=(120, 86, 60), width=26)
        # tree shade
        d.ellipse([60, 1040, 760, 1180], fill=(100, 160, 90, 160))
        # blanket in perspective with red checks
        q = [(430, 1060), (1420, 1060), (1560, 1480), (300, 1480)]
        d.polygon(q, fill=(252, 246, 236), outline=INK)
        def at(u, v):
            lx = q[0][0] + (q[3][0] - q[0][0]) * v
            rx = q[1][0] + (q[2][0] - q[1][0]) * v
            y = q[0][1] + (q[3][1] - q[0][1]) * v
            return (lx + (rx - lx) * u, y)
        n = 8
        for i in range(n):
            for j in range(n):
                if (i + j) % 2 == 0:
                    d.polygon([at(i / n, j / n), at((i + 1) / n, j / n), at((i + 1) / n, (j + 1) / n), at(i / n, (j + 1) / n)], fill=(222, 84, 76, 210))
        d.line(q + [q[0]], fill=INK, width=8)
        # basket
        bx, by = 700, 1220
        d.polygon([(bx - 170, by - 120), (bx + 170, by - 120), (bx + 140, by + 60), (bx - 140, by + 60)], fill=(214, 160, 90), outline=INK)
        for k in range(1, 4):
            y = by - 120 + k * 45
            d.line([(bx - 170 + k * 8, y), (bx + 170 - k * 8, y)], fill=(176, 120, 60), width=6)
        for k in range(-3, 4):
            d.line([(bx + k * 46, by - 120), (bx + k * 40, by + 60)], fill=(176, 120, 60), width=5)
        d.arc([bx - 150, by - 300, bx + 150, by - 20], 180, 360, fill=INK, width=18)
        d.arc([bx - 150, by - 300, bx + 150, by - 20], 180, 360, fill=(190, 136, 70), width=10)
        d.polygon([(bx - 170, by - 130), (bx - 40, by - 160), (bx + 20, by - 118)], fill=(240, 120, 110), outline=INK)
        # lemonade jug + glasses
        d.rounded_rectangle([1010, 1050, 1130, 1250], 26, fill=(255, 240, 150, 230), outline=INK, width=7)
        d.arc([1110, 1100, 1180, 1190], -90, 90, fill=INK, width=9)
        d.ellipse([1040, 1110, 1100, 1140], fill=(255, 250, 220))
        for gx in (1200, 1290):
            d.rounded_rectangle([gx, 1180, gx + 60, 1270], 10, fill=(255, 236, 140, 220), outline=INK, width=6)
        # fruit plate
        d.ellipse([880, 1330, 1160, 1420], fill=(255, 255, 255), outline=INK, width=6)
        for fx, col in [(950, (230, 60, 60)), (1010, (130, 190, 70)), (1070, (240, 160, 50)), (985, (230, 60, 60))]:
            fy = 1350 if fx != 985 else 1330
            d.ellipse([fx - 30, fy - 30, fx + 30, fy + 30], fill=col, outline=INK, width=5)
        # sandwiches
        for sx in (500, 590):
            d.polygon([(sx, 1400), (sx + 90, 1400), (sx + 45, 1330)], fill=(246, 220, 160), outline=INK)
            d.line([(sx + 12, 1386), (sx + 78, 1386)], fill=(110, 180, 80), width=8)
        self.base = img
        self.leaves = [(random.uniform(-260, 260), random.uniform(-200, 160), random.uniform(60, 120), random.uniform(0, 6)) for _ in range(16)]
        self.leaves.sort(key=lambda l: l[2])
        self.fall = [(random.uniform(0, 1), random.uniform(0, 6)) for _ in range(5)]
        self.grass = [(random.uniform(0, 1600), random.uniform(900, 1600), random.uniform(30, 60), random.uniform(0, 6)) for _ in range(90)]
        self.grass = [g for g in self.grass if not (300 < g[0] < 1560 and 1040 < g[1] < 1490)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, h, ph in self.grass:
            sw = 10 * math.sin(t * 1.6 + ph)
            d.line([(x, y), (x + sw, y - h)], fill=(80, 150, 80), width=6)
        # leafy crown that sways a little
        cx, cy = 300, 430
        for i, (ox, oy, r, ph) in enumerate(self.leaves):
            sx = 8 * math.sin(t * 0.9 + ph)
            g = 120 + int(r * 0.4)
            d.ellipse([cx + ox + sx - r, cy + oy - r, cx + ox + sx + r, cy + oy + r], fill=(70, g, 80), outline=INK if i % 4 == 0 else None)
        # falling leaves
        for ph, rot in self.fall:
            p = (t * 0.05 + ph) % 1.0
            lx = 200 + p * 700 + 60 * math.sin(t * 1.3 + rot)
            ly = 500 + p * 600
            d.ellipse([lx - 18, ly - 10, lx + 18, ly + 10], fill=(110, 170, 80))
        # butterfly
        bx = 1100 + 260 * math.sin(t * 0.3)
        by = 800 + 90 * math.sin(t * 0.7) - 40 * math.cos(t * 1.1)
        f = 0.35 + 0.65 * abs(math.sin(t * 6))
        for s in (-1, 1):
            d.ellipse([bx + min(0, s * 60 * f), by - 46, bx + max(0, s * 60 * f), by + 4], fill=(250, 150, 60), outline=INK, width=4)
            d.ellipse([bx + min(0, s * 44 * f), by - 4, bx + max(0, s * 44 * f), by + 36], fill=(250, 196, 90), outline=INK, width=4)
        d.line([(bx, by - 40), (bx, by + 34)], fill=INK, width=7)
        # sparkle on lemonade
        a = int(140 + 110 * math.sin(t * 2))
        d.ellipse([1036, 1160, 1052, 1176], fill=(255, 255, 255, a))
        return img
