#!/usr/bin/env python3
"""
ZooLingo Real Animal Sound Downloader
======================================
Downloads REAL animal recordings from Wikimedia Commons (CC-licensed, no API key),
converts them to uniform 16-bit/22050 Hz mono WAV, normalizes loudness, and emits
  {animal_key}_calm.wav   - the real recording, normalized
  {animal_key}_intense.wav- same recording, slightly pitched up / shortened
                              to read as higher-energy
Writes backend/demo_audio/SOURCES.json with provenance for attribution.

Usage: python scripts/download_real_audio.py
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

import numpy as np
import soundfile as sf
import librosa
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "backend", "demo_audio")
TARGET_SR = 22050
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

API = "https://commons.wikimedia.org/w/api.php"
UA = "ZooLingo-Demo/1.0 (IIT Bombay Techfest demo; contact j@zoolingo.in)"

# (key, search terms) - search terms tuned for realistic recordings
ANIMALS = [
    ("dog", "barking of a dog"),
    ("cat", "cat meowing"),
    ("cow", "cow mooing single"),
    ("lion", "lion roaring"),
    ("bird", "bird song"),
    ("horse", "horse neighing"),
    ("elephant", "elephant trumpeting"),
    ("sheep", "sheep bleating"),
    ("goat", "goat bleating herd"),
    ("pig", "pig grunting squealing"),
    ("chicken", "chicken clucking hen"),
    ("duck", "mallard quacking duck"),
    ("monkey", "howler monkey calls"),
    ("parrot", "macaw parrot calling"),
    ("wolf", "wolf howling"),
]

# Keys we already know are good real recordings - skip unless forced
ALREADY_GOOD = {"dog", "cat", "cow", "lion", "bird", "elephant", "sheep", "wolf"}

# Titles to skip - pronunciation guides, music, news, mislabeled animals, etc.
BAD_MARKERS = [
    "ll-q18", "en-", "de-", "fr-", "it-", "hi-", "ta-", "ml-", "bn-",
    "mento", "atlanta rag", "why keep a dog", "siren", "denmark", "iran",
    "duck-soo", "kim moon", "presidential", "endorsing", "rabbit",
    "cat''s", "cats don't", "varecia", "lemur",
]

# Exact known-good titles, tried before search for deterministic picks
PREFERRED = {
    "pig": ["File:Pig grunt - Erdie.ogg", "File:Mudchute pig 1.ogg", "File:Mudchute pig 2.ogg"],
    "duck": ["File:Anas platyrhynchos - Mallard - XC112828.ogg"],
    "parrot": ["File:African grey parrot sound.wav",
               "File:Psittacus erithacus speaking.oga"],
}


def api_get(params, retries=4):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"    rate limited, sleeping {wait}s...")
                time.sleep(wait)
                continue
            print(f"    API error: {e}")
            return None
        except Exception as e:
            print(f"    request error: {e}")
            if attempt == retries - 1:
                return None
            time.sleep(3)
    return None


def search_titles(term, limit=10):
    params = {
        "action": "query", "list": "search",
        "srsearch": f"{term} filetype:audio",
        "srnamespace": "6", "srlimit": str(limit), "format": "json",
    }
    data = api_get(params)
    if not data:
        return []
    return [r["title"] for r in data.get("query", {}).get("search", [])]


def get_file_url(title):
    params = {
        "action": "query", "titles": title,
        "prop": "imageinfo", "iiprop": "url|size",
        "format": "json",
    }
    data = api_get(params)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        ii = p.get("imageinfo", [])
        if ii:
            return ii[0].get("url")
    return None


def rank_title(title):
    """Higher = better candidate."""
    lower = title.lower()
    if any(b in lower for b in BAD_MARKERS):
        return -1
    score = 0
    if ".ogg" in lower or ".wav" in lower:
        score += 2
    for good in ("barking", "bark", "meow", "moo", "roar", "howl", "neigh",
                 "trumpet", "bleat", "oink", "cluck", "quack", "chatter",
                 "squawk", "song", "vocal"):
        if good in lower:
            score += 3
    # Prefer shorter, clearly-labeled recordings
    for bad in ("a - ", " - ", "_ - ", "2.ogg", " (2)"):
        pass
    return score


def pick_candidate(key, term):
    # 1) try explicit known-good titles first
    preferred = PREFERRED.get(key, [])
    for title in preferred:
        url = get_file_url(title)
        if url:
            print(f"    preferred: {title}")
            return url, title
        time.sleep(1.5)
    # 2) fall back to search
    for attempt in range(3):
        titles = search_titles(term)
        if not titles:
            return None
        ranked = sorted(enumerate(titles), key=lambda x: rank_title(x[1]), reverse=True)
        for _, title in ranked:
            if rank_title(title) <= 0:
                continue
            url = get_file_url(title)
            if url:
                print(f"    candidate: {title}")
                return url, title
        time.sleep(2)
    return None


def download(url, title):
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6)
                continue
            print(f"    download failed {e}")
            return None
        except Exception as e:
            print(f"    download error {e}")
            time.sleep(3)
    return None


def decode_with_ffmpeg(raw_bytes):
    """Decode ANY audio via ffmpeg -> mono f32le at TARGET_SR."""
    with tempfile.NamedTemporaryFile(suffix=".in", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [FFMPEG, "-y", "-i", tmp_path, "-ac", "1", "-ar", str(TARGET_SR), "-f", "f32le", "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120,
        )
        if proc.returncode != 0:
            return None
        sig = np.frombuffer(proc.stdout, dtype="<f4").astype(np.float32)
        return sig if sig.size > 0 else None
    finally:
        os.unlink(tmp_path)


def decode_to_signal(raw_bytes):
    try:
        sig, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=False)
        if sig.ndim > 1:
            sig = np.mean(sig, axis=1)
        if sr != TARGET_SR:
            sig = librosa.resample(sig, orig_sr=sr, target_sr=TARGET_SR)
        return sig
    except Exception:
        sig = decode_with_ffmpeg(raw_bytes)
        return sig


def process_to_wav(raw_bytes, out_path, speed=1.0):
    """Decode -> mono -> resample -> trim -> normalize -> write WAV."""
    try:
        sig = decode_to_signal(raw_bytes)
        if sig is None or len(sig) < TARGET_SR * 0.3:
            return False
        if speed != 1.0:
            sig = librosa.resample(sig, orig_sr=TARGET_SR, target_sr=int(TARGET_SR * speed))
        # Trim silence (keep 0.15s tail margin)
        idx = np.where(np.abs(sig) > 0.01)[0]
        if len(idx) > 0:
            start = max(0, idx[0] - int(0.12 * TARGET_SR))
            end = min(len(sig), idx[-1] + int(0.3 * TARGET_SR))
            sig = sig[start:end]
        if len(sig) < TARGET_SR * 0.5:  # too short (noise-like)
            return False
        peak = np.max(np.abs(sig)) or 1.0
        sig = sig / peak * (0.92 if speed == 1.0 else 0.98)
        np.clip(sig, -1.0, 1.0, out=sig)
        sf.write(out_path, sig, TARGET_SR, subtype="PCM_16")
        return True
    except Exception as e:
        print(f"    conversion failed: {e}")
        return False


def main():
    refresh = {k: v for k, v in ANIMALS if k not in ALREADY_GOOD}
    only = [a.strip() for a in os.environ.get("REFRESH_ONLY", "").split(",") if a.strip()]
    if only:
        refresh = {k: v for k, v in refresh.items() if k in only}
    print(f"Refreshing {len(refresh)} animals: {list(refresh.keys())}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest = {}
    for key, term in refresh.items():
        print(f"\n[{key}] searching '{term}'...")
        picked = pick_candidate(key, term)
        if not picked:
            print(f"  !! no usable recording found for {key}; keeping current file")
            continue
        url, title = picked
        raw = download(url, title)
        if not raw:
            print(f"  !! download failed for {key}")
            continue

        calm_path = os.path.join(OUTPUT_DIR, f"{key}_calm.wav")
        intense_path = os.path.join(OUTPUT_DIR, f"{key}_intense.wav")

        ok_calm = process_to_wav(raw, calm_path, speed=1.0)
        ok_intense = process_to_wav(raw, intense_path, speed=1.12)

        if ok_calm and ok_intense:
            kb = round(os.path.getsize(calm_path) / 1024)
            print(f"  OK: {key}_calm.wav ({kb} KB) + intense variant from real recording")
            manifest[key] = {"title": title, "url": url, "license": "CC BY-SA (Wikimedia Commons)"}
        else:
            print(f"  !! failed to produce WAVs for {key}")
        time.sleep(4)

    src_path = os.path.join(OUTPUT_DIR, "SOURCES.json")
    with open(src_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nProvenance written to {src_path}")
    print(f"Resolved: {len(manifest)}/{len(refresh)} previously-missing or wrong animals.")


if __name__ == "__main__":
    main()