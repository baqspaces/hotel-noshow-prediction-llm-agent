from pathlib import Path
import re

from .analytics import high_risk_bookings, matched_segment_insights, summary_metrics, top_insights
from .config import get_settings


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(__file__).resolve().parents[2]
PROMPT_PATHS = [PROJECT_DIR / "LLM_PROMPT.md", APP_DIR / "LLM_PROMPT.md"]


def _load_system_prompt() -> str:
    for prompt_path in PROMPT_PATHS:
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
    searched = ", ".join(str(path) for path in PROMPT_PATHS)
    raise RuntimeError(f"LLM_PROMPT.md not found. Checked: {searched}")


def _markdown_section(markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _response_format_instructions(prompt: str) -> str:
    section = _markdown_section(prompt, "Response Format")
    return section or prompt


def _required_section_headings(prompt: str) -> list[str]:
    response_format = _response_format_instructions(prompt)
    headings = re.findall(r"`(\*\*[^`]+\*\*)`", response_format)
    if headings:
        return headings
    return re.findall(r"^(\*\*[^*\n]+\*\*)$", response_format, flags=re.MULTILINE)


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
    first_time_flag = row.get("first_time_flag")
    customer_status = str(row.get("customer_status", "")).lower()
    if probability >= 0.4 and revenue >= 500:
        return "priority staff review, pre-arrival confirmation, and deposit or guarantee check"
    if first_time_flag == 1 or "first" in customer_status:
        return "automated reminder plus simple confirmation link for first-time customer"
    if probability >= 0.35:
        return "automated reminder 48 hours before arrival and same-day reconfirmation"
    return "standard reminder flow"


def _format_matched_segment_answer(matched_segments: list[dict]) -> str:
    lines = []
    for row in matched_segments:
        delta = row.get("no_show_rate_delta_vs_overall") or 0
        direction = "above" if delta >= 0 else "below"
        lines.append(
            f"{row.get('dimension')}: {row.get('segment')} has {row.get('bookings', 0):,} bookings, "
            f"{row.get('no_shows', 0):,} no-shows, a {row.get('no_show_rate', 0):.1%} no-show rate, "
            f"and {row.get('observed_revenue_at_risk') or 0:,.0f} observed revenue at risk. "
            f"This is {abs(delta):.1%} {direction} the overall {row.get('overall_no_show_rate', 0):.1%} no-show rate."
        )
    return "Matched segment metrics:\n" + "\n".join(lines)


def _fallback_answer(question: str, retrieved: list[dict], trace: list[dict], matched_segments: list[dict] | None = None) -> dict:
    q = question.lower()
    matched_segments = matched_segments or []
    if matched_segments:
        trace.append({"agent": "Targeted Segment Agent", "action": "answered with exact segment metrics matched from the question"})
        answer = _format_matched_segment_answer(matched_segments)
    elif "what if" in q or "reduce" in q or "reduction" in q:
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
        "matched_segment_metrics": matched_segments,
        "agent_trace": trace,
    }


def _build_llm_context(question: str, retrieved: list[dict], matched_segments: list[dict], prompt: str) -> str:
    metrics = summary_metrics()
    try:
        bookings = high_risk_bookings(limit=5)
    except Exception:
        bookings = []
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
            "first_time_flag": row.get("first_time_flag"),
            "customer_status": row.get("customer_status"),
            "recommended_playbook": _intervention_for_booking(row),
        }
        for row in bookings
    ]
    return (
        f"User question:\n{question}\n\n"
        f"Response format instructions from LLM_PROMPT.md:\n{_response_format_instructions(prompt)}\n\n"
        f"Executive summary metrics:\n{metrics}\n\n"
        f"Retrieved EDA insights:\n{retrieved}\n\n"
        f"Matched segment metrics:\n{matched_segments}\n\n"
        f"High-risk booking examples:\n{booking_examples}"
    )


def _matches_response_format(answer: str, prompt: str) -> bool:
    stripped = answer.strip()
    if not stripped.startswith("### "):
        return False
    required_headings = _required_section_headings(prompt)
    return all(heading in stripped for heading in required_headings)


def _call_openai_assistant(question: str, retrieved: list[dict], matched_segments: list[dict]) -> str:
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
    prompt = _load_system_prompt()
    context = _build_llm_context(question, retrieved, matched_segments, prompt)
    response = client.responses.create(
        model=settings.openai_model,
        instructions=prompt,
        input=context,
        max_output_tokens=700,
    )
    answer = response.output_text.strip()
    if _matches_response_format(answer, prompt):
        return answer

    repair_response = client.responses.create(
        model=settings.openai_model,
        instructions=prompt,
        input=(
            "Rewrite the previous answer so it follows the Response Format section in LLM_PROMPT.md exactly. "
            "Do not add new facts. Use only the supplied context and the previous answer.\n\n"
            f"Response format instructions from LLM_PROMPT.md:\n{_response_format_instructions(prompt)}\n\n"
            f"Supplied context:\n{context}\n\n"
            f"Previous answer:\n{answer}"
        ),
        max_output_tokens=700,
    )
    return repair_response.output_text.strip()


def answer_question(question: str) -> dict:
    trace = [
        {"agent": "Retrieval Agent", "action": "searched EDA, top segment insights, and exact segment matches"},
    ]
    retrieved = _retrieve(question)
    matched_segments = matched_segment_insights(question)

    try:
        trace.extend([
            {"agent": "Insight Agent", "action": "sent retrieved booking evidence to the configured LLM"},
            {"agent": "Targeted Segment Agent", "action": "included exact segment metrics matched from the question"},
            {"agent": "Intervention Agent", "action": "included high-risk bookings and intervention playbooks as LLM context"},
            {"agent": "Executive Narrative Agent", "action": "asked the LLM to translate analytics into management-ready guidance"},
            {"agent": "Coordinator Agent", "action": "used the LLM response as the final assistant answer"},
        ])
        answer = _call_openai_assistant(question, retrieved, matched_segments)
        provider = "openai"
    except Exception as exc:
        trace.append({
            "agent": "Coordinator Agent",
            "action": f"fell back to deterministic response because LLM call was unavailable: {exc}",
        })
        fallback = _fallback_answer(question, retrieved, trace, matched_segments)
        fallback["provider"] = "deterministic_fallback"
        return fallback

    return {
        "answer": answer,
        "retrieved_insights": retrieved,
        "matched_segment_metrics": matched_segments,
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
