"""Shared drawing helpers: fonts, gradients, text layout, animated text blocks."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")

INK = (34, 32, 44)
MUTE = (96, 92, 108)
PAPER = (255, 252, 245)

_cache = {}

def inter(weight, size):
    key = ("inter", weight, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FONTS, f"Inter-{weight}.otf"), size)
    return _cache[key]

def gel(size, variation=b"Bold", italic=False):
    key = ("gel", size, variation, italic)
    if key not in _cache:
        f = ImageFont.truetype(os.path.join(FONTS, "Gelasio-Italic[wght].ttf" if italic else "Gelasio[wght].ttf"), size)
        f.set_variation_by_name(variation)
        _cache[key] = f
    return _cache[key]

def dejavu(size):
    return ImageFont.truetype(os.path.join(FONTS, "DejaVuSans.ttf"), size)

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def vgrad(w, h, stops):
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, 3))
    for c in range(3):
        out[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(out[:, None, :], w, axis=1).astype(np.uint8), "RGB")

def glow(img, center, radius, color, strength=0.6):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = center
    ImageDraw.Draw(layer).ellipse([x - radius, y - radius, x + radius, y + radius], fill=color + (int(255 * strength),))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.6))
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")

def render_rich(tokens, width, lh):
    """tokens: list of (word, font, color); wraps to width. Returns an RGBA image."""
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines, cur, cw = [], [], 0
    for w, f, c in tokens:
        tw = probe.textlength(w, font=f)
        sp = probe.textlength(" ", font=f)
        if cur and cw + sp + tw > width:
            lines.append(cur); cur, cw = [], 0
        if cur:
            cw += sp
        cur.append((w, f, c, cw)); cw += tw
    if cur:
        lines.append(cur)
    img = Image.new("RGBA", (width + 20, int(lh * len(lines)) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        for w, f, c, x in line:
            d.text((x, i * lh), w, font=f, fill=c)
    return img

def simple(text, font, color, width=840, lh=None):
    return render_rich([(w, font, color) for w in text.split(" ")], width, lh or int(font.size * 1.35))

def hstack(imgs, gap):
    h = max(i.height for i in imgs)
    out = Image.new("RGBA", (sum(i.width for i in imgs) + gap * (len(imgs) - 1), h), (0, 0, 0, 0))
    x = 0
    for i in imgs:
        out.alpha_composite(i, (x, (h - i.height) // 2))
        x += i.width + gap
    return out

class Block:
    """A pre-rendered text/graphic layer that fades in at t0, optionally out at t1,
    and can cross-fade to an 'alt' image during highlight intervals."""
    def __init__(self, img, x, y, t0, t1=None, alt=None, hi=()):
        def arr(im):
            a = np.asarray(im).astype(np.float32) / 255.0
            return a[..., :3] * 255.0, a[..., 3:4]
        self.rgb, self.a = arr(img)
        self.alt = arr(alt) if alt is not None else None
        self.x, self.y, self.t0, self.t1, self.hi = x, y, t0, t1, list(hi)
        self.h, self.w = self.a.shape[:2]

    def level(self, t):
        p = ease((t - self.t0) / 0.6)
        if self.t1 is not None:
            p *= 1 - ease((t - self.t1) / 0.45)
        return p

    def hl(self, t):
        h = 0.0
        for a, b in self.hi:
            if a - 0.12 <= t <= b + 0.25:
                h = max(h, min(1.0, (t - a + 0.12) / 0.12, (b + 0.25 - t) / 0.25))
        return h

def composite(frame, blocks, t):
    H, W = frame.shape[:2]
    for b in blocks:
        p = b.level(t)
        if p <= 0.003:
            continue
        rgb, a = b.rgb, b.a
        if b.alt is not None:
            h = b.hl(t)
            if h > 0:
                rgb = rgb * (1 - h) + b.alt[0] * h
                a = a * (1 - h) + b.alt[1] * h
        y0 = b.y + int((1 - ease((t - b.t0) / 0.6)) * 24)
        y1 = min(H, y0 + b.h); x1 = min(W, b.x + b.w)
        hh, ww = y1 - y0, x1 - b.x
        if hh <= 0 or ww <= 0:
            continue
        reg = frame[y0:y1, b.x:x1]
        aa = a[:hh, :ww] * p
        frame[y0:y1, b.x:x1] = reg * (1 - aa) + rgb[:hh, :ww] * aa

# ---- paper-style widgets ----
def pill(text, font, fg, bg):
    tw = ImageDraw.Draw(Image.new("RGBA", (5, 5))).textlength(text, font=font)
    h = int(font.size * 1.6)
    im = Image.new("RGBA", (int(tw + 44), h + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, tw + 43, h + 5], h // 2, fill=INK)
    d.rounded_rectangle([0, 0, tw + 39, h], h // 2, fill=bg, outline=INK, width=3)
    d.text((20 + tw / 2, h / 2), text, font=font, fill=fg, anchor="mm")
    return im

def chip(text, stressed, on, accent):
    f = inter("Bold", 60) if stressed else inter("Medium", 46)
    tw = ImageDraw.Draw(Image.new("RGBA", (5, 5))).textlength(text, font=f)
    w, h = int(tw + 64), 100
    im = Image.new("RGBA", (w + 6, h + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, w + 5, h + 5], 24, fill=INK)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 24, fill=accent if on else PAPER, outline=INK, width=4)
    col = PAPER if on else (accent if stressed else INK)
    d.text((w / 2, h / 2), text, font=f, fill=col, anchor="mm")
    return im

def ring(prog, pulse, accent):
    s = 72; c = s
    im = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = 30 + 4 * pulse
    d.ellipse([c - r * 2, c - r * 2, c + r * 2, c + r * 2], fill=PAPER + (255,), outline=INK + (255,), width=6)
    if prog > 0:
        d.arc([c - r * 2 + 6, c - r * 2 + 6, c + r * 2 - 6, c + r * 2 - 6], -90, -90 + 360 * prog, fill=tuple(accent) + (255,), width=12)
    d.rounded_rectangle([c - 12, c - 30, c + 12, c + 10], 12, fill=INK + (255,))
    d.arc([c - 22, c - 14, c + 22, c + 24], 0, 180, fill=INK + (255,), width=6)
    d.line([c, c + 24, c, c + 34], fill=INK + (255,), width=6)
    return im.reduce(2)
