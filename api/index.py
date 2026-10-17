import os
import sys
from pathlib import Path

# Make the backend package importable from the serverless entrypoint
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

# Keep config anchored regardless of CWD
os.environ.setdefault("BE_BACKEND_DIR", str(_BACKEND))

from app import app  # noqa: E402  FastAPI app for Vercel's Python runtime