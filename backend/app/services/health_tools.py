"""Small deterministic health calculators + lab-report text analyser."""
from __future__ import annotations

import re


def bmi(weight_kg: float, height_cm: float) -> dict:
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("Weight and height must be positive.")
    m = height_cm / 100
    v = weight_kg / (m * m)
    # WHO adult categories (Asian cut-offs are lower; shown as a note)
    cat = ("Underweight" if v < 18.5 else "Normal weight" if v < 25 else "Overweight" if v < 30 else "Obese")
    return {
        "bmi": round(v, 1),
        "category": cat,
        "healthy_weight_range_kg": [round(18.5 * m * m, 1), round(24.9 * m * m, 1)],
        "note": "For South Asian adults, health risk rises from a BMI of about 23. BMI ignores muscle mass and is not diagnostic.",
    }


def blood_pressure(systolic: int, diastolic: int) -> dict:
    if not (50 <= systolic <= 300 and 30 <= diastolic <= 200) or diastolic >= systolic:
        raise ValueError("Please enter realistic values (systolic > diastolic).")
    if systolic > 180 or diastolic > 120:
        cat, level, msg = "Hypertensive crisis range", "emergency", "If you also have chest pain, breathlessness, weakness, confusion or severe headache call emergency services now; otherwise re-check after 5 minutes of rest and contact a doctor urgently."
    elif systolic >= 140 or diastolic >= 90:
        cat, level, msg = "Stage 2 hypertension range", "high", "Book a doctor's appointment soon; repeated readings at this level usually need treatment."
    elif systolic >= 130 or diastolic >= 80:
        cat, level, msg = "Stage 1 hypertension range", "moderate", "Lifestyle changes (less salt, exercise, weight control) and a doctor review are recommended."
    elif systolic >= 120:
        cat, level, msg = "Elevated", "low", "Lifestyle measures can prevent progression to hypertension."
    else:
        cat, level, msg = "Normal", "low", "Keep up healthy habits and check periodically."
    return {"category": cat, "level": level, "advice": msg}


# test name -> (aliases regex, unit, [(upper_bound_exclusive, status, note), ...])
_TESTS = {
    "Fasting glucose": (r"fasting\s*(blood\s*)?(glucose|sugar)|fbs|fbg", "mg/dL",
        [(70, "low", "Below usual range"), (100, "normal", "Normal"), (126, "borderline", "Prediabetes range"), (1e9, "high", "Diabetes range (needs confirmation by a doctor)")]),
    "HbA1c": (r"hba1c|glycosylated h(a)?emoglobin|a1c", "%",
        [(5.7, "normal", "Normal"), (6.5, "borderline", "Prediabetes range"), (1e9, "high", "Diabetes range (needs confirmation by a doctor)")]),
    "Total cholesterol": (r"total\s*cholesterol|cholesterol,?\s*total", "mg/dL",
        [(200, "normal", "Desirable"), (240, "borderline", "Borderline high"), (1e9, "high", "High")]),
    "LDL cholesterol": (r"\bldl\b(\s*cholesterol)?", "mg/dL",
        [(100, "normal", "Optimal"), (130, "normal", "Near optimal"), (160, "borderline", "Borderline high"), (1e9, "high", "High")]),
    "HDL cholesterol": (r"\bhdl\b(\s*cholesterol)?", "mg/dL",
        [(40, "low", "Low (protective HDL is 40+ mg/dL)"), (1e9, "normal", "Acceptable")]),
    "Triglycerides": (r"triglycerides?|\btg\b", "mg/dL",
        [(150, "normal", "Normal"), (200, "borderline", "Borderline high"), (500, "high", "High"), (1e9, "high", "Very high")]),
    "TSH": (r"\btsh\b", "mIU/L",
        [(0.4, "low", "Below typical range"), (4.0, "normal", "Within typical range"), (1e9, "high", "Above typical range")]),
}


def analyse_report(text: str, sex: str | None = None) -> dict:
    """Pull 'Test name ... number' pairs out of pasted lab text and classify against standard ranges."""
    found = []
    lines = [ln for ln in re.split(r"[\n;]+", text or "") if ln.strip()]
    for name, (alias, unit, bands) in _TESTS.items():
        for ln in lines:
            m = re.search(rf"(?:{alias})[^0-9\-]{{0,40}}(?P<num>\d+(?:\.\d+)?)", ln, re.I)
            if m:
                val = float(m.group("num"))
                status, note = next((s, n) for ub, s, n in bands if val < ub)
                found.append({"test": name, "value": val, "unit": unit, "status": status, "note": note})
                break
    for ln in lines:
        low = ln.lower()
        if re.search(r"h(a)?emoglobin|\bhb\b", low) and not re.search(r"a1c|glycosylated|glycated", low):
            m = re.search(r"(?:h(?:a)?emoglobin|\bhb\b)[^0-9\-]{0,25}(\d+(?:\.\d+)?)", low)
            if m:
                val = float(m.group(1))
                lo, hi = (13.5, 17.5) if (sex or "").lower().startswith("m") else (12.0, 15.5)
                if val < lo:
                    status, note = "low", f"Below typical range ({lo}-{hi} g/dL) - possible anaemia"
                elif val > hi:
                    status, note = "high", f"Above typical range ({lo}-{hi} g/dL)"
                else:
                    status, note = "normal", f"Within typical range ({lo}-{hi} g/dL)"
                found.append({"test": "Haemoglobin", "value": val, "unit": "g/dL", "status": status, "note": note})
                break
    return {
        "results": found,
        "abnormal_count": sum(1 for r in found if r["status"] not in ("normal",)),
        "note": "Reference ranges differ between laboratories - always compare with the range printed on your report.",
    }
