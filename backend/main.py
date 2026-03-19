"""Vercel deployment entrypoint — re-exports the FastAPI app from src layout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pilot_space.main import app

__all__ = ["app"]
