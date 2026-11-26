# How to write a new word

Used by the scheduled Claude task "Daily English – add new words" (and by hand). It runs every 2 days
and adds 5 words when `python scripts/check_words.py` says `low=yes`. One word = 3 changes:

1. `words/<word>.json`: the content (fields below)
2. `engine/art/auto_<word>.py`: its animated picture
3. the word appended to `words/queue.json`

Then check: `python scripts/check_words.py --check <word> ...` until it prints **All good.**
Look at the previews in `out/new_art_<word>.png`.

## Choosing words

- Single, everyday English words for Vietnamese learners, A2–B2 level.
- Calm, pleasant, easy to picture, so they fit the relaxing, cozy channel. Mix verbs, adjectives and nouns.
- Not rare or formal. No sad, scary, violent or adult meanings.
- Never repeat a word already in this folder, or a close form of one.

## Fields (copy `linger.json` for the shape)

| Field | What to write |
|---|---|
| `word` | the word, lowercase |
| `ipa` | American IPA with slashes, e.g. `/ˈlɪŋɡər/` |
| `pos` | `verb`, `adjective`, `noun` or `adverb` |
| `vi` | 1–3 short Vietnamese meanings, comma-separated |
| `meaning` / `mean_say` | one short, simple English meaning; `mean_say` is the same text read aloud (lowercase start) |
| `example` / `ex_say` | one short natural sentence using the word; `ex_say` is the same sentence read aloud |
| `forms` | every spelling of the word used in `example`, plus the base word, e.g. `["lingered", "linger"]` |
| `ph` | Kokoro phonemes. Write anything here: `--check` replaces it with Kokoro's own value |
| `syl` | `ph` split into spoken syllables, one per chip; the pieces must join to **exactly** `ph`, e.g. `["lˈɪŋ", "ɡɚ"]` |
| `chips` | the written word split into syllables, e.g. `["lin", "ger"]` (1 chip for 1 syllable) |
| `stress` | index (from 0) of the stressed chip |
| `like` | "sounds like" pieces, one per chip: `[text, is_stressed]`, with the stressed one in CAPITALS, e.g. `[["LING", true], ["-ger", false]]` |
| `note` / `note_say` | short pronunciation note on screen; spoken version starts "The stress is on the … syllable." |
| `tip` / `tip_say` | one short extra usage tip on screen; spoken version |
| `vn_tip` / `vn_tip_say` | a short tip **in Vietnamese** about a mistake Vietnamese speakers make with this word's sound; the same tip in simple English, read aloud |
| `bg` | light pastel background `[r, g, b]` (each 190–250) that suits the word's mood |
| `accent` | darker matching color `[r, g, b]` (each 30–200), readable on `bg` |
| `scene` | one sentence describing the picture and what gently moves |

## The picture (`engine/art/auto_<word>.py`)

Match the style and detail of `engine/art/set1.py` and `set2.py`: flat, warm, hand-made-looking shapes,
with no text and no faces.

- Imports, only these: `math`, `random`, `numpy as np`, `PIL` (`Image`, `ImageDraw`, `ImageFilter`),
  and from `engine.common`: `vgrad`, `glow`, `ease`, `gel`.
- Not allowed: files, network, `os`/`sys`/`open`/`eval`/`exec`, or names and attributes starting with `_` (other than `__init__`).
- `S = 1600` and exactly one class with `WORD = "<word>"`.
- `__init__(self)`: seed `random` with a fixed number, then draw the still background once into `self.base` (RGB, S×S). It must take under 2 s.
- `frame(self, t)`: copy `self.base`, draw only the moving parts, and return an RGB S×S image.
  Keep movement slow and gentle, looping or drifting. Each frame must take well under 0.05 s: use only ImageDraw shapes, with no per-pixel loops or blur.
- Keep the main subject near the middle; the picture is shown as a square card.

If a picture can't pass the check, delete its file. The word then uses the backup picture in its own colors
(`engine/art/fallback.py`), and the video still works.
