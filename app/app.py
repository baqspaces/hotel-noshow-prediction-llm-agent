"""FastAPI wrapper entrypoint.

Run with:
    uvicorn app:app --host 127.0.0.1 --port 8000

The full application implementation lives in src.main.
"""

from src.main import app
