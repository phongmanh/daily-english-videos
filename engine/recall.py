"""Review Short (1080x1920): 3 words we already posted. Show the word, the viewer recalls
the meaning during a countdown, then the picture, Vietnamese meaning and example are revealed."""
import math, os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from engine.common import INK, MUTE, inter, gel, dejavu, simple, Block, composite, pill, ease
from engine.art import get_art
from engine import voice, music
from engine.media import render_frames, write_wav, mux
from engine.quiz import _bg, _masks, _countdown, W, H, FPS, NEUTRAL, PS, PX, PY, X0, TWS

def build_scene(words, dur, mk):
    BGA = _bg("review time")
    MASK, BORDER = _masks()
    arts = [get_art(w["word"]) for w in words]
    first = lambda k: mk[k][0][0]
    n = len(words)
    starts = [first(f"w{i}") - 0.3 for i in range(n)] + [first("outro") - 0.3]
    reveal = [first(f"w{i}_mean") - 0.1 for i in range(n)]
    def title(big, small, t0, t1=None):
        a = simple(big, gel(88, b"Bold"), INK, 900, 104)
        b = simple(small, inter("Medium", 38), MUTE, 900, 50)
        return [Block(a, X0, 880, t0, t1), Block(b, X0, 880 + a.getbbox()[3] + 28, t0 + 0.3, t1)]
    blocks = title("Do you remember?", f"{n} words you learned · Bạn còn nhớ nghĩa không?", -1.0, starts[0] - 0.3)
    for i, w in enumerate(words):
        acc = tuple(w["accent"])
        t_in, t_out = starts[i], starts[i + 1] - 0.4
        blocks.append(Block(pill(f"WORD {i + 1} / {n}", inter("Bold", 24), (255, 252, 245), INK), X0, 812, t_in, t_out))
        word = simple(w["word"], gel(120, b"Bold"), INK, TWS, 140)
        blocks.append(Block(word, X0, 872, t_in + 0.1, t_out))
        ipa = simple(f"{w['ipa']}  ·  {w['pos']}", dejavu(40), MUTE, TWS, 52)
        blocks.append(Block(ipa, X0, 1022, t_in + 0.2, t_out))
        ask = simple("What does it mean? · Nghĩa là gì?", inter("Bold", 46), acc, TWS, 58)
        blocks.append(Block(ask, X0, 1124, first(f"w{i}_ask") - 0.2, reveal[i]))
        vi = simple(w["vi"], inter("Bold", 60), acc, TWS, 74)
        blocks.append(Block(vi, X0, 1124, reveal[i], t_out))
        y = 1124 + vi.getbbox()[3] + 14
        en = simple(w["meaning"], inter("Regular", 40), MUTE, TWS, 52)
        blocks.append(Block(en, X0, y, reveal[i] + 0.25, t_out))
        y += en.getbbox()[3] + 30
        ex = simple("“" + w["example"] + "”", gel(48, b"Bold Italic", italic=True), INK, TWS, 64)
        blocks.append(Block(ex, X0, y, first(f"w{i}_ex") - 0.15, t_out))
    blocks += title("How many did you remember?", "Comment your score: 0, 1, 2 or 3!", starts[-1])
    bgc = np.array(NEUTRAL, np.float32); inkc = np.array(INK, np.float32)
    counts = [mk[f"w{i}_count"][0] for i in range(n)]
    qfont = gel(300, b"Bold")

    def panel(t):
        wi = max([i for i, s in enumerate(starts[:-1]) if t >= s - 0.3] or [0])
        if t >= starts[-1] - 0.3:
            wi = n - 1
        acc = words[wi]["accent"]
        im = Image.new("RGB", (PS, PS), tuple(acc))
        ImageDraw.Draw(im).text((PS / 2, PS / 2 + 10 * math.sin(t * 3)), "?", font=qfont, fill=(255, 252, 245), anchor="mm")
        q = np.asarray(im).astype(np.float32)
        r = 1.0 if t >= starts[-1] - 0.3 else ease((t - reveal[wi]) / 0.5)
        if r > 0:
            art = np.asarray(arts[wi].frame(t).reduce(2).resize((PS, PS), Image.BILINEAR)).astype(np.float32)
            return q * (1 - r) + art * r
        return q

    def draw(t):
        f = BGA.copy()
        reg = f[PY:PY + PS, PX:PX + PS]
        reg = reg * (1 - MASK) + panel(t) * MASK
        f[PY:PY + PS, PX:PX + PS] = reg * (1 - BORDER) + inkc * BORDER
        composite(f, blocks, t)
        for i, (a, b) in enumerate(counts):
            if a - 0.2 <= t <= b + 0.2:
                prog = min(1.0, max(0.0, (t - a) / (b - a)))
                vis = min(1.0, (t - a + 0.2) / 0.2, (b + 0.2 - t) / 0.2)
                cd = np.asarray(_countdown(max(1, 3 - int(prog * 3)), prog, tuple(words[i]["accent"]))).astype(np.float32) / 255.0
                x0, y0 = PX + PS - 150, PY + PS - 150
                hh, ww = cd.shape[:2]
                aa = cd[..., 3:4] * vis
                f[y0:y0 + hh, x0:x0 + ww] = f[y0:y0 + hh, x0:x0 + ww] * (1 - aa) + cd[..., :3] * 255 * aa
        k = min(1.0, max(0.0, (dur - t) / 0.6))   # no fade-in: frame 0 = cover
        return f if k >= 1 else f * k + bgc * (1 - k)
    return draw

def render_recall(words, out_path, seed=0, preview_png=None):
    audio, dur, marks = voice.recall_track(words)
    dur = round(dur * FPS) / FPS
    draw = build_scene(words, dur, marks)
    with tempfile.TemporaryDirectory() as tmp:
        vid = os.path.join(tmp, "v.mp4")
        render_frames(vid, draw, dur, W, H, FPS)
        if preview_png:
            Image.fromarray(draw(marks["w0_word"][0][1] + 0.3).clip(0, 255).astype(np.uint8)).save(preview_png)
        wav = os.path.join(tmp, "a.wav")
        write_wav(wav, music.mix_with_voice(audio, voice.SR, dur, seed=seed))
        mux(vid, wav, out_path)
    return dur
