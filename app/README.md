# No-Show Intelligence Platform

This app turns the booking no-show notebook into a small full-stack demo.

## What It Demonstrates

- `src/` FastAPI package with OpenAPI docs at `/docs`
- JWT-style bearer authentication
- Health and monitoring endpoints
- SQLAlchemy data access over `noshow.db`
- Cached summary, segment, and risk queries
- WebSocket summary stream at `/ws/summary`
- Booking-level risk scoring and intervention recommendations
- AI insight assistant with retrieved evidence and intervention guidance
- Interactive dashboard for KPIs, drill-downs, and a risk-filterable operational queue
- Docker and environment-specific configuration

## Run Locally

From `visa/app`:

```powershell
py -m pip install -r requirements.txt
py -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

If your machine uses `python` instead of `py`, replace `py -m` with `python -m`. Run the command from `visa/app`; running `uvicorn main:app` from inside `src` will break Python package imports.

The same app can also be launched with:

```bash
cd visa/app
./run.sh
```

`run.sh` assumes dependencies have already been installed from `requirements.txt`.

Open:

```text
http://127.0.0.1:8000
```

Demo login:

```text
username: manager
password: password123
```

Optional LLM assistant config:

```text
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_ORG_ID=
OPENAI_PROJECT_ID=
OPENAI_MODEL=gpt-5
OPENAI_TIMEOUT_SECONDS=20
```

If `OPENAI_API_KEY` is not configured, the assistant endpoint still works by falling back to the deterministic assessment-safe response logic.

To adjust the LLM's answer style, edit `LLM_PROMPT.md`. The `src` package reloads this Markdown prompt for every assistant request, so formatting and tone changes do not require Python code changes.

API docs:

```text
http://127.0.0.1:8000/docs
```

## Docker

From `visa/app`:

```powershell
docker compose up --build
```

## Common Startup Fixes

If you see `ModuleNotFoundError`, install the requirements from `visa/app`:

```powershell
py -m pip install -r requirements.txt
```

If you see a database error, use an absolute SQLite URL:

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/nujen/OneDrive/Desktop/yini/visa/noshow.db"
py -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks `npm`, use `npm.cmd`. This app does not require npm to run.

## Useful Endpoints

- `GET /health`
- `GET /monitoring`
- `POST /auth/login`
- `GET /api/summary`
- `GET /api/segments?dimension=branch`
- `GET /api/bookings/high-risk`
- `POST /api/assistant/query`
- `POST /api/predict`
- `WS /ws/summary?token=<access_token>`

## Assessment Documentation

- `ARCHITECTURE.md`: system architecture, data flow, model lifecycle, and deployment strategy
- `API_DOCUMENTATION.md`: endpoint guide with request and response examples
- `AGENT_PROTOCOL.md`: agent roles, coordination logic, intervention policy, and evaluation scenarios
- `AGENT_EVALUATION.md`: agent performance and reliability evaluation report
- `AGENT_ARCHITECTURE_REPORT.pdf`: PDF explanation of the agent architecture and invocation flow
- `app.py`: assessment-friendly FastAPI entrypoint that imports `src.main:app`

## Risk Score Logic

The operational queue uses the Random Forest ML no-show probability saved by the notebook in `booking_ml_scores`. The notebook also saves one probability column for each real model:

- `ml_risk_logistic_regression`
- `ml_risk_decision_tree`
- `ml_risk_random_forest`
- `ml_risk_extra_trees`
- `ml_risk_gradient_boosting`

The dashboard displays `risk_score`, which is set to `ml_risk_random_forest`. Risk bands are assigned by quantiles of this score:

- Low: bottom third of scores
- Medium: middle third of scores
- High: top third of scores

Rerun the notebook ML scoring cell to refresh the `booking_ml_scores` table before launching the app.


## QA Report

| Area | Check | Expected Result | Status |
|---|---|---|---|
| App startup | `py -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000` | App starts without import or database connection errors | Pass |
| Health check | `GET /health` | Returns `status: ok`, environment, raw booking table, and active analytics table | Pass |
| Authentication | Login with `manager` / `password123` | Returns a bearer token for protected endpoints | Pass |
| Dashboard load | Open `/` after login | KPI cards, segment controls, and segment chart load | Pass |
| Risk queue | Click `Load` in the operational queue | High-risk bookings, ML risk scores, expected exposure, and interventions appear | Pass |
| Assistant | Ask an executive summary question | Dashboard renders provider badge, Markdown answer, and collapsible agent trace | Pass |
| LLM fallback | Run without `OPENAI_API_KEY` | Assistant still responds with `Provider: fallback` | Pass |
| API docs | Open `/docs` | FastAPI Swagger UI loads endpoint documentation and request schemas | Pass |
| OpenAPI schema | Open `/openapi.json` | Machine-readable API schema is available for review or Postman import | Pass |
| Docker | `docker compose up --build` | Containerized app starts with bundled `noshow.db` and `LLM_PROMPT.md` | Pending reviewer environment |

## Submission Safety

Do not submit `visa/app/.env`. It is ignored by `.gitignore`; submit `.env.example` instead and provide real secrets only through local environment variables or the deployment environment.
