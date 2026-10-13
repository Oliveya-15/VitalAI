# VitalAI - Plan, Architecture & Roadmap

## 1. Vision
Turn the 3-model Streamlit demo into a **multi-module health platform** that solves real, urgent needs (screening, guidance, blood, ambulance) using modern AI - while staying 100% deployable on free tiers.

## 2. Modules

| # | Module | What it does | AI / tech used | Status |
|---|---|---|---|---|
| 1 | **Diagnosis** | Diabetes, heart disease, Parkinson's screening; probability, risk level, "why" explanation, saved history | scikit-learn: Logistic Regression, SVM, Random Forest, **Feed-forward NN (MLP)** compared by 5-fold CV; best auto-selected; occlusion-based explainability | Built |
| 2 | **AI Health Assistant** | Chat for symptoms, first aid, disease info; can run the ML models and look up blood donors | **LLM + agentic tool-calling loop**, **RAG** (TF-IDF retrieval over a curated knowledge base, NLP), deterministic safety triage, graceful no-LLM fallback | Built |
| 3 | **Blood Network** | Donor registry, blood requests, urgency board, compatibility matching | Rule + distance ranking (haversine), ABO/Rh compatibility, donation rest-period eligibility, consent and self-delete | Built |
| 4 | **Emergency** | Symptom triage, emergency numbers, nearby hospitals/clinics/pharmacies/blood banks on a map, ambulance request + status tracker, ambulance operator registry with admin verification | Rule-based red-flag triage, OpenStreetMap Overpass, Leaflet | Built |
| 5 | **Health Tools** | BMI, blood-pressure category, lab-report reader | Deterministic standards-based logic, regex NLP parsing | Built |
| 6 | **My History** | Past screenings per browser | PostgreSQL | Built |

## 3. Architecture

```
Browser (React + Tailwind + Leaflet)  ---- Vercel
        | HTTPS / JSON
        v
FastAPI backend ---------------------- Render (free web service)
  routers/   diagnosis, assistant+tools, blood, emergency, system
  services/  ml_service (load, validate, predict, explain)
             agent (safety triage -> LLM tool loop -> rule fallback)
             knowledge (TF-IDF RAG), triage, blood_service, geo, health_tools, llm_service
  ml/        train.py + CSVs + versioned artifacts (.joblib + .meta.json)
        |                                   |
        v                                   v
PostgreSQL (Neon, free)             Groq LLM API (optional, free tier)
                                    OpenStreetMap Overpass (free, no key)
```

Key design decisions

- **Metadata-driven forms:** each model ships a `.meta.json` (fields, ranges, medians, metrics). The UI form, validation and explanations are generated from it, so adding a new tabular disease means adding a CSV and one config entry in `ml/train.py`.
- **Safety first:** emergency detection is deterministic code, never an LLM. It runs before the LLM on every chat message, so life-threatening messages get an instant answer even if the LLM is down or hallucinates.
- **Graceful degradation (same pattern as NeceCity):** no LLM key, provider down, or Overpass busy never crash the app.
- **Free-tier realism:** lightweight sklearn models (fit in 512 MB RAM), SQLite locally / Neon in production, keep-alive strategy for Render sleep.
- **Models are retrained** rather than reused from the old pickles. The old files came from scikit-learn 1.3.2 and unpickling across versions is unsafe. Retraining also fixed a data issue: zeros in glucose, blood pressure, skin thickness, insulin and BMI mean "not measured" in the Pima dataset and are now treated as missing values and imputed.

## 4. Model results (held-out 20 % test split, honest numbers)

| Disease | Best model (CV ROC-AUC) | Accuracy | Recall | ROC-AUC (test) |
|---|---|---|---|---|
| Diabetes (768 rows) | Logistic Regression (0.84) | 70.8 % | 50.0 % | 0.81 |
| Heart (303 rows) | Logistic Regression (0.89) | 80.3 % | 90.9 % | 0.87 |
| Parkinson's (195 rows) | Feed-forward NN (0.97) | 94.9 % | 96.6 % | 0.99 |

These are small public datasets: treat results as educational screening estimates. The diabetes dataset in particular has a ceiling around 75-80 % accuracy. The Parkinson's dataset has several recordings per person, so the test score is probably optimistic. These caveats are part of the project's honesty and make good viva material.

## 5. Roadmap (not built yet - the architecture is ready for these)

| Phase | Feature | Technology | Notes |
|---|---|---|---|
| 2 | **Chest X-ray / skin-lesion screening** | **CNN** (transfer learning, e.g. MobileNetV2 / EfficientNet) trained on Colab with a public Kaggle dataset, exported to **ONNX**, served with onnxruntime (same trick as NeceCity) | Needs a labelled dataset + Colab training; keeps RAM low on free hosting |
| 2 | **Vitals forecasting** | **RNN / LSTM** on glucose or heart-rate time series (PyTorch -> ONNX) | Needs a time-series dataset or user-logged readings |
| 2 | **Semantic RAG** | Sentence embeddings + pgvector on Neon replacing TF-IDF | Larger, cited knowledge base (WHO / NHS guidelines) |
| 2 | **User accounts** | JWT auth, donor verification, per-user records | Needed before any real-world use |
| 3 | **Multi-agent workflow** | LangGraph (triage agent, records agent, scheduling agent) | Builds on the existing tool-calling loop |
| 3 | **Notifications** | WhatsApp / SMS alerts to matched donors | Provider costs may apply |
| 3 | **Voice + multilingual** | Browser speech APIs, Hindi / Bengali UI | Accessibility |
| 3 | **Report OCR** | Tesseract / vision LLM to read photographed lab reports | Heavier compute |
| 3 | **PWA / mobile** | Installable app, offline emergency numbers | |

## 6. Suggested viva talking points
1. Why compare four model families and choose by cross-validation rather than defaulting to one.
2. Why safety triage is rule-based, not LLM-based.
3. Explainability: occlusion analysis works for any model (SVM, MLP) without special libraries.
4. ABO/Rh compatibility and the donor rest-period rule.
5. Limitations: dataset size, no clinical validation, anonymous data, not a medical device.
