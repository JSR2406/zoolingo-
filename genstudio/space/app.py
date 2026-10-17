"""GenStudio MVP — free prompt→image / prompt→video / long-form film / voice studio.

Single ZeroGPU Space. Video strategy: every generated shot is capped at LTX-native
8 s (fits the 120 s ZeroGPU function cap); long-form films chain N shots and are
assembled with ffmpeg on CPU (no GPU quota). Each shot is checkpointed to a private
HF dataset repo (if HF_TOKEN secret present) so films survive Space restarts.

GPU quota honesty (free tier ~300 GPU-s/day, billed by actual runtime):
  one 3-min film ≈ 40 shots ≈ the full daily free budget.
"""
import base64
import gc
import os
import shlex
import subprocess
import tempfile
import time
import uuid

import gradio as gr
import httpx
import spaces  # noqa: F401  — must be the first import on ZeroGPU Spaces
import torch
from diffusers import LTXPipeline, ZImagePipeline
from diffusers.utils import export_to_video

Z_IMAGE_REPO = os.environ.get("Z_IMAGE_REPO", "Tongyi-MAI/Z-Image-Turbo")   # Apache 2.0, 8 steps, guidance 0.0
# License note: repo-main checkpoint = 2B v0.9 (RAIL-M: academic/research only — fine for
# personal use). For license-clean video (LTXV Open Weights 0.X), set LTX_REPO to a
# 0.9.8-distilled variant once its latency/disk math is verified.
LTX_2B_REPO = os.environ.get("LTX_REPO", "Lightricks/LTX-Video")            # 2B, fastest open video model
FPS = 24
MAX_SHOT_FRAMES = 193                       # ≈ 8 s (193 = ((8*24)//8)*8 + 1)
SHOTS_REPO = f"{os.environ.get('SPACE_OWNER', 'Theinvinvible24')}/genstudio-films"  # private dataset
TMP = tempfile.gettempdir()
GEN_DIR = os.path.join(TMP, "genstudio")
os.makedirs(os.path.join(GEN_DIR, "shots"), exist_ok=True)
os.makedirs(os.path.join(GEN_DIR, "films"), exist_ok=True)
os.makedirs(os.path.join(GEN_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(GEN_DIR, "audio"), exist_ok=True)


def _hf_token():
    return os.environ.get("HF_TOKEN") or ""


def _frames_for(seconds: float) -> int:
    return max(9, min(MAX_SHOT_FRAMES, ((int(float(seconds) * FPS)) // 8) * 8 + 1))


def _clock(fn):
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    out = fn()
    torch.cuda.synchronize()
    return out, round(time.perf_counter() - t0, 2)


# ------------------------------------------------------------------ pipelines
_PIPES = {}


def _get(kind: str):
    """Lazy build, cached across calls while the worker stays alive."""
    if kind in _PIPES:
        return _PIPES[kind]
    if kind == "zimage":
        _PIPES[kind] = ZImagePipeline.from_pretrained(Z_IMAGE_REPO, dtype=torch.bfloat16)
    elif kind == "ltx2b":
        _PIPES[kind] = LTXPipeline.from_pretrained(LTX_2B_REPO, dtype=torch.bfloat16)
    else:
        raise ValueError(kind)
    return _PIPES[kind]


def _quota_hint(e: Exception) -> str:
    m = str(e).lower()
    if "quota" in m or "exceeded" in m or "402" in m:
        # keep the ZeroGPU numbers (requested vs left, retry clock) visible — they are
        # the only way to observe the live pool; details: docs/latency-report.md
        import re
        raw = str(e)
        spec = re.search(r"\(([^()]*requested[^()]*left)\).*?Try again in (\d+:\d+:\d+)", raw, re.I)
        numbers = f" [{spec.group(1)} | Try again in {spec.group(2)}]" if spec else ""
        return ("Daily GPU quota exhausted — the free tier is ~3.5-5 GPU-minutes/day "
                "(measured: resets ~24 h after the cycle's first GPU call; "
                "in-flight calls reserve their requested duration, so grants are kept minimal). "
                "Upgrade to HF PRO for ~8x quota, or resume later — film shots are checkpointed "
                "and can be assembled later." + numbers)
    return ""


def _raise_friendly(fn_name: str, e: Exception) -> None:
    hint = _quota_hint(e)
    if hint:
        raise gr.Error(hint)
    raise gr.Error(f"Problem in {fn_name}: {e.__class__.__name__}: {e}. Check the Space log page for details.")


# ------------------------------------------------------------------ image tab
def _image_duration(prompt, height, width, steps, repeats, seed):
    """Dynamic grant: generous only while the Z-Image pipeline is cold."""
    return 60 if "zimage" not in _PIPES else 25


@spaces.GPU(duration=_image_duration)
def generate_image(prompt, height, width, steps, repeats, seed):
    if not str(prompt).strip():
        raise gr.Error("Please enter a prompt.")
    repeats = max(1, min(4, int(repeats)))
    try:
        pipe = _get("zimage")
        pipe.to("cuda")
        runs, images = [], []
        for i in range(repeats):
            def go():
                return pipe(
                    prompt=prompt, height=int(height), width=int(width),
                    num_inference_steps=int(steps), guidance_scale=0.0,
                    generator=torch.Generator("cuda").manual_seed(int(seed) + i),
                )
            img, wall = _clock(go)
            path = os.path.join(GEN_DIR, "images", f"{uuid.uuid4().hex[:8]}.png")
            img.images[0].save(path)
            images.append(path)
            runs.append({"run": i, "seed": int(seed) + i, "wall_s": wall,
                         "size": f"{int(width)}x{int(height)}", "steps": int(steps)})
        return images, {"model": "Z-Image-Turbo", "runs": runs, "unit": "seconds"}
    except Exception as e:
        _raise_friendly("generate_image", e)


# ------------------------------------------------------------------ video tab
def _video_duration(prompt, seconds, res_preset, steps, seed):
    """Dynamic ZeroGPU duration: generous only when the LTX pipeline is cold.

    Grant accounting (measured 2026-10-17): the pool bills declared x 1.5 —
    cold 90 ⇒ ~135 billed, warm 25 ⇒ ~37.5 billed, against a ~213 s daily pool."""
    return 90 if "ltx2b" not in _PIPES else 25


@spaces.GPU(duration=_video_duration)
def generate_video(prompt, seconds, res_preset, steps, seed):
    if not str(prompt).strip():
        raise gr.Error("Please enter a prompt.")
    fps = FPS
    width, height = {"landscape 768×512": (768, 512),
                     "portrait 512×768": (512, 768),
                     "squarish 512×512": (512, 512)}[res_preset]
    frames = _frames_for(seconds)
    try:
        pipe = _get("ltx2b")
        pipe.to("cuda")
        def go():
            return pipe(
                prompt=prompt,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
                width=width, height=height, num_frames=frames,
                decode_timestep=0.03, decode_noise_scale=0.025,
                num_inference_steps=int(steps),
                generator=torch.Generator("cuda").manual_seed(int(seed)),
            )
        vid, wall = _clock(go)
        path = os.path.join(GEN_DIR, "shots", f"single_{uuid.uuid4().hex[:8]}.mp4")
        export_to_video(vid.frames[0], path, fps=fps)
        info = {"model": LTX_2B_REPO, "wall_s": wall, "frames": frames,
                "size": f"{width}x{height}", "steps": int(steps),
                "clip_seconds": round(frames / fps, 2)}
        return path, info
    except Exception as e:
        _raise_friendly("generate_video", e)


# ------------------------------------------------------------- long-form film
def _film_fetch_existing(film_id, n_shots) -> dict:
    """Re-download previously checkpointed shots from the dataset repo (resume path).

    Returns {index: local_path} — partial on any failure; never raises."""
    token = _hf_token()
    got = {}
    if not token:
        return got
    try:
        from huggingface_hub import HfApi, hf_hub_download
        api = HfApi(token=token)
        for f in api.list_repo_files(SHOTS_REPO, repo_type="dataset"):
            pref = f"{film_id}/"
            if not (f.startswith(pref) and f.endswith(".mp4")):
                continue
            try:
                idx = int(f[len(pref):-4])
            except ValueError:
                continue
            if 0 <= idx < n_shots:
                try:
                    got[idx] = hf_hub_download(
                        SHOTS_REPO, f, repo_type="dataset", local_dir=os.path.join(GEN_DIR, "shots")
                    )
                except Exception:
                    continue
    except Exception:
        pass
    return got


def _shot_persist(film_id, index, path) -> str:
    """Copy artifact into a stable remote dataset repo (best-effort)."""
    token = _hf_token()
    if not token:
        return "local-only"
    from huggingface_hub import HfApi
    try:
        api = HfApi(token=token)
        api.create_repo(SHOTS_REPO, repo_type="dataset", exist_ok=True)
        api.upload_file(
            path_or_fileobj=path,
            path_in_repo=f"{film_id}/{index:03d}.mp4",
            repo_id=SHOTS_REPO,
            repo_type="dataset",
        )
        return f"hf:{SHOTS_REPO}/{film_id}/{index:03d}.mp4"
    except Exception as e:  # persistence is best-effort; never block generation
        return f"local-only (upload failed: {e.__class__.__name__})"


def _concat_film(film_id, shot_paths) -> str:
    """ffmpeg concat (CPU only — no GPU quota). Falls back to re-encode."""
    exe = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    list_path = os.path.join(GEN_DIR, "films", f"{film_id}_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in shot_paths:
            f.write(f"file {shlex.quote(p)}\n")
    out = os.path.join(GEN_DIR, "films", f"{film_id}.mp4")
    r = subprocess.run([exe, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(out):
        r = subprocess.run([exe, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise gr.Error(f"ffmpeg assembly failed: {r.stderr[-400:]}")
    return out


def film_loop(film_id, shot_lines, seconds, res_preset, steps, seed, persist, progress=gr.Progress()):
    """Sequential chain: one GPU call per shot, resume-safe, then free-CPU assembly."""
    if not film_id.strip():
        film_id = time.strftime("%Y%m%d_%H%M%S")
    film_id = film_id.strip()
    shots = [s.strip() for s in str(shot_lines).splitlines() if s.strip()]
    if not shots:
        raise gr.Error("Add at least one shot (one prompt per line).")
    fps = FPS
    width, height = {"landscape 768×512": (768, 512),
                     "portrait 512×768": (512, 768),
                     "squarish 512×512": (512, 512)}[res_preset]
    est_gpu = int(len(shots) * (seconds * 2 + 6))
    note = (f"📸 Film plan: {len(shots)} shots × ~{seconds} s = ~{len(shots) * seconds:.0f} s of video. "
            f"Projected GPU burn ≈ {est_gpu} s of the ~300 s/day free budget.")

    shot_paths, timings = [], []
    gallery_items = []
    have = _film_fetch_existing(film_id, len(shots)) if persist else {}
    for i, shot in enumerate(shots):
        progress((i / len(shots)), desc=f"Shot {i + 1}/{len(shots)}")
        # resume: dataset-repo checkpoint first, then local /tmp cache, then generate
        cached = os.path.join(GEN_DIR, "shots", film_id, f"{i:03d}.mp4")
        if i in have:
            path, wall = have[i], 0.0
            src = "checkpoint"
        elif os.path.exists(cached):
            path, wall = cached, 0.0
            src = "local-cache"
        else:
            try:
                path, wall = _gen_one_shot(shot, seconds, width, height, steps, int(seed) + i, film_id, i)
                src = "generated"
            except Exception as e:
                _raise_friendly(f"shot {i+1}", e)
        shot_paths.append(path)
        # NOTE: keys must NOT include "path" — gradio_client treats any dict with a
        # "path" key as a downloadable FileData (legacy matcher) and the UI API call
        # then dies at /gradio_api/file=000.mp4. Use "file" instead.
        walltime = {"shot": i + 1, "file": os.path.basename(path), "wall_s": wall, "source": src}
        timings.append(walltime)
        gallery_items.append(path)
        dest = _shot_persist(film_id, i, path) if persist else "skipped"
        progress(((i + 1) / len(shots)), desc=f"Shot {i+1}/{len(shots)} done ({dest})")
        yield gallery_items, {"plan": note, "shots_done": f"{len(timings)}/{len(shots)}", "note": f"shot {i+1} [{src}]: {dest}"}, None

    progress(1.0, desc="ffmpeg assembly (free CPU)")
    final = _concat_film(film_id, shot_paths)
    dur = _probe_duration(final)
    summary = {"film_id": film_id, "shots": len(shots), "seconds": dur,
               "wall_times": timings, "persist": dest if persist else "all shots local-only"}
    yield gallery_items, summary, final


def _shot_duration(shot, seconds, width, height, steps, seed, film_id, index):
    """Dynamic ZeroGPU duration for film shots (warm cache ⇒ small grant).

    Pool bills declared x 1.5 — see _video_duration note."""
    return 90 if "ltx2b" not in _PIPES else 25


@spaces.GPU(duration=_shot_duration)
def _gen_one_shot(shot, seconds, width, height, steps, seed, film_id, index):
    fps = FPS
    frames = _frames_for(seconds)
    try:
        pipe = _get("ltx2b")
        pipe.to("cuda")
        def go():
            return pipe(
                prompt=shot,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
                width=width, height=height, num_frames=frames,
                decode_timestep=0.03, decode_noise_scale=0.025,
                num_inference_steps=int(steps),
                generator=torch.Generator("cuda").manual_seed(int(seed)),
            )
        vid, wall = _clock(go)
        path = os.path.join(GEN_DIR, "shots", film_id)
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f"{index:03d}.mp4")
        export_to_video(vid.frames[0], path, fps=fps)
        del vid
        gc.collect()
        return path, wall
    except Exception as e:
        _raise_friendly(f"_gen_one_shot[{index}]", e)


def _probe_duration(path) -> float:
    try:
        import imageio
        v = imageio.get_reader(path)
        n = v.count_frames()
        v.close()
        return round(n / FPS, 2)
    except Exception:
        return -1.0  # never let the summary crash the finished film


# ------------------------------------------------------------------ voice tab
SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
VOICE_LIMIT = 1500


def generate_voice(text, language_code, speaker, model_choice):
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        raise gr.Error("SARVAM_API_KEY Space secret is not set. Add it in Space settings → Variables and secrets.")
    text = str(text).strip()
    if not text:
        raise gr.Error("Enter text to speak.")
    if len(text) > VOICE_LIMIT:
        raise gr.Error(f"Sarvam accepts up to {VOICE_LIMIT} chars in one call; trim or split the text.")
    t0 = time.perf_counter()
    try:
        r = httpx.post(SARVAM_URL,
                       headers={"api-subscription-key": key},
                       json={"text": text, "language_code": language_code,
                             "model": model_choice, **({"speaker": speaker} if speaker else {})},
                       timeout=120)
        r.raise_for_status()
        audio_b64 = r.json()["audios"][0]
    except httpx.HTTPStatusError as e:
        raise gr.Error(f"Sarvam API error {e.response.status_code}: {e.response.text[:200]}")
    path = os.path.join(GEN_DIR, "audio", f"{uuid.uuid4().hex[:8]}.wav")
    with open(path, "wb") as f:
        f.write(base64.b64decode(audio_b64))
    return path, {"model": model_choice, "language": language_code, "wall_s": round(time.perf_counter() - t0, 2)}


# ------------------------------------------------------------------------ UI
RES_PRESETS = ["landscape 768×512", "portrait 512×768", "squarish 512×512"]
LANGS = ["en-IN", "hi-IN", "ta-IN", "bn-IN", "te-IN", "mr-IN", "gu-IN", "kn-IN", "ml-IN", "pa-IN", "od-IN"]

with gr.Blocks(title="GenStudio", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 GenStudio — free prompt→image / video studio\n"
                "Open weights only, self-hosted on one ZeroGPU Space. "
                "Free daily GPU budget ≈ 300 s — visible burn shown after every run.")
    with gr.Tabs():
        with gr.Tab("🖼 Image"):
            p_img = gr.Textbox(label="Prompt", placeholder="A photorealistic morning market street in Kolkata, natural light…", lines=3)
            with gr.Row():
                i_steps, i_reps, i_seed = gr.Number(8, label="steps (Turbo: 8)"), gr.Number(1, label="batch 1–4"), gr.Number(0, label="seed")
            with gr.Row():
                i_w, i_h = gr.Number(1024, label="width"), gr.Number(1024, label="height")
            img_btn = gr.Button("Generate image(s)", variant="primary")
            img_gal, img_json = gr.Gallery(label="outputs", columns=4), gr.JSON(label="timing / GPU burn")
            img_btn.click(generate_image, inputs=[p_img, i_h, i_w, i_steps, i_reps, i_seed],
                          outputs=[img_gal, img_json], api_name="generate_image")
        with gr.Tab("🎬 Video (single shot)"):
            p_vid = gr.Textbox(label="Prompt", placeholder="A golden retriever running through tall grass at sunset, cinematic, smooth motion…", lines=3)
            with gr.Row():
                vid_sec = gr.Number(4, label="seconds per shot (≤8)")
                vid_res = gr.Dropdown(RES_PRESETS, value="landscape 768×512", label="resolution")
                vid_steps, vid_seed = gr.Number(8, label="steps"), gr.Number(7, label="seed")
            vid_btn = gr.Button("Generate clip", variant="primary")
            vid_out, vid_json = gr.Video(label="output"), gr.JSON(label="timing / GPU burn")
            vid_btn.click(generate_video, inputs=[p_vid, vid_sec, vid_res, vid_steps, vid_seed],
                          outputs=[vid_out, vid_json], api_name="generate_video")
        with gr.Tab("🎞 Long-form film (1–3+ min)"):
            gr.Markdown("### Chain many ≤8 s shots into one stitched film\n"
                        "One prompt per line = one shot. Assembly uses ffmpeg on CPU (free). "
                        "Shots are checkpointed to your private HF dataset repo when HF_TOKEN is configured. "
                        "Every shot is a separate GPU call — quota is spent as the film grows.")
            f_id = gr.Textbox(label="Film id (optional — used for resume)")
            f_shots = gr.Textbox(label="Shot list (one prompt per line)", lines=5,
                                 placeholder="Aerial dawn over Himalayan peaks, misty valleys…\nA shepherd walks a winding ridge trail at golden hour…")
            with gr.Row():
                f_sec = gr.Number(5, label="seconds per shot (≤8)")
                f_res = gr.Dropdown(RES_PRESETS, value="landscape 768×512", label="resolution")
                f_steps, f_seed = gr.Number(8, label="steps"), gr.Number(7, label="seed")
            f_persist = gr.Checkbox(True, label="Checkpoint shots to your HF dataset (resume across restarts)")
            f_btn = gr.Button("Generate film", variant="primary")
            with gr.Row():
                f_gal = gr.Gallery(label="shot previews", columns=6)
                f_final = gr.Video(label="assembled film", scale=2)
            f_state = gr.JSON(label="progress / timing")
            f_btn.click(film_loop, inputs=[f_id, f_shots, f_sec, f_res, f_steps, f_seed, f_persist],
                        outputs=[f_gal, f_state, f_final], api_name="generate_film")
        with gr.Tab("🔊 Voice (Sarvam)"):
            t_voice = gr.Textbox(label="Text (≤1500 chars)", lines=4)
            with gr.Row():
                v_lang = gr.Dropdown(LANGS, value="en-IN", label="language")
                v_speaker = gr.Textbox(value="", label="speaker (optional, e.g. simran_en_customer)")
                v_model = gr.Dropdown(["bulbul:v4-flash", "bulbul:v3"], value="bulbul:v4-flash", label="model")
            v_btn = gr.Button("Speak", variant="primary")
            v_out, v_json = gr.Audio(label="audio"), gr.JSON(label="timing")
            v_btn.click(generate_voice, inputs=[t_voice, v_lang, v_speaker, v_model],
                        outputs=[v_out, v_json], api_name="generate_voice")

demo.queue(default_concurrency_limit=1).launch(ssr_mode=False)
