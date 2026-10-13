"""Loads trained pipelines once, validates input, predicts, and explains."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)
ART_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "artifacts"
_lock = threading.Lock()
_registry: dict[str, dict] = {}


def _load_all() -> None:
    """Load artifacts; if missing/incompatible, retrain from the bundled CSVs (takes ~1 min)."""
    from ml import train  # local import keeps startup light if never needed

    for key in train.DISEASES:
        pipe_path, meta_path = ART_DIR / f"{key}.joblib", ART_DIR / f"{key}.meta.json"
        try:
            pipe = joblib.load(pipe_path)
            meta = json.loads(meta_path.read_text())
        except Exception as exc:  # missing file or sklearn version mismatch
            logger.warning("Could not load %s model (%s). Retraining from CSV...", key, exc)
            train.main([key])
            pipe = joblib.load(pipe_path)
            meta = json.loads(meta_path.read_text())
        _registry[key] = {"pipe": pipe, "meta": meta}
    logger.info("Loaded models: %s", ", ".join(_registry))


def registry() -> dict[str, dict]:
    if not _registry:
        with _lock:
            if not _registry:
                _load_all()
    return _registry


def list_models() -> list[dict]:
    return [
        {
            "key": k,
            "title": v["meta"]["title"],
            "best_model": v["meta"]["best_model"],
            "metrics": v["meta"]["metrics"],
            "n_samples": v["meta"]["n_samples"],
            "n_features": len(v["meta"]["features"]),
        }
        for k, v in registry().items()
    ]


def get_meta(disease: str) -> dict:
    reg = registry()
    if disease not in reg:
        raise KeyError(disease)
    return reg[disease]["meta"]


def _risk_level(p: float) -> str:
    return "low" if p < 0.35 else "moderate" if p < 0.65 else "high"


def predict(disease: str, values: dict[str, float]) -> dict:
    reg = registry()
    if disease not in reg:
        raise KeyError(disease)
    pipe, meta = reg[disease]["pipe"], reg[disease]["meta"]
    names = [f["name"] for f in meta["features"]]

    missing = [n for n in names if n not in values]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(missing)}")

    row = {n: float(values[n]) for n in names}
    for col in meta.get("zero_is_missing", []):  # 0 means "not measured" for these fields
        if row.get(col) == 0:
            row[col] = np.nan
    X = pd.DataFrame([row], columns=names)
    prob = float(pipe.predict_proba(X)[0, 1])

    # Model-agnostic explanation: replace each feature with the training median and
    # see how much the probability moves (a simple occlusion / "what-if" analysis).
    contributions = []
    for f in meta["features"]:
        alt = X.copy()
        alt.loc[0, f["name"]] = f["median"]
        delta = prob - float(pipe.predict_proba(alt)[0, 1])
        contributions.append(
            {"feature": f["name"], "label": f["label"], "value": values[f["name"]], "impact": round(delta, 4)}
        )
    contributions.sort(key=lambda c: abs(c["impact"]), reverse=True)

    return {
        "disease": disease,
        "title": meta["title"],
        "probability": round(prob, 4),
        "risk_level": _risk_level(prob),
        "prediction": int(prob >= 0.5),
        "model": meta["best_model"],
        "model_metrics": meta["metrics"],
        "top_factors": contributions[:5],
        "disclaimer": (
            "This is a screening estimate from a small public dataset, not a medical diagnosis. "
            "Please consult a qualified doctor."
        ),
    }
