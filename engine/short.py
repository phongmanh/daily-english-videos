"""Render one vertical Short (1080x1920, 30 fps) for a word."""
import math, os, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw
from engine.common import (INK, MUTE, PAPER, inter, gel, dejavu, ease, simple, render_rich, hstack,
                           Block, composite, pill, chip, ring)
from engine.art import get_art
from engine import voice, music

W, H, FPS = 1080, 1920, 30
X0, TWS = 96, 860
PS = 720
PX, PY = (W - PS) // 2 - 7, 220

def _paper_bg(bg, accent):
    rng = np.random.default_rng(7)
    arr = np.ones((H, W, 3), np.float32) * np.array(bg, np.float32)
    arr += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(40, H, 48):
        for x in range(36, W, 48):
            if (y > PY + PS + 30 and 60 < x < 1000) or (80 < y < 180 and 200 < x < 880):
                continue
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=INK + (38,))
    d.rounded_rectangle([PX + 16, PY + 16, PX + PS + 16, PY + PS + 16], 40, fill=INK + (255,))
    f = inter("Bold", 30); f2 = gel(36, b"Bold Italic", italic=True)
    t1, t2 = "DAILY ENGLISH", "word of the day"
    w1, w2 = d.textlength(t1, font=f), d.textlength(t2, font=f2)
    x = (W - (w1 + 72 + w2)) / 2
    d.rounded_rectangle([x, 104, x + w1 + 48, 160], 28, fill=INK + (255,))
    d.text((x + 24, 132), t1, font=f, fill=PAPER, anchor="lm")
    d.text((x + w1 + 72, 130), t2, font=f2, fill=accent, anchor="lm")
    return np.asarray(im.convert("RGB")).astype(np.float32)

def _masks():
    m = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 76, fill=255)
    b = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(b).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 76, outline=255, width=14)
    f = lambda im: (np.asarray(im.reduce(2)).astype(np.float32) / 255.0)[..., None]
    return f(m), f(b)

def _card(wd, accent):
    pad = 30
    chips_y, like_y = 108, 108 + 100 + 32
    ch = like_y + 66
    im = Image.new("RGBA", (TWS + 8, ch + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, TWS + 7, ch + 7], 26, fill=INK)
    d.rounded_rectangle([0, 0, TWS - 1, ch - 1], 26, fill=(255, 252, 245, 245), outline=INK, width=4)
    d.text((pad, 24), "PRONUNCIATION  ·  PHÁT ÂM", font=inter("SemiBold", 24), fill=MUTE)
    fl = inter("Regular", 34)
    d.text((pad, like_y), "Sounds like:", font=fl, fill=MUTE)
    x = pad + d.textlength("Sounds like:  ", font=fl)
    for s, strong in wd["like"]:
        f = inter("Bold", 40) if strong else inter("Medium", 38)
        d.text((x, like_y - (3 if strong else 0)), s, font=f, fill=accent if strong else INK)
        x += d.textlength(s, font=f)
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

