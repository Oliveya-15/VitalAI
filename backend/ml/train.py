"""
Train / retrain the disease-prediction models.

    cd backend
    python -m ml.train

For each disease (diabetes, heart, parkinsons) this script:
  1. loads the CSV from ml/data
  2. compares 4 model families with 5-fold stratified cross-validation:
        Logistic Regression, SVM (RBF), Random Forest,
        Feed-forward Neural Network (sklearn MLPClassifier = "FNN")
  3. picks the best by ROC-AUC, evaluates it on a held-out 20 % test split
  4. saves  ml/artifacts/<disease>.joblib   (full sklearn Pipeline)
            ml/artifacts/<disease>.meta.json (features, ranges, medians, metrics)

The metadata drives the API (form schema, input validation, explanations),
so adding a new tabular disease = add a CSV + one entry in DISEASES below.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
ART_DIR = HERE / "artifacts"
SEED = 42

# label: human readable name, hint: help text shown in the UI form
DISEASES = {
    "diabetes": {
        "csv": "diabetes.csv",
        "target": "Outcome",
        "title": "Diabetes",
        "drop": [],
        # zeros in these columns mean "not measured" in the Pima dataset -> treat as missing
        "zero_is_missing": ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"],
        "fields": {
            "Pregnancies": ("Number of pregnancies", "Count (0 if not applicable)", "number"),
            "Glucose": ("Glucose level", "mg/dL, plasma glucose (2h OGTT)", "number"),
            "BloodPressure": ("Diastolic blood pressure", "mm Hg", "number"),
            "SkinThickness": ("Skin-fold thickness", "mm, triceps (leave 0 if unknown)", "number"),
            "Insulin": ("Insulin level", "mu U/ml, 2-hour serum (leave 0 if unknown)", "number"),
            "BMI": ("BMI", "kg/m²", "number"),
            "DiabetesPedigreeFunction": ("Diabetes pedigree function", "Family-history score, typically 0.08 - 2.5", "number"),
            "Age": ("Age", "Years", "number"),
        },
    },
    "heart": {
        "csv": "heart.csv",
        "target": "target",
        "title": "Heart disease",
        "drop": [],
        "zero_is_missing": [],
        "fields": {
            "age": ("Age", "Years", "number"),
            "sex": ("Sex", "1 = male, 0 = female", "select:1=Male,0=Female"),
            "cp": ("Chest pain type", "0-3", "select:0=Typical angina,1=Atypical angina,2=Non-anginal pain,3=Asymptomatic"),
            "trestbps": ("Resting blood pressure", "mm Hg", "number"),
            "chol": ("Cholesterol", "mg/dL", "number"),
            "fbs": ("Fasting blood sugar > 120 mg/dL", "1 = true, 0 = false", "select:1=Yes,0=No"),
            "restecg": ("Resting ECG result", "0-2", "select:0=Normal,1=ST-T abnormality,2=LV hypertrophy"),
            "thalach": ("Max heart rate achieved", "bpm", "number"),
            "exang": ("Exercise-induced angina", "1 = yes, 0 = no", "select:1=Yes,0=No"),
            "oldpeak": ("ST depression induced by exercise", "Relative to rest", "number"),
            "slope": ("Slope of peak exercise ST segment", "0-2", "select:0=Upsloping,1=Flat,2=Downsloping"),
            "ca": ("Major vessels coloured by fluoroscopy", "0-3 (4 appears in the dataset as missing)", "select:0=0,1=1,2=2,3=3,4=4"),
            "thal": ("Thalassemia", "Dataset coding 0-3", "select:0=Unknown,1=Normal,2=Fixed defect,3=Reversible defect"),
        },
    },
    "parkinsons": {
        "csv": "parkinsons.csv",
        "target": "status",
        "title": "Parkinson's disease",
        "drop": ["name"],
        "zero_is_missing": [],
        "fields": {},  # all 22 voice features: label == column name
    },
}

CANDIDATES = {
    "Logistic Regression": lambda: LogisticRegression(max_iter=2000, random_state=SEED),
    "SVM (RBF)": lambda: SVC(kernel="rbf", probability=True, random_state=SEED),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=250, random_state=SEED, n_jobs=1),
    "Feed-forward NN": lambda: MLPClassifier(
        hidden_layer_sizes=(32, 16), alpha=1e-2, max_iter=1500, early_stopping=False, random_state=SEED
    ),
}


def build_pipeline(model) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def load_xy(key: str, cfg: dict):
    df = pd.read_csv(DATA_DIR / cfg["csv"])
    df = df.drop(columns=cfg["drop"], errors="ignore")
    for col in cfg["zero_is_missing"]:
        df[col] = df[col].replace(0, np.nan)
    y = df[cfg["target"]].astype(int)
    X = df.drop(columns=[cfg["target"]]).astype(float)
    return X, y


def train_one(key: str, cfg: dict) -> dict:
    X, y = load_xy(key, cfg)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    leaderboard = []
    for name, make in CANDIDATES.items():
        scores = cross_val_score(build_pipeline(make()), X_tr, y_tr, cv=cv, scoring="roc_auc")
        leaderboard.append({"model": name, "cv_roc_auc": round(float(scores.mean()), 4), "cv_std": round(float(scores.std()), 4)})
        print(f"  [{key}] {name:<22} CV ROC-AUC = {scores.mean():.3f} (+/- {scores.std():.3f})")

    best_name = max(leaderboard, key=lambda r: r["cv_roc_auc"])["model"]
    pipe = build_pipeline(CANDIDATES[best_name]())
    pipe.fit(X_tr, y_tr)
    proba = pipe.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_te, pred)), 4),
        "precision": round(float(precision_score(y_te, pred)), 4),
        "recall": round(float(recall_score(y_te, pred)), 4),
        "f1": round(float(f1_score(y_te, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
        "test_size": int(len(y_te)),
    }
    print(f"  [{key}] BEST = {best_name} | held-out: {metrics}")

    # refit on ALL data for the shipped model (metrics above come from the held-out split)
    final = build_pipeline(CANDIDATES[best_name]())
    final.fit(X, y)

    features = []
    for col in X.columns:
        label, hint, kind = cfg["fields"].get(col, (col, "", "number"))
        features.append(
            {
                "name": col,
                "label": label,
                "hint": hint,
                "kind": kind,
                "min": float(X[col].min()),
                "max": float(X[col].max()),
                "median": float(X[col].median()),
            }
        )
    meta = {
        "key": key,
        "title": cfg["title"],
        "best_model": best_name,
        "leaderboard": leaderboard,
        "metrics": metrics,
        "n_samples": int(len(X)),
        "positive_rate": round(float(y.mean()), 4),
        "zero_is_missing": cfg["zero_is_missing"],
        "features": features,
    }
    ART_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, ART_DIR / f"{key}.joblib", compress=3)
    (ART_DIR / f"{key}.meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main(only: list[str] | None = None) -> None:
    for key, cfg in DISEASES.items():
        if only and key not in only:
            continue
        print(f"Training {key} ...")
        train_one(key, cfg)
    print("Done. Artifacts in", ART_DIR)


if __name__ == "__main__":
    main()
