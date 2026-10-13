# VitalAI - AI Health Platform

Multi-module health platform: **ML disease screening, an agentic AI health assistant, a community blood-donor network, and emergency / ambulance coordination.** Free to run and deploy (Vercel + Render + Neon).

> Evolved from the original Streamlit "Multiple Disease Prediction System" (kept in [`legacy/`](legacy/)).

| Module | Highlights |
|---|---|
| **Diagnosis** | Diabetes · Heart · Parkinson's. Four model families compared (LogReg, SVM, Random Forest, feed-forward NN), best chosen by cross-validation, per-prediction explanations |
| **AI Assistant** | LLM tool-calling agent + RAG knowledge base + deterministic emergency triage; works without an LLM key |
| **Blood Network** | Donors, requests, ABO/Rh compatibility matching, distance ranking, consent + self-delete |
| **Emergency** | Triage, nearby hospitals map (OpenStreetMap), ambulance requests with live status, verified operator registry |
| **Health Tools** | BMI, blood pressure, lab-report reader |

```
frontend/  React + Vite + Tailwind + Leaflet        -> Vercel
backend/   FastAPI + scikit-learn + SQLAlchemy      -> Render
           ml/ training pipeline, data, artifacts
           tests/ pytest suite (API + business rules)
docs/      SETUP_GUIDE.md (start here) · ARCHITECTURE.md
legacy/    original Streamlit app
render.yaml · .env.example · .github/workflows/ci.yml
```

## Quick start
```bash
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt && uvicorn app.main:app --reload   # http://localhost:8000/docs

cd frontend && npm install && cp .env.example .env.local && npm run dev   # http://localhost:5173
```
Full local + deployment walkthrough: **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** · Design, results and roadmap: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Disclaimer
Educational screening tool, **not a medical device**; it does not diagnose or replace a doctor. In an emergency call your local ambulance number (112 / 108 in India).
