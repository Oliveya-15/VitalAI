---
title: "VitalAI - Setup & Deployment Guide"
subtitle: "Run it locally, then deploy for free on Neon + Render + Vercel"
---

# 0. What you are deploying

| Part | Technology | Hosted on | Cost |
|---|---|---|---|
| Frontend (website) | React + Vite + Tailwind | **Vercel** | Free |
| Backend (API + ML + AI agent) | FastAPI + scikit-learn | **Render** (web service) | Free |
| Database | PostgreSQL | **Neon** | Free |
| LLM for the AI assistant (optional) | Llama via Groq API | Groq | Free tier |
| Maps / hospitals | OpenStreetMap + Overpass | - | Free, no key |

Accounts you need: **GitHub, Neon, Render, Vercel** (all free, sign in with GitHub). **Groq** is optional - the assistant works without it in knowledge-base mode.

API keys / secrets you will create:

| Name | Where you get it | Required? |
|---|---|---|
| `DATABASE_URL` | Neon dashboard, "Connection string" | **Yes** (production) |
| `ADMIN_KEY` | You invent it (random string, see step 3) | **Yes** (to verify ambulances) |
| `LLM_API_KEY` | console.groq.com, "API Keys" | Optional |
| `CORS_ORIGINS` | Your Vercel URL (known after step 5) | **Yes** |
| `VITE_API_BASE_URL` | Your Render URL + `/api/v1` | **Yes** (Vercel) |

---

# 1. Run it on your computer first (10 minutes)

You need **Python 3.11+** and **Node.js 18+**.

**Backend** (terminal 1):

```
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.seed              # optional: adds clearly-labelled DEMO donors/ambulance
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs - you should see the interactive API. No database setup is needed locally: it uses a SQLite file.

**Frontend** (terminal 2):

```
cd frontend
npm install
copy .env.example .env.local    # Mac/Linux: cp .env.example .env.local
npm run dev
```

Open http://localhost:5173.

**Run the tests** (optional): `cd backend && pip install -r requirements-dev.txt && python -m pytest`

**Retrain the ML models** (optional): `cd backend && python -m ml.train` (about 1 minute).

---

# 2. Push the project to GitHub

From the project root (the folder that contains `backend/`, `frontend/`, `render.yaml`):

```
git add .
git commit -m "VitalAI: full-stack health platform"
git push origin main
```

Your old Streamlit app is kept in the `legacy/` folder.

---

# 3. Create the database on Neon

1. Go to **neon.tech** and sign in with GitHub.
2. Create a project (any name, choose a region near your users, e.g. Singapore for India).
3. On the project dashboard click **Connect** and copy the **connection string**. It looks like  
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`
4. Keep it safe - this is your `DATABASE_URL`. The backend creates all tables automatically on first start.

Also generate an admin key (any long random string). Easiest:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Note: Neon's free database pauses when idle and wakes in about a second on the next request. This is normal.

> Why Neon and not Render's free database? Render's free Postgres expires 30 days after creation. Neon's free tier does not.

---

# 4. (Optional) Get a free LLM key from Groq

1. Go to **console.groq.com**, sign in, open **API Keys**, click **Create API Key**, copy it.
2. This becomes `LLM_API_KEY`. Model names change over time: check the model list in the Groq console and update `LLM_MODEL` if `llama-3.3-70b-versatile` is no longer offered.
3. Skip this step to run the assistant in knowledge-base mode (still works, answers from the built-in medical knowledge base, and emergency detection always works either way).

