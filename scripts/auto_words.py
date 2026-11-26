"""Add new words automatically when words/queue.json is running low.

Runs in the daily workflow before the video is made. If fewer than MIN_LEFT words in the queue
are still unposted, it asks the Claude API for BATCH new words and, for each one, writes:
  words/<word>.json        all the content (meaning, Vietnamese, example, tips, colors)
  engine/art/auto_<word>.py  an animated illustration class (WORD = "<word>")
and appends the words to words/queue.json.

Checks before anything is saved:
  - every field the video code reads is there and has the right shape
  - ph (Kokoro phonemes) comes from Kokoro's own phonemizer, not from the model; the model only
    splits it into syllables, and the pieces must join back to exactly ph
  - the drawing code may only use math/random/numpy/PIL and engine.common helpers (no files,
    no network, no os/sys), and it is test-rendered in a separate process with no secrets,
    with time limits. If it still fails after one retry, the word is kept and uses the backup
    scene (engine/art/fallback.py).

Usage:
  ANTHROPIC_API_KEY=... python scripts/auto_words.py            # only if the queue is low
  ANTHROPIC_API_KEY=... python scripts/auto_words.py --force    # add a batch now
Optional: CLAUDE_MODEL (default below).
"""
import argparse, ast, json, os, re, subprocess, sys, tempfile, time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MIN_LEFT = 2          # add words when fewer than this many queue words are still unposted
BATCH = 5             # one cycle = 5 word Shorts + 1 long video
MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-5-5"
API = "https://api.anthropic.com/v1/messages"

TEXT_FIELDS = ["word", "ipa", "pos", "vi", "meaning", "example", "note", "note_say", "mean_say",
               "ex_say", "tip", "tip_say", "vn_tip", "vn_tip_say", "scene"]


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(os.path.join(ROOT, p), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def known_words():
    return sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "words"))
                  if f.endswith(".json") and f != "queue.json")


def unposted_left():
    pub = load("state/published.json")["published"]
    posted = {e["word"] for e in pub if e.get("kind", "word") == "word" and "word" in e}
    return [w for w in load("words/queue.json")["queue"] if w not in posted]


# ---------------------------------------------------------------- Claude API

