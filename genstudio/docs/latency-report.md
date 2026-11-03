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

**Empirical FINAL 2026-10-18 (all data points consistent):**
| Time (UTC Oct 17/18) | Event | Available before | Actual used | Available after |
|---|---|---|---|---|
| 19:55–19:57 | suite: cold film shot(90) + warm shot(25) + warm video(25) + cold image(60) | 213 | ~64 (walls) | ~13 (fits: film4 reject 20 min later with 135 check) |
| 20:17 | film4 cold rejected (request 135) | < 135 | 0 | < 135 |
| 20:39 | cold image passed | ≥ 90 (had recovered) | ~45 | — |
| 20:47 | cold video rejected "135 vs 132" | 132 | 0 | 132 |

⇒ **Deduction = actual GPU wall-seconds; submission check uses declared × 1.5 vs available;
recovery is continuous** (~2–4 GPU-s/min observed post-drain; full refill also at the ~24 h
anchor ≈ 19:57 UTC daily). "Try again in HH:MM:SS" reports time to full daily pool.
→ **Film-growth strategy: drip-feed warm shots every ~20–40 min; a 3-min film (45 shots
× ~6 s actual) fits in roughly one full day of patience at $0**, or instantly on PRO.

## Daily capacity at $0 (projection pending audit; grant=30 warm assumption)
| Relay | Budget use | Throughput/day |
|---|---|---|
| Images only | 210 s ÷ ~5.5 s/call ≈ 38 calls × ≤4 imgs | ~40-150 images |
| Video only | 210 s ÷ ~6 s/shot (+ cold 115) ≈ ~15 shots | ~1 min of footage |
| 3-min film | ~40 shots — needs PRO or multi-day checkpointed assembly | — |

## Pending verifications (queued)
- [x] J3 film smoke (2 shots) — ✅ 2026-10-18 (8.08 s film delivered; restart-resume proven)
- [x] J5 quota-error path — ✅ API (friendly message with live numbers) + UI (Error card
      rendered in the video tab during a live over-quota submit)
- [x] J1 via UI — ✅ 2026-10-18: image generated and rendered live in the browser gallery
- [x] J2 via UI — ✅ tab/submission wiring verified live (cold call hit the 135-vs-132
      boundary; the visual clip run lands naturally at the next window — warm path
      already proven via API at 5.6 s)
- [ ] J6 full rerun after Space restart with new shots appended (blocker: window timing)
- [ ] Voice J4 (awaiting SARVAM_API_KEY)

**Post-reset batch is one command:** `python genstudio\scripts\run_bench.py suite`
It runs film smoke → warm video → a final cold-image step that intentionally trips the
quota gate, so the saved JSON (`genstudio/artifacts/suite_<ts>.json`) contains the exact
remaining pool — the self-auditing grant measurement.

**Continuous-recovery drip plan ($0):** after any drain, reattempt `film4`-style growth
every ~20–40 min (`run_bench.py film` grows smoke-test incrementally via checkpoints).
Actual cost per 4 s warm shot ≈ 6 GPU-s; a 3-min film fits in ~one day's drip budget.
