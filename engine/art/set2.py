"""Scenes for: stroll, sip, doze, soothing, linger."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine.common import vgrad, glow, gel

S = 1600
INK = (34, 32, 44)

def tree(d, x, y, s, col, trunk=(96, 70, 52)):
    d.rounded_rectangle([x - 14 * s, y - 150 * s, x + 14 * s, y], 8, fill=trunk)
    for ox, oy, r in [(0, -230, 110), (-80, -170, 80), (80, -175, 85), (0, -150, 90)]:
        d.ellipse([x + (ox - r) * s, y + (oy - r) * s, x + (ox + r) * s, y + (oy + r) * s], fill=col)

class Stroll:
    WORD = "stroll"

    def __init__(self):
        img = vgrad(S, S, [(0, (252, 226, 190)), (0.5, (250, 240, 220)), (1, (250, 240, 220))])
        img = glow(img, (1180, 420), 220, (255, 220, 150), 0.6)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([1090, 330, 1270, 510], fill=(255, 214, 140))
        d.polygon([(0, 900)] + [(x, 760 - 90 * math.sin(x / 520 + 0.6)) for x in range(0, 1601, 40)] + [(1600, 1600), (0, 1600)], fill=(150, 196, 130))
        d.polygon([(0, 1000)] + [(x, 930 - 60 * math.sin(x / 380 + 2)) for x in range(0, 1601, 40)] + [(1600, 1600), (0, 1600)], fill=(112, 172, 106))
        # winding path
        left = [(760 + 40 * math.sin(s * 3) - 20 - 520 * s ** 1.6, 900 + 700 * s) for s in np.linspace(0, 1, 30)]
        right = [(840 + 40 * math.sin(s * 3) + 20 + 520 * s ** 1.6, 900 + 700 * s) for s in np.linspace(0, 1, 30)]
        d.polygon(left + right[::-1], fill=(232, 210, 172))
        for s in np.linspace(0.1, 1, 9):
            y = 900 + 700 * s
            d.line([(800 - 200 * s, y), (800 + 200 * s, y)], fill=(214, 188, 148, 120), width=int(4 + 6 * s))
        for x, y, s in [(330, 960, 0.9), (180, 1150, 1.3), (1270, 950, 0.95), (1430, 1180, 1.35), (560, 880, 0.55), (1050, 870, 0.55)]:
            tree(d, x, y, s, (70, 140, 90) if s > 1 else (88, 158, 98))
        # lamp posts
        for x, y, s in [(560, 1200, 1.0), (1060, 1200, 1.0)]:
            d.rectangle([x - 8 * s, y - 380 * s, x + 8 * s, y], fill=INK)
            d.ellipse([x - 34 * s, y - 430 * s, x + 34 * s, y - 362 * s], fill=(255, 236, 180), outline=INK, width=8)
        self.base = img
        random.seed(21)
        self.leaves = [(random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 6)) for _ in range(14)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for cx, cy, sc in [((300 + 18 * t) % 1900 - 150, 230, 1.0), ((1000 + 11 * t) % 1900 - 150, 160, 0.7)]:
            for ox, oy, r in [(-100, 20, 70), (0, -10, 95), (100, 15, 75)]:
                d.ellipse([cx + (ox - r) * sc, cy + (oy - r) * sc, cx + (ox + r) * sc, cy + (oy + r) * sc], fill=(255, 255, 255, 230))
        # walker going up the path
        p = (t * 0.03) % 1.0
        s = 1.25 - p * 0.9
        x = 800 + 30 * math.sin(p * 3)
        y = 1480 - p * 540
        step = math.sin(t * 5)
        d.line([(x, y - 70 * s), (x - 22 * s * step, y)], fill=INK, width=int(14 * s))
        d.line([(x, y - 70 * s), (x + 22 * s * step, y)], fill=INK, width=int(14 * s))
        d.rounded_rectangle([x - 30 * s, y - 190 * s, x + 30 * s, y - 60 * s], int(24 * s), fill=(200, 80, 70))
        d.ellipse([x - 26 * s, y - 250 * s, x + 26 * s, y - 196 * s], fill=INK)
        for ph, yy, rot in self.leaves:
            lx = ((ph + t * 0.05) % 1.0) * 1700 - 50
            ly = ((yy + t * 0.06) % 1.0) * 1100 + 200
            a = t * 2 + rot
            d.ellipse([lx - 16, ly - 9, lx + 16, ly + 9], fill=(232, 150, 60) if rot > 3 else (200, 110, 50))
        return img

class Sip:
    WORD = "sip"

    def __init__(self):
        img = vgrad(S, S, [(0, (244, 228, 206)), (1, (226, 196, 160))])
        img = glow(img, (400, 400), 300, (255, 240, 210), 0.5)
        d = ImageDraw.Draw(img, "RGBA")
        # window light
        d.polygon([(100, 140), (520, 140), (520, 700), (100, 700)], fill=(255, 248, 230))
        d.rectangle([100, 140, 520, 700], outline=(170, 130, 100), width=16)
        d.line([(310, 140), (310, 700)], fill=(170, 130, 100), width=12)
        # plant
        d.polygon([(1250, 1150), (1450, 1150), (1420, 1330), (1280, 1330)], fill=(200, 110, 80))
        for a in range(-70, 71, 28):
            r = math.radians(a - 90)
            d.ellipse([1350 + 170 * math.cos(r) - 50, 1150 + 170 * math.sin(r) - 22, 1350 + 170 * math.cos(r) + 50, 1150 + 170 * math.sin(r) + 22], fill=(80, 140, 80))
            d.line([(1350, 1150), (1350 + 150 * math.cos(r), 1150 + 150 * math.sin(r))], fill=(70, 120, 70), width=8)
        # table
        d.rectangle([0, 1330, 1600, 1600], fill=(140, 92, 60))
        d.rectangle([0, 1320, 1600, 1345], fill=(170, 118, 80))
        self.base = img
        self.glass = (620, 820, 980, 1325)  # x0 y0 x1 y1

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        x0, y0, x1, y1 = self.glass
        inset = 30
        # milk layer + coffee rising
        lvl = 0.25 + 0.35 * (0.5 - 0.5 * math.cos(min(t / 30, 1) * math.pi))
        top = y1 - (y1 - y0) * lvl
        milk = y1 - (y1 - y0) * 0.14
        def lx(y): return x0 + inset * (y1 - y) / (y1 - y0)
        def rx(y): return x1 - inset * (y1 - y) / (y1 - y0)
        d.polygon([(lx(top), top), (rx(top), top), (rx(milk), milk), (lx(milk), milk)], fill=(92, 50, 28, 240))
        d.polygon([(lx(milk), milk), (rx(milk), milk), (x1, y1), (x0, y1)], fill=(246, 232, 200, 250))
        # glass outline
        d.polygon([(x0 - inset, y0), (x1 + inset, y0), (x1, y1), (x0, y1)], outline=(255, 255, 255, 200), width=10)
        d.line([(x0 - 10, y0 + 60), (x0 + 6, y1 - 60)], fill=(255, 255, 255, 120), width=14)
        # phin filter on top
        d.rounded_rectangle([660, 560, 940, 820], 18, fill=(178, 182, 190), outline=INK, width=8)
        d.rectangle([600, 800, 1000, 830], fill=(160, 164, 172), outline=INK, width=6)
        d.rounded_rectangle([680, 520, 920, 572], 14, fill=(198, 202, 210), outline=INK, width=8)
        d.ellipse([775, 480, 825, 530], fill=(198, 202, 210), outline=INK, width=6)
        # drips
        for k in range(3):
            p = ((t * 0.9 + k / 3) % 1.0)
            dy = 840 + p * (top - 840)
            d.ellipse([792, dy - 14, 808, dy + 14], fill=(92, 50, 28))
        # steam
        for k in range(2):
            pts = [(760 + k * 80 + 30 * math.sin(s * 6 + t * 1.6 + k * 2), 470 - s * 330) for s in np.linspace(0, 1, 30)]
            for i in range(len(pts) - 1):
                d.line([pts[i], pts[i + 1]], fill=(255, 255, 255, int(170 * (1 - i / 29))), width=12)
        return img

class Doze:
    WORD = "doze"

    def __init__(self):
        img = vgrad(S, S, [(0, (206, 196, 232)), (1, (176, 164, 214))])
        d = ImageDraw.Draw(img, "RGBA")
        # window with afternoon light
        d.rectangle([880, 160, 1440, 760], fill=(255, 238, 200))
        d.rectangle([880, 160, 1440, 760], outline=(120, 100, 160), width=20)
        d.line([(1160, 160), (1160, 760)], fill=(120, 100, 160), width=14)
        d.line([(880, 460), (1440, 460)], fill=(120, 100, 160), width=14)
        d.polygon([(880, 760), (1440, 760), (1240, 1500), (220, 1500)], fill=(255, 236, 190, 90))
        # floor + cushion
        d.rectangle([0, 1180, 1600, 1600], fill=(150, 132, 196))
        d.ellipse([260, 1080, 1180, 1380], fill=(240, 120, 110))
        d.ellipse([300, 1060, 1140, 1320], fill=(250, 150, 132))
        # plant
        d.polygon([(1300, 1060), (1480, 1060), (1450, 1220), (1330, 1220)], fill=(120, 90, 160))
        for a in range(-60, 61, 30):
            r = math.radians(a - 90)
            d.ellipse([1390 + 150 * math.cos(r) - 46, 1060 + 150 * math.sin(r) - 20, 1390 + 150 * math.cos(r) + 46, 1060 + 150 * math.sin(r) + 20], fill=(90, 150, 100))
        self.base = img

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        br = 1 + 0.035 * math.sin(t * 1.6)
        cx, cy = 720, 1090
        rw, rh = 300, 150 * br
        fur = (242, 168, 82)
        # tail
        pts = [(cx + 260 + 120 * math.cos(a), cy + 60 + 70 * math.sin(a)) for a in np.linspace(-0.6, 2.4, 20)]
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=fur, width=46)
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=fur, outline=INK, width=8)
        for k in range(3):
            d.arc([cx - 120 + k * 90, cy - rh + 10, cx - 20 + k * 90, cy - rh + 110], 200, 340, fill=(214, 130, 60), width=10)
        hx, hy = cx - 250, cy - 20
        d.polygon([(hx - 95, hy - 60), (hx - 60, hy - 170), (hx - 10, hy - 85)], fill=fur, outline=INK, width=8)
        d.polygon([(hx + 10, hy - 85), (hx + 60, hy - 170), (hx + 95, hy - 60)], fill=fur, outline=INK, width=8)
        d.ellipse([hx - 130, hy - 115, hx + 130, hy + 105], fill=fur, outline=INK, width=8)
        d.arc([hx - 80, hy - 20, hx - 20, hy + 20], 20, 160, fill=INK, width=8)
        d.arc([hx + 20, hy - 20, hx + 80, hy + 20], 20, 160, fill=INK, width=8)
        d.polygon([(hx - 12, hy + 30), (hx + 12, hy + 30), (hx, hy + 44)], fill=(200, 90, 90))
        for k in range(3):
            p = ((t * 0.25 + k / 3) % 1.0)
            x = hx + 60 + p * 260 + 20 * math.sin(p * 8)
            y = hy - 180 - p * 420
            a = int(255 * math.sin(math.pi * p))
            d.text((x, y), "z", font=gel(int(80 + 90 * p), b"Bold"), fill=(80, 60, 140, a))
        return img

class Soothing:
    WORD = "soothing"

    def __init__(self):
        img = vgrad(S, S, [(0, (150, 196, 210)), (0.3, (120, 176, 196)), (1, (70, 130, 160))])
        d = ImageDraw.Draw(img, "RGBA")
        random.seed(31)
        self.pads = [(250, 1150, 170), (1250, 1050, 150), (700, 1380, 200), (1100, 1420, 120), (420, 700, 110), (1300, 560, 100), (850, 520, 80)]
        for x, y, r in self.pads:
            d.ellipse([x - r, y - r * 0.55, x + r, y + r * 0.55], fill=(70, 150, 90))
            d.pieslice([x - r, y - r * 0.55, x + r, y + r * 0.55], -20, 20, fill=(120, 176, 196))
            d.line([(x, y), (x - r * 0.7, y - r * 0.2)], fill=(90, 170, 110), width=6)
        # lotus flowers
        for x, y, s in [(330, 1060, 1.0), (1220, 960, 0.85)]:
            for a in [-60, -30, 0, 30, 60]:
                r = math.radians(a - 90)
                tip = (x + 150 * s * math.cos(r), y + 150 * s * math.sin(r))
                d.polygon([(x - 40 * s, y), tip, (x + 40 * s, y)], fill=(248, 160, 186), outline=(210, 100, 140), width=4)
            d.ellipse([x - 40 * s, y - 30 * s, x + 40 * s, y + 10 * s], fill=(250, 216, 110))
        self.base = img
        self.rip = [(random.uniform(100, 1500), random.uniform(300, 1550), random.uniform(0, 2.5)) for _ in range(26)]
        self.rain = [(random.uniform(0, 1700), random.uniform(0, 1), random.uniform(0.8, 1.2)) for _ in range(60)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, ph in self.rip:
            p = ((t + ph) % 2.5) / 2.5
            r = 20 + p * 160
            a = int(200 * (1 - p))
            d.ellipse([x - r, y - r * 0.4, x + r, y + r * 0.4], outline=(235, 250, 255, a), width=6)
        for x, ph, sp in self.rain:
            y = ((ph + t * 0.9 * sp) % 1.0) * 1700 - 100
            d.line([(x - y * 0.15, y), (x - y * 0.15 - 12, y + 60)], fill=(240, 250, 255, 150), width=4)
        return img

class Linger:
    WORD = "linger"

    def __init__(self):
        img = vgrad(S, S, [(0, (70, 64, 120)), (0.45, (230, 140, 120)), (0.7, (250, 200, 150)), (1, (250, 200, 150))])
        d = ImageDraw.Draw(img, "RGBA")
        # building with window
        d.rectangle([0, 520, 700, 1600], fill=(200, 110, 80))
        d.rectangle([110, 700, 560, 1100], fill=(255, 214, 140))
        d.rectangle([110, 700, 560, 1100], outline=INK, width=14)
        d.line([(335, 700), (335, 1100)], fill=INK, width=10)
        d.polygon([(60, 640), (620, 640), (680, 560), (0, 560)], fill=(60, 120, 100))
        for k in range(8):
            d.polygon([(k * 85, 640), (k * 85 + 85, 640), (k * 85 + 42, 700)], fill=(60, 120, 100) if k % 2 else (240, 230, 210))
        # ground
        d.rectangle([0, 1300, 1600, 1600], fill=(120, 90, 80))
        # table + chairs
        d.ellipse([820, 1080, 1360, 1170], fill=(240, 230, 214), outline=INK, width=10)
        d.line([(1090, 1150), (1090, 1430)], fill=INK, width=18)
        d.line([(980, 1440), (1200, 1440)], fill=INK, width=16)
        for cx, flip in [(760, -1), (1430, 1)]:
            d.line([(cx, 1000), (cx, 1440)], fill=INK, width=14)
            d.line([(cx, 1200), (cx - 120 * flip, 1200)], fill=INK, width=14)
            d.line([(cx - 120 * flip, 1200), (cx - 120 * flip, 1440)], fill=INK, width=14)
        for x in (980, 1180):
            d.rounded_rectangle([x - 50, 1010, x + 50, 1100], 18, fill=(255, 255, 255), outline=INK, width=8)
            d.ellipse([x - 50, 998, x + 50, 1026], fill=(120, 70, 40), outline=INK, width=6)
        self.base = img
        self.bulbs = [(s, 700 + s * 900, 330 + 140 * math.sin(math.pi * s)) for s in np.linspace(0, 1, 11)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        pts = [(x, y) for _, x, y in self.bulbs]
        d.line([(700, 330)] + pts, fill=INK, width=6)
        for i, (s, x, y) in enumerate(self.bulbs):
            a = 0.65 + 0.35 * math.sin(t * 2 + i * 1.3)
            d.ellipse([x - 46, y - 10, x + 46, y + 82], fill=(255, 220, 140, int(70 * a)))
            d.ellipse([x - 18, y + 12, x + 18, y + 52], fill=(255, int(220 + 30 * a), int(150 + 60 * a)))
        for k in range(2):
            x = 980 + k * 200
            pts = [(x + 18 * math.sin(s * 6 + t * 1.7 + k), 990 - s * 200) for s in np.linspace(0, 1, 24)]
            for i in range(len(pts) - 1):
                d.line([pts[i], pts[i + 1]], fill=(255, 255, 255, int(160 * (1 - i / 23))), width=9)
        return img

