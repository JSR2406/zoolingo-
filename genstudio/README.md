# GenStudio

Free, self-hosted prompt→**image / video / long-form film** studio on one Hugging Face
ZeroGPU Space — open weights only, strictly $0.

**Live app:** https://huggingface.co/spaces/Theinvinvible24/genstudio
(owner: Theinvinvible24)

## What it does
| Tab | Engine (self-hosted open weights) | License |
|---|---|---|
| 🖼 Image | `Tongyi-MAI/Z-Image-Turbo` (8 steps, no CFG) | Apache 2.0 |
| 🎬 Video (single shot) | `Lightricks/LTX-Video` 2B, ≤ 8 s per shot | RAIL-M (research-only; personal use OK) |
| 🎞 Long-form film | N shots ≤ 8 s each → **ffmpeg concat on CPU (no GPU quota)**; shots checkpointed to a private HF dataset repo, resume-safe | same per-shot license |
| 🔊 Voice | Sarvam `bulbul:v4-flash` REST (user's credits) | Sarvam SaaS terms |

## Why this architecture (verified empirically)
- ZeroGPU free tier: ~3.5 min GPU-seconds/day, grant-based ("duration=" reserves); **120 s max
  per function** → only real-time-ish models fit (LTX 2B ≈ 5.7 s per 4 s clip measured).
- Long videos = chaining: length is limited by daily budget, not architecture; assembly is free CPU.
- All model weights are pulled from the Hub into the Space itself (no external inference APIs).

## Layout
```
genstudio/
├─ .env                     # HF_TOKEN, SARVAM_API_KEY (git-ignored, never printed)
├─ space/                   # THE app: app.py + requirements.txt + README.md (HF Space repo)
├─ docs/                    # phase0-plan.md (audit log), latency-baseline.md (measured)
├─ scripts/                 # create/upload/poll/logs/set_secrets, run_bench.py (test driver)
├─ tests/test_plan.py       # Phase-2 E2E + latency journey plan (J1-J6)
└─ artifacts/               # generated media pulled locally (git-ignored)
```

## Operating notes
- ZeroGPU gotchas (first-import `spaces`, direct `@spaces.GPU` decorators, dynamic durations)
  are documented in `docs/phase0-plan.md` — read before restructuring `space/app.py`.
- Deploy: `python scripts/upload_space.py` (Space restarts automatically).
- Test: `python scripts/run_bench.py image|video|film|voice`.
- Secrets: set via `scripts/set_secrets.py`; never commit, never print.
