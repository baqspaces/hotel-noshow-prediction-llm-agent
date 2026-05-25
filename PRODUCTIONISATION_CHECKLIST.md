# Productionisation Checklist

This checklist summarises a few possible next steps to move this prototype no-show prediction dashboard, ML workflow and AI assistant into a production ready application.

## Database Connection and MLOps Lifecycle

- [ ] Move from local `noshow.db` to a managed database or controlled production database.
- [ ] Replace ipynb scoring with a scheduled data ingestion, validation, and ML scoring pipeline. This can possibly be implemented with a py script running on a scheduler like Airflow.
- [ ] Add model drift monitoring for ML no-show prediction scores, booking mix and segment distributions.
- [ ] Define retraining triggers, approval gates, and ownership for model releases.
- [ ] Store model version datasets, feature definitions, model artifacts, model metrics, and scoring outputs for version control and rollback capabilities.
- [ ] Incoporate fairness audit tests across customer segments (e.g. demographic parity, equal opportunity)
- [ ] Conduct furhter feature importance analysis e.g. SHAP scores

## LLM Assistant

- [ ] Keep the provider boundary explicit. The current demo implements OpenAI only; for future implementations of other models - Claude, Gemini, or local models would require provider-specific config, client calls, dependencies, and response normalisation.
- [ ] Add guardrails for unsupported claims, hallucinated metrics, and missing operational caveats.
- [ ] Add regression tests for common assistant questions and required answer structure.
- [ ] Track and log provider name, model name, prompt version, latency, fallback rate, and error rate for agent performance and monitoring
- [ ] Define safe fallback behavior when the LLM provider, prompt file, or scored booking table is unavailable.

## Backend And API

- [ ] Add automated tests for auth, summary metrics, segment drill-downs, risk queue, prediction, assistant responses, and websocket streaming.
- [ ] Validate required `booking_ml_scores` columns before serving risk, prediction, or assistant endpoints.
- [ ] Return clear data/schema errors instead of generic 500 responses.
- [ ] Add structured logging, request IDs, health checks, and readiness checks.
- [ ] Replace in-memory rate limiting with Redis or another shared production-safe limiter.

## Frontend

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

## Security

- [ ] Rotate development API keys and store all secrets in environment variables or a managed secret store.
- [ ] Replace demo credentials such as `manager` / `password123` and require a strong production `JWT_SECRET`.
- [ ] Remove prefilled production login values from the frontend.
- [ ] Add audit logging for login, dashboard access, assistant queries, prediction requests, and high-risk queue usage.


## Governance And Review

- [ ] Document data sources, assumptions, known limitations, and model caveats.
- [ ] Define human review rules for interventions that affect customers or revenue.
- [ ] Track changes to prompts, model versions, thresholds, and business rules.
- [ ] Add privacy and compliance review for customer or booking-level data usage.
- [ ] Assign ownership for model monitoring, prompt maintenance, incident response, and KPI review.
