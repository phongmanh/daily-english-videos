"""Weekly long video (1920x1080): title, one scene per word, 'repeat after me' review, outro."""
import math, os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from engine.common import (INK, MUTE, PAPER, inter, gel, dejavu, ease, simple, render_rich, hstack,
                           Block, composite, pill, chip, ring)
from engine.art import get_art
from engine import voice, music
from engine.media import render_frames, concat, write_wav, mux

W, H, FPS = 1920, 1080, 30
PS, PX, PY = 800, 110, 132
TX, TW = 1010, 810
NEUTRAL = (244, 236, 222)
NEUTRAL_ACC = (186, 78, 46)

def _paper(bg, panel=True, skip=None):
    rng = np.random.default_rng(3)
    arr = np.ones((H, W, 3), np.float32) * np.array(bg, np.float32)
    arr += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(30, H, 48):
        for x in range(30, W, 48):
            if skip and skip(x, y):
                continue
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=INK + (36,))
    if panel:
        d.rounded_rectangle([PX + 16, PY + 16, PX + PS + 16, PY + PS + 16], 44, fill=INK + (255,))
    return np.asarray(im.convert("RGB")).astype(np.float32)

def _masks():
    m = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 84, fill=255)
    b = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(b).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 84, outline=255, width=14)
    f = lambda im: (np.asarray(im.reduce(2)).astype(np.float32) / 255.0)[..., None]
    return f(m), f(b)

def _fade(f, t, dur, bgc, fout=0.5):
    k = min(1.0, t / 0.5, max(0.0, (dur - t) / fout))
    return f if k >= 1 else f * k + bgc * (1 - k)

def _boxed(w, h, fill=(255, 252, 245, 245), r=26, shadow=8, outline=4):
    im = Image.new("RGBA", (w + shadow, h + shadow), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([shadow, shadow, w + shadow - 1, h + shadow - 1], r, fill=INK)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill, outline=INK, width=outline)
    return im, d

def _card(wd, accent):
    pad = 30
    note = render_rich([(x, inter("Regular", 30), INK) for x in wd["note"].split(" ")], TW - 2 * pad, 42)
    note = note.crop((0, 0, note.width, note.getbbox()[3] + 4))
    chips_y, like_y = 108, 108 + 100 + 32
    note_y = like_y + 66
    im, d = _boxed(TW, note_y + note.height + 24)
    d.text((pad, 24), "PRONUNCIATION  ·  PHÁT ÂM", font=inter("SemiBold", 24), fill=MUTE)
    fl = inter("Regular", 34)
    d.text((pad, like_y), "Sounds like:", font=fl, fill=MUTE)
    x = pad + d.textlength("Sounds like:  ", font=fl)
    for s, strong in wd["like"]:
        f = inter("Bold", 40) if strong else inter("Medium", 38)
        d.text((x, like_y - (3 if strong else 0)), s, font=f, fill=accent if strong else INK)
        x += d.textlength(s, font=f)
    im.alpha_composite(note, (pad, note_y))
    chips, cx = [], pad
    for j, s in enumerate(wd["chips"]):
        st = j == wd["stress"]
        off, on = chip(s, st, False, accent), chip(s, st, True, accent)
        chips.append((off, on, cx, chips_y))
        if st:
            d.ellipse([cx + 4, chips_y - 30, cx + 16, chips_y - 18], fill=accent)
            d.text((cx + 26, chips_y - 24), "STRESS" if len(wd["chips"]) > 1 else "1 SYLLABLE",
                   font=inter("SemiBold", 20), fill=accent, anchor="lm")
        cx += off.width
        if j < len(wd["chips"]) - 1:
            d.text((cx + 20, chips_y + 50), "·", font=inter("Bold", 50), fill=MUTE, anchor="mm")
            cx += 40
    return im, chips

