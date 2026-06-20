import json

from .client import _get_client
from .context import context_as_prompt
from .prompt import SYSTEM_PROMPT


ANALYST_RULES = """
You are answering from a closed evidence registry.

Return valid JSON only:
{
  "answer": "direct answer in plain English",
  "citation_ids": ["exact evidence id"],
  "follow_up": "one useful next question or action"
}

Rules:
- Cite only IDs that appear in the evidence registry.
- Every measured claim must have a citation.
- Do not calculate new metrics.
- Do not invent causes, conversion rates, users, dates, or outcomes.
- Distinguish technical audit evidence from real user behavior.
- If evidence is insufficient, say so directly and cite the evidence that
  establishes what is available, when possible.
- Use the current Decision Card and experiment results as context, but do not
  treat a recommendation as measured evidence.
- Treat product context as owner-declared context, not measured evidence.
- Treat Decision Card hypotheses as possible causes, not findings. State their
  confidence and validation action when discussing them.
- Keep the answer concise and actionable.
"""


def chat_with_agent(message, analyst_context, chat_history):
    evidence_registry = {
        item["id"]: item
        for item in analyst_context.get("evidence", [])
    }
    messages = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n{ANALYST_RULES}\n\n"
                f"Current ShipSense context:\n{context_as_prompt(analyst_context)}"
            ),
        },
    ]
    for item in chat_history[-12:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})

    try:
        client = _get_client()
        if not client:
            raise RuntimeError("No API key")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        answer = str(parsed.get("answer", "")).strip()
        citation_ids = [
            citation_id
            for citation_id in parsed.get("citation_ids", [])
            if citation_id in evidence_registry
        ]
        if not answer:
            raise ValueError("Empty analyst answer")
        return {
            "reply": answer,
            "citation_ids": citation_ids,
            "follow_up": str(parsed.get("follow_up", "")).strip(),
        }
    except Exception:
        return _fallback_chat(message, analyst_context)


def _fallback_chat(message, context):
    lowered = message.lower()
    decision = context.get("current_decision")
    experiments = context.get("experiments", [])
    evidence = {item["id"]: item for item in context.get("evidence", [])}

    if ("experiment" in lowered or "work" in lowered) and experiments:
        latest = experiments[0]
        result = latest.get("result")
        citation_id = f"experiment:{latest['id']}:result"
        if result and citation_id in evidence:
            conclusion = result.get("conclusion", "unknown")
            recommendation = result.get("recommendation", "review")
            return {
                "reply": (
                    f"The latest experiment is {conclusion}. "
                    f"ShipSense recommends: {recommendation}."
                ),
                "citation_ids": [citation_id],
                "follow_up": "What should we change in the next iteration?",
            }
        return {
            "reply": (
                f"The latest experiment is currently '{latest['status']}'. "
                "There is no conclusive measured result yet."
            ),
            "citation_ids": [],
            "follow_up": "Do we have enough post-release data to evaluate it?",
        }

    if decision and ("priority" in lowered or "why" in lowered):
        citation_ids = [
            item["id"]
            for item in decision.get("evidence", [])
            if item["id"] in evidence
        ]
        return {
            "reply": (
                f"'{decision['title']}' is the current priority because it is "
                f"the highest-ranked issue supported by the available evidence. "
                f"{decision['problem']}"
            ),
            "citation_ids": citation_ids,
            "follow_up": "What evidence would invalidate this recommendation?",
        }

    if decision and ("implement" in lowered or "how" in lowered):
        return {
            "reply": decision["recommendation"],
            "citation_ids": [
                item["id"]
                for item in decision.get("evidence", [])
                if item["id"] in evidence
            ],
            "follow_up": f"Track {decision['target_metric']} after release.",
        }

    behavior = [
        item for item in evidence.values()
        if item["source_type"] in {"behavior", "funnel"}
    ]
    if behavior:
        strongest = behavior[0]
        return {
            "reply": (
                f"The clearest behavioral evidence available is "
                f"{strongest['label']}: {strongest['value']} {strongest['unit']}."
            ),
            "citation_ids": [strongest["id"]],
            "follow_up": "How does this connect to the current Decision Card?",
        }

    technical = [
        item for item in evidence.values()
        if item["source_type"] == "technical_audit"
    ]
    if technical:
        strongest = technical[0]
        return {
            "reply": (
                "There is technical evidence, but not enough real user behavior "
                "to answer a behavioral question without guessing. "
                f"The available measurement is {strongest['label']}: "
                f"{strongest['value']} {strongest['unit']}."
            ),
            "citation_ids": [strongest["id"]],
            "follow_up": "What behavioral events should we collect next?",
        }

    return {
        "reply": "ShipSense does not have enough measured evidence to answer that yet.",
        "citation_ids": [],
        "follow_up": "What data should we collect first?",
    }
