"""Validate HF token + inspect Lightricks/Z-Image repo availability (no quota burn)."""
import json, os, sys
from huggingface_hub import HfApi

def token():
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")) as f:
        for line in f:
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("HF_TOKEN missing in genstudio/.env")

api = HfApi(token=token())
me = api.whoami()
info = {
    "username": me["name"],
    "type": me.get("type"),
    "auth": me.get("auth", {}).get("accessToken", {}).get("role"),
}
print(json.dumps(info))

# --- Model repo discovery (Phase 0 picks) ---
want = {"Z-Image": [], "LTX-Video": [], "FLUX-schnell": []}
for m in api.list_models(search="Z-Image", limit=10):
    want["Z-Image"].append(m.id)
for m in api.list_models(author="Lightricks", limit=30, sort="downloads"):
    want["LTX-Video"].append(m.id)
for m in api.list_models(author="black-forest-labs", search="schnell", limit=5):
    want["FLUX-schnell"].append(m.id)
print(json.dumps(want, indent=1))
