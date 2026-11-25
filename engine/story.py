"""Story Short (1080x1920, 30 fps): a tiny story built from words we already taught.

Each line of the story uses one word. The line is read, the words light up as they are
spoken, then the word is said once more on its own while a small card shows the
Vietnamese meaning. Ends with a quick "do you remember?" recap of all the words.

story dict:
  {"title": "A Rainy Evening",
   "lines": [{"word": "cozy", "text": "It was raining, but Mai's room was warm and cozy.",
              "say": "It was raining, but Mai's room was warm, and cozy."}, ...]}
"say" is optional (only needed when the spoken text should differ, e.g. extra commas).
"""
import math, os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from engine.common import INK, MUTE, PAPER, inter, gel, dejavu, ease, simple, Block, composite, pill
from engine.art import get_art
from engine import voice, music
from engine.media import render_frames, write_wav, mux

W, H, FPS = 1080, 1920, 30
PS = 720
PX, PY = (W - PS) // 2 - 7, 220
X0, TW = 96, 888
TEXT_Y = PY + PS + 120
DIM = (178, 170, 160)


def _paper(bg):
    rng = np.random.default_rng(11)
    arr = np.ones((H, W, 3), np.float32) * np.array(bg, np.float32)
    arr += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(40, H, 48):
        for x in range(36, W, 48):
            if (y > PY + PS + 30 and 60 < x < 1020) or (80 < y < 180 and 200 < x < 880):
                continue
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=INK + (38,))
    d.rounded_rectangle([PX + 16, PY + 16, PX + PS + 16, PY + PS + 16], 40, fill=INK + (255,))
    return np.asarray(im.convert("RGB")).astype(np.float32)


def _header(accent):
    f = inter("Bold", 30); f2 = gel(36, b"Bold Italic", italic=True)
    t1, t2 = "DAILY ENGLISH", "story time"
    probe = ImageDraw.Draw(Image.new("RGBA", (5, 5)))
    w1, w2 = probe.textlength(t1, font=f), probe.textlength(t2, font=f2)
    im = Image.new("RGBA", (int(w1 + 72 + w2 + 10), 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 4, w1 + 48, 60], 28, fill=INK)
    d.text((24, 32), t1, font=f, fill=PAPER, anchor="lm")
    d.text((w1 + 72, 30), t2, font=f2, fill=accent, anchor="lm")
    return im


def _masks():
    m = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 76, fill=255)
    b = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(b).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 76, outline=255, width=14)
    f = lambda im: (np.asarray(im.reduce(2)).astype(np.float32) / 255.0)[..., None]
    return f(m), f(b)


def _is_hit(token, forms):
    return token.strip(".,!?\"'…").lower() in forms


def _karaoke(text, forms, accent, width=TW):
    """Lay out a sentence. Returns (dim RGBA, lit RGBA, [(x0, x1, y0, y1, char_start, char_end)])."""
    fn, fb = gel(64, b"Regular"), gel(64, b"Bold")
    lh = 90
    probe = ImageDraw.Draw(Image.new("RGBA", (5, 5)))
    toks, pos = [], 0
    for w in text.split(" "):
        toks.append((w, pos, pos + len(w))); pos += len(w) + 1
    lines, cur, cw = [], [], 0
    for w, a, b in toks:
        f = fb if _is_hit(w, forms) else fn
        tw, sp = probe.textlength(w, font=f), probe.textlength(" ", font=fn)
        if cur and cw + sp + tw > width:
            lines.append((cur, cw)); cur, cw = [], 0
        if cur:
            cw += sp
        cur.append((w, f, cw, tw, a, b)); cw += tw
    lines.append((cur, cw))
    size = (width + 20, lh * len(lines) + 30)
    dim, lit = Image.new("RGBA", size, (0, 0, 0, 0)), Image.new("RGBA", size, (0, 0, 0, 0))
    dd, dl = ImageDraw.Draw(dim), ImageDraw.Draw(lit)
    boxes = []
    for i, (line, lw) in enumerate(lines):
        off = (width - lw) / 2
        for w, f, x, tw, a, b in line:
            hit = _is_hit(w, forms)
            xx, yy = off + x, i * lh
            dd.text((xx, yy), w, font=f, fill=DIM)
            if hit:
                dl.rounded_rectangle([xx - 6, yy + 70, xx + tw + 6, yy + 80], 5, fill=accent + (90,))
            dl.text((xx, yy), w, font=f, fill=accent if hit else INK)
            boxes.append((int(xx) - 8, int(xx + tw) + 10, yy, yy + lh, a, b))
    return dim, lit, boxes


