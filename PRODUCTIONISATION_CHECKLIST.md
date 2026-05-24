# Productionisation Checklist

This checklist summarises the key next steps to move the hotel no-show prediction dashboard, API, ML workflow, and LLM assistant from an assessment prototype toward a production-ready system.

## Security

- [ ] Rotate development API keys and store all secrets in environment variables or a managed secret store.
- [ ] Replace demo credentials such as `manager` / `password123` and require a strong production `JWT_SECRET`.
- [ ] Restrict CORS to approved frontend domains and serve the app through HTTPS/TLS.
- [ ] Remove prefilled production login values from the frontend.
- [ ] Add audit logging for login, dashboard access, assistant queries, prediction requests, and high-risk queue usage.

## Data And Model

- [ ] Move from local `noshow.db` to a managed database or controlled production data store.
- [ ] Replace notebook-only scoring with a repeatable data ingestion, validation, and scheduled scoring pipeline.
- [ ] Version datasets, feature definitions, model artifacts, model metrics, and scoring outputs.
- [ ] Add drift monitoring for no-show rate, booking mix, segment distributions, and prediction scores.
- [ ] Define retraining triggers, approval gates, and ownership for model releases.

## LLM Assistant

- [ ] Keep the provider boundary explicit. The current demo implements OpenAI only; Claude, Gemini, or local models would require provider-specific config, client calls, dependencies, and response normalisation.
- [ ] Track provider name, model name, prompt version, latency, fallback rate, and error rate.
- [ ] Add regression tests for common assistant questions and required answer structure.
- [ ] Add guardrails for unsupported claims, hallucinated metrics, and missing operational caveats.
- [ ] Define safe fallback behavior when the LLM provider, prompt file, or scored booking table is unavailable.

## Backend And API

- [ ] Add automated tests for auth, summary metrics, segment drill-downs, risk queue, prediction, assistant responses, and websocket streaming.
- [ ] Validate required `booking_ml_scores` columns before serving risk, prediction, or assistant endpoints.
- [ ] Return clear data/schema errors instead of generic 500 responses.
- [ ] Add structured logging, request IDs, health checks, and readiness checks.
- [ ] Replace in-memory rate limiting with Redis or another shared production-safe limiter.

## Frontend

- [ ] Escape all API and database-derived values before inserting them into `innerHTML`.
- [ ] Handle expired tokens by clearing local storage and prompting the user to log in again.
- [ ] Add clear loading, empty, and error states for each dashboard section.
- [ ] Remove hardcoded demo values from production login fields.
- [ ] Test target browser, mobile, and desktop layouts for dashboard workflows.

## Deployment And Operations

- [ ] Build immutable Docker images for each release.
- [ ] Use separate configuration for development, staging, and production.
- [ ] Add CI/CD checks for tests, Docker build, vulnerability scanning, and deployment.
- [ ] Define rollback procedures for app, prompt, data, and model releases.
- [ ] Centralise logs, metrics, alerts, and operational runbooks.

## Governance And Review

- [ ] Document data sources, assumptions, known limitations, and model caveats.
- [ ] Define human review rules for interventions that affect customers or revenue.
- [ ] Track changes to prompts, model versions, thresholds, and business rules.
- [ ] Add privacy and compliance review for customer or booking-level data usage.
- [ ] Assign ownership for model monitoring, prompt maintenance, incident response, and KPI review.
