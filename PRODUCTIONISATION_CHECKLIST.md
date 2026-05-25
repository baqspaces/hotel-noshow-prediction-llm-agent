# Productionisation Checklist

This checklist summarises practical next steps to move the prototype no-show prediction dashboard, ML workflow, and AI assistant into a production-ready web application that external users can access.

## Database And MLOps Lifecycle

- [ ] Move from local `noshow.db` to a managed production database such as PostgreSQL, MySQL, AWS RDS, Google Cloud SQL, or Azure Database.
- [ ] Add database migration scripts for booking tables, scored model tables, indexes, and future schema changes.
- [ ] Add indexes for common dashboard queries such as branch, platform, country, room, risk band, and risk score.
- [ ] Add database backups, point-in-time recovery, and restore testing.
- [ ] Replace notebook-only scoring with a scheduled data ingestion, validation, and ML scoring pipeline, such as a Python job orchestrated by Airflow.
- [ ] Version datasets, feature definitions, model artifacts, model metrics, and scoring outputs for auditability and rollback.
- [ ] Add model drift monitoring for no-show prediction scores, booking mix, and segment distributions.
- [ ] Define retraining triggers, approval gates, and ownership for model releases.
- [ ] Incorporate fairness audit tests across customer segments, such as demographic parity and equal opportunity.
- [ ] Conduct further model interpretability analysis, such as SHAP feature importance.

## LLM Assistant

- [ ] Keep the provider boundary explicit. The current demo implements OpenAI only; Claude, Gemini, or local models would require provider-specific config, client calls, dependencies, and response normalisation.
- [ ] Add guardrails for unsupported claims, hallucinated metrics, and missing operational caveats.
- [ ] Add regression tests for common assistant questions and required answer structure.
- [ ] Track provider name, model name, prompt version, latency, fallback rate, and error rate for agent monitoring.
- [ ] Add prompt and model version tracking so assistant behavior can be audited and rolled back.
- [ ] Add user-level assistant rate limits, prompt length limits, and LLM cost/budget alerts.
- [ ] Define safe fallback behavior when the LLM provider, prompt file, or scored booking table is unavailable.

## Authentication And Security

- [ ] Replace demo credentials such as `manager` / `password123` with OAuth2/OpenID Connect or SSO using an identity provider such as Microsoft Entra ID, Google, Okta, or Auth0.
- [ ] Add role-based access control for user groups such as viewer, manager, analyst, and admin.
- [ ] Require a strong production `JWT_SECRET` and rotate any development API keys.
- [ ] Store `OPENAI_API_KEY`, `JWT_SECRET`, database credentials, and OAuth client secrets in a managed secret store.
- [ ] Restrict CORS to the production dashboard domain only.
- [ ] Add logout, session expiry, token refresh, and token revocation handling.
- [ ] Remove prefilled production login values from the frontend.
- [ ] Add audit logging for login, dashboard access, assistant queries, prediction requests, and high-risk queue usage.

## Backend And API

- [ ] Add automated tests for auth, summary metrics, segment drill-downs, risk queue, prediction, assistant responses, and websocket streaming.
- [ ] Validate required `booking_ml_scores` columns before serving risk, prediction, or assistant endpoints.
- [ ] Return clear data/schema errors instead of generic 500 responses.
- [ ] Add structured logging, request IDs, health checks, and readiness checks.
- [ ] Make readiness checks validate database connectivity, required tables, and required production secrets.
- [ ] Replace in-memory rate limiting with Redis or another shared production-safe limiter.
- [ ] Replace in-memory cache with Redis or another shared cache if the app runs across multiple instances.

## Web Hosting And External Access

- [ ] Choose a hosting platform for external access, such as AWS ECS/Fargate, Google Cloud Run, Azure Container Apps, Render, Railway, or a managed VM.
- [ ] Build immutable Docker images for each release.
- [ ] Push production Docker images to a container registry such as AWS ECR, Google Artifact Registry, Azure Container Registry, or Docker Hub.
- [ ] Configure a production domain name such as `https://noshow-dashboard.example.com`.
- [ ] Put the app behind HTTPS/TLS using a managed certificate, load balancer, reverse proxy, or managed ingress.
- [ ] Configure request size limits, timeout controls, and health/readiness probes for the hosted service.

## Frontend

- [ ] Escape or sanitize all API and database-derived values before inserting them into HTML.
- [ ] Add a visible logout button.
- [ ] Handle expired tokens by clearing local storage and prompting the user to log in again.
- [ ] Add clear loading, empty, and error states for each dashboard section.
- [ ] Remove hardcoded demo values from production login fields.
- [ ] Test target browser, mobile, and desktop layouts for dashboard workflows.
- [ ] Add privacy notices or usage disclaimers if external users can view booking-level data.

## Deployment And Operations

- [ ] Use separate configuration for development, staging, and production.
- [ ] Add CI/CD checks for tests, Docker build, vulnerability scanning, and deployment.
- [ ] Add a staging deployment before production deployment.
- [ ] Add post-deployment smoke tests for `/health`, login, dashboard load, and key API endpoints.
- [ ] Define rollback procedures for app releases, prompt changes, data refreshes, model-score table updates, and database migrations.
- [ ] Centralise logs, metrics, alerts, and operational runbooks.
- [ ] Monitor API latency, error rate, login failures, assistant fallback rate, LLM provider latency/cost, and database query latency.
- [ ] Add alerts for app downtime, high 5xx error rate, database failures, and LLM provider failures.
- [ ] Run multiple FastAPI instances behind a load balancer if high availability is required.
- [ ] Configure production-safe WebSocket support, or replace live updates with polling if the hosting platform does not support WebSockets reliably.

## Governance And Review

- [ ] Document data sources, assumptions, known limitations, and model caveats.
- [ ] Define human review rules for interventions that affect customers or revenue.
- [ ] Track changes to prompts, model versions, thresholds, and business rules.
- [ ] Add privacy and compliance review for customer or booking-level data usage.
- [ ] Assign ownership for model monitoring, prompt maintenance, incident response, and KPI review.
