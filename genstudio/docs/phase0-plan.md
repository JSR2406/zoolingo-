# Phase 0 — Feasibility spike (GenStudio)

## Goal
Measure real latency + quota accounting of free ZeroGPU for the locked model picks,
then go/no-go for the MVP.

## Locked picks (verified via HF Hub + current diffusers docs)
| Modality | Repo | License | Pipeline |
|---|---|---|---|
| Image primary | `Tongyi-MAI/Z-Image-Turbo` | Apache 2.0 | `diffusers.ZImagePipeline` (8 steps, guidance 0.0) |
| Image fallback | `black-forest-labs/FLUX.1-schnell` | Apache 2.0 | `FluxPipeline` |
| Video primary | `Lightricks/LTX-Video` (2B) | LTX open-weights (re-verify terms) | `diffusers.LTXPipeline` + `export_to_video` |
| Video quality tier (later) | `Lightricks/LTX-Video-0.9.8-13B-distilled` | LTX open-weights | `LTXPipeline` (needs ~30 GB disk) |
| Voice (out of scope for self-host) | Sarvam `bulbul:v4-flash` API (user credits) | — | REST `POST api.sarvam.ai/text-to-speech` |

## How to run the benchmark
1. Space: `Theinvinvible24/genstudio` (ZeroGPU, free account, Gradio SDK).
2. `python scripts/run_bench.py` (uses `gradio_client` + `HF_TOKEN` from `genstudio/.env`).
3. Record every timing JSON into `docs/latency-baseline.md`.

## Audit points (known unknowns to verify)
- [ ] Quota math: does `@spaces.GPU(duration=...)` bill **requested** vs **actual** seconds?
      (Forum reports older billing rounded to requested 60 s/call → dynamic durations may matter.)
- [ ] Cold start: first call per model downloads weights inside the GPU call — measure &
      compare; if brutal, refactor to boot-time predownload (module-scope load, no quota burn).
- [ ] Real caps: 120 s/function;  ~5 GPU-min/day free account (some sources say 3.5 min).
- [ ] Disk: Space disk is 50 GB non-persistent — Z-Image + LTX-2B + (13B?) sizes.
- [ ] Free-account grading: can we host 2 ZeroGPU Gradio Spaces (needed for API + app split later)?

