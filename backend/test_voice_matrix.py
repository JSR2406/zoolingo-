"""
Voice matrix test: exercise ALL ElevenLabs demo records through /api/process-audio
using every available SARVAM voice.

Matrix:  12 records (dog + cat x 6 emotions) x {hi-IN: shubh, ritu, tanya} x {en-IN: neha, rohan}
Total:   60 pipeline runs (classify -> LLM translate -> TTS)

Each run verifies:
  - status == success
  - translation is non-empty and matches the language (Devanagari for hi-IN, ASCII for en-IN)
  - response voice == requested (validated) voice
  - TTS mp3 exists and serves with audio/mpeg

Usage:
  python test_voice_matrix.py                # full matrix (60 runs)
  python test_voice_matrix.py --limit 6      # first 6 runs only (smoke)
  python test_voice_matrix.py --report demo/voice_matrix_report.md
"""

import argparse
import json
import os
import sys
import time

import requests

BACKEND_URL = os.getenv("ZOOLINGO_BACKEND_URL", "http://127.0.0.1:8001")

VOICES_BY_LANGUAGE = {
    "hi-IN": ["shubh", "ritu", "tanya"],
    "en-IN": ["neha", "rohan"],
}


def is_devanagari(text):
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def is_ascii(text):
    return all(ord(c) < 128 for c in text)


def run_one(file_path, filename, language, voice):
    sentry = time.time()
    with open(file_path, "rb") as fh:
        response = requests.post(
            f"{BACKEND_URL}/api/process-audio",
            files={"file": (filename, fh, "audio/wav")},
            data={"language": language, "voice": voice},
            timeout=120,
        )
    elapsed = round(time.time() - sentry, 1)
    payload = response.json() if response.ok else {}
    data = payload.get("data") or {}

    checks = {
        "http_ok": response.ok,
        "status": payload.get("status") == "success",
        "translation_nonempty": bool(data.get("translation")),
        "language_text": (is_devanagari(data.get("translation", "")) if language == "hi-IN"
                          else is_ascii(data.get("translation", "")) if data.get("translation")
                          else True),
        "voice_echoed": data.get("voice") == voice,
        "tts_mp3": data.get("audio_url") is not None,
    }
    ok = all(checks.values())

    tts_ok = "n/a"
    if checks["tts_mp3"] and ok:
        try:
            r = requests.get(f"{BACKEND_URL}{data['audio_url']}", timeout=60)
            tts_ok = f"{r.status_code}:{r.headers.get('Content-Type', '?')}:{len(r.content)}B"
            checks["tts_serves_ok"] = r.status_code == 200 and "audio" in r.headers.get("Content-Type", "")
        except Exception as e:
            checks["tts_serves_ok"] = False
            tts_ok = f"ERR:{str(e)[:60]}"

    return {
        "file": filename,
        "language": language,
        "voice": voice,
        "elapsed_s": elapsed,
        "ok": ok,
        "checks": checks,
        "tts_serves": tts_ok,
        "animal": data.get("animal"),
        "emotion": data.get("emotion"),
        "confidence": data.get("confidence"),
        "translation": (data.get("translation") or "")[:80],
        "http_status": response.status_code,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the record x voice matrix test")
    parser.add_argument("--limit", type=int, default=0, help="only run first N combinations")
    parser.add_argument("--delay", type=float, default=0.2, help="seconds between calls")
    parser.add_argument("--report", default="", help="path to write a Markdown report")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)  # zoolingo-local/
    data_dir = os.path.join(repo_root, "data", "test", "elevenlabs")

    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".wav"))
    if not files:
        print("No ElevenLabs wav files found; run generate_elevenlabs_sounds.py first.")
        sys.exit(1)

    combinations = []
    for f in files:
        for lang, voices in VOICES_BY_LANGUAGE.items():
            for voice in voices:
                combinations.append((f, lang, voice))

    if args.limit:
        combinations = combinations[: args.limit]

    print(f"Matrix: {len(combinations)} runs "
          f"({len(files)} records x {sum(len(v) for v in VOICES_BY_LANGUAGE.values())} voices)")
    print(f"Backend: {BACKEND_URL}\n" + "-" * 70)

    results = []
    for i, (f, lang, voice) in enumerate(combinations, 1):
        result = run_one(os.path.join(data_dir, f), f, lang, voice)
        results.append(result)
        mark = "OK " if result["ok"] else "FAIL"
        print(f"[{mark}] {i:02d}/{len(combinations):02d} {f:25s} {lang:5s} {voice:8s} "
              f"-> {result.get('animal')}/{result.get('emotion')} ({result.get('confidence')}) "
              f"{result['elapsed_s']}s tts={result['tts_serves'][:40]}")
        if not result["ok"]:
            print(f"        checks={json.dumps(result['checks'])}, http={result['http_status']}, "
                  f"translation={result['translation']!r}")
        time.sleep(args.delay)

    passed = sum(1 for r in results if r["ok"])
    total_tts = sum(1 for r in results if r["checks"].get("tts_serves_ok"))
    print("-" * 70)
    print(f"PASSED: {passed}/{len(results)}   TTS verified: {total_tts}/{len(results)}")

    if args.report:
        out = os.path.join(repo_root, args.report) if not os.path.isabs(args.report) else args.report
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(make_report(results, passed, total_tts))
        print(f"Report written: {out}")

    sys.exit(0 if passed == len(results) else 1)


def make_report(results, passed, total_tts):
    lines = [
        "# ZooLingo Voice x Record Matrix Test Report",
        "",
        f"- Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Backend: `{BACKEND_URL}`",
        f"- Runs: {len(results)}  (12 ElevenLabs demo records x 5 SARVAM voices)",
        f"- Passed: **{passed}/{len(results)}**  TTS served: **{total_tts}/{len(results)}**",
        "",
        "## Per-run results",
        "",
        "| # | Record | Language | Voice | Status | Animal | Emotion | Conf | TTS | Elapsed |",
        "|---|--------|----------|-------|--------|--------|---------|------|-----|---------|",
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"| {i} | {r['file']} | {r['language']} | {r['voice']} | "
            f"{'PASS' if r['ok'] else 'FAIL'} | {r.get('animal')} | {r.get('emotion')} | "
            f"{r.get('confidence')} | {r['tts_serves'][:30]} | {r['elapsed_s']}s |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()