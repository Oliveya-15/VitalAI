"""
VitalAI health assistant - an AI agent.

Flow for every message:
  1. SAFETY FIRST: deterministic emergency triage runs on the text. A life-threatening red flag
     returns an emergency answer immediately (no LLM needed, no latency, no hallucination risk).
  2. If an LLM key is configured: a tool-calling agent loop (max AGENT_MAX_STEPS) where the model can
     call tools: search_health_knowledge (RAG), run_diagnosis (our ML models), emergency_triage,
     count_blood_donors, nearby_places.
  3. No key / provider down: graceful rule-based fallback using TF-IDF retrieval over the knowledge base.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Donor
from app.services import geo, knowledge, llm_service, ml_service, triage
from app.services.blood_service import GROUPS, RBC_COMPATIBLE_DONORS, is_eligible

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are VitalAI, a careful, friendly health information assistant inside a health platform.
Rules:
- You give general health information, never a diagnosis or prescription. Encourage seeing a doctor for anything concerning.
- For emergencies (chest pain, stroke signs, breathing trouble, heavy bleeding, unconsciousness, poisoning, self-harm) tell the user to call the ambulance number immediately.
- Use the tools: search_health_knowledge for medical/first-aid questions, run_diagnosis when the user gives clinical values for diabetes/heart/parkinsons screening,
  count_blood_donors for blood availability questions, nearby_places for hospitals/clinics/pharmacies/blood banks when a location is available.
- Ground facts in tool results; if the knowledge base has nothing, say what is generally known and be clear about uncertainty.
- Keep answers short (under 180 words), plain language, with simple bullet points when listing steps.
- Mention the platform pages when useful: Diagnosis, Blood Network, Emergency, Health Tools."""

TOOLS = [
    {"type": "function", "function": {
        "name": "search_health_knowledge",
        "description": "Search the curated health knowledge base (symptoms, first aid, blood donation rules, disease basics).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "run_diagnosis",
        "description": "Run a screening ML model. disease must be diabetes, heart or parkinsons. 'values' maps feature name to number. Call get fields from the user; do not invent values.",
        "parameters": {"type": "object", "properties": {
            "disease": {"type": "string", "enum": ["diabetes", "heart", "parkinsons"]},
            "values": {"type": "object", "additionalProperties": {"type": "number"}}},
            "required": ["disease", "values"]}}},
    {"type": "function", "function": {
        "name": "emergency_triage",
        "description": "Check free text symptoms for emergency red flags.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "count_blood_donors",
        "description": "Count currently eligible registered donors who could give to a patient of the given blood group in a city.",
        "parameters": {"type": "object", "properties": {"blood_group": {"type": "string", "enum": GROUPS}, "city": {"type": "string"}},
                       "required": ["blood_group", "city"]}}},
    {"type": "function", "function": {
        "name": "nearby_places",
        "description": "Find nearby hospital, clinic, pharmacy or blood_bank using the user's shared location.",
        "parameters": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["hospital", "clinic", "pharmacy", "blood_bank"]}},
                       "required": ["kind"]}}},
]


def _run_tool(name: str, args: dict, db: Session, location: dict | None) -> dict:
    try:
        if name == "search_health_knowledge":
            return {"results": knowledge.search(args.get("query", ""), k=3)}
        if name == "run_diagnosis":
            return ml_service.predict(args["disease"], args["values"])
        if name == "emergency_triage":
            return triage.triage(args.get("text", ""))
        if name == "count_blood_donors":
            bg, city = args["blood_group"], args["city"].strip().lower()
            allowed = RBC_COMPATIBLE_DONORS.get(bg, [bg])
            donors = [d for d in db.query(Donor).filter(Donor.blood_group.in_(allowed)).all()
                      if d.city.strip().lower() == city and is_eligible(d)]
            return {"eligible_donors": len(donors), "exact_group": sum(d.blood_group == bg for d in donors),
                    "hint": "Open the Blood Network page and post a request to contact matched donors."}
        if name == "nearby_places":
            if not location:
                return {"error": "User has not shared a location. Ask them to tap 'Use my location' on the Emergency page."}
            return {"places": geo.nearby(args["kind"], location["lat"], location["lon"], limit=5)}
    except Exception as exc:  # tool errors go back to the model, never crash the chat
        return {"error": str(exc)}
    return {"error": f"unknown tool {name}"}


