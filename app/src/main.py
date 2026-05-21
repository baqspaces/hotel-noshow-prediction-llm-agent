import asyncio
import logging
from logging.handlers import RotatingFileHandler
from time import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .analytics import active_analytics_table, high_risk_bookings, predict, segment_summary, summary_metrics, available_dimensions
from .assistant import answer_question, intervention_recommendation
from .cache import cache
from .config import get_settings
from .database import BOOKING_TABLE, engine
from .schemas import AssistantQuery, LoginRequest, PredictionRequest, TokenResponse
from .security import create_access_token, require_user, verify_access_token


settings = get_settings()
log_dir = Path(__file__).resolve().parents[1] / "logs"
log_dir.mkdir(exist_ok=True)
logger = logging.getLogger("noshow_app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Booking no-show analytics, AI insight assistant, and operational intervention API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

_rate_limit: dict[str, list[float]] = {}


@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    started = time()
    if request.url.path.startswith("/api") or request.url.path.startswith("/auth"):
        key = request.client.host if request.client else "unknown"
        now = time()
        hits = [stamp for stamp in _rate_limit.get(key, []) if now - stamp < 60]
        if len(hits) >= 120:
            logger.warning("rate_limited path=%s client=%s", request.url.path, key)
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        hits.append(now)
        _rate_limit[key] = hits
    response = await call_next(request)
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        (time() - started) * 1000,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unexpected server error. Check visa/app/logs/app.log for the traceback."},
    )


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(frontend_dir / "index.html")


@app.get("/health", tags=["Monitoring"])
def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "booking_table": BOOKING_TABLE,
        "active_analytics_table": active_analytics_table(),
    }


@app.get("/monitoring", tags=["Monitoring"])
def monitoring(user: Annotated[dict, Depends(require_user)]):
    pool_status = engine.pool.status() if hasattr(engine.pool, "status") else "unavailable"
    return {"cache": cache.stats(), "pool": pool_status, "user": user["sub"]}


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(payload: LoginRequest):
    if payload.username != settings.demo_username or payload.password != settings.demo_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(payload.username))


@app.get("/api/summary", tags=["Analytics"])
def get_summary(user: Annotated[dict, Depends(require_user)]):
    return summary_metrics()


@app.websocket("/ws/summary")
async def summary_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        verify_access_token(token)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            await websocket.send_json(summary_metrics())
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return


@app.get("/api/dimensions", tags=["Analytics"])
def get_dimensions(user: Annotated[dict, Depends(require_user)]):
    return {"dimensions": available_dimensions()}


@app.get("/api/segments", tags=["Analytics"])
def get_segments(
    user: Annotated[dict, Depends(require_user)],
    dimension: str = Query(default="branch"),
    min_bookings: int = Query(default=20, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return {"dimension": dimension, "rows": segment_summary(dimension, min_bookings=min_bookings, limit=limit)}


@app.get("/api/bookings/high-risk", tags=["Risk"])
def get_high_risk_bookings(
    user: Annotated[dict, Depends(require_user)],
    limit: int = Query(default=25, ge=1, le=100),
    risk_band: str = Query(default="All", pattern="^(All|High|Medium|Low)$"),
):
    rows = high_risk_bookings(limit=limit, risk_band=risk_band)
    return {
        "risk_band": risk_band,
        "rows": [
            {**row, "intervention": intervention_recommendation(row)}
            for row in rows
        ]
    }


@app.post("/api/predict", tags=["Risk"])
def predict_booking(payload: PredictionRequest, user: Annotated[dict, Depends(require_user)]):
    row = predict(payload.model_dump())
    return {**row, "intervention": intervention_recommendation(row)}


@app.post("/api/assistant/query", tags=["AI Assistant"])
def query_assistant(payload: AssistantQuery, user: Annotated[dict, Depends(require_user)]):
    return answer_question(payload.question)
