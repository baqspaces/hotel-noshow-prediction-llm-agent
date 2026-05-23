# Hotel No-Show Prediction AI Agent Architecture

## Executive Overview

The Hotel No-Show AI agent uses a lightweight multi-agent orchestration pattern to answer hotel no-show prediction questions. The agents are logical roles inside one controlled Python workflow rather than independent services. This keeps the prototype auditable, easy to run, and aligned with enterprise review expectations.

The assistant is invoked by the dashboard through `POST /api/assistant/query`. The `src` package retrieves no-show insights from `noshow.db`, builds an evidence package from the `booking_ml_scores` table, sends the package to the configured OpenAI model, and returns the answer with a provider label and an agent trace. If the LLM is unavailable, the same endpoint returns a deterministic fallback response.

## Invocation Flow

1. User enters a question in the dashboard assistant panel.
2. `frontend/app.js` sends the question to `POST /api/assistant/query`.
3. `src/main.py` receives the request and calls py function `answer_question(payload.question)`.
4. `src/assistant.py` runs the agent workflow.
5. The Retrieval Agent ranks relevant EDA and segment insights.
6. The Insight and Intervention agents package metrics, high-risk bookings, and playbooks.
7. The Executive Narrative Agent applies instructions from `LLM_PROMPT.md`.
8. The Coordinator Agent calls OpenAI or returns the deterministic fallback.
9. The dashboard displays the provider, rendered answer, and collapsible agent trace.

## Agent Roles

| Agent | Python implementation | Input | Output | Purpose |
|---|---|---|---|---|
| Retrieval Agent | `_retrieve(question)` | User question | Ranked booking insights | Grounds the answer with the provided EDA insights and data |
| Insight Agent | `_build_llm_context(...)` | Retrieved insights and summary metrics | Evidence package | Provides segment patterns, no-show rates, and revenue exposure |
| Intervention Agent | `high_risk_bookings(...)` and `_intervention_for_booking(...)` | High-risk bookings | Action playbooks | Adds operational recommendations such as reminders, staff review, or deposit checks |
| Executive Narrative Agent | `_load_system_prompt()` and `LLM_PROMPT.md` | Evidence and formatting rules | LLM instructions | Controls tone, structure, Markdown formatting, and grounding rules |
| Coordinator Agent | `answer_question(...)` | Question, evidence, LLM result | Final response | Orchestrates the workflow, records the trace, and manages fallback |

## Runtime Sequence

```text
Dashboard question
  -> FastAPI /api/assistant/query
  -> answer_question()
  -> Retrieval Agent: _retrieve()
  -> Insight Agent: _build_llm_context()
  -> Intervention Agent: high_risk_bookings() + _intervention_for_booking()
  -> Executive Narrative Agent: LLM_PROMPT.md
  -> Coordinator Agent: _call_openai_assistant()
  -> Response: answer + provider + retrieved_insights + agent_trace
```

## Evidence Grounding

The LLM does not receive free-form access to the database. Instead, Python retrieves and packages a bounded evidence set:

- executive summary metrics from `summary_metrics()`
- ranked EDA insights from `top_insights()`
- high-risk booking examples from `booking_ml_scores`
- intervention playbooks generated from booking risk, revenue exposure, and customer type

This design reduces hallucination risk because the model is asked to reason over supplied evidence instead of inventing facts.

## LLM Prompt Control

The assistant prompt is stored in `LLM_PROMPT.md`. This allows non-code edits to response style and grounding rules. The prompt currently instructs the model to:

- use only supplied booking metrics and retrieved evidence
- return concise Markdown
- start with a short heading
- include sections such as `What the data shows`, `Recommended action`, and `Operational caveat` when useful
- bold important segments, metrics, and actions

The `src` package reloads this Markdown prompt for every assistant request.

## Fallback And Observability

The assistant returns a `provider` field:

- `openai`: the live LLM call succeeded
- `deterministic_fallback`: the LLM call was unavailable and fallback logic answered instead

The dashboard maps `deterministic_fallback` to the display label `fallback`. The `agent_trace` field records each orchestration step so reviewers can see which roles ran and whether the final answer came from OpenAI or fallback logic.

## Why This Counts As Agentic Orchestration

This is a single-orchestrator multi-role agent pattern. The agents are not autonomous background workers, but they do represent distinct responsibilities in the reasoning pipeline. This is common in production LLM applications where teams want controlled evidence retrieval, deterministic guardrails, traceability, and a small number of LLM calls.

The architecture can scale into a heavier multi-agent system by turning each role into a class or service, adding separate prompts per agent, introducing tool calls, adding memory, and using an evaluation harness for agent outputs.

## Production Extension Path

Recommended next steps for a production implementation:

- store prompt versions and model settings in a model or prompt registry
- add structured JSON outputs for intervention recommendations
- evaluate responses against a prompt test set
- log provider, latency, retrieved insight IDs, and fallback reason
- add human approval for high-impact interventions such as deposits or overbooking
- monitor drift in booking segments and no-show rates
- add role-specific prompts or separate LLM calls when the workflow becomes more complex

## Key Files

| File | Role |
|---|---|
| `src/assistant.py` | Main agent orchestration and OpenAI/fallback call |
| `src/main.py` | FastAPI endpoint that invokes the assistant |
| `src/analytics.py` | Summary metrics, segment insights, risk queue, and prediction estimates |
| `frontend/app.js` | Sends assistant questions and renders provider, answer, and trace |
| `LLM_PROMPT.md` | Editable LLM instructions |
| `AGENT_PROTOCOL.md` | Agent protocol, roles, reliability checks, and limitations |