def _fallback_reply(message: str) -> tuple[str, list[dict]]:
    hits = knowledge.search(message, k=2)
    low = message.lower()
    tips = []
    if re.search(r"blood|donor|donat", low):
        tips.append("Use the **Blood Network** page to register as a donor or post a request.")
    if re.search(r"ambulance|hospital|emergency|sos", low):
        tips.append("Use the **Emergency** page for ambulance requests and nearby hospitals.")
    if re.search(r"diabet|sugar|heart|parkinson|predict", low):
        tips.append("Use the **Diagnosis** page to run a screening model.")
    if not hits:
        body = ("I couldn't find a close match in my health knowledge base. Try asking about a symptom, first aid, "
                "diabetes, heart health, Parkinson's or blood donation - or see a doctor for personal advice.")
    else:
        body = "\n\n".join(f"**{h['title']}**\n{h['text']}" for h in hits)
    if tips:
        body += "\n\n" + "\n".join(f"- {t}" for t in tips)
    return body, hits


_INFO_Q = re.compile(r"^\s*(what|how|why|who|when|which|explain|tell me about|define|signs|symptoms|causes?)\b", re.I)
_PERSONAL = re.compile(r"\b(my|me|i|i'm|im|we|he|she|his|her|him|they|someone|somebody|dad|mom|mother|father|wife|husband|son|daughter|baby|child|friend|now|currently|right now|having|has|have)\b", re.I)


def _is_general_question(message: str) -> bool:
    """'What are the signs of a stroke?' is education, not an emergency report."""
    return bool(_INFO_Q.match(message)) and not _PERSONAL.search(message)


def respond(message: str, history: list[dict], db: Session, location: dict | None = None) -> dict:
    tri = triage.triage(message)
    if tri["level"] == "emergency" and not _is_general_question(message):
        reply = (f"**{tri['headline']}.** {tri['call']['label']} right now.\n\n"
                 + "\n".join(f"- {a}" for a in tri["actions"])
                 + f"\n\n_{tri['note']}_")
        return {"reply": reply, "mode": "safety_triage", "triage": tri, "sources": [], "tools_used": []}

    if settings.llm_enabled:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs += [{"role": m["role"], "content": m["content"]} for m in history[-8:] if m["role"] in ("user", "assistant")]
        msgs.append({"role": "user", "content": message})
        used, sources = [], []
        try:
            for _ in range(settings.AGENT_MAX_STEPS):
                out = llm_service.chat(msgs, tools=TOOLS)
                calls = out.get("tool_calls")
                if not calls:
                    return {"reply": (out.get("content") or "").strip() or "Sorry, I couldn't produce an answer.",
                            "mode": "llm_agent", "triage": tri, "sources": sources, "tools_used": used}
                msgs.append({"role": "assistant", "content": out.get("content") or "", "tool_calls": calls})
                for c in calls:
                    fn = c["function"]["name"]
                    try:
                        args = json.loads(c["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = _run_tool(fn, args, db, location)
                    used.append(fn)
                    if fn == "search_health_knowledge":
                        sources += [{"id": r["id"], "title": r["title"]} for r in result.get("results", [])]
                    msgs.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)[:6000]})
            # step budget exhausted: ask for a final answer without tools
            out = llm_service.chat(msgs + [{"role": "user", "content": "Please give your final answer now."}])
            return {"reply": (out.get("content") or "").strip(), "mode": "llm_agent", "triage": tri, "sources": sources, "tools_used": used}
        except llm_service.LLMUnavailable as exc:
            logger.warning("LLM unavailable, using fallback: %s", exc)

    reply, hits = _fallback_reply(message)
    return {"reply": reply, "mode": "rule_based", "triage": tri,
            "sources": [{"id": h["id"], "title": h["title"]} for h in hits], "tools_used": ["search_health_knowledge"]}
