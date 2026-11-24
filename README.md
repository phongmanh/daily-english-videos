# Daily English videos

Makes one English-vocabulary Short every day and posts it to YouTube Shorts and Facebook Reels.

Each Short (~30–35 s, 1080×1920): today's word → syllables with stress → "sounds like" → pronunciation tip →
"your turn" pause → Vietnamese meaning → definition → example → follow reminder.
Paper-style background, a new illustration per word, Kokoro AI voice, original background music.

**First time?** Read [SETUP.md](SETUP.md) to connect YouTube and Facebook.

## How it works

```
GitHub Actions (daily, 02:37 VN)
  └─ scripts/make_short.py      next word from words/queue.json → out/<word>.mp4 + meta.json
  └─ scripts/upload_youtube.py  private, publishAt 18:00 VN
  └─ scripts/upload_facebook.py Reel, scheduled 18:00 VN
  └─ scripts/mark_published.py  adds the word to state/published.json (commit)
```

## Folders

| Path | What |
|---|---|
| `words/<word>.json` | All content for one word (meaning, example, phonemes, colors) |
| `words/queue.json` | Posting order |
| `state/published.json` | What has been posted (don't edit by hand unless re-posting) |
| `engine/art/` | One illustration class per word (`WORD = "..."`, `frame(t)` → 1600×1600 image) |
| `engine/short.py` | Short layout and rendering |
| `engine/voice.py` | Narration script + Kokoro TTS |
| `engine/music.py` | Generated background music |
| `assets/fonts/` | Inter, Gelasio, DejaVu Sans (open licenses included) |

## Add new words

1. Add `words/<word>.json` (copy an existing one; `ph`/`syl` are Kokoro phonemes, e.g. `kˈoʊzi`).
2. Add an illustration class with `WORD = "<word>"` in `engine/art/` (any file in that folder is loaded).
3. Append the word to `words/queue.json`.

Test locally:
```bash
pip install -r requirements.txt   # plus ffmpeg on your PATH
mkdir models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx && mv kokoro-v1.0.int8.onnx kokoro.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin && mv voices-v1.0.bin voices.bin
cd .. && python scripts/make_short.py --word cozy
```
