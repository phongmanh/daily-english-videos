"""Original, copyright-free background music: a soft chord pad plus gentle plucks."""
import numpy as np

SR = 44100

def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)

PROGRESSIONS = [
    [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 55, 59]],   # C  Am F  G
    [[50, 57, 60, 65], [46, 53, 57, 62], [41, 48, 52, 57], [48, 55, 59, 64]],   # Dm Bb F  C
    [[45, 52, 55, 60], [41, 48, 53, 57], [48, 55, 60, 64], [43, 50, 55, 59]],   # Am F  C  G
]

def make_music(dur, seed=0):
    """Stereo float array (n, 2), peak about 0.25."""
    rng = np.random.default_rng(seed)
    chords = PROGRESSIONS[seed % len(PROGRESSIONS)]
    n = int(SR * dur)
    t = np.arange(n) / SR
    seg = 8.0
    pad = np.zeros(n)
    for k in range(int(dur / seg) + 1):
        start = k * seg - 2.0
        env = np.clip((t - start) / 3.0, 0, 1) * np.clip((start + seg + 4.0 - t) / 3.0, 0, 1)
        env = 0.5 - 0.5 * np.cos(np.pi * env)
        for m in chords[k % 4]:
            for det in (-0.12, 0.12):
                ff = _hz(m) * 2 ** (det / 12)
                pad += env * (np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(4 * np.pi * ff * t + 1.0))
    pad *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    scale = [72, 74, 76, 79, 81, 84]
    plk = np.zeros(n)
    tt = 1.5
    while tt < dur - 4:
        f = _hz(scale[rng.integers(len(scale))])
        i0 = int(tt * SR); L = min(int(3.0 * SR), n - i0)
        x = np.arange(L) / SR
        plk[i0:i0 + L] += (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 1.8) * np.clip(x / 0.01, 0, 1)
        tt += rng.choice([2.0, 2.5, 3.0, 4.0])
    mix = pad / np.abs(pad).max() * 0.5 + (plk / np.abs(plk).max() * 0.35 if plk.any() else 0)
    out = mix.copy()
    for d, g in [(0.29, 0.35), (0.47, 0.25), (0.71, 0.18), (1.1, 0.1)]:
        s = int(d * SR); out[s:] += g * mix[:-s]
    out *= np.clip(t / 2.0, 0, 1) * np.clip((dur - t) / 3.0, 0, 1)
    out = out / np.abs(out).max() * 0.25
    return np.stack([out, np.roll(out, int(0.012 * SR))], 1)

def mix_with_voice(voice, voice_sr, dur, seed=0):
    """Resample voice to 44.1k, duck music under it, return stereo float array."""
    total = int(dur * SR)
    v = np.interp(np.arange(int(len(voice) * SR / voice_sr)) * voice_sr / SR, np.arange(len(voice)), voice)
    vo = np.zeros(total); vo[:min(total, len(v))] = v[:total]
    vo = vo / max(1e-6, np.abs(vo).max()) * 0.85
    m = make_music(dur + 1, seed)[:total]
    env = np.convolve(np.abs(vo), np.ones(SR // 5) / (SR // 5), mode="same")
    duck = np.convolve(1 - 0.55 * np.clip(env / 0.05, 0, 1), np.ones(SR // 4) / (SR // 4), mode="same")
    out = m * 0.9 * duck[:, None] + vo[:, None]
    return out / max(1.0, np.abs(out).max()) * 0.95
