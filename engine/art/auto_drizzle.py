"""Scene for: drizzle. A yellow umbrella on a quiet street with fine rain and ripples."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad

S = 1600
INK = (34, 32, 44)


class Drizzle:
    WORD = "drizzle"

    def __init__(self):
        random.seed(63)
        img = vgrad(S, S, [(0, (176, 190, 210)), (0.6, (210, 218, 228)), (1, (150, 160, 176))])
        d = ImageDraw.Draw(img, "RGBA")
        # soft clouds
        for cx, cy, sc in [(300, 200, 1.2), (900, 150, 1.0), (1400, 240, 1.1)]:
            for ox, oy, r in [(-110, 20, 90), (0, -10, 120), (120, 15, 95)]:
                d.ellipse([cx + (ox - r) * sc, cy + (oy - r) * sc, cx + (ox + r) * sc, cy + (oy + r) * sc], fill=(226, 232, 240, 200))
        # houses in the back
        houses = [(0, 300, (196, 150, 140)), (300, 260, (150, 170, 190)), (560, 280, (220, 196, 150)),
                  (1040, 270, (170, 150, 186)), (1310, 290, (190, 160, 130))]
        for x, w, col in houses:
            top = 620 + random.uniform(-40, 40)
            d.rectangle([x, top, x + w, 1040], fill=col, outline=INK, width=6)
            d.polygon([(x - 20, top), (x + w / 2, top - 140), (x + w + 20, top)], fill=(120, 90, 96), outline=INK)
            for wx in range(int(x + 40), int(x + w - 60), 90):
                for wy in (int(top + 60), int(top + 220)):
                    d.rectangle([wx, wy, wx + 50, wy + 80], fill=(255, 226, 160), outline=INK, width=5)
        # street
        d.rectangle([0, 1040, 1600, 1600], fill=(120, 128, 140))
        d.rectangle([0, 1030, 1600, 1070], fill=(170, 176, 186))
        for x in range(0, 1600, 160):
            d.rectangle([x, 1030, x + 6, 1070], fill=(140, 146, 158))
        # puddle
        self.pud = (520, 1370, 1180, 1500)
        d.ellipse(self.pud, fill=(150, 166, 190))
        d.ellipse([560, 1390, 1140, 1480], fill=(170, 186, 208))
        # lamp post
        d.rectangle([1360, 620, 1376, 1050], fill=INK)
        d.ellipse([1330, 570, 1406, 646], fill=(255, 230, 170), outline=INK, width=6)
        for k in range(8):
            rr = 130 * (1 - k / 8)
            d.ellipse([1368 - rr, 608 - rr, 1368 + rr, 608 + rr], fill=(255, 236, 180) + (22,))
        self.base = img
        self.drops = [(random.uniform(0, 1700), random.uniform(0, 1), random.uniform(0.7, 1.3)) for _ in range(150)]
        self.rips = [(random.uniform(580, 1120), random.uniform(1400, 1470), random.uniform(0, 2)) for _ in range(8)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        # ripples in the puddle
        for x, y, ph in self.rips:
            p = ((t + ph) % 2.0) / 2.0
            r = 10 + p * 80
            d.ellipse([x - r, y - r * 0.3, x + r, y + r * 0.3], outline=(235, 242, 255, int(200 * (1 - p))), width=4)
        # umbrella walker in the middle, bobbing slowly
        cx = 800 + 40 * math.sin(t * 0.25)
        by = 1360
        bob = 6 * math.sin(t * 2.4)
        step = math.sin(t * 2.4)
        # reflection in puddle
        d.ellipse([cx - 160, by + 40, cx + 160, by + 90], fill=(250, 210, 80, 70))
        # legs
        d.line([(cx, by - 230 + bob), (cx - 34 * step, by)], fill=INK, width=20)
        d.line([(cx, by - 230 + bob), (cx + 34 * step, by)], fill=INK, width=20)
        d.ellipse([cx - 34 * step - 22, by - 14, cx - 34 * step + 26, by + 10], fill=(200, 80, 70))
        d.ellipse([cx + 34 * step - 22, by - 14, cx + 34 * step + 26, by + 10], fill=(200, 80, 70))
        # coat
        d.rounded_rectangle([cx - 70, by - 480 + bob, cx + 70, by - 210 + bob], 40, fill=(70, 120, 150), outline=INK, width=7)
        d.ellipse([cx - 52, by - 590 + bob, cx + 52, by - 486 + bob], fill=INK)
        # arm + handle
        hx, hy = cx + 40, by - 400 + bob
        d.line([(cx + 30, by - 450 + bob), (hx + 20, hy)], fill=(70, 120, 150), width=26)
        tilt = 0.06 * math.sin(t * 0.6)
        R, H = 300, 190
        ux = cx + 20 + 520 * math.sin(tilt)
        uy = by - 640 + bob
        top = (ux, uy - H)
        d.line([(hx + 20, hy), top], fill=INK, width=10)
        d.arc([hx + 2, hy - 10, hx + 40, hy + 30], 0, 180, fill=INK, width=8)
        # canopy: dome on top, scalloped edge below
        dome = [(ux + R * math.cos(a), uy + H * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 40)]
        edge = []
        for k in range(6, 0, -1):
            x0 = ux - R + k * 2 * R / 6
            x1 = ux - R + (k - 1) * 2 * R / 6
            for q in np.linspace(0, 1, 8)[:-1]:
                edge.append((x0 + (x1 - x0) * q, uy - 26 * math.sin(math.pi * q)))
        d.polygon(dome + edge, fill=(250, 204, 70))
        for k in range(1, 6, 2):
            x0 = ux - R + k * 2 * R / 6
            x1 = x0 + 2 * R / 6
            seg = [(xx, uy - H * math.sqrt(max(0, 1 - ((xx - ux) / R) ** 2))) for xx in np.linspace(x0, x1, 10)]
            d.polygon([top] + seg, fill=(240, 120, 90))
        d.line(dome + edge + [dome[0]], fill=INK, width=7)
        for k in range(1, 6):
            xx = ux - R + k * 2 * R / 6
            d.line([top, (xx, uy - 26 * (0 if True else 1))], fill=(190, 140, 40), width=5)
        d.ellipse([ux - 12, uy - H - 26, ux + 12, uy - H + 2], fill=INK)
        # fine rain
        for x, ph, sp in self.drops:
            y = ((ph + t * 0.6 * sp) % 1.0) * 1700 - 100
            xx = x - y * 0.12
            if abs(xx - ux) < R and uy - H < y < by:
                continue
            d.line([(xx, y), (xx - 5, y + 34)], fill=(240, 246, 255, 170), width=3)
        # drips falling from the umbrella rim
        for k in range(4):
            p = ((t * 0.7 + k / 4) % 1.0)
            rx = ux - R + 40 + k * (2 * R - 80) / 3
            ry = uy + 6 + p * 240
            d.ellipse([rx - 6, ry - 9, rx + 6, ry + 9], fill=(230, 240, 255, int(230 * (1 - p))))
        return img