## Model picks (license-verified 2026-10-17)
| Modality | Repo | License (read from actual license text) | Verdict |
|---|---|---|---|
| Image primary | `Tongyi-MAI/Z-Image-Turbo` | Apache 2.0 | ✅ unrestricted |
| Image fallback | `black-forest-labs/FLUX.1-schnell` | Apache 2.0 | ✅ unrestricted |
| Video (current default) | `Lightricks/LTX-Video` (2B v0.9) | RAIL-M — "Permitted Purpose: academic/research only, explicitly excludes commercialization" | ✅ personal use OK; ❌ never commercial |
| Video (license-clean) | LTX 0.9.8-distilled family (2B/13B) | LTXV Open Weights License 0.X — any purpose incl. commercial for entities < $10M/yr | ✅ recommended upgrade path |
| Voice | Sarvam `bulbul:v4-flash` (user's paid credits) | SaaS terms | ✅ per Sarvam account |

**Engine plan:** keep the measured 2B v0.9 as default (works, personal use); add a
`LTX_REPO` env-var override so `Lightricks/LTX-Video-0.9.8-13B-distilled` can be slotted
in after latency/disk verification (26 GB bf16 + T5 ≈ 30 GB — fits 48 GB VRAM, ~46 GB of the
50 GB disk budget together with Z-Image → verify disk math before switching).

## Acceptance targets (to verify in Phase 2)
- Image ≤ 5 s p95 warm; video (4s–5s, 768×512) ≤ 60 s p95; all on one URL.
- Daily capacity measured and documented (images/day, clips/day at $0).

## Status log
- 2026-10-16: Space created directly with `space_hardware="zero-a10g"` (free accounts cannot
  create CPU-basic Gradio Spaces — 402 — but ZeroGPU creation works). Spike app uploaded.
- 2026-10-16: ZeroGPU gotcha #1 — `import spaces` must be the FIRST import and `@spaces.GPU`
  must be applied in direct decorator form ("No @spaces.GPU function detected during startup"
  otherwise). Dynamic wrappers break detection.
- 2026-10-16: Benchmarks measured (see latency-baseline.md): Z-Image-Turbo warm ~5.1-6.4 s
  per 1024² image; LTX-Video 2B ~5.7 s per 4 s 768×512 clip. Cold pipeline build ~33-46 s
  inside first call of boot.
- 2026-10-16: ZeroGPU gotcha #2 — free-tier quota is **grant-based**: the in-flight call
  reserves its `duration=` budget ("172s requested vs. 41s left" error). Measured empirical
  daily pool ≈ 3.5 min (account showed reset "23:15:21" after cumulative use).
- 2026-10-16: Fix deployed — dynamic durations via `@spaces.GPU(duration=callable)`:
  cold grant 115 s, warm grant 30 s, so warm calls stop over-reserving the pool.
- 2026-10-16: MVP deployed (image ✅ verified live; video ✅ verified in spike; film chain +
  ffmpeg assembly + HF-dataset checkpointing deployed, pending chain E2E).
- 2026-10-17 (pre-reset): **Film-chain mechanic cross-verified through the quota gate** —
  the plain-generator film loop reached the nested `_gen_one_shot` GPU call and was rejected
  by the quota subsystem (not by a nested-call restriction). Friendly-error journey (J5)
  also confirmed. Full film smoke test (2 shots, 4 s each) queued for post-reset.
- 2026-10-18 01:25 IST: **Quota window opened ~01:01 as predicted; suite run completed.**
  J3 film smoke: server side fully worked (2 shots generated + persisted; assembled film
  existed) but the API POST died with a client 403 on `/gradio_api/file=000.mp4`. Root
  cause: gradio_client's legacy `is_file_obj` treats *any* dict containing a `"path"`
  key as a downloadable FileData — our timing JSON hit it. Fix: timing dict key
  renamed `path`→`file` (Space commit 8da952a). Free re-run via the resume path
  (checkpoints, zero GPU) delivered the full tuple: gallery + summary + 8.08 s film.
  J6 restart-resume verified in the same pass. Warm video 5.6 s, warm image 5.17 s.
  Grant model refined: ×1.5 is the request-check multiplier only; deduction fits a
  declared-sum or wall-time model (200 declared ran clean in one window). 
- 2026-10-18 01:47 IST: **Pool model pinned** — growth run (film smoke-test 2→4 shots,
  cold 90 requested(×1.5)=135) was rejected after the earlier suite consumed ~200 declared,
  ~6 h layer ⇒ remaining < 135 ⇒ **deduction ≈ declared**, not wall-time; pool refills to
  full ≈ +24 h from the cycle's first call ⇒ next full window ≈ 19:31 UTC / 01:01 IST Oct 19.
  Free-rejected pass burned nothing (resume fetch + checkpoints unaffected).
  Capacity plan ($0): ~4-6 warm 4 s shots/day (declared 25 ⇒ check 37.5 each) ⇒ film grows
  16-24 s/day ⇒ ~7-9 days to 3 min, OR one PRO day completes it in a single window.
  Instrumentation: friendly quota error now surfaces ZeroGPU's "requested/left/retry" numbers.
- 2026-10-17: Pending-implementation audit closed three gaps:
  (1) image tab now uses dynamic grants (60 cold / 25 warm) like video/film;
  (2) film resume made real — shots are re-fetched from the checkpoint dataset repo after
  a Space restart (prior logic only consulted /tmp cache); per-shot source now reported
  (checkpoint | local-cache | generated);
  (3) `_probe_duration` hardened (never crashes the film summary).
  HF_TOKEN rotated to a fresh fine-grained token (local .env + Space secret).
- 2026-10-17: **Archive reorganization completed** — BharatAQI-X (358 MB), deepseek-harness
  (1.75 GB), zoolingo-local (2.445 GB, 51,228 files, zero FAILED) + `.vercel` all moved to
  `E:\coding\Default Project Archive`; `frontend`/`app.log` → `_strays`; empty `temp_uploads`
  removed. Workspace root now contains only: bharataqi_2 (tracked), genstudio, docs, and
  workspace infra. Manifest updated to final state. Full workspace also snapshot-copied to
  `E:\coding\Default Project` (independent of OneDrive) per user request.
- 2026-10-17: **Grant-billing rule measured**: ZeroGPU error messages report
  `requested = declared duration × 1.5` (image 60 → "90s requested"; film shot 115 →
  "172s requested"). Against a ~213 s/day free pool this means the 115 s cold video grant
  would have burned 81% of the day alone → tightened video/shot grants to 90 cold / 25 warm
  (bills 135 / 37.5) so the film smoke test (cold+warm ≈ 172.5) fits with slack.
  Pool reset confirmed for ~19:31 UTC Oct 17 (01:01 IST Oct 18).

## Phase 1 checklist (MVP) — deployed
- [x] Single Space: https://huggingface.co/spaces/Theinvinvible24/genstudio (zero-a10g)
- [x] Image tab: Z-Image-Turbo, batch 1-4, seed, sizes, gallery + timing JSON — **live-verified**
- [x] Video tab: LTX-Video 2B T2V, ≤8 s per shot, 3 presets — **live-verified (5.6 s warm)**
- [x] Long-form film tab: shot chain → ffmpeg concat → delivery — **live-verified 2026-10-18
      (8.08 s smoke film; restart-resume from dataset repo proven at zero GPU cost)**
- [x] Voice tab: Sarvam `bulbul:v4-flash` REST (needs `SARVAM_API_KEY` Space secret — pending user)
- [x] Friendly quota/OOM errors; queue concurrency 1; dynamic required GPU grants
- [x] Live E2E: film smoke test (2 shots) — ✅ 2026-10-18
- [ ] Voice live test once SARVAM key provided
- [ ] Phase 2: Playwright E2E suite + p50/p95 latency report (genstudio/scripts/*)
