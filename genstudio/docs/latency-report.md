# GenStudio — Phase 2 latency report (live measurements)

> Method: `gradio_client` API calls against `Theinvinvible24/genstudio` (zero-a10g),
> wall-clock from client submit to artifact; `wall_s` measured inside the GPU function.
> p50/p95 computed once ≥ 5 samples per row are collected (rows below show n).

## Environment
| Fact | Value |
|---|---|
| Space hardware | ZeroGPU (`zero-a10g`), Gradio 6.30, diffusers 0.41 |
| Account tier | Free (grant-based daily pool ≈ 3.5 min, reset 24 h after first use) |
| Date measured | 2026-10-16/17 |

## Results matrix (updated as runs land)
| # | Task | Config | n | wall_s (observed) | Grant reserved | Notes |
|---|---|---|---|---|---|---|
| 1 | Image, cold boot | Z-Image-Turbo 1024², 8 steps | 1 | 6.4 gen (+39.8 build) | 45 | build inside first call |
| 2 | Image, warm | 1024², 8 steps | 2 | 5.13, 5.28 | 45 | grant still 45 → tuning candidate |
| 3 | Video, cold boot | LTX 2B 768×512, 97 f, 8 steps | 1 | 5.71 gen (+33.4 build) | 115 | dynamic grant fix pending test |
| 4 | Film, 2 shots (smoke) | 2 × 4 s + ffmpeg concat | 0 | — | — | blocked by quota reset; queued |

## Grant accounting (billing rule measured 2026-10-17)
ZeroGPU quota errors report `requested = declared duration × 1.5` against the daily pool:
| Probe | Declared via `@spaces.GPU(duration=…)` | Reported "requested" | Available |
|---|---|---|---|
| Image (cold) | 60 | 90 | 41 |
| Film shot (cold, prev. build) | 115 | 172 | 41 |

`Try again in 1:54:30` at ~17:37 UTC Oct 17 ⇒ pool reset ≈ **19:31 UTC Oct 17**, and **41 s left**
remained unchanged across days ⇒ unbilled day roll-over… to be nailed by the post-reset audit:
one warm image call (declared 25), then a forced over-quota call to read the pool delta —
that decides whether deduction is `declared` or `×1.5 requested`.

## Daily capacity at $0 with the measured rule (pool ≈ 213 s)
| Action | Billed | Calls after a cold boot |
|---|---|---|
| Image cold (60) | 90 | ~210 ÷ 90 = 2 cold boots, then |
| Image warm (25) | 37.5 | ~3 more calls |
| Film: cold shot + warm shots | 135 + 37.5 each | 2-shot smoke = 172.5 ✓ (slack 40) |

## Daily capacity at $0 (projection pending audit; grant=30 warm assumption)
| Relay | Budget use | Throughput/day |
|---|---|---|
| Images only | 210 s ÷ ~5.5 s/call ≈ 38 calls × ≤4 imgs | ~40-150 images |
| Video only | 210 s ÷ ~6 s/shot (+ cold 115) ≈ ~15 shots | ~1 min of footage |
| 3-min film | ~40 shots — needs PRO or multi-day checkpointed assembly | — |

## Pending verifications (queued)
- [ ] J3 film smoke (2 shots) — post-reset, then `video`, then `suite`'s self-audit step
- [ ] J6 resume test (stop Space mid-film, rerun same film id)
- [ ] Voice J4 (awaiting SARVAM_API_KEY)
- [ ] J5 quota-error path via UI (partially verified via API already ✅)

**Post-reset batch is one command:** `python genstudio\scripts\run_bench.py suite`
It runs film smoke → warm video → a final cold-image step that intentionally trips the
quota gate, so the saved JSON (`genstudio/artifacts/suite_<ts>.json`) contains the exact
remaining pool — the self-auditing grant measurement.
