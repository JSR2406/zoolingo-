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
| 1 | Image, cold boot | Z-Image-Turbo 1024², 8 steps | 2 | 6.4 (+39.8 build); 5.17 (+53 client incl. build) | 60 | build inside first call |
| 2 | Image, warm | 1024², 8 steps | 2 | 5.13, 5.28 | 25 | |
| 3 | Video, cold boot | LTX 2B 768×512, 97 f, 8 steps | 1 | 5.71 (+33.4 build) | 115→90 | |
| 4 | Video, warm | 768×512 4.04 s | 2 | 5.6 (16.5 client) | 25 | ✅ 2026-10-18 |
| 5 | Film smoke, 2×4 s | cold build + 2 shots + CPU concat | 1 | server OK ~70 s; 8.08 s film delivered | 90+25 | ✅ J3 2026-10-18 |
| 6 | Film resume after restart | 2 shots refetched from dataset repo | 1 | 0.0 GPU, assembly+delivery only | — | ✅ J6 core 2026-10-18 |

## J3/J5/J6 outcome (2026-10-18 01:26 IST)
- **J3 ✅** — 2×4 s shots generated, persisted to `Theinvinvible24/genstudio-films`,
  assembled via ffmpeg concat, and the results tuple delivered to the API client.
- **J6 ✅ (core)** — Space was restarted (new deploy) between shot generation and the
  re-run; shots recovered from the checkpoint repo (`wall_s 0.0`, provenance
  "checkpoint"), no GPU spent.
- **Delivery bug (fixed)** — first assembled film POST suffered a client 403 on
  `/gradio_api/file=000.mp4`: gradio_client's legacy `is_file_obj` downloads *any* dict
  with a `"path"` key; our timing JSON `{"path": "000.mp4"}` looked like FileData.
  Fixed by renaming the key to `"file"` (commit 8da952a).

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

**Empirical update 2026-10-18:** a full suite (film cold shot 90 + warm shot 25 + warm
video 25 + cold image 60 = **200 declared**) ran with **no quota error** ⇒ ×1.5 is used
for the *request check*, but actual deduction is lower (declared-sum 200 still fits; or
deduction ≈ wall seconds ≈ 64). Refined model to verify with a longer drain test.

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
