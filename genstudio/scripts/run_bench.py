"""Drive the GenStudio MVP Space via gradio_client (token from .env, never printed).

usage:
  python run_bench.py image
  python run_bench.py video
  python run_bench.py film   # small 2-shot film (smoke test of chaining)
  python run_bench.py voice  # Sarvam TTS (server needs SARVAM_API_KEY secret)
  python run_bench.py suite  # ordered post-reset batch; ends with an over-quota
                             # probe so the JSON log contains exact pool accounting
"""
import json, os, sys, time

from gradio_client import Client

REPO = "Theinvinvible24/genstudio"

def token():
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env) as f:
        for line in f:
            if line.startswith("HF_TOKEN=") and line.strip() != "HF_TOKEN=":
                return line.split("=", 1)[1].strip()
    raise SystemExit("no token")

def run_suite(client):
    """Ordered post-reset batch. Film smoke uses cold+warm grants (~172.5 billed
    of ~213 pool); the final cold-image step intentionally trips the quota gate so
    its error message reports the exact remaining pool — a self-auditing run."""
    steps = [
        ("film_smoke_2x4s", "/generate_film", dict(
            film_id="smoke-test",
            shot_lines="A lone lighthouse on a cliff at dawn, waves crashing\n"
                       "A pod of dolphins leaping offshore, golden light",
            seconds=4, res_preset="landscape 768×512", steps=8, seed=7, persist=True)),
        ("video_warm_4s", "/generate_video", dict(
            prompt="A red sports car driving along a coastal highway at sunset, cinematic, smooth motion",
            seconds=4, res_preset="landscape 768×512", steps=8, seed=7)),
        ("image_final_probe", "/generate_image", dict(
            prompt="An aerial shot of a winding mountain road at sunrise, cinematic",
            height=1024, width=1024, steps=8, repeats=1, seed=0)),
    ]
    results = []
    for name, api, kwargs in steps:
        t0 = time.perf_counter()
        try:
            res = client.predict(**kwargs, api_name=api)
            wall = time.perf_counter() - t0
            out = res[0] if isinstance(res, (list, tuple)) else res
            info = res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else None
            print(f"[{name}] OK in {wall:0.1f}s (client wall, incl. upload/queue)", flush=True)
            print(f"  output: {out}", flush=True)
            if info is not None:
                print(f"  info: {json.dumps(info, indent=1, default=str)}", flush=True)
            results.append({"step": name, "ok": True, "wall_client_s": round(wall, 2)})
        except Exception as e:  # noqa: BLE001 — every failure is data in a quota audit
            wall = time.perf_counter() - t0
            msg = str(getattr(e, "message", e))
            if "quota" in msg.lower() or "ZeroGPU" in msg:
                print(f"[{name}] QUOTA GATE after {wall:0.1f}s: {msg[:300]}", flush=True)
                results.append({"step": name, "ok": False, "quota_msg": msg})
            else:
                print(f"[{name}] ERROR after {wall:0.1f}s: {msg[:300]}", flush=True)
                results.append({"step": name, "ok": False, "error": msg})
    arts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
    os.makedirs(arts, exist_ok=True)
    path = os.path.join(arts, f"suite_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    print(f"saved: {path}", flush=True)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "image"
    client = Client(REPO, token=token())
    if which == "suite":
        run_suite(client)
        return
    if which == "image":
        res = client.predict(
            prompt="An aerial shot of a winding mountain road at sunrise, cinematic",
            height=1024, width=1024, steps=8, repeats=1, seed=0,
            api_name="/generate_image",
        )
    elif which == "video":
        res = client.predict(
            prompt="A red sports car driving along a coastal highway at sunset, cinematic, smooth motion",
            seconds=4, res_preset="landscape 768×512", steps=8, seed=7,
            api_name="/generate_video",
        )
    elif which == "film":
        res = client.predict(
            film_id="smoke-test",
            shot_lines="A lone lighthouse on a cliff at dawn, waves crashing\nA pod of dolphins leaping offshore, golden light",
            seconds=4, res_preset="landscape 768×512", steps=8, seed=7, persist=True,
            api_name="/generate_film",
        )
    elif which == "voice":
        res = client.predict(
            text="Hello, this is GenStudio. A free and open studio for images, videos and voice.",
            language_code="en-IN", speaker="", model_choice="bulbul:v4-flash",
            api_name="/generate_voice",
        )
    else:
        raise SystemExit("usage: python run_bench.py [image|video|film|voice]")

    out = res[0] if isinstance(res, (list, tuple)) else res
    info = res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else None
    print("output:", out)
    if info is not None:
        print("info:", json.dumps(info, indent=1, default=str))

if __name__ == "__main__":
    main()
