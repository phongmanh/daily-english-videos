"""Encoding helpers shared by all video types."""
import os, subprocess, wave
import numpy as np
from engine import music

class Encoder:
    """Pipe RGB frames into an H.264 file (same settings for every scene so they can be joined)."""
    def __init__(self, path, w, h, fps=30):
        self.p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                   "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "18",
                                   "-preset", "veryfast", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    def write(self, frame):
        self.p.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())
    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError("ffmpeg encode failed")

def render_frames(path, draw, dur, w, h, fps=30):
    enc = Encoder(path, w, h, fps)
    for k in range(int(round(dur * fps))):
        enc.write(draw(k / fps))
    enc.close()

def concat(parts, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    os.remove(lst)
    if r.returncode:
        raise RuntimeError("ffmpeg concat failed")

def write_wav(path, stereo):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(music.SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())

def mux(video, wav, out):
    tmp = out + ".tmp.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", tmp])
    if r.returncode:
        raise RuntimeError("ffmpeg mux failed")
    os.replace(tmp, out)
