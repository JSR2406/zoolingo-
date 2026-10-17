# Latency baseline — measured on live ZeroGPU (free account, 2026-10-16)

Space: [Theinvinvible24/genstudio](https://huggingface.co/spaces/Theinvinvible24/genstudio) — hardware `zero-a10g`, Gradio 6.30, diffusers 0.41.

## Measured results (API calls, own token)

| Bench | Config | Cold (first call this boot: download+build pipel.) | Warm inference wall |
|---|---|---|---|
| **Image** — Z-Image-Turbo | 1024×1024, 8 steps, guidance 0.0 | 39.8 s build + 6.4 s gen = **46.2 s cold** | **5.13 s** (2.55 s of that is post-cache build-check; raw ~2.5-5 s) |
| **Video** — LTX-Video 2B | 768×512, 97 frames (≈4 s @ 24 fps), 8 steps | 33.4 s build + 5.71 s gen = **39.2 s cold** | **5.71 s** |

Artifacts: `genstudio/artifacts/bench_image.png`, `genstudio/artifacts/bench_video.mp4`.

## Quota semantics (empirical, 2026-10-16 evening)
- Error text observed: `"You have exceeded your free ZeroGPU quota (172s requested vs. 41s left).
  Try again in 23:15:21."` → the pool counts the **duration granted per call** (in-flight reserve),
  not purely actual runtime; empirical free pool ≈ **3.5 min/day**, reset 24 h after first use.
- Consequence: dynamic durations implemented — `duration=115` only on the cold build call,
  `duration=30` (warm) afterwards. Future optimization: inspect whether completed calls refund
  actual vs granted time (needs controlled A/A test next session).

## Interpretation
- Both flagship picks fit the 120 s ZeroGPU cap with **~10-20× headroom**; even
  simultaneous residency (Z-Image + LTX2B, ≈ 24 GB combined) is fine on ~48 GB VRAM.
- 5 s per 1024² image and ~5.7 s per 4 s clip ≈ **generation faster than playback** for video.
- Cold-start per boot: ~40-46 s inside the first GPU call of each model. Every Space
  restart (rebuild/idle stop) resets this. Both models were warmed down to constant ~5-6 s calls.

## Daily capacity math at $0 (to be validated tomorrow: quota-label test pending)
- Assumed budget: ~300 GPU-seconds/day (free account; 24 h reset after first use).
- All-images relay: ~45-60 images/day (at ~5-6 s actual billed time). Effectively "unlimited
  draft images" for personal use.
- All-video relay: ~45-50 4 s clips/day (at ~5.7-6 s). Practically, video quota is OK.
- ⚠️ **Unverified**: whether ZeroGPU bills *requested* `duration=` or *actual* runtime
  (older forum reports suggest requested). If requested-billed, capacity drops by the ratio
  requested/actual (e.g., 115/6 ≈ 19× worse for the dynamic-duration video call).
  → Scheduled test: one low-work call with duration=115 vs duration=45, comparing where quota ticks.

## Known unknowns still open (tracked in phase0-plan.md)
- [ ] quota billing basis (requested vs actual) — test tomorrow after 24 h reset
- [ ] LTX-Video license exact terms for the `Lightricks/LTX-Video` repo (0.9.0-2B; late repos
      moved to a community license — re-read model card before MVP go-live)
- [ ] 13B-distilled video quality tier on disk budget (tests skipped today to protect quota)
- [ ] queue behavior at concurrency (Phase 2 plays this via Playwright)
