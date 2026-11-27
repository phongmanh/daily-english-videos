"""Scene for: bloom. A pink flower slowly opens in a pot on a sunny sill."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad, ease

S = 1600
INK = (34, 32, 44)


class Bloom:
    WORD = "bloom"

    def __init__(self):
        random.seed(41)
        img = vgrad(S, S, [(0, (255, 226, 214)), (0.55, (252, 240, 226)), (1, (244, 222, 200))])
        d = ImageDraw.Draw(img, "RGBA")
        for k in range(8):
            rr = 260 * (1 - k / 8)
            d.ellipse([1260 - rr, 330 - rr, 1260 + rr, 330 + rr], fill=(255, 230, 160) + (22,))
        d.ellipse([1170, 240, 1350, 420], fill=(255, 214, 130))
        # soft hills far away
        d.polygon([(0, 1000)] + [(x, 900 - 60 * math.sin(x / 400 + 1)) for x in range(0, 1601, 40)] + [(1600, 1000)], fill=(196, 222, 176))
        d.polygon([(0, 1060)] + [(x, 980 - 40 * math.sin(x / 300 + 3)) for x in range(0, 1601, 40)] + [(1600, 1060)], fill=(170, 206, 156))
        # window sill / table
        d.rectangle([0, 1040, 1600, 1600], fill=(226, 176, 140))
        d.rectangle([0, 1030, 1600, 1062], fill=(244, 200, 162))
        for i in range(5):
            d.line([(0, 1130 + i * 95), (1600, 1130 + i * 95)], fill=(206, 156, 122, 140), width=5)
        # small side pots
        for x, s, col in [(300, 0.7, (130, 170, 200)), (1330, 0.8, (240, 200, 110))]:
            d.polygon([(x - 90 * s, 1040 - 150 * s), (x + 90 * s, 1040 - 150 * s), (x + 70 * s, 1040), (x - 70 * s, 1040)], fill=col, outline=INK)
            d.rectangle([x - 100 * s, 1040 - 175 * s, x + 100 * s, 1040 - 145 * s], fill=col, outline=INK, width=6)
            for k in range(5):
                a = math.radians(-150 + k * 30)
                lx, ly = x + 110 * s * math.cos(a), 1040 - 175 * s + 110 * s * math.sin(a)
                d.line([(x, 1040 - 175 * s), (lx, ly)], fill=(70, 130, 80), width=8)
                d.ellipse([lx - 24 * s, ly - 24 * s, lx + 24 * s, ly + 24 * s], fill=(90, 160, 96))
        # main pot
        d.polygon([(640, 880), (960, 880), (920, 1100), (680, 1100)], fill=(214, 112, 82), outline=INK, width=8)
        d.rounded_rectangle([610, 840, 990, 900], 14, fill=(232, 132, 96), outline=INK, width=8)
        d.ellipse([650, 846, 950, 880], fill=(110, 72, 52))
        # stem and leaves
        d.line([(800, 860), (806, 700), (796, 560)], fill=(70, 130, 80), width=20)
        for sx, sy, dirn in [(803, 760, -1), (800, 660, 1)]:
            pts = [(sx, sy), (sx + dirn * 90, sy - 70), (sx + dirn * 180, sy - 40), (sx + dirn * 90, sy + 10)]
            d.polygon(pts, fill=(96, 168, 98), outline=INK)
            d.line([(sx, sy), (sx + dirn * 150, sy - 38)], fill=(70, 130, 80), width=5)
        self.base = img
        self.petals = [(random.uniform(0, 1), random.uniform(150, 800), random.uniform(0, 6)) for _ in range(10)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        cx, cy = 796, 520
        # opening: closed bud -> full bloom over ~24 s, then breathing gently
        op = ease(t / 24.0)
        op = op * (0.94 + 0.06 * math.sin(t * 0.8))
        for layer, (n, ln, col, off) in enumerate([(8, 230, (240, 120, 150), 0.0), (8, 170, (250, 160, 184), 0.4), (6, 110, (255, 200, 214), 0.0)]):
            spread = 0.15 + 0.85 * op
            L = ln * (0.55 + 0.45 * op)
            for i in range(n):
                base_a = -math.pi / 2 + (i - (n - 1) / 2) * (2 * math.pi / n) * spread + off * spread
                sway = 0.03 * math.sin(t * 1.2 + i)
                a = base_a + sway
                w = 0.32 + 0.1 * layer
                tip = (cx + L * math.cos(a), cy + L * math.sin(a))
                l1 = (cx + L * 0.6 * math.cos(a - w), cy + L * 0.6 * math.sin(a - w))
                r1 = (cx + L * 0.6 * math.cos(a + w), cy + L * 0.6 * math.sin(a + w))
                d.polygon([(cx, cy), l1, tip, r1], fill=col, outline=INK)
        r = 22 + 30 * op
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 208, 90), outline=INK, width=6)
        for k in range(8):
            a = k * math.pi / 4 + t * 0.2
            d.ellipse([cx + r * 0.55 * math.cos(a) - 5, cy + r * 0.55 * math.sin(a) - 5, cx + r * 0.55 * math.cos(a) + 5, cy + r * 0.55 * math.sin(a) + 5], fill=(214, 150, 50))
        # sepals hugging the bud
        for s in (-1, 1):
            d.polygon([(cx, cy + 20), (cx + s * 60 * (1 - 0.5 * op), cy - 30), (cx + s * 20, cy + 40)], fill=(80, 150, 86))
        # drifting petals
        for ph, y, rot in self.petals:
            x = ((ph + t * 0.04) % 1.0) * 1800 - 100
            yy = y + 50 * math.sin(t * 1.1 + rot) + ((t * 8 + rot * 30) % 300)
            a = t * 1.5 + rot
            dx, dy = 22 * math.cos(a), 12 * math.sin(a)
            d.ellipse([x - 22, yy - 12 - dy * 0.3, x + 22, yy + 12 + dy * 0.3], fill=(250, 170, 190, 220))
        # two bees circling the flower
        for k in range(2):
            a = t * 0.6 + k * math.pi
            bx = cx + 360 * math.cos(a)
            by = cy - 60 + 130 * math.sin(a * 2) * 0.6
            flap = 10 * abs(math.sin(t * 14 + k))
            d.ellipse([bx - 20, by - 34 - flap, bx + 6, by - 6], fill=(255, 255, 255, 190), outline=INK, width=3)
            d.ellipse([bx - 2, by - 34 - flap, bx + 24, by - 6], fill=(255, 255, 255, 190), outline=INK, width=3)
            d.ellipse([bx - 30, by - 18, bx + 30, by + 18], fill=(250, 200, 70), outline=INK, width=5)
            d.line([(bx - 8, by - 16), (bx - 8, by + 16)], fill=INK, width=7)
            d.line([(bx + 10, by - 15), (bx + 10, by + 15)], fill=INK, width=7)
        return img
