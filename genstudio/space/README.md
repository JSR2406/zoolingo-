---
title: GenStudio
emoji: 🎬
colorFrom: indigo
colorTo: pink
sdk: gradio
app_file: app.py
pinned: false
license: mit
short_description: Free image/video benchmarks on one ZeroGPU Space
---

# GenStudio (Phase 0 spike)

Free, self-hosted open-weights text→image and text→video on one ZeroGPU Space.

- Image: `Tongyi-MAI/Z-Image-Turbo` (Apache 2.0)
- Video: `Lightricks/LTX-Video` 2B (fastest model that fits the 120s ZeroGPU cap)

This Space is a **benchmark harness**, not the final app: every run returns a timing
JSON (p50/p95 matrix is produced by the local harness calling these APIs).