def _tipbox(text, accent):
    body = render_rich([("Tip:", inter("Bold", 29), accent)] + [(w, inter("Regular", 29), INK) for w in text.split(" ")], TW - 60, 42)
    body = body.crop((0, 0, body.width, body.getbbox()[3] + 4))
    im, d = _boxed(TW, body.height + 44, fill=(255, 252, 245, 235), r=22, shadow=6, outline=3)
    im.alpha_composite(body, (30, 22))
    return im

def word_scene(i, n, wd, dur, mk):
    accent, bg = tuple(wd["accent"]), tuple(wd["bg"])
    BGA = _paper(bg, skip=lambda x, y: x > TX - 40)
    MASK, BORDER = _masks()
    art = get_art(wd["word"])
    first = lambda k: mk[k][0][0]
    hi = mk["word"]
    p1_in, p2_in = first("listen") - 0.2, first("pos")
    p1_out = p2_in - 0.5
    blocks, y = [], 0
    blocks.append(Block(pill(f"WORD {i + 1} / {n}", inter("Bold", 24), PAPER, INK), TX, y, max(0.2, first("label") - 0.2))); y += 62
    wf = gel(124, b"Bold")
    blocks.append(Block(simple(wd["word"], wf, INK, 900, 150), TX - 4, y, first("word") - 0.3,
                        alt=simple(wd["word"], wf, accent, 900, 150), hi=hi)); y += 160
    ipa = simple(wd["ipa"], dejavu(40), MUTE)
    row = hstack([ipa.crop(ipa.getbbox()), pill(wd["pos"], inter("SemiBold", 26), PAPER, accent)], 26)
    blocks.append(Block(row, TX, y, first("word") + 0.6)); y += row.height + 28
    top_end = y
    cd, chips = _card(wd, accent)
    blocks.append(Block(cd, TX, y, p1_in, p1_out))
    for j, (off, on, cx, cy) in enumerate(chips):
        h2 = list(mk.get(f"syl{j}", [])) + [iv for iv in hi if iv[0] > p1_in]
        blocks.append(Block(off, TX + cx, y + cy, p1_in, p1_out, alt=on, hi=h2))
    ty = y + cd.height + 24
    tr = Image.new("RGBA", (TW, 80), (0, 0, 0, 0))
    td = ImageDraw.Draw(tr)
    fb = inter("Bold", 34)
    td.text((96, 20), "Your turn: say it out loud!", font=fb, fill=INK)
    td.text((96 + td.textlength("Your turn: say it out loud!  ", font=fb), 25), "Đến lượt bạn!", font=inter("Medium", 30), fill=accent)
    turn_in = first("turn_say") - 0.1
    blocks.append(Block(tr, TX, ty, turn_in, p1_out))
    ring_pos = [TX + 8, ty + 4]
    ta, tb = mk["turn"][0]
    p1_end = ty + 80
    y = top_end
    vi = render_rich([("Tiếng Việt:", inter("Regular", 36), MUTE)] + [(x, inter("Bold", 38), accent) for x in wd["vi"].split(" ")], TW, 50)
    blocks.append(Block(vi, TX, y, p2_in + 1.0)); y += vi.getbbox()[3] + 22
    blocks.append(Block(Image.new("RGBA", (TW, 4), INK + (60,)), TX, y, p2_in + 1.3)); y += 26
    blocks.append(Block(simple("MEANING", inter("Bold", 22), MUTE), TX, y, first("meaning") - 0.3)); y += 36
    mm = simple(wd["meaning"], inter("Regular", 36), INK, TW, 50)
    blocks.append(Block(mm, TX, y, first("meaning") - 0.1)); y += mm.getbbox()[3] + 22
    blocks.append(Block(simple("EXAMPLE", inter("Bold", 22), MUTE), TX, y, first("example") - 0.3)); y += 36
    toks = []
    for x in wd["example"].split(" "):
        hit = x.strip(".,!?\"'").lower() in wd["forms"]
        toks.append((x, inter("BoldItalic" if hit else "Italic", 36), accent if hit else INK))
    ex = render_rich(toks, TW, 50)
    blocks.append(Block(ex, TX, y, first("example") - 0.1)); y += ex.getbbox()[3] + 26
    tb_ = _tipbox(wd["tip"], accent)
    blocks.append(Block(tb_, TX, y, first("tip") - 0.1)); y += tb_.height
    off = int((PY + PS / 2) - max(p1_end, y) / 2)
    for b in blocks:
        b.y += off
    ring_pos[1] += off
    bgc = np.array(bg, np.float32); inkc = np.array(INK, np.float32)

    def draw(t):
        f = BGA.copy()
        ill = art.frame(t).reduce(2)
        nw = int(PS * (1.0 + 0.04 * (t / dur)))
        if nw > PS:
            o = (nw - PS) // 2
            ill = ill.resize((nw, nw), Image.BILINEAR).crop((o, o, o + PS, o + PS))
        pa = np.asarray(ill).astype(np.float32)
        reg = f[PY:PY + PS, PX:PX + PS]
        reg = reg * (1 - MASK) + pa * MASK
        f[PY:PY + PS, PX:PX + PS] = reg * (1 - BORDER) + inkc * BORDER
        composite(f, blocks, t)
        vis = ease((t - turn_in) / 0.6) * (1 - ease((t - p1_out) / 0.45))
        if vis > 0.003:
            prog = min(1.0, max(0.0, (t - ta) / (tb - ta)))
            pulse = 0.5 + 0.5 * math.sin(t * 6) if ta <= t <= tb else 0
            a = np.asarray(ring(prog, pulse, accent)).astype(np.float32) / 255.0
            x0, y0 = ring_pos; hh, ww = a.shape[:2]
            reg = f[y0:y0 + hh, x0:x0 + ww]
            aa = a[..., 3:4] * vis
            f[y0:y0 + hh, x0:x0 + ww] = reg * (1 - aa) + a[..., :3] * 255 * aa
        return _fade(f, t, dur, bgc)
    return draw

