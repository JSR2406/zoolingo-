#!/usr/bin/env python3
"""
Generate the 12 ElevenLabs dog/cat demo sounds (6 emotions x 2 species)
into data/test/elevenlabs/{species}_{emotion}.wav.

Usage (from the backend directory):
    python generate_elevenlabs_sounds.py [--force]

Existing files are skipped unless --force is passed.
"""

import argparse
import os
import sys
import time

import numpy as np
import soundfile as sf

from config import config
from services.elevenlabs_demo import all_sounds
from services.elevenlabs_sfx import ElevenLabsSFX, PCM_SAMPLE_RATE

SAMPLE_RATE = PCM_SAMPLE_RATE


def main():
    parser = argparse.ArgumentParser(description="Generate ElevenLabs demo sounds")
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even if files exist"
    )
    parser.add_argument(
        "--species", choices=["dog", "cat"], help="Only generate one species"
    )
    args = parser.parse_args()

    client = ElevenLabsSFX(api_key=config.ELEVENLABS_API_KEY)
    if not client.configured:
        print("ERROR: ELEVENLABS_API_KEY is not set in backend/.env")
        return 1

    out_dir = config.ELEVENLABS_DEMO_DIR
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output dir: {out_dir}")

    sounds = all_sounds()
    if args.species:
        sounds = [s for s in sounds if s["species"] == args.species]

    generated = 0
    for s in sounds:
        path = os.path.join(out_dir, s["filename"])
        if os.path.exists(path) and not args.force:
            print(f"skip   {s['filename']} (exists)")
            continue
        print(f"gen    {s['filename']} | {s['prompt'][:60]}...")
        try:
            raw = client.generate_sound_effect(
                text=s["prompt"],
                duration_seconds=2.5,
                output_format="pcm_22050",
                prompt_influence=0.6,
            )
            samples = client.pcm_to_samples(raw)
            sf.write(path, samples, SAMPLE_RATE, subtype="PCM_16")
            duration = len(samples) / SAMPLE_RATE
            print(f"  ok ({duration:.2f}s, {os.path.getsize(path) // 1024} KB)")
            generated += 1
        except Exception as e:
            print(f"  FAIL: {e}")
        time.sleep(1.2)  # be gentle with the API

    print(f"\nDone. {generated} sound(s) generated into {out_dir}")


if __name__ == "__main__":
    sys.exit(main())