def claude(prompt, max_tokens):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set")
    body = {"model": MODEL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for attempt in range(4):
        r = requests.post(API, headers=headers, json=body, timeout=600)
        if r.status_code in (429, 500, 502, 503, 504, 529) and attempt < 3:
            wait = int(r.headers.get("retry-after", 0) or 0) or 20 * (attempt + 1)
            print(f"Claude API busy ({r.status_code}), retrying in {wait}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            sys.exit(f"Claude API error {r.status_code}: {r.text[:500]}")
        data = r.json()
        if data.get("stop_reason") == "max_tokens":
            print("Warning: the answer was cut off (max_tokens)")
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def json_from(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


def code_from(text):
    m = re.search(r"```python\s*(.*?)```", text, re.S) or re.search(r"```\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"


# ---------------------------------------------------------------- step 1: the words

WORDS_PROMPT = """You write content for "Daily English", a calm YouTube/Facebook channel. Every day it posts one
short video teaching one English word to Vietnamese learners (A2–B2 level). The mood is relaxing
and cozy, the words are useful in everyday life.

Words the channel already has (do NOT repeat any of them, or a close form of them):
{known}

Pick {n} NEW single English words that fit this channel: everyday, calm, pleasant, easy to picture,
not rare or formal. Mix parts of speech (verbs, adjectives, nouns). Avoid words with sad, scary,
violent or adult meanings.

For each word give exactly the same fields as this example (it is the word "linger"):
{example}

Rules for the fields:
- ipa: American IPA with slashes. pos: "verb", "adjective", "noun" or "adverb".
- vi: 1–3 short Vietnamese meanings, comma-separated.
- meaning: one short simple English sentence or phrase. mean_say: the same, as it should be read aloud (lowercase start).
- example: one short natural sentence that uses the word; ex_say: the same sentence for reading aloud.
- forms: every spelling of the word used in "example", plus the base word (e.g. ["lingered", "linger"]).
- chips: the written word split into spoken syllables (e.g. ["lin", "ger"]); a 1-syllable word has 1 chip.
- stress: index (0-based) of the stressed chip.
- like: "sounds like" pieces, one per chip, [text, is_stressed], stressed piece in CAPITALS (e.g. [["LING", true], ["-ger", false]]).
- note: short on-screen pronunciation note. note_say: a spoken version, starting "The stress is on the ... syllable."
- tip: one short extra usage tip shown on screen; tip_say: spoken version.
- vn_tip: a short tip IN VIETNAMESE about a mistake Vietnamese speakers often make with this word's sound.
  vn_tip_say: the same tip in simple English, for reading aloud.
- bg: a light pastel RGB background color [r, g, b] (each 190–250) that suits the word's mood.
  accent: a darker matching RGB accent color (each 30–200), readable on bg.
- scene: one sentence describing a calm, simple, ANIMATED illustration for the word (what is in the
  picture and what gently moves), e.g. "Two cups on a café table at dusk, steam rising, lights dimming outside."
  No people's faces; simple shapes.

Answer with only a JSON object: {{"words": [ ... {n} word objects ... ]}}"""


def rgb(v, lo, hi):
    return isinstance(v, list) and len(v) == 3 and all(isinstance(c, int) and lo <= c <= hi for c in v)


def check_word(wd, taken):
    errs = []
    for k in TEXT_FIELDS:
        if not isinstance(wd.get(k), str) or not wd[k].strip():
            errs.append(f"missing text field {k}")
    w = str(wd.get("word", ""))
    if not re.fullmatch(r"[a-z]+", w):
        errs.append("word must be one lowercase word")
    if w in taken:
        errs.append("word already used")
    forms = wd.get("forms")
    if not (isinstance(forms, list) and forms and all(isinstance(f, str) for f in forms)):
        errs.append("forms must be a list of strings")
    elif not any(re.search(rf"\b{re.escape(f)}\b", wd.get("example", ""), re.I) for f in forms):
        errs.append("example does not use any of the forms")
    chips, like, stress = wd.get("chips"), wd.get("like"), wd.get("stress")
    if not (isinstance(chips, list) and chips and all(isinstance(c, str) and c for c in chips)):
        errs.append("chips must be a list of strings")
    else:
        if not (isinstance(stress, int) and 0 <= stress < len(chips)):
            errs.append("stress must be a chip index")
        if not (isinstance(like, list) and len(like) == len(chips) and
                all(isinstance(p, list) and len(p) == 2 and isinstance(p[0], str) and isinstance(p[1], bool) for p in like)):
            errs.append("like must have one [text, bool] per chip")
    if not rgb(wd.get("bg"), 150, 255):
        errs.append("bg must be [r,g,b], light")
    if not rgb(wd.get("accent"), 0, 230):
        errs.append("accent must be [r,g,b]")
    return errs


def phonemes(word):
    from kokoro_onnx.tokenizer import Tokenizer
    return Tokenizer().phonemize(word, "en-us").strip()


SYL_PROMPT = """Split each word's Kokoro phoneme string into spoken syllables. The syllables must join back to
EXACTLY the phoneme string (same characters, same order, nothing added or removed, keep the stress
mark ˈ inside its syllable), and there must be exactly as many syllables as chips.

Example: {{"word": "linger", "ph": "lˈɪŋɡɚ", "chips": ["lin", "ger"]}}  ->  "linger": ["lˈɪŋ", "ɡɚ"]

{items}

Answer with only a JSON object mapping each word to its list of syllables."""


def add_syllables(words):
    items = [{"word": w["word"], "ph": w["ph"], "chips": w["chips"]} for w in words]
    todo = {w["word"]: w for w in words}
    for w in words:                                     # 1 syllable: nothing to split
        if len(w["chips"]) == 1:
            w["syl"] = [w["ph"]]
            todo.pop(w["word"])
    for attempt in range(2):
        if not todo:
            break
        ask = [i for i in items if i["word"] in todo]
        ans = json_from(claude(SYL_PROMPT.format(items="\n".join(json.dumps(i, ensure_ascii=False) for i in ask)), 2000))
        for w in list(todo):
            syl = ans.get(w)
            wd = todo[w]
            if isinstance(syl, list) and len(syl) == len(wd["chips"]) and "".join(syl) == wd["ph"]:
                wd["syl"] = syl
                todo.pop(w)
    return list(todo)                                   # words that still have no syllables


# ---------------------------------------------------------------- step 2: the drawings

ART_PROMPT = """Write one Python class that draws an animated illustration for the English word "{word}"
for the "Daily English" channel. Picture idea: {scene}
Mood colors of this word: background {bg}, accent {accent}.

The channel's illustrations are flat, warm, hand-made-looking shapes (no photos, no text in the
picture, no faces). Here is a file with five of them; match this style, quality and level of detail:

```python
{example}
```

Rules (the code is checked automatically, and rejected if it breaks one):
- Start with exactly these imports (you may leave out what you don't use):
    import math, random
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    from engine.common import vgrad, glow
  No other imports. Don't read or write files, no os/sys/open/eval/exec, no names starting with "_"
  other than __init__.
- Define S = 1600 and exactly one class with WORD = "{word}", like the examples.
- __init__(self) draws the still background once into self.base (an RGB image S x S), and seeds random
  with a fixed number. It must finish in under 2 seconds.
- frame(self, t) returns a NEW RGB image of size S x S for time t in seconds (0 to about 60): copy
  self.base and draw only the moving parts. Movement is slow and gentle and loops or drifts forever.
  Each frame must take well under 0.05 seconds, so draw with ImageDraw shapes (no per-pixel loops, no
  blur inside frame()).
- Keep the main subject roughly in the middle; the picture is shown as a square card.

Answer with only the Python code in one ```python block."""

ALLOWED_IMPORTS = {"math", "random", "numpy", "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFilter",
                   "PIL.ImageChops", "PIL.ImageOps", "engine.common"}
ALLOWED_COMMON = {"vgrad", "glow", "ease", "gel"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                "setattr", "delattr", "input", "breakpoint", "memoryview", "os", "sys", "subprocess",
                "importlib", "builtins", "exit", "quit", "help"}
BANNED_ATTRS = {"open", "save", "load", "loadtxt", "savetxt", "genfromtxt", "fromfile", "tofile",
                "system", "popen", "remove", "unlink", "frombuffer", "ctypeslib", "lib"}


def check_code(code, word):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    errs, classes = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_IMPORTS:
                    errs.append(f"import {a.name} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_IMPORTS or node.level:
                errs.append(f"from {node.module} import is not allowed")
            elif node.module == "engine.common" and any(a.name not in ALLOWED_COMMON for a in node.names):
                errs.append("only vgrad, glow, ease, gel may be imported from engine.common")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            errs.append(f"name {node.id} is not allowed")
        elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in BANNED_ATTRS):
            errs.append(f"attribute .{node.attr} is not allowed")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            errs.append("global/nonlocal is not allowed")
        elif isinstance(node, ast.ClassDef):
            for st in node.body:
                if (isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WORD" for t in st.targets)
                        and isinstance(st.value, ast.Constant)):
                    classes.append(st.value.value)
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("_") and node.name != "__init__":
            errs.append(f"function {node.name} is not allowed")
    if classes != [word]:
        errs.append(f'need exactly one class with WORD = "{word}" (found {classes})')
    return sorted(set(errs))


TEST_RUNNER = r'''
import importlib.util, json, sys, time
sys.path.insert(0, sys.argv[3])
path, word, root, preview = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("art_under_test", path)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cls = [v for v in vars(mod).values() if isinstance(v, type) and getattr(v, "WORD", None) == word][0]
t0 = time.time(); art = cls(); init = time.time() - t0
times, frames = [], []
for i in range(40):
    t = i * 1.5
    t1 = time.time(); im = art.frame(t); times.append(time.time() - t1)
    if im.size != (1600, 1600) or im.mode != "RGB":
        raise SystemExit(f"frame({t}) returned {im.size} {im.mode}, need (1600, 1600) RGB")
    if i in (0, 4, 8):
        frames.append(im)
from PIL import Image, ImageStat
st = ImageStat.Stat(frames[0].reduce(8))
if max(st.stddev) < 6:
    raise SystemExit("the picture is almost one flat color")
sheet = Image.new("RGB", (1200, 400))
for i, im in enumerate(frames):
    sheet.paste(im.resize((400, 400)), (400 * i, 0))
sheet.save(preview)
print(json.dumps({"init": init, "frame": sum(times) / len(times), "max_frame": max(times)}))
'''


def test_render(code, word):
    """Render the drawing in a separate process with no secrets in its environment."""
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    preview = os.path.join(ROOT, "out", f"new_art_{word}.png")
    with tempfile.TemporaryDirectory() as tmp:
        src, runner = os.path.join(tmp, f"auto_{word}.py"), os.path.join(tmp, "run.py")
        open(src, "w", encoding="utf-8").write(code)
        open(runner, "w", encoding="utf-8").write(TEST_RUNNER)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tmp, "PYTHONNOUSERSITE": "1"}
        try:
            p = subprocess.run([sys.executable, runner, src, word, ROOT, preview], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return ["test render took longer than 120 s"]
    if p.returncode != 0:
        return ["test render failed: " + (p.stderr.strip().splitlines() or [p.stdout.strip()])[-1][:400]]
    r = json.loads(p.stdout.strip().splitlines()[-1])
    errs = []
    if r["init"] > 5:
        errs.append(f"__init__ took {r['init']:.1f}s (limit 2s)")
    if r["frame"] > 0.08 or r["max_frame"] > 0.5:
        errs.append(f"frame() is too slow: {r['frame']:.3f}s on average (limit 0.05s)")
    print(f"  {word}: init {r['init']:.2f}s, frame {r['frame'] * 1000:.1f} ms")
    return errs


def make_art(wd, example):
    word = wd["word"]
    prompt = ART_PROMPT.format(word=word, scene=wd["scene"], bg=wd["bg"], accent=wd["accent"], example=example)
    for attempt in range(2):
        code = code_from(claude(prompt, 16000))
        errs = check_code(code, word) or test_render(code, word)
        if not errs:
            header = f'"""Scene for: {word} (auto-generated by scripts/auto_words.py). Idea: {wd["scene"]}"""\n'
            return header + code
        print(f"  {word}: drawing rejected ({'; '.join(errs)})" + (", asking again" if attempt == 0 else ""))
        prompt += ("\n\nYour previous answer was rejected for these reasons:\n- " + "\n- ".join(errs) +
                   "\nWrite the whole class again and fix them.")
    return None


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="add a batch even if the queue is not low")
    ap.add_argument("--count", type=int, default=BATCH)
    a = ap.parse_args()

    left = unposted_left()
    print(f"Unposted words in the queue: {left}")
    if len(left) >= MIN_LEFT and not a.force:
        print("Queue is fine, nothing to add.")
        return

    taken = set(known_words())
    example = json.dumps(load("words/linger.json"), ensure_ascii=False, indent=1)
    ans = json_from(claude(WORDS_PROMPT.format(known=", ".join(sorted(taken)), n=a.count + 2, example=example), 12000))
    good = []
    for wd in ans.get("words", []):
        errs = check_word(wd, taken | {g["word"] for g in good})
        if errs:
            print(f"Skipping {wd.get('word')!r}: {'; '.join(errs)}")
            continue
        wd["ph"] = phonemes(wd["word"])
        good.append(wd)
        if len(good) == a.count:
            break
    if not good:
        sys.exit("No usable words came back")

    for w in add_syllables(good):
        print(f"Skipping {w!r}: could not split its phonemes into syllables")
        good = [g for g in good if g["word"] != w]

    art_example = open(os.path.join(ROOT, "engine", "art", "set2.py"), encoding="utf-8").read()
    order = ["word", "ipa", "pos", "vi", "meaning", "example", "forms", "ph", "syl", "chips", "stress", "like",
             "note", "note_say", "mean_say", "ex_say", "tip", "tip_say", "vn_tip", "vn_tip_say", "bg", "accent", "scene"]
    added, backup = [], []
    for wd in good:
        w = wd["word"]
        print(f"Drawing {w} …")
        code = make_art(wd, art_example)
        if code:
            open(os.path.join(ROOT, "engine", "art", f"auto_{w}.py"), "w", encoding="utf-8").write(code)
        else:
            backup.append(w)
        save(f"words/{w}.json", {k: wd[k] for k in order})
        added.append(w)

    q = load("words/queue.json")
    q["queue"] += added
    save("words/queue.json", q)

    msg = f"Added {len(added)} words: {', '.join(added)}"
    if backup:
        msg += f" (backup picture for: {', '.join(backup)})"
    print(msg)
    for name, val in (("GITHUB_OUTPUT", f"added={','.join(added)}\n"),
                      ("GITHUB_STEP_SUMMARY", f"### New words\n- {msg}\n- Picture previews: out/new_art_*.png in *Artifacts*\n")):
        if os.environ.get(name):
            with open(os.environ[name], "a", encoding="utf-8") as f:
                f.write(val)


if __name__ == "__main__":
    main()
