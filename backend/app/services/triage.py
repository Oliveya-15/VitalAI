"""
Rule-based emergency triage. Deliberately NOT machine-learned and NOT dependent on an LLM:
red-flag detection for life-threatening symptoms must be deterministic and always available.
"""
from __future__ import annotations

import re

from app.core.config import get_settings

settings = get_settings()

# (name, regex, immediate advice)
RED_FLAGS = [
    ("Possible heart attack",
     r"chest (pain|pressure|tightness)|pain (in|down) (the |my )?(left )?arm|crushing|heart attack",
     ["Stop all activity and sit or lie down.", "Call the ambulance number now.", "If not allergic and advised, chew one 300 mg aspirin.", "Do not drive yourself."]),
    ("Possible stroke",
     r"face (is )?droop|slurred speech|can'?t speak|arm (is )?weak|one side (of (the )?(body|face))?.*(weak|numb)|sudden (confusion|vision loss|numbness)|stroke",
     ["Call the ambulance number now - note the time symptoms started.", "Do not give food, drink or medicine.", "Keep the person calm, lying with head slightly raised."]),
    ("Breathing emergency",
     r"can'?t breathe|cannot breathe|struggling to breathe|difficulty breathing|severe (shortness of breath|breathlessness)|choking|turning blue|lips (are )?blue",
     ["Call the ambulance number now.", "Sit upright, loosen tight clothing.", "If choking and unable to cough or speak, give back blows then abdominal thrusts."]),
    ("Severe bleeding",
     r"heavy bleeding|bleeding (a lot|heavily|won'?t stop|profusely)|blood (is )?(pouring|gushing)|severe bleeding",
     ["Press firmly on the wound with a clean cloth and keep pressing.", "Call the ambulance number.", "Keep the person lying down and warm."]),
    ("Unconsciousness / seizure",
     r"unconscious|unresponsive|passed out|not responding|collapsed|seizure|convulsion|fitting",
     ["Call the ambulance number now.", "Check breathing; if not breathing normally start CPR.", "If breathing, place on their side (recovery position).", "Do not put anything in their mouth."]),
    ("Poisoning / overdose",
     r"poison|overdose|swallowed (bleach|pesticide|chemicals?|too many)|drank (bleach|pesticide)",
     ["Call the ambulance and poison-control number now.", "Do not induce vomiting unless a professional tells you to.", "Keep the container/packaging to show responders."]),
    ("Severe allergic reaction",
     r"anaphyla|throat (is )?(swelling|closing)|swollen (tongue|lips|face).*(breath|sting|ate)|allergic reaction.*(breath|swelling)",
     ["Call the ambulance now.", "Use an adrenaline auto-injector if the person has one.", "Lie flat with legs raised unless breathing is difficult."]),
    ("Self-harm risk",
     r"suicid|kill myself|end my life|want to die|self[- ]harm",
     ["You are not alone - please contact your local emergency number or a crisis helpline now.", "If you can, stay with a trusted person and move away from anything you could use to hurt yourself."]),
    ("Severe injury / burn",
     r"major (burn|injury|accident)|severe burn|head injury.*(vomit|confus|unconscious)|broken (neck|back)|road accident|fell from",
     ["Call the ambulance number.", "Do not move the person if a head, neck or back injury is possible.", "Cool burns with running water for 20 minutes."]),
    ("Pregnancy emergency",
     r"pregnan.*(bleeding|severe pain|fits|seizure|no movement)|labou?r.*(bleeding|early)",
     ["Call the ambulance number now (maternal ambulance if available).", "Lie on the left side and avoid eating or drinking."]),
]

URGENT_HINTS = r"high fever|fever.*(3|three) days|persistent vomiting|severe (headache|pain|abdominal)|blood in (urine|stool)|vomiting blood|dehydrat|infant.*fever|baby.*fever"


def triage(text: str) -> dict:
    t = (text or "").lower()
    hits = []
    for name, pattern, advice in RED_FLAGS:
        if re.search(pattern, t):
            hits.append({"condition": name, "advice": advice})
    nums = settings.EMERGENCY_NUMBERS
    if hits:
        steps = []
        for h in hits[:2]:
            steps += [a for a in h["advice"] if a not in steps]
        return {
            "level": "emergency",
            "headline": "This may be a life-threatening emergency",
            "flags": [h["condition"] for h in hits],
            "actions": steps,
            "call": {"number": nums["ambulance"], "label": f"Call ambulance ({nums['ambulance']})",
                     "national": nums["national_emergency"]},
            "note": "Automated screening can miss things. If you are worried, call emergency services anyway.",
        }
    if re.search(URGENT_HINTS, t):
        return {
            "level": "urgent",
            "headline": "See a doctor today",
            "flags": [],
            "actions": ["Visit a clinic or hospital within the next few hours.", "Keep drinking fluids and rest.", "Call emergency services if symptoms get worse suddenly."],
            "call": None,
            "note": "Not an emergency by itself, but should not wait.",
        }
    return {
        "level": "routine",
        "headline": "No emergency red flags detected",
        "flags": [],
        "actions": ["Monitor your symptoms and rest.", "Book a routine doctor visit if symptoms last more than a few days or worsen."],
        "call": None,
        "note": "This checks only for common emergency red flags - it is not a diagnosis.",
    }
