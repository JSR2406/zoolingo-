#!/usr/bin/env python3
"""
ZooLingo Demo Audio Generator
Synthesizes recognizable animal vocalization WAV files so the demo pipeline
can be tested end-to-end with real (synthetic) audio.

Outputs two variants per animal:
  {animal_key}_calm.wav    - soft/neutral vocalization
  {animal_key}_intense.wav - loud/rapid vocalization

Uses only Python stdlib (wave + math) so it runs anywhere.
"""

import math
import os
import struct
import wave

SAMPLE_RATE = 22050
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "demo_audio")


def write_wav(path, samples):
    """Write 16-bit mono PCM samples to a WAV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            frames += struct.pack("<h", int(v * 32767))
        wf.writeframes(bytes(frames))


def env_ad(n, attack, release):
    """Simple attack/release amplitude envelope."""
    env = []
    for i in range(n):
        if i < attack:
            env.append(i / attack)
        elif i > n - release:
            env.append(max(0.0, (n - i) / release))
        else:
            env.append(1.0)
    return env


def tone(freq, dur, amp=0.7, harmonics=5, vibrato_hz=0.0, vibrato_depth=0.0, phase_start=0.0):
    """Generate a tone with optional harmonics and vibrato."""
    n = int(dur * SAMPLE_RATE)
    p = phase_start
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        vib = vibrato_depth * math.sin(2 * math.pi * vibrato_hz * t)
        phi = 2 * math.pi * freq * t + 2 * math.pi * (freq * vib) * t * 0.0
        # integrate vibrato as phase modulation
        f = freq * (1 + vib)
        phase = 2 * math.pi * i * (f / SAMPLE_RATE)
        s = 0.0
        for h in range(1, harmonics + 1):
            s += math.sin(phase * h + p) / (h ** 1.2)
        out.append(s * amp)
    return out


def glide(f0, f1, dur, amp=0.7, harmonics=4):
    """Frequency sweep from f0 to f1."""
    n = int(dur * SAMPLE_RATE)
    phase = 0.0
    out = []
    for i in range(n):
        frac = i / max(1, n)
        f = f0 + (f1 - f0) * frac
        phase += 2 * math.pi * f / SAMPLE_RATE
        s = sum(math.sin(phase * h) / h for h in range(1, harmonics + 1))
        out.append(s * amp)
    return out


def bursts(freq, burst_dur, gap_dur, count, amp=0.8, harmonics=5):
    """Series of short tones (bark / cluck / quack)."""
    out = []
    for _ in range(count):
        out += tone(freq, burst_dur, amp=amp, harmonics=harmonics)
        out += [0.0] * int(gap_dur * SAMPLE_RATE)
    return out


def noisy(freq, dur, amp=0.6, noise_amt=0.4):
    """Tone blended with pseudo-random noise (harsh/aggressive sounds)."""
    n = int(dur * SAMPLE_RATE)
    phase = 0.0
    seed = 12345
    out = []
    for i in range(n):
        phase += 2 * math.pi * freq / SAMPLE_RATE
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        rnd = (seed / 0x7FFFFFFF) * 2 - 1
        s = math.sin(phase) * (1 - noise_amt) + rnd * noise_amt
        out.append(s * amp)
    return out


def pitch_sweep_repeat(f0, f1, dur, repeat=1, amp=0.7):
    """Repeated frequency sweeps (meow / howl / neigh)."""
    out = []
    seg = dur / repeat
    for _ in range(repeat):
        out += glide(f0, f1, seg, amp=amp)
    return out


# --- Animal sound synthesizers ---------------------------------------------

def synthesize(name):
    calm, intense = None, None

    if name == "dog":
        calm = bursts(380, 0.09, 0.14, 5, amp=0.6, harmonics=4)
        intense = bursts(310, 0.07, 0.06, 12, amp=0.9, harmonics=6)
    elif name == "cat":
        calm = pitch_sweep_repeat(520, 280, 0.9, repeat=2, amp=0.55)
        intense = pitch_sweep_repeat(700, 220, 0.6, repeat=3, amp=0.9)
        intense = noisy(500, 0.25, amp=0.5, noise_amt=0.5) + intense
    elif name == "cow":
        calm = tone(200, 1.1, amp=0.7, harmonics=6, vibrato_hz=5, vibrato_depth=0.02)
        intense = tone(170, 0.9, amp=0.9, harmonics=7, vibrato_hz=7, vibrato_depth=0.04)
    elif name == "lion":
        calm = tone(120, 1.4, amp=0.55, harmonics=3, vibrato_hz=4, vibrato_depth=0.03)
        intense = noisy(110, 1.2, amp=0.9, noise_amt=0.5)
        intense = tone(110, 0.8, amp=0.8, harmonics=3) + intense
    elif name == "bird":
        calm = bursts(2600, 0.05, 0.06, 12, amp=0.4, harmonics=6)
        intense = bursts(1900, 0.03, 0.02, 34, amp=0.7, harmonics=8)
    elif name == "horse":
        calm = pitch_sweep_repeat(380, 860, 1.0, repeat=2, amp=0.6)
        intense = pitch_sweep_repeat(300, 1100, 0.7, repeat=3, amp=0.9)
    elif name == "elephant":
        calm = tone(280, 1.0, amp=0.65, harmonics=8, vibrato_hz=6, vibrato_depth=0.03)
        intense = tone(240, 0.9, amp=0.9, harmonics=10, vibrato_hz=8, vibrato_depth=0.05)
    elif name == "sheep":
        calm = pitch_sweep_repeat(420, 300, 0.7, repeat=3, amp=0.55)
        intense = pitch_sweep_repeat(460, 240, 0.55, repeat=5, amp=0.85)
    elif name == "goat":
        calm = pitch_sweep_repeat(600, 480, 0.5, repeat=3, amp=0.55)
        intense = pitch_sweep_repeat(680, 400, 0.4, repeat=5, amp=0.85)
    elif name == "pig":
        calm = bursts(240, 0.14, 0.2, 5, amp=0.6, harmonics=6)
        intense = bursts(200, 0.08, 0.07, 14, amp=0.9, harmonics=8)
        intense = bursts(900, 0.12, 0.08, 5, amp=0.7, harmonics=8) + intense
    elif name == "chicken":
        calm = bursts(620, 0.07, 0.12, 7, amp=0.5, harmonics=7)
        intense = bursts(700, 0.05, 0.05, 16, amp=0.85, harmonics=9)
    elif name == "duck":
        calm = bursts(480, 0.1, 0.16, 6, amp=0.55, harmonics=6)
        intense = bursts(560, 0.07, 0.05, 16, amp=0.9, harmonics=8)
    elif name == "monkey":
        calm = bursts(340, 0.06, 0.05, 12, amp=0.5, harmonics=5)
        intense = bursts(260, 0.05, 0.04, 22, amp=0.8, harmonics=7)
    elif name == "parrot":
        calm = bursts(1500, 0.12, 0.14, 6, amp=0.55, harmonics=8)
        intense = bursts(1200, 0.06, 0.04, 20, amp=0.9, harmonics=10)
    elif name == "wolf":
        calm = pitch_sweep_repeat(520, 380, 2.0, repeat=1, amp=0.6)
        intense = pitch_sweep_repeat(560, 300, 1.2, repeat=2, amp=0.95)

    if calm is None:
        calm = tone(400, 0.8, amp=0.6)
    if intense is None:
        intense = tone(400, 0.8, amp=0.9)

    # Apply envelope to soften clicks and pad with silence
    calm = ([0.0] * int(0.08 * SAMPLE_RATE)) + calm + ([0.0] * int(0.2 * SAMPLE_RATE))
    intense = ([0.0] * int(0.05 * SAMPLE_RATE)) + intense + ([0.0] * int(0.2 * SAMPLE_RATE))

    return calm, intense


def main():
    animals = [
        "dog", "cat", "cow", "lion", "bird", "horse", "elephant",
        "sheep", "goat", "pig", "chicken", "duck", "monkey", "parrot", "wolf",
    ]
    written = []
    for name in animals:
        calm, intense = synthesize(name)
        calm_path = os.path.join(OUTPUT_DIR, f"{name}_calm.wav")
        intense_path = os.path.join(OUTPUT_DIR, f"{name}_intense.wav")
        write_wav(calm_path, calm)
        write_wav(intense_path, intense)
        written.append(f"{name}_calm.wav ({len(calm) / SAMPLE_RATE:.1f}s)")
        written.append(f"{name}_intense.wav ({len(intense) / SAMPLE_RATE:.1f}s)")

    print("Generated {} demo audio files in {}:".format(len(written), os.path.abspath(OUTPUT_DIR)))
    for w in written:
        print("  -", w)


if __name__ == "__main__":
    main()