def _word_card(wd, accent):
    w = 700
    vi = simple(wd["vi"], inter("Bold", 38), accent, w - 60, 50)
    vi = vi.crop((0, 0, vi.width, vi.getbbox()[3] + 4))
    h = 120 + vi.height + 26
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, w + 7, h + 7], 26, fill=INK)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=PAPER, outline=INK, width=4)
    d.text((30, 26), wd["word"], font=gel(58, b"Bold"), fill=INK)
    x = 30 + d.textlength(wd["word"] + "  ", font=gel(58, b"Bold"))
    d.text((x, 44), wd["ipa"], font=dejavu(34), fill=MUTE)
    pl = pill(wd["pos"], inter("SemiBold", 24), PAPER, accent)
    im.alpha_composite(pl, (w - pl.width - 24, 34))
    im.alpha_composite(vi, (30, 118))
    return im


def _recap_grid(words):
    cw, ch, gap = 420, 170, 28
    rows = (len(words) + 1) // 2
    im = Image.new("RGBA", (cw * 2 + gap + 8, rows * (ch + gap)), (0, 0, 0, 0))
    cells = []
    for i, wd in enumerate(words):
        acc = tuple(wd["accent"])
        x, y = (i % 2) * (cw + gap), (i // 2) * (ch + gap)
        for on in (False, True):
            c = Image.new("RGBA", (cw + 8, ch + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(c)
            d.rounded_rectangle([8, 8, cw + 7, ch + 7], 24, fill=INK)
            d.rounded_rectangle([0, 0, cw - 1, ch - 1], 24, fill=acc if on else PAPER, outline=INK, width=4)
            d.text((cw / 2, 58), wd["word"], font=gel(54, b"Bold"), fill=PAPER if on else INK, anchor="mm")
            vi = wd["vi"].split(",")[0]
            d.text((cw / 2, 124), vi, font=inter("SemiBold", 32), fill=PAPER if on else acc, anchor="mm")
            cells.append((i, on, c, x, y))
    return im.size, cells


def story_track(story, words):
    tr = voice.Track(0.4)
    tr.add("intro", voice.say(f"A short story. Listen for {voice.NUM[len(words) - 1]} words you know."), 0.7)
    for i, (ln, wd) in enumerate(zip(story["lines"], words)):
        tr.add(f"l{i}", voice.say(ln.get("say", ln["text"])), 0.55)
        tr.add(f"w{i}", voice.say(wd["ph"], ph=True), 1.0)
    tr.add("recap", voice.say("Do you remember them?"), 0.35)
    for i, wd in enumerate(words):
        tr.add(f"r{i}", voice.say(wd["ph"], ph=True), 0.55)
    tr.gap(0.3)
    tr.add("follow", voice.say("Follow for a new story every week!"), 0.0)
    audio, dur = tr.render(1.6)
    return audio, dur, tr.marks


def _speech_span(a, b):
    """Kokoro adds a little silence at both ends; trim it for the word timing estimate."""
    return a + 0.12, b - 0.15


def build_scene(story, words, dur, mk):
    n = len(words)
    first = lambda k: mk[k][0][0]
    line_t = [first(f"l{i}") for i in range(n)]
    recap_t = first("recap")
    bgs = [_paper(tuple(w["bg"])) for w in words]
    neutral = _paper((244, 236, 222))
    MASK, BORDER = _masks()
    arts = [get_art(w["word"]) for w in words]
    inkc = np.array(INK, np.float32)

    # scene index over time: line i owns [line_t[i] - 0.4, line_t[i+1] - 0.4)
    starts = [line_t[0] - 0.4] + [t - 0.4 for t in line_t[1:]]

    def scene_mix(t):
        """(index a, index b, mix) for cross-fading art/background between scenes."""
        if t < starts[0]:
            return 0, 0, 0.0
        for i in range(n - 1, -1, -1):
            if t >= starts[i]:
                if i > 0 and t < starts[i] + 0.6:
                    return i - 1, i, ease((t - starts[i]) / 0.6)
                return i, i, 0.0
        return 0, 0, 0.0

    blocks = []
    # header (static, from frame 0)
    hd = _header(tuple(words[0]["accent"]))
    blocks.append(Block(hd, (W - hd.width) // 2, 100, -1.0))

    # title (cover) — shown on frame 0, leaves when the first line starts
    tt = gel(84, b"Bold")
    title = simple(story["title"], tt, INK, TW, 100)
    title = title.crop((0, 0, title.width, title.getbbox()[3] + 6))
    blocks.append(Block(title, X0 + (TW - title.getbbox()[2]) // 2, TEXT_Y - 20, -1.0, line_t[0] - 0.8))
    y = TEXT_Y + title.height + 24
    for txt, fnt, col in [(f"A tiny story with {n} words", inter("Medium", 38), MUTE),
                          ("  ·  ".join(w["word"] for w in words), inter("Bold", 40), tuple(words[0]["accent"]))]:
        sb = simple(txt, fnt, col, 2000, 52)
        sb = sb.crop(sb.getbbox())
        blocks.append(Block(sb, (W - sb.width) // 2, y, -1.0, line_t[0] - 0.8)); y += sb.height + 22

    # per line: karaoke text + word card
    lines = []
    for i, (ln, wd) in enumerate(zip(story["lines"], words)):
        acc = tuple(wd["accent"])
        dim, lit, boxes = _karaoke(ln["text"], wd["forms"], acc)
        end = (line_t[i + 1] - 0.5) if i + 1 < n else recap_t - 0.4
        a, b = _speech_span(*mk[f"l{i}"][0])
        nchar = len(ln["text"])
        lines.append(dict(dim=np.asarray(dim).astype(np.float32) / 255.0,
                          lit=np.asarray(lit).astype(np.float32) / 255.0,
                          boxes=[(x0, x1, y0, y1, a + (b - a) * c0 / nchar, a + (b - a) * c1 / nchar)
                                 for x0, x1, y0, y1, c0, c1 in boxes],
                          t0=line_t[i] - 0.3, t1=end, y=TEXT_Y - 10))
        card = _word_card(wd, acc)
        blocks.append(Block(card, (W - card.width) // 2, TEXT_Y + dim.height + 40, first(f"w{i}") - 0.15, end))
        # progress dots under the picture
        dots = Image.new("RGBA", (n * 44, 24), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dots)
        for j in range(n):
            col = tuple(words[j]["accent"]) if j <= i else INK + (60,)
            r = 9 if j == i else 6
            dd.ellipse([j * 44 + 12 - r, 12 - r, j * 44 + 12 + r, 12 + r], fill=col)
        blocks.append(Block(dots, (W - dots.width) // 2, PY + PS + 50, line_t[i] - 0.3, end))

    # recap
    rh = simple("Do you remember? · Bạn còn nhớ không?", inter("Bold", 40), INK, TW, 54)
    blocks.append(Block(rh, X0 + (TW - rh.getbbox()[2]) // 2, TEXT_Y - 30, recap_t - 0.1))
    (gw, gh), cells = _recap_grid(words)
    gx, gy = (W - gw) // 2, TEXT_Y + 60
    for i, on, c, x, y in cells:
        if not on:
            blocks.append(Block(c, gx + x, gy + y, recap_t + 0.1 * i))
    for i, on, c, x, y in cells:
        if on:
            a, b = mk[f"r{i}"][0]
            blocks.append(Block(c, gx + x, gy + y, a - 0.1, b + 0.35))

    BW = 660
    fbn = Image.new("RGBA", (BW + 8, 104), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fbn)
    fd.rounded_rectangle([8, 8, BW + 7, 103], 48, fill=INK)
    fd.rounded_rectangle([0, 0, BW - 1, 95], 48, fill=tuple(words[-1]["accent"]), outline=INK, width=4)
    fd.text((BW / 2, 48), "Follow for a new story every week", font=inter("Bold", 32), fill=PAPER, anchor="mm")
    blocks.append(Block(fbn, (W - BW) // 2, PY + PS - 140, first("follow") - 0.2))

    def draw_line(f, L, t):
        p = ease((t - L["t0"]) / 0.5) * (1 - ease((t - L["t1"]) / 0.45))
        if p <= 0.003:
            return
        dim, lit = L["dim"], L["lit"]
        hh, ww = dim.shape[:2]
        y0 = L["y"] + int((1 - ease((t - L["t0"]) / 0.5)) * 20)
        lvl = np.zeros((hh, ww, 1), np.float32)
        for x0, x1, by0, by1, s0, s1 in L["boxes"]:
            k = ease((t - s0) / max(0.12, (s1 - s0)))
            if k > 0:
                lvl[by0:by1, max(0, x0):x1] = k
        rgb = dim[..., :3] * (1 - lvl) + lit[..., :3] * lvl
        a = np.maximum(dim[..., 3:4] * (1 - lvl), lit[..., 3:4] * lvl) * p
        x = X0 - 10
        reg = f[y0:y0 + hh, x:x + ww]
        f[y0:y0 + hh, x:x + ww] = reg * (1 - a) + rgb * 255 * a

    def art_img(i, t):
        ill = arts[i].frame(t).reduce(2)
        z = 1.0 + 0.05 * min(1.0, max(0.0, (t - starts[i]) / 8.0))
        nw = int(800 * z); o = (nw - 800) // 2
        ill = ill.resize((nw, nw), Image.BILINEAR).crop((o, o, o + 800, o + 800)).resize((PS, PS), Image.BILINEAR)
        return np.asarray(ill).astype(np.float32)

    def draw(t):
        ia, ib, m = scene_mix(t)
        if t >= recap_t - 0.4:
            k = ease((t - recap_t + 0.4) / 0.8)
            f = bgs[-1] * (1 - k) + neutral * k
        elif ia == ib:
            f = bgs[ia].copy()
        else:
            f = bgs[ia] * (1 - m) + bgs[ib] * m
        pa = art_img(ia, t) if ia == ib else art_img(ia, t) * (1 - m) + art_img(ib, t) * m
        reg = f[PY:PY + PS, PX:PX + PS]
        reg = reg * (1 - MASK) + pa * MASK
        f[PY:PY + PS, PX:PX + PS] = reg * (1 - BORDER) + inkc * BORDER
        composite(f, blocks, t)
        for L in lines:
            draw_line(f, L, t)
        # no fade-in: frame 0 is the cover
        k = min(1.0, max(0.0, (dur - t) / 0.6))
        if k < 1:
            f = f * k + neutral * (1 - k)
        return f
    return draw


def render_story(story, words, out_path, music_seed=0, preview_png=None, preview_times=None, preview_dir=None):
    audio, dur, marks = story_track(story, words)
    dur = round(dur * FPS) / FPS
    draw = build_scene(story, words, dur, marks)
    if preview_times is not None:
        for name, fn in preview_times.items():
            Image.fromarray(draw(fn(marks)).clip(0, 255).astype(np.uint8)).save(os.path.join(preview_dir, f"{name}.png"))
        return dur, marks
    with tempfile.TemporaryDirectory() as tmp:
        vid = os.path.join(tmp, "v.mp4")
        render_frames(vid, draw, dur, W, H, FPS)
        if preview_png:
            Image.fromarray(draw(marks["w0"][0][0] + 0.6).clip(0, 255).astype(np.uint8)).save(preview_png)
        mix = music.mix_with_voice(audio, voice.SR, dur, seed=music_seed)
        wav = os.path.join(tmp, "a.wav")
        write_wav(wav, mix)
        mux(vid, wav, out_path)
    return dur, marks
