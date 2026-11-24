"""Quiz Short (1080x1920): 3 questions on the batch's words, A/B/C options, countdown, reveal."""
import math, os, random, tempfile
import numpy as np
from PIL import Image, ImageDraw
from engine.common import INK, MUTE, PAPER, inter, gel, ease, simple, render_rich, Block, composite, pill
from engine.art import get_art
from engine import voice, music
from engine.media import render_frames, write_wav, mux

W, H, FPS = 1080, 1920, 30
NEUTRAL = (244, 236, 222)
PS = 560
PX, PY = (W - PS) // 2 - 6, 210
X0, TWS = 96, 880
OPT_Y, OPT_H, OPT_GAP = 1128, 116, 22

def make_questions(words, n=3, seed=0):
    rng = random.Random(seed)
    picks = rng.sample(words, min(n, len(words)))
    qs = []
    for ans in picks:
        others = [w for w in words if w["word"] != ans["word"]]
        opts = rng.sample(others, 2) + [ans]
        rng.shuffle(opts)
        qs.append({"answer": ans, "options": opts, "correct": opts.index(ans)})
    return qs

def _bg():
    rng = np.random.default_rng(11)
    arr = np.ones((H, W, 3), np.float32) * np.array(NEUTRAL, np.float32)
    arr += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(40, H, 48):
        for x in range(36, W, 48):
            if (y > PY + PS + 20 and 60 < x < 1010) or (80 < y < 180 and 220 < x < 860):
                continue
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=INK + (38,))
    d.rounded_rectangle([PX + 16, PY + 16, PX + PS + 16, PY + PS + 16], 40, fill=INK + (255,))
    f = inter("Bold", 30); f2 = gel(36, b"Bold Italic", italic=True)
    t1, t2 = "DAILY ENGLISH", "quiz time"
    w1, w2 = d.textlength(t1, font=f), d.textlength(t2, font=f2)
    x = (W - (w1 + 72 + w2)) / 2
    d.rounded_rectangle([x, 104, x + w1 + 48, 160], 28, fill=INK + (255,))
    d.text((x + 24, 132), t1, font=f, fill=PAPER, anchor="lm")
    d.text((x + w1 + 72, 130), t2, font=f2, fill=(186, 78, 46), anchor="lm")
    return np.asarray(im.convert("RGB")).astype(np.float32)

def _option(letter, word, state, accent):
    """state: 'idle' | 'right' | 'wrong'"""
    w, h = TWS, OPT_H
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, w + 7, h + 7], 30, fill=INK)
    fill = accent if state == "right" else PAPER
    d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=fill, outline=INK, width=4)
    txt = PAPER if state == "right" else INK
    d.ellipse([22, h / 2 - 34, 90, h / 2 + 34], fill=PAPER if state == "right" else INK)
    d.text((56, h / 2), letter, font=inter("Bold", 36), fill=accent if state == "right" else PAPER, anchor="mm")
    d.text((120, h / 2 - 4), word, font=gel(64, b"Bold"), fill=txt, anchor="lm")
    if state == "right":
        cx, cy = w - 70, h / 2
        d.line([(cx - 24, cy), (cx - 6, cy + 20), (cx + 26, cy - 22)], fill=PAPER, width=10, joint="curve")
    if state == "wrong":
        im.putalpha(Image.eval(im.getchannel("A"), lambda a: int(a * 0.35)))
    return im

def _masks():
    m = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 70, fill=255)
    b = Image.new("L", (PS * 2, PS * 2), 0)
    ImageDraw.Draw(b).rounded_rectangle([0, 0, PS * 2 - 1, PS * 2 - 1], 70, outline=255, width=14)
    f = lambda im: (np.asarray(im.reduce(2)).astype(np.float32) / 255.0)[..., None]
    return f(m), f(b)

def _countdown(n_left, prog, accent):
    s = 220
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([10, 10, s - 4, s - 4], fill=INK)
    d.ellipse([4, 4, s - 10, s - 10], fill=PAPER, outline=INK, width=6)
    d.arc([18, 18, s - 24, s - 24], -90, -90 + 360 * (1 - prog), fill=accent, width=16)
    d.text(((s - 6) / 2, (s - 6) / 2), str(n_left), font=gel(110, b"Bold"), fill=INK, anchor="mm")
    return im

