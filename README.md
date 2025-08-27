# Anything Anywhere Cost Estimator — Cloud-ready (Free-tier friendly)

This repo is a cloud-ready refactor of the open-source MVP, adapted to run on **free tiers**:
- Frontend: **Streamlit Community Cloud**
- Backend API: **Render / Railway / Fly** (free tiers)
- Database: **Supabase** (free Postgres) or Railway Postgres (free)
- LLM: **Hugging Face Inference API** (free tier) — `HF_TOKEN` required
- Search: **Serper.dev** (100 free searches/day) or **DuckDuckGo** fallback (no key)

**Download:** this zip / push to GitHub and connect the services.

## Quick deploy (high level)

1. Create a GitHub repo and push this project.
2. Create a Supabase project → copy `DATABASE_URL`.
3. Get a Hugging Face token (free): https://huggingface.co/settings/tokens → `HF_TOKEN`.
4. (Optional) Create Serper account for better search: https://serper.dev → `SERPER_API_KEY`.
5. Deploy the API to Render (or Railway):
   - Set environment variables: `DATABASE_URL`, `HF_TOKEN`, `HF_MODEL` (optional), `SERPER_API_KEY` (optional).
   - Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
6. Deploy frontend to Streamlit Community Cloud:
   - Set Streamlit secret `API_URL` to your deployed API URL.
   - Link repo and launch.

## What changed from the "self-host" scaffold

- Removed Ollama and SearXNG heavy containers.
- Backend now uses Hugging Face Inference API for classification/LLM tasks.
- Search uses Serper API when available, otherwise DuckDuckGo HTML scrape fallback.
- Database uses any `DATABASE_URL` env var (Supabase/Railway).
- Streamlit frontend calls the hosted API.

## Files
- /api - FastAPI backend
- /frontend - Streamlit UI
- README.md (this file)

Read on for Deploy & Production tips inside `/DEPLOY.md`.
