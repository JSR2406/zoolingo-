"""Upload genstudio/space/* to the HF Space (token from .env; never printed)."""
import os
from huggingface_hub import HfApi

REPO_ID = "Theinvinvible24/genstudio"
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "space")

def token():
    env = os.path.join(os.path.dirname(SRC), ".env")
    with open(env) as f:
        for line in f:
            if line.startswith("HF_TOKEN=") and line.strip() != "HF_TOKEN=":
                return line.split("=", 1)[1].strip()
    raise SystemExit("HF_TOKEN missing")

api = HfApi(token=token())
res = api.upload_folder(repo_id=REPO_ID, repo_type="space", folder_path=SRC, commit_message="Phase 0 spike: image+video benchmark harness")
print("uploaded:", getattr(res, "commit_url", res))
