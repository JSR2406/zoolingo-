"""Fetch Space build + runtime logs."""
import json, os
from huggingface_hub import HfApi

REPO_ID = "Theinvinvible24/genstudio"

def token():
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env) as f:
        for line in f:
            if line.startswith("HF_TOKEN=") and line.strip() != "HF_TOKEN=":
                return line.split("=", 1)[1].strip()
    raise SystemExit("no token")

api = HfApi(token=token())
try:
    logs = api.get_space_logs(REPO_ID, stream=False)  # newer hub versions
    for kind, entries in (logs if isinstance(logs, dict) else {}).items():
        print("==", kind, "==")
        lines = entries if isinstance(entries, list) else [entries]
        for l in lines[-40:]:
            print(str(l)[-500:])
except Exception as e:
    print("get_space_logs unsupported/failed:", type(e).__name__, str(e)[:200])
    # fallback: raw endpoints
    import httpx
    base = f"https://huggingface.co/api/spaces/{REPO_ID}/logs"
    headers = {"Authorization": f"Bearer {token()}"}
    for kind in ("build", "run"):
        try:
            r = httpx.get(base + "/" + kind, headers=headers, timeout=30)
            print("==", kind, r.status_code, "==")
            txt = r.text
            print(txt[-3500:])
        except Exception as e2:
            print(kind, "fail:", e2)