def _centered(text, font, color, y, t0):
    tw = ImageDraw.Draw(Image.new("RGB", (5, 5))).textlength(text, font=font)
    return Block(simple(text, font, color, 1800, int(font.size * 1.25)), int((W - tw) / 2), y, t0)

def title_scene(words, dur, mk):
    first = lambda k: mk[k][0][0]
    n = len(words)
    BGA = _paper(NEUTRAL, panel=False, skip=lambda x, y: 280 < y < 700 and 200 < x < 1720)
    tag = pill("DAILY ENGLISH  ·  WEEKLY REVIEW", inter("Bold", 30), PAPER, INK)
    blocks = [Block(tag, (W - tag.width) // 2, 300, first("intro") - 0.2),
              _centered(f"This Week's {n} Words", gel(124, b"Bold"), INK, 390, first("intro") + 0.3),
              _centered(" · ".join(w["word"] for w in words), gel(44, b"Bold Italic", italic=True), NEUTRAL_ACC, 560, first("sub") - 0.3),
              _centered(f"{n} từ vựng tiếng Anh tuần này  ·  Listen & repeat", inter("Medium", 38), MUTE, 640, first("sub") + 0.4)]
    sw = Image.new("RGBA", (n * 114, 98), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sw)
    for k, w in enumerate(words):
        x = k * 114
        sd.rounded_rectangle([x + 6, 6, x + 95, 95], 20, fill=INK)
        sd.rounded_rectangle([x, 0, x + 89, 89], 20, fill=tuple(w["accent"]), outline=INK, width=4)
    blocks.append(Block(sw, (W - sw.width) // 2, 760, first("sub") + 0.8))
    bgc = np.array(NEUTRAL, np.float32)
    def draw(t):
        f = BGA.copy(); composite(f, blocks, t); return _fade(f, t, dur, bgc)
    return draw

def review_scene(words, dur, mk):
    first = lambda k: mk[k][0][0]
    BGA = _paper(NEUTRAL, panel=False, skip=lambda x, y: 100 < y < 1000 and 200 < x < 1720)
    blocks = [Block(simple("Repeat after me · Đọc theo nhé", gel(70, b"Bold"), INK, 1600, 90), 250, 110, first("head") - 0.2)]
    step = min(140, 700 // max(1, len(words)))
    for i, w in enumerate(words):
        y = 270 + i * step
        t0 = first(f"r{i}") - 0.4
        acc = tuple(w["accent"])
        circ = Image.new("RGBA", (78, 78), (0, 0, 0, 0))
        cd = ImageDraw.Draw(circ)
        cd.ellipse([6, 6, 77, 77], fill=INK); cd.ellipse([0, 0, 71, 71], fill=acc, outline=INK, width=4)
        cd.text((36, 36), str(i + 1), font=inter("Bold", 32), fill=PAPER, anchor="mm")
        wf = gel(64, b"Bold")
        blocks.append(Block(circ, 250, y + 4, t0))
        blocks.append(Block(simple(w["word"], wf, INK, 600, 80), 360, y - 10, t0, alt=simple(w["word"], wf, acc, 600, 80), hi=mk[f"r{i}"]))
        blocks.append(Block(simple("".join(s for s, _ in w["like"]), inter("SemiBold", 34), MUTE, 400), 800, y + 14, t0 + 0.15))
        blocks.append(Block(simple(w["vi"], inter("Bold", 36), acc, 800), 1130, y + 12, t0 + 0.3))
    bgc = np.array(NEUTRAL, np.float32)
    def draw(t):
        f = BGA.copy(); composite(f, blocks, t); return _fade(f, t, dur, bgc)
    return draw

def outro_scene(dur, mk):
    first = lambda k: mk[k][0][0]
    BGA = _paper(NEUTRAL, panel=False, skip=lambda x, y: 380 < y < 640 and 150 < x < 1770)
    blocks = [_centered("Great job! Use one of these words today.", gel(64, b"Bold"), INK, 420, first("l1") - 0.2),
              _centered("Hãy thử đặt một câu với một từ hôm nay nhé!", inter("Medium", 40), NEUTRAL_ACC, 530, first("l2") - 0.1)]
    bgc = np.array(NEUTRAL, np.float32)
    def draw(t):
        f = BGA.copy(); composite(f, blocks, t); return _fade(f, t, dur, bgc, fout=1.0)
    return draw

def render_long(words, out_path, seed=0):
    """Returns (total duration, chapters [(seconds, label)])."""
    tracks = voice.long_tracks(words, intro=f"Here are this week's {len(words)} words. Listen, and repeat after me.")
    order = ["title"] + [f"w{i}" for i in range(len(words))] + ["review", "outro"]
    with tempfile.TemporaryDirectory() as tmp:
        parts, audio_parts, chapters, t = [], [], [], 0.0
        for name in order:
            audio, dur, mk = tracks[name]
            dur = round(dur * FPS) / FPS
            if name == "title":
                draw = title_scene(words, dur, mk); label = "Intro"
            elif name == "review":
                draw = review_scene(words, dur, mk); label = "Repeat after me"
            elif name == "outro":
                draw = outro_scene(dur, mk); label = None
            else:
                i = int(name[1:]); wd = words[i]
                draw = word_scene(i, len(words), wd, dur, mk); label = f"{wd['word']} – {wd['vi']}"
            if label:
                chapters.append((t, label))
            p = os.path.join(tmp, f"{name}.mp4")
            render_frames(p, draw, dur, W, H, FPS)
            parts.append(p)
            buf = np.zeros(int(dur * voice.SR), np.float32)
            buf[:min(len(buf), len(audio))] = audio[:len(buf)]
            audio_parts.append(buf)
            t += dur
        vid = os.path.join(tmp, "v.mp4")
        concat(parts, vid)
        wav = os.path.join(tmp, "a.wav")
        write_wav(wav, music.mix_with_voice(np.concatenate(audio_parts), voice.SR, t, seed=seed))
        mux(vid, wav, out_path)
    return t, chapters
