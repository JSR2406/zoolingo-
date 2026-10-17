# Default Project workspace

Two active projects live here; both are deployed and useable:

## 🎬 GenStudio (primary)
Free, single-platform prompt → **image / video / long-form film** studio on one
Hugging Face ZeroGPU Space — open weights only, strictly $0.

- **Live app:** https://huggingface.co/spaces/Theinvinvible24/genstudio
- Code: [`genstudio/`](genstudio/) — Space app (`space/app.py`), deploy/test scripts,
  measured docs (`docs/latency-report.md`), E2E journey plan
- Engines: `Tongyi-MAI/Z-Image-Turbo` (image, Apache 2.0) + `Lightricks/LTX-Video` 2B
  (video, RAIL-M personal use; swap-in 0.9.8-distilled for license-clean footage)
- Long-form films: sequential ≤8 s shots, checkpointed to a private dataset repo,
  **resume across restarts**, ffmpeg assembly on free CPU — film grows day by day on $0
- Voice: Sarvam `bulbul:v4-flash` (activity pending `SARVAM_API_KEY`)

> Quick start (local driver): `pip install gradio_client huggingface_hub httpx`, copy
> `genstudio/.env.example` → `genstudio/.env`, then
> `python genstudio/scripts/run_bench.py image | video | film4 | voice | suite`

## 🌆 bharataqi_2
City-air dashboard project (see its own tree), with an ONNX runtime + confidence gate
tooling in the history. All state verified via committed changes only.

---
Session notes for agents: see `AGENTS.md`; verified ZeroGPU quota model + deploy
runbooks are in `genstudio/docs/`. Mirror snapshot: `E:\coding\Default Project`.
