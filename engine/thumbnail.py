"""Custom YouTube thumbnail (1280x720) for the weekly long video."""
import numpy as np
from PIL import Image, ImageDraw
from engine.common import INK, MUTE, PAPER, inter, gel
from engine.art import get_art

W, H = 1280, 720
NEUTRAL = (244, 236, 222)

def _sticker(img, size, angle, border=10, shadow=12, radius=40):
    """Picture in a rounded frame with an ink border and hard shadow, rotated."""
    s = size
    pic = img.resize((s, s), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius, fill=255)
    tile = Image.new("RGBA", (s + shadow, s + shadow), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle([shadow, shadow, s + shadow - 1, s + shadow - 1], radius, fill=INK + (255,))
    tile.paste(pic, (0, 0), mask)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius, outline=INK + (255,), width=border)
    return tile.rotate(angle, resample=Image.BICUBIC, expand=True)

def make_long_thumbnail(words, path):
    rng = np.random.default_rng(5)
    arr = np.ones((H, W, 3), np.float32) * np.array(NEUTRAL, np.float32)
    arr += rng.normal(0, 4, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for y in range(24, H, 40):
        for x in range(24, W, 40):
            if x < 640:
                continue
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=INK + (40,))

    # right: three overlapping picture stickers
    frames = [get_art(w["word"]).frame(3.0).reduce(2) for w in words[:3]]
    spots = [(820, 40, 330, -6), (690, 300, 300, 5), (960, 330, 300, -3)]
    for img, (x, y, s, ang) in zip(frames, spots):
        im.alpha_composite(_sticker(img, s, ang), (x, y))

    # left: big text
    d = ImageDraw.Draw(im)
    tag = "DAILY ENGLISH"
    ft = inter("Bold", 30)
    tw = d.textlength(tag, font=ft)
    d.rounded_rectangle([60, 56, 60 + tw + 44, 108], 26, fill=INK)
    d.text((82, 82), tag, font=ft, fill=PAPER, anchor="lm")
    n = len(words)
    d.text((54, 118), f"{n} English", font=gel(104, b"Bold"), fill=INK)
    d.text((54, 228), "Words", font=gel(104, b"Bold"), fill=INK)
    acc0 = tuple(words[0]["accent"])
    d.text((58, 352), "with pronunciation", font=gel(40, b"Bold Italic", italic=True), fill=acc0)
    # word pills
    x, y = 58, 430
    fp = inter("Bold", 34)
    for w in words:
        t = w["word"]
        pw = d.textlength(t, font=fp) + 44
        if x + pw > 640:
            x, y = 58, y + 76
        acc = tuple(w["accent"])
        d.rounded_rectangle([x + 5, y + 5, x + pw + 5, y + 60], 30, fill=INK)
        d.rounded_rectangle([x, y, x + pw, y + 55], 30, fill=acc, outline=INK, width=4)
        d.text((x + pw / 2, y + 28), t, font=fp, fill=PAPER, anchor="mm")
        x += pw + 18
    d.text((58, y + 84), f"Học {n} từ vựng tiếng Anh", font=inter("SemiBold", 32), fill=MUTE)
    im.convert("RGB").save(path, "PNG", optimize=True)
    return path
