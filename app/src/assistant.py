from pathlib import Path

from .analytics import high_risk_bookings, summary_metrics, top_insights
from .config import get_settings


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SYSTEM_PROMPT = """You are the AI insight assistant for a hotel no-show revenue optimization platform.
Answer as a concise executive analytics partner. Use only the supplied booking metrics, retrieved
insights, and high-risk booking examples. Do not invent fields, metrics, or root causes."""


def _load_system_prompt() -> str:
    prompt_path = APP_DIR / "LLM_PROMPT.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT


def _retrieve(question: str) -> list[dict]:
    terms = {term.strip("?,.!:;").lower() for term in question.split() if len(term.strip("?,.!:;")) > 2}
    insights = top_insights()
    ranked = []
    for insight in insights:
        haystack = f"{insight['title']} {insight['text']}".lower()
        lexical = sum(1 for term in terms if term in haystack)
        ranked.append({**insight, "retrieval_score": lexical + insight["score"]})
    return sorted(ranked, key=lambda item: item["retrieval_score"], reverse=True)[:5]


def _intervention_for_booking(row: dict) -> str:
    probability = row.get("predicted_no_show_probability", 0)
    revenue = row.get("expected_revenue_at_risk", 0)
    customer_type = str(row.get("customer_type", "")).lower()
    if probability >= 0.4 and revenue >= 500:
        return "priority staff review, pre-arrival confirmation, and deposit or guarantee check"
    if "first" in customer_type:
        return "automated reminder plus simple confirmation link for first-time customer"
    if probability >= 0.35:
        return "automated reminder 48 hours before arrival and same-day reconfirmation"
    return "standard reminder flow"


def _fallback_answer(question: str, retrieved: list[dict], trace: list[dict]) -> dict:
    q = question.lower()
    if "what if" in q or "reduce" in q or "reduction" in q:
        trace.append({"agent": "Queue Prioritization Agent", "action": "redirected scenario question to risk queue actions"})
        answer = (
            "The dashboard now focuses on actioning bookings through the operational queue. "
            "Use the operational queue filter to review High, Medium, or Low risk bookings, compare risk scores, and prioritize the recommended interventions."
        )
    elif "intervention" in q or "recommend" in q or "action" in q:
        trace.append({"agent": "Intervention Agent", "action": "ranked high-risk bookings and matched intervention playbooks"})
        bookings = high_risk_bookings(limit=3)
        actions = [
            f"Booking {row.get('booking_id')}: {row.get('risk_band')} risk, {row.get('predicted_no_show_probability', 0):.1%} probability, recommend {_intervention_for_booking(row)}."
            for row in bookings
        ]
        answer = "Recommended intervention focus:\n" + "\n".join(actions)
    elif "summary" in q or "executive" in q or "overview" in q:
        trace.append({"agent": "Executive Narrative Agent", "action": "translated metrics into business summary"})
        summary = summary_metrics()
        answer = (
            f"The dataset contains {summary['total_bookings']:,} bookings with a {summary['no_show_rate']:.1%} no-show rate. "
            f"Observed historical revenue exposure is approximately {summary.get('observed_revenue_at_risk') or 0:,.0f}. "
            "Risk is concentrated in identifiable booking segments, so targeted reminders, confirmations, and deposit tests are preferable to a blanket policy."
        )
    else:
        trace.append({"agent": "Insight Agent", "action": "combined retrieved evidence into a concise answer"})
        evidence = " ".join(item["text"] for item in retrieved[:3])
        answer = f"Based on the booking data: {evidence}"

    trace.append({"agent": "Coordinator Agent", "action": "prioritized answer based on user intent and retrieved evidence"})
    return {
        "answer": answer,
        "retrieved_insights": retrieved,
        "agent_trace": trace,
    }


def _build_llm_context(question: str, retrieved: list[dict]) -> str:
    metrics = summary_metrics()
    bookings = high_risk_bookings(limit=5)
    booking_examples = [
        {
            "booking_id": row.get("booking_id"),
            "risk_band": row.get("risk_band"),
            "predicted_no_show_probability": row.get("predicted_no_show_probability"),
            "expected_revenue_at_risk": row.get("expected_revenue_at_risk"),
            "branch": row.get("branch"),
            "platform": row.get("platform"),
            "country": row.get("country"),
            "room": row.get("room"),
            "customer_type": row.get("customer_type"),
            "recommended_playbook": _intervention_for_booking(row),
        }
        for row in bookings
    ]
    return (
        f"User question:\n{question}\n\n"
        f"Executive summary metrics:\n{metrics}\n\n"
        f"Retrieved EDA insights:\n{retrieved}\n\n"
        f"High-risk booking examples:\n{booking_examples}"
    )


def _call_openai_assistant(question: str, retrieved: list[dict]) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError("The openai package is not installed") from exc

    client = OpenAI(
        api_key=settings.openai_api_key,
        organization=settings.openai_org_id,
        project=settings.openai_project_id,
        timeout=settings.openai_timeout_seconds,
    )
    response = client.responses.create(
        model=settings.openai_model,
        instructions=_load_system_prompt(),
        input=_build_llm_context(question, retrieved),
        max_output_tokens=700,
    )
    return response.output_text.strip()


def answer_question(question: str) -> dict:
    trace = [
        {"agent": "Retrieval Agent", "action": "searched EDA and segment insights"},
    ]
    retrieved = _retrieve(question)

    try:
        trace.extend([
            {"agent": "Insight Agent", "action": "sent retrieved booking evidence to the configured LLM"},
            {"agent": "Intervention Agent", "action": "included high-risk bookings and intervention playbooks as LLM context"},
            {"agent": "Executive Narrative Agent", "action": "asked the LLM to translate analytics into management-ready guidance"},
            {"agent": "Coordinator Agent", "action": "used the LLM response as the final assistant answer"},
        ])
        answer = _call_openai_assistant(question, retrieved)
        provider = "openai"
    except Exception as exc:
        trace.append({
            "agent": "Coordinator Agent",
            "action": f"fell back to deterministic response because LLM call was unavailable: {exc}",
        })
        fallback = _fallback_answer(question, retrieved, trace)
        fallback["provider"] = "deterministic_fallback"
        return fallback

    return {
        "answer": answer,
        "retrieved_insights": retrieved,
        "agent_trace": trace,
        "provider": provider,
    }


def intervention_recommendation(row: dict) -> dict:
    return {
        "booking_id": row.get("booking_id"),
        "recommended_action": _intervention_for_booking(row),
        "reason": (
            f"{row.get('risk_band')} risk booking with {row.get('predicted_no_show_probability', 0):.1%} predicted no-show probability "
            f"and {row.get('expected_revenue_at_risk', 0):,.0f} expected revenue at risk."
        ),
    }
