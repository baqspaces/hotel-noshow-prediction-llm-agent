# Hotel No-Show Prediction AI Agent Architecture

## Executive Overview

The Hotel No-Show AI agent uses a lightweight multi-agent orchestration pattern to answer hotel no-show prediction questions. The agents are logical roles inside one controlled Python workflow rather than independent services. This keeps the prototype auditable, easy to run, and aligned with enterprise review expectations.

The AI agent is invoked by the dashboard through `POST /api/assistant/query`. The `src` package retrieves no-show insights from `noshow.db`, builds an evidence package from the `booking_ml_scores` table, sends the package to the configured LLM provider, and returns the answer with a provider label and an agent trace. 

The current demo implementation uses OpenAI only. The API response contract is designed so future LLM providers such as Claude or Gemini can be added later without changing the dashboard request shape. If the LLM is unavailable, the same endpoint returns a deterministic fallback response.

## Communication Protocol

The AI agent endpoint receives:

```json
{
  "question": "Give me an executive summary of the no-show risk."
}
```

The assistant returns:

```json
{
  "answer": "...",
  "retrieved_insights": [],
  "matched_segment_metrics": [],
  "agent_trace": [],
  "provider": "openai"
}
```

`provider` is `openai` when the current live OpenAI call succeeds and `deterministic_fallback` when the fallback path is used. Future provider values can be added behind the same response contract after provider-specific config, client calls, dependencies, and response normalisation are implemented. The dashboard displays the provider badge, rendered Markdown answer, and collapsible agent trace.

## Invocation Flow

1. User enters a question in the dashboard assistant panel.
2. `frontend/app.js` sends the question to `POST /api/assistant/query`.
3. `src/main.py` receives the request and calls py function `answer_question(payload.question)`.
4. `src/assistant.py` runs the agent workflow.
5. The Retrieval Agent ranks relevant EDA and segment insights, including exact segment matches from the user question.
6. The Insight and Intervention agents package metrics, high-risk bookings, and playbooks.
7. The Executive Narrative Agent applies instructions from `LLM_PROMPT.md`.
8. The Coordinator Agent calls the configured LLM provider or returns the deterministic fallback.
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
  -> Retrieval Agent: _retrieve() + matched_segment_insights()
  -> Insight Agent: _build_llm_context()
  -> Intervention Agent: high_risk_bookings() + _intervention_for_booking()
  -> Executive Narrative Agent: LLM_PROMPT.md
  -> Coordinator Agent: current OpenAI provider call
  -> Response: answer + provider + retrieved_insights + matched_segment_metrics + agent_trace
```

## Evidence Grounding

The LLM does not receive free-form access to the database. Instead, Python retrieves and packages a bounded evidence set:

- executive summary metrics from `summary_metrics()`
- ranked EDA insights from `top_insights()`
- exact segment matches from `matched_segment_insights(question)`
- high-risk booking examples from `booking_ml_scores`
- intervention playbooks generated from booking risk, revenue exposure, and first-time customer status

This design reduces hallucination risk because the model is asked to reason over supplied evidence instead of inventing facts.

## LLM Prompt Control

The assistant prompt is stored in `LLM_PROMPT.md`. This allows non-code edits to response style and grounding rules. The prompt currently instructs the model to:

- use only supplied booking metrics and retrieved evidence
- return concise Markdown
- start with a short heading
- return the required sections `What the data shows`, `Recommended action`, and `Operational caveat`
- bold important segments, metrics, and actions

The `src` package reloads this Markdown prompt for every assistant request.

## Fallback And Observability

The assistant returns a `provider` field:

- `openai`: the current live OpenAI LLM call succeeded
- `deterministic_fallback`: the LLM call was unavailable and fallback logic answered instead

The `agent_trace` field records each orchestration step so reviewers can see which roles ran and whether the final answer came from a live LLM provider, such as OpenAI today, or fallback logic.

## Future LLM Provider Extension

The dashboard and API response shape are provider-labeled, but the current code only implements OpenAI. To add providers such as Claude or Gemini:

- add provider selection config such as `LLM_PROVIDER`
- add provider-specific credentials and model settings to `config.py`, `.env.example`, and Docker config
- implement provider-specific client calls in `src/assistant.py`
- normalise provider responses to the same `answer`, `provider`, `retrieved_insights`, `matched_segment_metrics`, and `agent_trace` contract
- add any required SDK dependencies to `requirements.txt`

## Key Files

| File | Role |
|---|---|
| `src/assistant.py` | Main agent orchestration, current OpenAI provider call, fallback logic, and future LLM provider extension point |
| `src/main.py` | FastAPI endpoint that invokes the assistant |
| `src/analytics.py` | Summary metrics, segment insights, operational risk queue, and prediction scores |
| `frontend/app.js` | Sends assistant questions and renders provider, answer, and trace |
| `LLM_PROMPT.md` | Editable LLM instructions |
| `AGENT_EVALUATION.md` | Agent evaluation and reliability tests |
