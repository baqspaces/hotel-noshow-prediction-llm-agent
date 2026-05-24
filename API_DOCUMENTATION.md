# API Documentation

Base URL:

```text
http://localhost:8000
```

Interactive OpenAPI documentation is available at:

```text
http://localhost:8000/docs
```

## Authentication

Most API endpoints require a bearer token.

### Login

```http
POST /auth/login
Content-Type: application/json
```

Request:

```json
{
  "username": "manager",
  "password": "password123"
}
```

Response:

```json
{
  "access_token": "<token>",
  "token_type": "bearer"
}
```

Use the token in subsequent requests:

```http
Authorization: Bearer <token>
```

## Monitoring

### Health Check

```http
GET /health
```

Returns app status, environment, raw booking table, and active analytics table.

### Monitoring

```http
GET /monitoring
Authorization: Bearer <token>
```

Returns cache and database pool status.

## Analytics

### Summary

```http
GET /api/summary
Authorization: Bearer <token>
```

Returns total bookings, no-show rate, no-shows, average price, revenue at risk, and available drill-down dimensions.

### Available Dimensions

```http
GET /api/dimensions
Authorization: Bearer <token>
```

Returns the segment dimensions available in the active table.

### Segment Drill-Down

```http
GET /api/segments?dimension=branch&min_bookings=20&limit=20
Authorization: Bearer <token>
```

Returns segment-level bookings, no-show rate, average price, and observed revenue at risk.

## Operational Queue

### Risk-Ranked Bookings

```http
GET /api/bookings/high-risk?risk_band=High&limit=25
Authorization: Bearer <token>
```

Accepted `risk_band` values:

```text
All, High, Medium, Low
```

Returns bookings from `booking_ml_scores`, including:

- `risk_score`
- `predicted_no_show_probability`
- `risk_band`
- `expected_revenue_at_risk`
- five `ml_risk_*` model score columns
- intervention recommendation

If `booking_ml_scores` does not exist, rerun the notebook ML scoring cell first.

### Segment-Based Prediction Estimate

```http
POST /api/predict
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "branch": "Changi",
  "platform": "Website",
  "country": "China",
  "room": "King",
  "customer_status": "First-time",
  "price": 1200
}
```

Returns a lightweight booking no-show risk estimate from historical rows in `booking_ml_scores` that match the supplied segment fields. 

Response includes:

- `model_source`
- `matched_bookings`
- `predicted_no_show_probability`
- `risk_score`
- `risk_band`
- `expected_revenue_at_risk`
- intervention recommendation

## AI Agent Assistant

### Ask AI Agent Assistant

```http
POST /api/assistant/query
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "question": "Give me an executive summary of the no-show risk."
}
```

Response includes:

- `answer`
- `retrieved_insights`
- `matched_segment_metrics`
- `agent_trace`
- `provider`

`matched_segment_metrics` contains exact segment metrics when the user question mentions a known branch, platform, country, room, customer status, or month segment. `provider` is `openai` when the current configured OpenAI LLM call succeeds and `deterministic_fallback` when the fallback path is used. The response contract is provider-labeled so future LLM providers can be added without changing the dashboard request shape.

## WebSocket

### Summary Stream

```text
ws://localhost:8000/ws/summary?token=<token>
```

Streams summary metrics every 15 seconds for the dashboard KPI cards.
