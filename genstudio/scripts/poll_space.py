"""Bounded poll of Space runtime stage (<= ~5 min)."""
import time as _t

from huggingface_hub import HfApi

def token():
    import os
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env) as f:
        for line in f:
            if line.startswith("HF_TOKEN=") and line.strip() != "HF_TOKEN=":
                return line.split("=", 1)[1].strip()
    raise SystemExit("no token")

api = HfApi(token=token())
deadline = _t.time() + 280
stage = None
_last = None
while _t.time() < deadline:
    r = api.get_space_runtime("Theinvinvible24/genstudio")
    cur = (r.stage, str(r.hardware))
    if cur != (stage, _last):
        # print only on change
        stage = r.stage
        _last = str(r.hardware)
        print("stage:", stage, "| hw:", _last, flush=True)
    if stage in ("RUNNING", "BUILD_ERROR", "RUNTIME_ERROR", "PAUSED", "STOPPED"):
        break
    _t.sleep(15)

print("final:", stage)
