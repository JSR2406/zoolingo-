import os
import sys
from pathlib import Path

# Make the backend package importable from the serverless entrypoint
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

# Keep config anchored regardless of CWD
os.environ.setdefault("BE_BACKEND_DIR", str(_BACKEND))

# Vercel sets VERCEL=1; config.py detects this and enables serverless mode
# (read-only FS, /tmp scratch dir, :memory: SQLite, base64 audio responses)

from app import app  # noqa: E402  FastAPI app for Vercel's Python runtime
