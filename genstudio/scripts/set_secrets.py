"""Set Space secrets (never prints values)."""
import os

from huggingface_hub import HfApi

REPO_ID = "Theinvinvible24/genstudio"

def local_token():
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env) as f:
        vals = {}
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        return vals.get("HF_TOKEN", "")

api = HfApi(token=local_token())
hf_token = local_token()
if hf_token:
    api.add_space_secret(REPO_ID, "HF_TOKEN", hf_token)
    print("secret set: HF_TOKEN")
sarvam = os.environ.get("SARVAM_API_KEY", "")
if sarvam:
    api.add_space_secret(REPO_ID, "SARVAM_API_KEY", sarvam)
    print("secret set: SARVAM_API_KEY")
else:
    print("SARVAM_API_KEY not provided yet — voice tab will show a friendly error until set")
