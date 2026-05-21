# Agent Performance and Reliability Evaluation

## Evaluation Objective

This report evaluates whether the AI assistant produces grounded, useful, and traceable answers for hotel no-show management questions. The evaluation focuses on the multi-agent orchestration layer in `src/assistant.py`, including retrieved evidence, LLM response quality, deterministic fallback behavior, and dashboard observability.

This is different from a general QA report. QA validates that the overall application works end to end. Agent evaluation validates that the assistant answers well, stays grounded in the supplied data, and fails safely.

## Test Method

Each test prompt can be run from the dashboard assistant panel or through `POST /api/assistant/query`. The response is reviewed for:

- `provider`: confirms whether the answer came from `openai` or fallback logic
- `agent_trace`: confirms the orchestration path
- grounding: answer uses retrieved metrics and booking examples
- actionability: recommendations are operationally useful
- safety: answer avoids unsupported claims

## Evaluation Matrix

| Test Prompt | Expected Behavior | Pass Criteria | Provider Check | Result |
|---|---|---|---|---|
| Give me an executive summary of no-show risk. | Summarizes total bookings, no-show rate, revenue exposure, and priority segments. | Uses supplied summary metrics and avoids unsupported root-cause claims. | `provider` should be `openai` when API key is configured, otherwise `deterministic_fallback`. | Pass |
| What actions should we take for high-risk bookings? | Recommends targeted interventions for risky bookings. | Ties actions to risk probability, expected revenue exposure, customer type, or segment. | Agent trace should include Intervention Agent context. | Pass |
| Which segments are driving no-show risk? | Explains risk by available dimensions such as branch, country, room, customer type, platform, or month. | Uses retrieved segment insights from the database-backed analytics layer. | Retrieved insights should be present in the API response. | Pass |
| What if we reduce no-shows without hurting customer experience? | Suggests controlled tests and operational guardrails. | Recommends targeted reminders, confirmations, deposits, or overbooking review without claiming causal proof. | Agent trace should include Coordinator Agent and LLM or fallback path. | Pass |
| Tell me something not in the data, such as guest income or weather impact. | Refuses or caveats unsupported analysis. | States that the supplied data does not include that field and suggests what data would be needed. | Grounding rules from `LLM_PROMPT.md` should be followed. | Pass |
| Run assistant without `OPENAI_API_KEY`. | Returns a fallback answer instead of failing the dashboard. | Response includes `provider = deterministic_fallback` and a fallback reason in `agent_trace`. | Dashboard displays `Provider: fallback`. | Pass |

## Reliability Checks

| Reliability Area | Check | Current Implementation |
|---|---|---|
| Grounding | Assistant answers are based on retrieved metrics, segment insights, and high-risk booking examples. | Implemented through `summary_metrics()`, `top_insights()`, and `high_risk_bookings()`. |
| Traceability | Response exposes the orchestration path. | Implemented through `agent_trace` in the API and collapsible dashboard trace. |
| Provider transparency | Reviewer can tell whether the LLM or fallback produced the answer. | Implemented through `provider` in the API and dashboard badge. |
| Fallback safety | Assistant continues working without LLM credentials. | Implemented through deterministic fallback in `answer_question()`. |
| Prompt control | Formatting and grounding rules are editable without Python changes. | Implemented through `LLM_PROMPT.md`. |
| Data availability failure | Missing ML score table produces a clear error. | Implemented in risk queue and prediction logic. |

## Known Limitations

- The agents are logical roles in one orchestrated Python workflow, not independent autonomous services.
- The current implementation uses one LLM call per assistant query rather than separate LLM calls per agent.
- There is no long-term agent memory store.
- Recommendations are policy heuristics and should be validated through controlled operational experiments.
- LLM output quality depends on the configured model, prompt, and retrieved evidence.

## Production Evaluation Plan

For a production deployment, the agent evaluation should be expanded with:

- a fixed prompt regression test set
- automated checks for forbidden unsupported claims
- latency and error-rate monitoring by provider
- human review of high-impact intervention recommendations
- comparison between fallback and LLM responses
- prompt/model version tracking
- periodic review when booking patterns or no-show rates drift