Any OpenAI-compatible provider also works (Google Gemini's OpenAI-compatible endpoint, OpenRouter, a local Ollama): change `LLM_API_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY`.

---

# 5. Deploy the backend on Render

**Option A - Blueprint (fastest)**

1. render.com, **New +**, **Blueprint**, connect your GitHub repo. Render reads `render.yaml`.
2. When asked, fill in: `DATABASE_URL` (Neon string), `ADMIN_KEY`, `LLM_API_KEY` (or leave empty), `CORS_ORIGINS` (type `http://localhost:5173` for now - you will update it in step 7).
3. Click **Apply**. The first build takes a few minutes.

**Option B - Manual**

1. **New +**, **Web Service**, pick the repo.
2. Settings: **Root Directory** `backend` · **Runtime** Python · **Build Command** `pip install -r requirements.txt` · **Start Command** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` · **Instance type** Free · **Health Check Path** `/api/v1/health`.
3. Add environment variables from the table in section 0, plus `PYTHON_VERSION` = `3.12.7` and `ENVIRONMENT` = `production`.

When it is live, open `https://YOUR-SERVICE.onrender.com/api/v1/health`. You should see `{"status":"ok", ...}`. Also check `/docs`.

---

# 6. Deploy the frontend on Vercel

1. vercel.com, **Add New**, **Project**, import the same repo.
2. **Root Directory**: `frontend` (important). Framework preset: Vite (auto-detected).
3. **Environment Variables**: add `VITE_API_BASE_URL` = `https://YOUR-SERVICE.onrender.com/api/v1` (no trailing slash).
4. **Deploy**. You get a URL like `https://vitalai-xyz.vercel.app`.

---

# 7. Connect them (CORS)

Go back to Render, your service, **Environment**, and set `CORS_ORIGINS` to your Vercel URL, for example `https://vitalai-xyz.vercel.app` (several URLs can be separated by commas). Save - Render redeploys. Any `*.vercel.app` URL is already allowed by default, so previews work too.

Open your Vercel site: the sidebar shows "Server online" when everything is connected.

---

# 8. Stop the "waking up from sleep" problem

Render's free web services **sleep after 15 minutes without traffic** and take about a minute to wake. Streamlit Cloud had the same problem. Three layers of defence are built in or recommended:

1. **Built in:** the website pings the server the moment it opens and every 10 minutes while a tab is open, and shows "Waking server…". API calls wait up to 70 seconds instead of failing.
2. **Free uptime pinger (recommended):** create a free account at **uptimerobot.com** (or cron-job.org), add an HTTP monitor for `https://YOUR-SERVICE.onrender.com/api/v1/ping` every 5 minutes. This keeps the backend awake around the clock.
3. **Know the limit:** Render gives free services about **750 instance-hours per month shared across your whole workspace**. One always-awake service uses about 744 hours. If you also keep your NeceCity backend awake in the same Render account, you will run out. Either keep only one project awake permanently, or only ping during demo/viva periods. The only fully reliable fix is a paid instance (about $7/month).

---

# 9. Verify ambulances (admin)

Ambulance operators register on the Emergency page, but they stay hidden until you verify them. Open `https://YOUR-SERVICE.onrender.com/docs`, find `GET /api/v1/emergency/admin/ambulances/pending`, click "Try it out", enter your `ADMIN_KEY` in the `x-admin-key` field and execute. Then call `POST /api/v1/emergency/admin/ambulances/{aid}/verify` the same way with the ambulance id.

Dispatchers update a request's status with `PATCH /api/v1/emergency/ambulance-requests/{id}/status` (same header). The requester's page updates automatically.

---

# 10. Troubleshooting

| Symptom | Fix |
|---|---|
| Sidebar says "Server unreachable" | Check `VITE_API_BASE_URL` on Vercel (must end with `/api/v1`), then **redeploy** the frontend (env vars apply at build time). |
| Browser console: CORS error | `CORS_ORIGINS` on Render must contain your exact Vercel URL (no trailing slash). |
| First request very slow | Render waking up (normal, see section 8). |
| Render build fails on scikit-learn | Make sure `PYTHON_VERSION` is `3.12.7` and Root Directory is `backend`. |
| Assistant says "Knowledge-base mode" | `LLM_API_KEY` is empty or invalid - check Render logs for "LLM error". |
| "Map data service is busy" | The free Overpass service is rate limited - retry in a minute. |
| Database errors on Render | Confirm the Neon string is complete and ends with `?sslmode=require`. |
| Models fail to load | The server automatically retrains them from the CSVs on first start (about 1 minute). |

# 11. Safety and privacy notes (important for a health project)

- This is a **screening and coordination tool, not a medical device**. The UI states this everywhere. Keep it that way.
- Donor phone numbers are shown only to people who post a blood request, donors must consent, and can delete their data themselves (Blood Network, Manage tab).
- Diagnosis history is stored against a random browser ID, with no names or accounts.
- Never present the demo "DEMO" donors or ambulances as real services.
- Before real-world use you would need: user accounts and verification of donors, a privacy policy, data-protection compliance, and medical review of the models and knowledge base.
