"""Scenes for: serene, cozy, breeze, drowsy, unwind."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from engine.common import vgrad, glow, gel

S = 1600

class Serene:
    WORD = "serene"

    def __init__(self):
        img = vgrad(S, S, [(0, (110, 122, 186)), (0.42, (236, 170, 160)), (0.55, (250, 205, 160)),
                           (0.551, (205, 165, 180)), (1, (70, 76, 122))])
        img = glow(img, (560, 400), 200, (255, 225, 170), 0.7)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([470, 310, 650, 490], fill=(255, 236, 200))
        back = [(0, 880), (0, 640), (220, 520), (420, 650), (620, 470), (860, 660), (1060, 540), (1300, 700), (1600, 560), (1600, 880)]
        front = [(0, 880), (0, 760), (260, 680), (520, 800), (760, 720), (1000, 820), (1250, 700), (1600, 790), (1600, 880)]
        d.polygon(back, fill=(140, 128, 175))
        d.polygon(front, fill=(92, 88, 140))
        # reflection
        refl = [(x, 1760 - y) for x, y in back]
        refl2 = [(x, 1760 - y) for x, y in front]
        d.polygon(refl, fill=(140, 128, 175, 90))
        d.polygon(refl2, fill=(92, 88, 140, 120))
        d.rectangle([0, 878, 1600, 884], fill=(255, 235, 210, 120))
        self.base = img
        random.seed(3)
        self.shim = [(random.uniform(0, 1600), random.uniform(900, 1580), random.uniform(40, 160), random.uniform(0, 6)) for _ in range(40)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, ln, ph in self.shim:
            dx = 30 * math.sin(t * 0.8 + ph)
            a = int(60 + 50 * math.sin(t * 1.3 + ph))
            d.line([(x + dx, y), (x + dx + ln * (y / 1600), y)], fill=(255, 235, 215, a), width=4)
        # boat
        bx = 420 + 22 * t
        by = 1040 + 8 * math.sin(t * 1.6)
        d.polygon([(bx - 110, by), (bx + 110, by), (bx + 80, by + 40), (bx - 80, by + 40)], fill=(50, 45, 80))
        d.polygon([(bx, by - 200), (bx, by - 8), (bx + 120, by - 8)], fill=(250, 236, 220))
        d.line([(bx, by - 210), (bx, by)], fill=(50, 45, 80), width=8)
        # birds
        for i, (ox, oy) in enumerate([(0, 0), (90, 40), (40, 90)]):
            x = 1000 + ox + 30 * t
            y = 300 + oy + 10 * math.sin(t * 2 + i)
            w = 30 + 8 * math.sin(t * 6 + i)
            d.line([(x - 40, y - w * 0.5), (x, y), (x + 40, y - w * 0.5)], fill=(70, 60, 100), width=7)
        return img

class Cozy:
    WORD = "cozy"

    def __init__(self):
        img = vgrad(S, S, [(0, (62, 38, 28)), (1, (96, 58, 36))])
        img = glow(img, (1300, 380), 420, (255, 190, 110), 0.55)
        d = ImageDraw.Draw(img, "RGBA")
        # window
        self.win = (160, 200, 860, 980)
        x0, y0, x1, y1 = self.win
        sky = vgrad(x1 - x0, y1 - y0, [(0, (24, 34, 70)), (1, (58, 70, 120))])
        img.paste(sky, (x0, y0))
        d.rectangle([x0 - 24, y0 - 24, x1 + 24, y1 + 24], outline=(40, 24, 16), width=30)
        d.line([((x0 + x1) // 2, y0), ((x0 + x1) // 2, y1)], fill=(40, 24, 16), width=22)
        d.line([(x0, (y0 + y1) // 2), (x1, (y0 + y1) // 2)], fill=(40, 24, 16), width=22)
        # lamp
        d.polygon([(1180, 220), (1420, 220), (1500, 420), (1100, 420)], fill=(250, 200, 130))
        d.line([(1300, 420), (1300, 1150)], fill=(60, 40, 30), width=18)
        # table
        d.rectangle([0, 1180, 1600, 1600], fill=(44, 27, 19))
        d.rectangle([0, 1170, 1600, 1196], fill=(78, 50, 34))
        # books
        d.rounded_rectangle([250, 1080, 650, 1130], 8, fill=(150, 70, 60))
        d.rounded_rectangle([280, 1030, 620, 1080], 8, fill=(80, 110, 130))
        d.rounded_rectangle([300, 985, 600, 1030], 8, fill=(210, 170, 100))
        # mug
        d.rounded_rectangle([880, 880, 1180, 1175], 40, fill=(236, 220, 200))
        d.ellipse([880, 860, 1180, 920], fill=(120, 70, 40))
        d.ellipse([880, 855, 1180, 915], outline=(236, 220, 200), width=14)
        d.arc([1120, 930, 1290, 1110], -90, 90, fill=(236, 220, 200), width=34)
        d.rounded_rectangle([960, 990, 1100, 1060], 20, fill=(200, 120, 90))
        self.base = img
        random.seed(5)
        self.drops = [(random.uniform(x0, x1), random.uniform(0, 1), random.uniform(0.6, 1.2)) for _ in range(70)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        x0, y0, x1, y1 = self.win
        hgt = y1 - y0
        for x, ph, sp in self.drops:
            y = y0 + ((ph + t * 0.55 * sp) % 1.0) * hgt
            y2 = min(y + 50, y1)
            d.line([(x, y), (x - 8, y2)], fill=(180, 200, 240, 150), width=4)
        for k in range(3):
            pts = []
            for i in range(40):
                s = i / 39
                y = 840 - s * 420
                x = 960 + k * 90 + 35 * math.sin(s * 6 + t * 1.8 + k * 2)
                pts.append((x, y))
            for i in range(len(pts) - 1):
                a = int(130 * (1 - i / 39) * (0.7 + 0.3 * math.sin(t + k)))
                d.line([pts[i], pts[i + 1]], fill=(255, 245, 235, a), width=12)
        return img

class Breeze:
    WORD = "breeze"

    def __init__(self):
        img = vgrad(S, S, [(0, (120, 190, 228)), (0.7, (220, 240, 248)), (1, (220, 240, 248))])
        img = glow(img, (280, 260), 170, (255, 250, 210), 0.9)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([200, 180, 360, 340], fill=(255, 248, 215))
        d.polygon([(0, 1150)] + [(x, 1060 - 120 * math.sin(x / 1600 * math.pi)) for x in range(0, 1601, 40)] + [(1600, 1600), (0, 1600)], fill=(130, 190, 120))
        d.polygon([(0, 1600), (0, 1280)] + [(x, 1280 - 80 * math.sin(x / 900 + 1)) for x in range(0, 1601, 40)] + [(1600, 1600)], fill=(90, 160, 95))
        self.base = img
        random.seed(7)
        self.grass = [(random.uniform(0, 1600), random.uniform(1380, 1600), random.uniform(90, 200), random.uniform(0, 6)) for _ in range(220)]
        self.grass.sort(key=lambda g: g[1])
        self.leaves = [(random.uniform(0, 1), random.uniform(450, 1000), random.uniform(0, 6)) for _ in range(9)]

    def cloud(self, d, cx, cy, s):
        for ox, oy, r in [(-120, 20, 90), (0, -20, 120), (130, 10, 95), (60, 40, 90), (-60, 45, 80)]:
            d.ellipse([cx + ox * s - r * s, cy + oy * s - r * s, cx + ox * s + r * s, cy + oy * s + r * s], fill=(255, 255, 255, 235))

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        self.cloud(d, (700 + 25 * t) % 2000 - 200, 330, 1.0)
        self.cloud(d, (1250 + 15 * t) % 2000 - 200, 560, 0.7)
        # wind swirls
        for k in range(3):
            off = (t * 260 + k * 600) % 2400 - 600
            pts = []
            for i in range(60):
                s = i / 59
                x = off + s * 700
                y = 620 + k * 150 + 50 * math.sin(s * 5 + k)
                pts.append((x, y))
            # little curl at the end
            ex, ey = pts[-1]
            for j in range(20):
                ang = -math.pi / 2 + j / 19 * math.pi * 1.4
                pts.append((ex + 50 * math.cos(ang) - 0, ey + 50 + 50 * math.sin(ang)))
            for i in range(len(pts) - 1):
                a = int(200 * math.sin(math.pi * i / len(pts)))
                d.line([pts[i], pts[i + 1]], fill=(255, 255, 255, a), width=10)
        for ph, y, rot in self.leaves:
            x = ((ph + t * 0.12) % 1.2) * 1800 - 200
            yy = y + 60 * math.sin(t * 1.5 + rot)
            ang = t * 2 + rot
            dx, dy = 28 * math.cos(ang), 28 * math.sin(ang)
            d.ellipse([x - 22, yy - 12, x + 22, yy + 12], fill=(230, 160, 60))
            d.line([(x - dx, yy - dy), (x + dx, yy + dy)], fill=(170, 100, 40), width=4)
        for x, y, h, ph in self.grass:
            sway = 35 * math.sin(t * 2.2 + x * 0.006 + ph * 0.3) + 25
            g = int(120 + (y - 1380) / 220 * 60)
            d.line([(x, y), (x + sway * 0.5, y - h * 0.5), (x + sway, y - h)], fill=(60, g, 70), width=9)
        return img

class Drowsy:
    WORD = "drowsy"

    def __init__(self):
        img = vgrad(S, S, [(0, (12, 16, 40)), (1, (40, 50, 110))])
        img = glow(img, (1200, 460), 200, (250, 230, 170), 0.18)
        moon = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(moon)
        md.ellipse([940, 240, 1300, 600], fill=255)
        md.ellipse([840, 180, 1200, 540], fill=0)
        img.paste(Image.new("RGB", (S, S), (250, 232, 180)), (0, 0), moon)
        d = ImageDraw.Draw(img, "RGBA")
        # bed
        d.rounded_rectangle([60, 1100, 1540, 1600 + 60], 70, fill=(70, 86, 160))
        d.rounded_rectangle([140, 960, 760, 1180], 90, fill=(225, 230, 250))
        d.rounded_rectangle([60, 1230, 1540, 1600 + 60], 70, fill=(92, 112, 190))
        for i in range(6):
            d.line([(60, 1300 + i * 50), (1540, 1300 + i * 50)], fill=(110, 130, 205, 120), width=6)
        self.base = img
        random.seed(11)
        self.stars = [(random.uniform(40, 1560), random.uniform(40, 900), random.uniform(3, 8), random.uniform(0, 6)) for _ in range(80)]
        self.zf = gel(150, b"Bold")

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, r, ph in self.stars:
            if 900 < x < 1350 and 200 < y < 650:
                continue
            a = int(140 + 110 * math.sin(t * 1.7 + ph))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 220, a))
        for k in range(3):
            p = ((t * 0.28 + k / 3) % 1.0)
            x = 700 + p * 380 + 30 * math.sin(p * 8)
            y = 900 - p * 520
            size = 0.5 + p * 0.9
            a = int(255 * math.sin(math.pi * p))
            f = gel(int(110 * size), b"Bold")
            d.text((x, y), "z", font=f, fill=(235, 235, 255, a))
        return img

class Unwind:
    WORD = "unwind"

    def __init__(self):
        img = vgrad(S, S, [(0, (98, 70, 146)), (0.4, (236, 130, 100)), (0.62, (255, 205, 130)),
                           (0.621, (230, 140, 110)), (1, (60, 70, 120))])
        img = glow(img, (800, 990), 230, (255, 220, 150), 0.7)
        d = ImageDraw.Draw(img, "RGBA")
        d.pieslice([640, 830, 960, 1150], 180, 360, fill=(255, 226, 160))
        # sand
        d.polygon([(0, 1600), (0, 1380), (500, 1330), (1100, 1360), (1600, 1310), (1600, 1600)], fill=(232, 190, 140))
        self.trunks = []
        for base_x, lean in [(260, 1), (1340, -1)]:
            pts = [(base_x + lean * 160 * (s ** 2), 1400 - s * 950) for s in np.linspace(0, 1, 30)]
            for i in range(len(pts) - 1):
                d.line([pts[i], pts[i + 1]], fill=(90, 55, 45), width=int(60 - 30 * i / 29))
            tx, ty = pts[-1]
            self.trunks.append(pts)
            for ang in [-160, -130, -100, -70, -40, -15, 15]:
                a = math.radians(ang)
                fr = []
                for s in np.linspace(0, 1, 20):
                    r = s * 380
                    fr.append((tx + r * math.cos(a), ty + r * math.sin(a) + 160 * s * s))
                for i in range(len(fr) - 1):
                    d.line([fr[i], fr[i + 1]], fill=(40, 70, 55), width=int(34 - 26 * i / 19))
        self.base = img
        random.seed(13)
        self.waves = [(random.uniform(0, 1600), random.uniform(1010, 1300), random.uniform(60, 200), random.uniform(0, 6)) for _ in range(45)]

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, ln, ph in self.waves:
            dx = 25 * math.sin(t * 0.9 + ph)
            near = 1 - abs(x - 800) / 900
            a = int((70 + 60 * math.sin(t * 1.4 + ph)) * (0.5 + near))
            d.line([(x + dx, y), (x + dx + ln, y)], fill=(255, 225, 190, max(0, min(255, a))), width=5)
        # hammock between trunks
        A = self.trunks[0][16]
        B = self.trunks[1][16]
        swing = 26 * math.sin(t * 1.2)
        pts = []
        for s in np.linspace(0, 1, 50):
            x = A[0] + (B[0] - A[0]) * s + swing * math.sin(math.pi * s)
            y = A[1] + (B[1] - A[1]) * s + 300 * math.sin(math.pi * s)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=(70, 40, 40), width=6)
        fabric = pts[8:42]
        lower = [(x, y + 70 * math.sin(math.pi * (i / (len(fabric) - 1)))) for i, (x, y) in enumerate(fabric)]
        d.polygon(fabric + lower[::-1], fill=(244, 225, 193))
        for i in range(0, len(fabric), 4):
            d.line([fabric[i], lower[i]], fill=(220, 120, 100), width=6)
        return img

