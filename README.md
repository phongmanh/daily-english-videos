# Daily English videos

Makes one post every day for YouTube and Facebook, in a repeating 7-day cycle:

| Day | Post | YouTube | Facebook | Instagram |
|---|---|---|---|---|
| 1–5 | **Word Short** (one new word) | Short | Reel | Reel |
| 6 | **Quiz Short** (3 questions on those 5 words) | Short | Reel | Reel |
| 7 | **Long video** (all 5 words, with chapters) | Video | Video post | Reel |

**Instagram limit:** Instagram's API refuses Reels longer than about 40 s, so Shorts are kept under 40 s
(quiz = 3 questions, options shown but not read; recall = 2 words). Anything longer (the weekly long video)
is skipped on Instagram with a warning; YouTube and Facebook still post. Change with the `IG_MAX_SECONDS` env.

**TikTok:** every video is also sent to your TikTok inbox as a draft (`scripts/tiktok.py`). Open it in the
TikTok app, paste the caption from <https://phongmanh.github.io/daily-english-videos/tiktok.html> and post.
Setup: SETUP.md section 2c.

At 12:00 every day there is a review Short. **On Sundays** it is a **Story Short** instead, when a story
is ready: a tiny story (~40 s) where each line uses one word we already taught, then a
"Do you remember?" recap. Stories live in `stories/`, in the order of `stories/queue.json`.

Each Short (~30–35 s, 1080×1920): today's word → syllables with stress → "sounds like" → pronunciation tip →
"your turn" pause → Vietnamese meaning → definition → example → follow reminder.
Paper-style background, a new illustration per word, Kokoro AI voice, original background music.

Manual run: **Actions → Daily video → Run workflow** (choose kind, words, or dry run).

**First time?** Read [SETUP.md](SETUP.md) to connect YouTube and Facebook.

## How it works

```
GitHub Actions (daily, 02:37 VN → 18:00 post; 03:07 VN → 12:00 review)  .github/workflows/daily-video.yml
  └─ scripts/make_video.py      decides word / long (18:00) or review (12:00) from state/published.json → out/*.mp4 + meta.json
  └─ scripts/upload_youtube.py  private, publishAt 18:00 / 12:00 VN
  └─ scripts/upload_facebook.py Reel (Shorts) or video post (long), scheduled 18:00 / 12:00 VN
  └─ scripts/instagram.py prepare  uploads the Reel, saves it in state/pending_instagram.json
  └─ scripts/mark_published.py  records the post in state/published.json (commit)
GitHub Actions (daily, 11:47 and 17:47 VN)  .github/workflows/publish-instagram.yml
  └─ scripts/instagram.py publish  publishes the waiting Instagram Reels that are due
```

## Folders

| Path | What |
|---|---|
| `words/<word>.json` | All content for one word (meaning, example, phonemes, colors) |
| `words/queue.json` | Posting order |
| `state/published.json` | What has been posted (don't edit by hand unless re-posting) |
| `engine/art/` | One illustration class per word (`WORD = "..."`, `frame(t)` → 1600×1600 image) |
| `engine/short.py` | Word Short |
| `engine/quiz.py` | Quiz Short (A/B/C) |
| `engine/recall.py` | "Do you remember?" review Short |
| `engine/long.py` | Weekly long video |
| `engine/story.py` | Story Short (one word per line, words light up as they are read) |
| `stories/<name>.json` | One story: title + lines (`stories/queue.json` = posting order) |
| `engine/voice.py` | Narration script + Kokoro TTS |
| `engine/music.py` | Generated background music |
| `assets/fonts/` | Inter, Gelasio, DejaVu Sans (open licenses included) |

## Add new words

1. Add `words/<word>.json` (copy `words/stroll.json`; `ph`/`syl` are Kokoro phonemes, e.g. `kˈoʊzi`; `note`/`tip`/`vn_tip` are shown on screen, `note_say`/`tip_say`/`vn_tip_say`/`mean_say`/`ex_say` are read aloud; `vn_tip` is the "Người Việt hay nhầm" tip for Vietnamese speakers).
2. Add an illustration class with `WORD = "<word>"` in `engine/art/` (any file in that folder is loaded).
3. Append the word to `words/queue.json`.

## Add a story

1. Add `stories/<name>.json` (copy `stories/rainy-evening.json`): a `title` and 3–5 `lines`.
   Each line has one `word` (must already exist in `words/`, with an illustration) and the `text` shown on screen.
   The word must appear in the text in one of its `forms` (e.g. "sipped"). Add `say` only if the voice
   should read it differently (extra commas or "..." for pauses).
2. Append the name to `stories/queue.json`. It posts on the first Sunday at 12:00 when all its words are public.
   To post it now: **Actions → Daily video → Run workflow**, kind = `story`, story = `<name>`.

Test locally:
```bash
pip install -r requirements.txt   # plus ffmpeg on your PATH
mkdir models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx && mv kokoro-v1.0.int8.onnx kokoro.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin && mv voices-v1.0.bin voices.bin
cd .. && python scripts/make_video.py --kind word --word stroll
python scripts/make_video.py --kind quiz --words stroll,sip,doze,soothing,linger
python scripts/make_video.py --kind review --style recall   # 12:00 review
python scripts/make_video.py --kind story --story rainy-evening
```
