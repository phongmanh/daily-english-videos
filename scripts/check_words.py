"""Check new words before they go into the queue (used by the scheduled Claude task that adds words).

  python scripts/check_words.py --status              # how many queue words are still unposted? low=yes/no
  python scripts/check_words.py --check bloom gentle  # check words/<word>.json + engine/art/auto_<word>.py

--check does, for each word:
  - sets ph from Kokoro's own phonemizer (so the voice says it right), then checks that syl
    joins back to exactly ph, one piece per chip
  - checks every field the video code reads (see words/README.md), and that it's in words/queue.json
  - checks the drawing code: only math/random/numpy/PIL and engine.common helpers, no files,
    no network, no os/sys/eval; then test-renders it in a separate process with time limits and
    saves a preview to out/new_art_<word>.png
A word with no engine/art/auto_<word>.py is allowed: it uses the backup picture (engine/art/fallback.py).
Exit code 1 if anything is wrong.
"""
import argparse, ast, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MIN_LEFT = 2          # the queue is "low" when fewer than this many queue words are unposted

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


def phonemes(word):
    from kokoro_onnx.tokenizer import Tokenizer
    return Tokenizer().phonemize(word, "en-us").strip()


# ---------------------------------------------------------------- word data

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


# ---------------------------------------------------------------- drawing code

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
    """Render the drawing in a separate process with a clean environment (no secrets)."""
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
    print(f"  drawing: init {r['init']:.2f}s, frame {r['frame'] * 1000:.1f} ms")
    return errs


# ---------------------------------------------------------------- main

def check_files(words):
    queue = load("words/queue.json")["queue"]
    problems = 0
    for w in words:
        print(f"== {w}")
        try:
            wd = load(f"words/{w}.json")
        except (OSError, ValueError) as e:
            print(f"  ERROR: words/{w}.json: {e}"); problems += 1; continue
        errs = check_word(wd, set(known_words()) - {w})
        ph = phonemes(w)
        if wd.get("ph") != ph:
            print(f"  ph set from Kokoro: {wd.get('ph')!r} -> {ph!r}")
            wd["ph"] = ph
            save(f"words/{w}.json", wd)
        syl, chips = wd.get("syl"), wd.get("chips") or []
        if not (isinstance(syl, list) and "".join(syl) == ph and len(syl) == len(chips)):
            errs.append(f"syl must have {len(chips)} pieces that join to exactly {ph!r} (got {syl!r})")
        if w not in queue:
            errs.append("not in words/queue.json")
        art = os.path.join(ROOT, "engine", "art", f"auto_{w}.py")
        if os.path.exists(art):
            code = open(art, encoding="utf-8").read()
            errs += check_code(code, w) or test_render(code, w)
        else:
            print(f"  note: no engine/art/auto_{w}.py, the backup picture will be used")
        for e in errs:
            print(f"  ERROR: {e}")
        problems += len(errs)
        if not errs:
            print(f"  OK (preview: out/new_art_{w}.png)" if os.path.exists(art) else "  OK")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true", help="print the unposted queue words")
    ap.add_argument("--check", nargs="+", metavar="WORD", help="check these new words")
    a = ap.parse_args()
    if a.check:
        n = check_files(a.check)
        print("All good." if n == 0 else f"{n} problem(s).")
        sys.exit(1 if n else 0)
    left = unposted_left()
    print(f"unposted={len(left)} low={'yes' if len(left) < MIN_LEFT else 'no'} words={','.join(left)}")


if __name__ == "__main__":
    main()
