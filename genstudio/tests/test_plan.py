"""
GenStudio Phase 2 — E2E + latency test plan (to execute after quota reset).

Runs via the configured Playwright MCP tools (browser_*) or `npx playwright test`.
Journey coverage mapped to AGENTS.md "critical user journeys".

Journeys:
  J1 Image      → open Space → Image tab → prompt + batch=1 → assert gallery non-empty
                  and timing JSON shows wall_s < 15 (warm).
  J2 Video      → Video tab → seconds=4 → assert video present, wall_s < 40 warm,
                  clip duration ≥ 3.9 s.
  J3 Long-form  → Film tab → 2-shot smoke film → assert: shot stream progress,
                  assembled film present, duration ≈ 8 s, checkpoint note shows
                  hf-dataset destination (or local-only if HF_TOKEN secret absent).
  J4 Voice      → Voice tab → short text → assert audio present, wall_s < 30
                  (skipped until SARVAM_API_KEY secret exists → assert friendly error instead).
  J5 Quota path → force over-quota call → assert the friendly "quota exhausted" toast,
                  NOT a raw traceback (measured: pool ≈ 3.5 min/day, grant-based).
  J6 Resume     → PENDING (needs restart semantics): stop/rebuild Space mid-film,
                  rerun same film id → assert previously checkpointed shots are reused
                  (wall_s = 0 and no new GPU grant consumed).

Latency matrix (phase-2 measurement, one row per run, appended to latency-report.md):
  image:   {1024², 768×1280} × steps {8} × batch {1,4}     → p50/p95 warm
  video:   {768×512, 512×768} × {4 s} × steps {8, 16}     → p50/p95 warm + cold
  film:    2-shot 4 s                                     → per-shot wall + assembly wall
  budget:  daily grant check message from forced-error probe (quota introspection)
"""
