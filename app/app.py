"""FastAPI wrapper entrypoint.

Run with:
    uvicorn app:app --host 0.0.0.0 --port 8000

The full application implementation lives in src.main.
"""

from src.main import app
