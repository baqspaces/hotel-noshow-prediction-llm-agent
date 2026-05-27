# Hotel No-Show Prediction with AI-Powered Insights Dashboard

This project takes data from the noshow.db to:
1. generate high level insights on no-show patterns in SG hotels,
2. generate ML model to predict probability of no show, 
3. creates an interactive web app dashboard showing an overview of key metrics and
4. contains an LLM AI assistant that helps summarise key insights and recommendations.

## What It Contains

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

## Setup and Run Locally

From `visa/app`:

```powershell
py -m pip install -r requirements.txt
py -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

If your machine uses `python` instead of `py`, replace `py -m` with `python -m`. Run the command from `visa/app`; running `uvicorn main:app` from inside `src` will break Python package imports.

## Launch App

The same app can also be launched with:

```bash
cd visa/app
./run.sh
```

`run.sh` assumes dependencies have already been installed from `requirements.txt`.

## Open:

```text
http://127.0.0.1:8000
```

## Demo login:

```text
username: manager
password: password123
```

## LLM assistant config:

The current demo implementation uses OpenAI only, with `OPENAI_MODEL` defaulting to `gpt-5.4-mini`. Users can switch between OpenAI model IDs by changing `OPENAI_MODEL`.

To add another LLM provider such as Claude or Gemini, extend the provider layer rather than changing the dashboard contract. At a high level, this would require:

- adding provider selection config such as `LLM_PROVIDER`
- adding provider-specific credentials and model settings
- implementing provider-specific client calls in `assistant.py`
- normalising all provider responses into the same assistant API shape
- adding any required SDK dependencies and updating Docker / `.env.example` docs

```text
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_ORG_ID=
OPENAI_PROJECT_ID=
OPENAI_MODEL=gpt-5.4-mini
OPENAI_TIMEOUT_SECONDS=20
```

If `OPENAI_API_KEY` is not configured, the assistant endpoint still works by falling back to the deterministic assessment-safe response logic.

To adjust the LLM assistant's answer style, edit `LLM_PROMPT.md`. The `src` package reloads this Markdown prompt for every assistant request.

## API docs:

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

If you see a database error, use an absolute SQLite filepath:

```powershell
$env:DATABASE_URL = "sqlite:///replace-with-filepath/noshow.db"
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

## Markdown Directory

- `OVERALL_ARCHITECTURE.md`: system architecture, data flow, model lifecycle, and deployment strategy
- `API_DOCUMENTATION.md`: endpoint guide with request and response examples
- `postman/visa_hotel_noshow_api.postman_collection.json`: Postman collection for manual API testing
- `AGENT_ARCHITECTURE.md`: agent roles, coordination logic, intervention policy, and invocation flow
- `AGENT_EVALUATION.md`: agent performance and reliability evaluation report
- `LLM_PROMPT.md`: editable assistant instructions, grounding rules, and response format
- `PRODUCTIONISATION_CHECKLIST.md`: checklist of work needed to be done to deploy this project (i.e. EDA -> Model -> Dashboard -> LLM Agent) to production.

## App Directory

- `app.py`: FastAPI entrypoint that imports `src.main:app`
- `main.py`: main FastAPI application; configures logging, CORS, static frontend serving, authentication routes, analytics endpoints, prediction endpoints, assistant endpoint, and the summary websocket
- `analytics.py`: analytics and risk logic; selects the active booking table, computes summary metrics, creates segment summaries, fetches high-risk bookings, estimates booking risk, and generates top insights
- `assistant.py`: AI assistant logic; loads `LLM_PROMPT.md`, retrieves relevant insights, builds LLM context, calls the current OpenAI provider implementation, falls back to deterministic answers, and creates intervention recommendations. This is the main extension point for future providers such as Claude or Gemini.
- `cache.py`: simple in-memory TTL cache used to avoid repeatedly recalculating common analytics results
- `config.py`: application settings layer; reads defaults and `.env` values for database, login, JWT, cache, and current OpenAI provider configuration
- `database.py`: database access layer; creates the SQLAlchemy engine, detects the booking table, manages sessions, validates columns, and provides query helpers
- `schemas.py`: Pydantic request and response models used to validate API inputs such as login, assistant queries, and prediction requests
- `security.py`: authentication helpers; creates and verifies bearer tokens and protects API routes with `require_user`
- `__init__.py`: marks `src` as a Python package so the app modules can import each other cleanly

## ML Model No-Show Probability Risk Scores

The "Operational Queue" section of the web app dashboard uses the Random Forest ML no-show probability generated by the ipynb. The notebook trains five ML models plus a dummy baseline, then saves the booking-level model scores into the `booking_ml_scores` table inside `noshow.db`. This table contains one score column for each trained model.

- `ml_risk_logistic_regression`
- `ml_risk_decision_tree`
- `ml_risk_random_forest`
- `ml_risk_extra_trees`
- `ml_risk_gradient_boosting`

The dashboard displays `risk_score`, which is set to `ml_risk_random_forest` (as it was shown to be the best performing model). Risk bands are assigned by quantiles of the score:

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
| Dashboard load | Opens dashboard data only after login | KPI cards, segment controls, and segment chart load after login | Pass |
| Risk queue | Click `Load` in the operational queue | High-risk bookings, ML risk scores, expected exposure, and interventions appear | Pass |
| Assistant | Ask an executive summary question | Dashboard renders provider badge, Markdown answer, and collapsible agent trace | Pass |
| LLM fallback | Run without `OPENAI_API_KEY` | Assistant still responds with `Provider: fallback` | Pass |
| API docs | Open `/docs` | FastAPI Swagger UI loads endpoint documentation and request schemas | Pass |
| OpenAPI schema | Open `/openapi.json` | Machine-readable API schema is available for review or Postman import | Pass |