def build_scene(wd, dur, mk):
    accent, bg = tuple(wd["accent"]), tuple(wd["bg"])
    BGA = _paper_bg(bg, accent)
    MASK, BORDER = _masks()
    art = get_art(wd["word"])
    first = lambda k: mk[k][0][0]
    hi = mk["word"]
    p1_in, p2_in = first("listen") - 0.2, first("meaning")
    p1_out = p2_in - 0.45
    blocks = []
    y = PY + PS + 56
    wf = gel(124, b"Bold")
    blocks.append(Block(simple(wd["word"], wf, INK, 1000, 150), X0 - 4, y, -1.0,   # visible from frame 0 (thumbnail)
                        alt=simple(wd["word"], wf, accent, 1000, 150), hi=hi)); y += 160
    ipa = simple(wd["ipa"], dejavu(40), MUTE)
    row = hstack([ipa.crop(ipa.getbbox()), pill(wd["pos"], inter("SemiBold", 26), PAPER, accent)], 26)
    blocks.append(Block(row, X0, y, -1.0)); y += row.height + 30
    top = y
    cd, chips = _card(wd, accent)
    blocks.append(Block(cd, X0, y, p1_in, p1_out))
    for j, (off, on, cx, cy) in enumerate(chips):
        h2 = list(mk.get(f"syl{j}", [])) + [iv for iv in hi if iv[0] > p1_in]
        blocks.append(Block(off, X0 + cx, y + cy, p1_in, p1_out, alt=on, hi=h2))
    ty = y + cd.height + 26
    tr = Image.new("RGBA", (TWS, 80), (0, 0, 0, 0))
    td = ImageDraw.Draw(tr)
    fb = inter("Bold", 36)
    td.text((96, 20), "Your turn: say it!", font=fb, fill=INK)
    td.text((96 + td.textlength("Your turn: say it!  ", font=fb), 26), "Đến lượt bạn!", font=inter("Medium", 30), fill=accent)
    turn_in = first("turn_say") - 0.1
    blocks.append(Block(tr, X0, ty, turn_in, p1_out))
    ring_pos = (X0 + 8, ty + 4)
    ta, tb = mk["turn"][0]
    y = top
    vi = render_rich([("Tiếng Việt:", inter("Regular", 36), MUTE)] + [(x, inter("Bold", 38), accent) for x in wd["vi"].split(" ")], TWS, 50)
    blocks.append(Block(vi, X0, y, p2_in - 0.2)); y += vi.getbbox()[3] + 24
    blocks.append(Block(Image.new("RGBA", (TWS, 4), INK + (60,)), X0, y, p2_in)); y += 30
    mm = simple(wd["meaning"], inter("Regular", 38), INK, TWS, 52)
    blocks.append(Block(mm, X0, y, p2_in + 0.2)); y += mm.getbbox()[3] + 30
    toks = []
    for x in wd["example"].split(" "):
        hit = x.strip(".,!?\"'").lower() in wd["forms"]
        toks.append((x, inter("BoldItalic" if hit else "Italic", 36), accent if hit else INK))
    blocks.append(Block(render_rich([("Example:", inter("SemiBold", 30), MUTE)] + toks, TWS, 50), X0, y, first("example") - 0.1))
    BW = 660
    fbn = Image.new("RGBA", (BW + 8, 104), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fbn)
    fd.rounded_rectangle([8, 8, BW + 7, 103], 48, fill=INK)
    fd.rounded_rectangle([0, 0, BW - 1, 95], 48, fill=accent, outline=INK, width=4)
    fd.text((BW / 2, 48), "Follow for a new word every day", font=inter("Bold", 34), fill=PAPER, anchor="mm")
    blocks.append(Block(fbn, (W - BW) // 2, PY + PS - 140, first("follow") - 0.2))
    bgc = np.array(bg, np.float32)
    inkc = np.array(INK, np.float32)

    def draw(t):
        f = BGA.copy()
        ill = art.frame(t).reduce(2)
        z = 1.0 + 0.04 * (t / dur)
        nw = int(800 * z); o = (nw - 800) // 2
        ill = ill.resize((nw, nw), Image.BILINEAR).crop((o, o, o + 800, o + 800)).resize((PS, PS), Image.BILINEAR)
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
        # no fade-in: frame 0 is what YouTube/Facebook use as the cover
        k = min(1.0, max(0.0, (dur - t) / 0.6))
        if k < 1:
            f = f * k + bgc * (1 - k)
        return f
    return draw

def render_short(wd, out_path, music_seed=0, preview_png=None):
    audio, dur, marks = voice.short_track(wd)
    dur = round(dur * FPS) / FPS
    draw = build_scene(wd, dur, marks)
    with tempfile.TemporaryDirectory() as tmp:
        vid = os.path.join(tmp, "v.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                              "-preset", "veryfast", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
        for k in range(int(round(dur * FPS))):
            p.stdin.write(draw(k / FPS).clip(0, 255).astype(np.uint8).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("ffmpeg video encode failed")
        if preview_png:
            Image.fromarray(draw(marks["follow"][0][0] + 1.0).clip(0, 255).astype(np.uint8)).save(preview_png)
        mix = music.mix_with_voice(audio, voice.SR, dur, seed=music_seed)
        wav = os.path.join(tmp, "a.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(music.SR)
            w.writeframes((mix * 32767).astype(np.int16).tobytes())
        tmp_out = out_path + ".tmp.mp4"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", tmp_out])
        if r.returncode != 0:
            raise RuntimeError("ffmpeg mux failed")
        os.replace(tmp_out, out_path)
    return dur