def build_scene(questions, dur, mk):
    BGA = _bg()
    MASK, BORDER = _masks()
    arts = [get_art(q["answer"]["word"]) for q in questions]
    first = lambda k: mk[k][0][0]
    blocks = []
    starts = [first(f"q{i}") - 0.3 for i in range(len(questions))] + [first("outro") - 0.3]
    reveal = [first(f"q{i}_ans") - 0.05 for i in range(len(questions))]
    intro = Block(simple("Quiz time!", gel(92, b"Bold"), INK, 900, 110), X0, 860, -1.0, starts[0] - 0.3)
    sub = Block(simple("3 questions · 3 câu hỏi · Comment your score!", inter("Medium", 34), MUTE, 900), X0, 990, -1.0, starts[0] - 0.3)
    blocks += [intro, sub]
    for i, q in enumerate(questions):
        a = q["answer"]; acc = tuple(a["accent"])
        t_in, t_out = starts[i], starts[i + 1] - 0.4
        blocks.append(Block(pill(f"QUESTION {i + 1} / {len(questions)}", inter("Bold", 24), PAPER, INK), X0, 812, t_in, t_out))
        qtxt = render_rich([("Which", inter("Bold", 42), INK), ("word", inter("Bold", 42), INK), ("means…", inter("Bold", 42), INK)], TWS, 56)
        blocks.append(Block(qtxt, X0, 878, t_in + 0.1, t_out))
        vi = simple(a["vi"], inter("Bold", 46), acc, TWS, 58)
        blocks.append(Block(vi, X0, 942, t_in + 0.2, t_out))
        en = simple(a["meaning"], inter("Regular", 30), MUTE, TWS, 40)
        blocks.append(Block(en, X0, 942 + vi.getbbox()[3] + 8, t_in + 0.3, t_out))
        for oi, o in enumerate(q["options"]):
            y = OPT_Y + oi * (OPT_H + OPT_GAP)
            t0 = first(f"q{i}_l{oi}") - 0.15
            idle = _option("ABC"[oi], o["word"], "idle", acc)
            after = _option("ABC"[oi], o["word"], "right" if oi == q["correct"] else "wrong", acc)
            blocks.append(Block(idle, X0, y, t0, t_out, alt=after, hi=[[reveal[i] + 0.12, 10_000]]))
    bgc = np.array(NEUTRAL, np.float32); inkc = np.array(INK, np.float32)
    counts = [mk[f"q{i}_count"][0] for i in range(len(questions))]
    qmark_font = gel(300, b"Bold")
    end_card = Block(simple("How many did you get?", gel(70, b"Bold"), INK, 900, 90), X0, 880, starts[-1])
    end_sub = Block(simple("Comment your score: 0, 1, 2 or 3!", inter("Medium", 36), MUTE, 900), X0, 990, starts[-1] + 0.3)
    blocks += [end_card, end_sub]

    def panel(t):
        qi = max([i for i, s in enumerate(starts[:-1]) if t >= s - 0.3] or [0])
        a = questions[qi]["answer"]; acc = np.array(a["accent"], np.float32)
        q_img = np.ones((PS, PS, 3), np.float32) * acc
        im = Image.fromarray(q_img.astype(np.uint8))
        d = ImageDraw.Draw(im)
        bob = 10 * math.sin(t * 3)
        d.text((PS / 2, PS / 2 + bob), "?", font=qmark_font, fill=PAPER, anchor="mm")
        q_img = np.asarray(im).astype(np.float32)
        r = ease((t - reveal[qi]) / 0.5) if qi < len(reveal) else 1.0
        if t >= starts[-1] - 0.3:
            r = 1.0
        if r > 0:
            art = np.asarray(arts[qi].frame(t).reduce(2).resize((PS, PS), Image.BILINEAR)).astype(np.float32)
            return q_img * (1 - r) + art * r
        return q_img

    def draw(t):
        f = BGA.copy()
        reg = f[PY:PY + PS, PX:PX + PS]
        reg = reg * (1 - MASK) + panel(t) * MASK
        f[PY:PY + PS, PX:PX + PS] = reg * (1 - BORDER) + inkc * BORDER
        composite(f, blocks, t)
        for i, (a, b) in enumerate(counts):
            if a - 0.2 <= t <= b + 0.2:
                prog = min(1.0, max(0.0, (t - a) / (b - a)))
                n_left = max(1, 3 - int(prog * 3))
                vis = min(1.0, (t - a + 0.2) / 0.2, (b + 0.2 - t) / 0.2)
                cd = np.asarray(_countdown(n_left, prog, tuple(questions[i]["answer"]["accent"]))).astype(np.float32) / 255.0
                x0, y0 = PX + PS - 150, PY + PS - 150
                hh, ww = cd.shape[:2]
                reg = f[y0:y0 + hh, x0:x0 + ww]
                aa = cd[..., 3:4] * vis
                f[y0:y0 + hh, x0:x0 + ww] = reg * (1 - aa) + cd[..., :3] * 255 * aa
        k = min(1.0, max(0.0, (dur - t) / 0.6))   # no fade-in: frame 0 = cover
        return f if k >= 1 else f * k + bgc * (1 - k)
    return draw

def render_quiz(words, out_path, seed=0, preview_png=None):
    qs = make_questions(words, 3, seed)
    audio, dur, marks = voice.quiz_track(qs)
    dur = round(dur * FPS) / FPS
    draw = build_scene(qs, dur, marks)
    with tempfile.TemporaryDirectory() as tmp:
        vid = os.path.join(tmp, "v.mp4")
        render_frames(vid, draw, dur, W, H, FPS)
        if preview_png:
            Image.fromarray(draw(marks["q0_word"][0][1] + 0.3).clip(0, 255).astype(np.uint8)).save(preview_png)
        wav = os.path.join(tmp, "a.wav")
        write_wav(wav, music.mix_with_voice(audio, voice.SR, dur, seed=seed))
        mux(vid, wav, out_path)
    return dur, qs
