# Agent Protocol and Evaluation

## Purpose

The AI assistant is a lightweight multi-agent orchestration layer for hotel no-show intelligence. It retrieves grounded booking evidence from `noshow.db`, packages that evidence for a configured OpenAI model, and returns an executive-ready answer. If `OPENAI_API_KEY` is not configured or the LLM call fails, the endpoint falls back to deterministic response logic so the demo remains reviewable without external services.

## Agent Roles

| Agent | Input | Output | Purpose |
|---|---|---|---|
| Retrieval Agent | User question | Top retrieved booking insights | Grounds answers in EDA and risk data |
| Insight Agent | Retrieved insights | Evidence package for LLM | Provides segment patterns and metrics |
| Intervention Agent | High-risk bookings | Action playbooks | Converts risk scores into operational context |
| Executive Narrative Agent | Metrics and evidence | Formatting/tone instruction | Asks the LLM to produce management-ready guidance |
| Coordinator Agent | User question, evidence, LLM result | Final response | Returns the LLM answer or deterministic fallback |

## Communication Protocol

The assistant endpoint receives:

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
  "agent_trace": [],
  "provider": "openai"
}
```

`provider` is `openai` when the live LLM call succeeds and `deterministic_fallback` when the fallback path is used. The dashboard displays the provider badge, rendered Markdown answer, and collapsible agent trace.

## Coordination Logic

All requests start with retrieval from EDA and risk outputs. The backend then builds an LLM context containing:

- the user's question
- executive summary metrics
- retrieved EDA insights
- high-risk booking examples
- intervention playbooks

The OpenAI model is instructed by `LLM_PROMPT.md`, which controls the assistant's grounding rules, response format, and tone. The deterministic fallback keeps the same high-level routing for summary, intervention, scenario, and general insight questions.

## Intervention Policy

The intervention context recommends actions based on predicted no-show probability, expected revenue exposure, and customer type:

- high probability and high revenue exposure -> staff review, confirmation, deposit or guarantee check
- first-time customer -> automated reminder plus confirmation link
- medium probability -> automated reminder and reconfirmation
- lower probability -> standard reminder flow

## Evaluation Scenarios

The assistant is evaluated with scenario prompts that check grounding, usefulness, traceability, and fallback safety. A reviewer can run these prompts through the dashboard assistant panel or `POST /api/assistant/query`.

Detailed agent performance and reliability results are documented in `AGENT_EVALUATION.md`.

| Test Prompt | Expected Behavior | Pass Criteria | Reliability Signal |
|---|---|---|---|
| Give me an executive summary of no-show risk | Summarizes booking count, no-show rate, revenue exposure, and targeted intervention rationale | Uses real metrics from `summary_metrics()` and does not invent unsupported causes | `provider` is visible and `agent_trace` includes Retrieval, Insight, Executive Narrative, and Coordinator steps |
| What actions should we take for risky bookings? | Uses high-risk bookings and recommends operational interventions | Mentions actions tied to risk probability, revenue exposure, or customer type | Intervention Agent step appears and examples come from `booking_ml_scores` |
| Which segments are driving risk? | Uses retrieved segment insights to explain drivers | Discusses known segments such as branch, country, room, customer type, platform, or month fields | Retrieved insights are returned in the API response |
| What if we reduce no-shows without hurting customer experience? | Recommends targeted tests and operational guardrails | Suggests controlled interventions instead of blanket policies | Answer includes caveats and avoids overclaiming causal impact |
| Tell me something not in the data, such as guest income or weather impact | Refuses or caveats unsupported claims | States that the supplied data does not include the requested field and gives a safe next step | Grounding rules from `LLM_PROMPT.md` are followed |
| Temporarily remove or omit `OPENAI_API_KEY` | Returns a deterministic fallback answer | Endpoint still returns HTTP 200 with `provider = deterministic_fallback` | Fallback path and reason appear in `agent_trace` |

Suggested scoring rubric:

| Dimension | Good Response Standard |
|---|---|
| Grounding | Uses supplied metrics, retrieved insights, and risk queue examples only |
| Accuracy | Does not fabricate booking rows, columns, model results, or causal claims |
| Actionability | Recommends realistic hotel operations actions such as reminders, confirmation, staff review, deposit checks, or controlled overbooking review |
| Traceability | Returns `provider`, `retrieved_insights`, and `agent_trace` for auditability |
| Robustness | Produces a fallback response when the LLM key or API call is unavailable |
| Executive readability | Uses concise Markdown suitable for a dashboard panel |

Current evaluation status for the prototype:

| Area | Status |
|---|---|
| Grounded evidence retrieval | Implemented through `top_insights()` and `summary_metrics()` |
| Risk-based intervention context | Implemented through `high_risk_bookings()` and `_intervention_for_booking()` |
| Live LLM response | Implemented when `OPENAI_API_KEY` is configured |
| Deterministic fallback | Implemented for missing credentials or LLM errors |
| Provider visibility | Implemented in API response and dashboard UI |
| Long-term memory evaluation | Not implemented; out of scope for this prototype |
| Human review workflow | Recommended for production before high-impact actions |

## Reliability Checks

- Responses are grounded in retrieved dashboard metrics and risk outputs.
- The assistant does not invent booking rows; intervention examples are pulled from the risk queue.
- The dashboard exposes `provider` so reviewers can verify whether the live LLM or fallback produced the answer.
- If the scored ML table is unavailable, risk-queue-backed intervention responses return a clear error until the notebook scoring cell is rerun.
- In production, agent quality should be evaluated with a prompt test set, response-grounding checks, and human review of intervention recommendations.

## Limitations

- The app uses a lightweight orchestration pattern rather than a persistent agent runtime.
- There is no long-term memory store.
- The fallback path is deterministic and less flexible than the LLM path.
- Recommendations are policy heuristics and should be validated through controlled operational tests before production use.
