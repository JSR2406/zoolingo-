"""Create the genstudio Space (Gradio SDK) + configure ZeroGPU hardware.

Reads HF_TOKEN from genstudio/.env. Never prints the token.
"""
import json, os, sys
from huggingface_hub import HfApi

REPO_ID = "Theinvinvible24/genstudio"

def token():
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env) as f:
        for line in f:
            if line.startswith("HF_TOKEN=") and line.strip() != "HF_TOKEN=":
                return line.split("=", 1)[1].strip()
    raise SystemExit("HF_TOKEN missing in genstudio/.env")

api = HfApi(token=token())

repo_url = api.create_repo(
    REPO_ID,
    repo_type="space",
    space_sdk="gradio",
    space_hardware="zero-a10g",  # create directly on ZeroGPU (free accounts: up to 2 Gradio ZeroGPU Spaces)
    private=False,
    exist_ok=True,
)
print("created/found Space:", repo_url)

try:
    api.request_space_hardware(REPO_ID, hardware="zero-a10g")
    print("hardware requested: zero-a10g (ZeroGPU)")
except Exception as e:
    print("hardware request failed:", type(e).__name__, str(e)[:300])

info = api.get_space_runtime(REPO_ID)
print("runtime:", json.dumps({"stage": info.stage, "hardware": str(info.hardware), "sdk": info.sdk}))
