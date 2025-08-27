# Deployment & Productionization (Free-tier focused) — Detailed

## 1. Supabase (Postgres) — Free database
1. Sign up at https://supabase.com and create a new project.
2. In **Settings → Database → Connection string**, copy the `postgres://...` URL.
3. In the Supabase SQL editor, run the SQL in `api/db_init.sql` to create tables.

## 2. Hugging Face
1. Get a token at https://huggingface.co/settings/tokens (Free).
2. Recommended model: `google/flan-t5-small` or any small HF model for classification.
3. Set `HF_TOKEN` in Render / Railway env vars.

## 3. Serper.dev (optional but recommended)
1. Sign up at https://serper.dev and get `SERPER_API_KEY`.
2. Add as env var `SERPER_API_KEY`. If missing, API falls back to DuckDuckGo.

## 4. Render / Railway deploy (Backend)
- Create a new Web Service (Python).
- Build command: `pip install -r api/requirements.txt`
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Set env vars: `DATABASE_URL`, `HF_TOKEN`, (optional) `HF_MODEL`, `SERPER_API_KEY`
- After deploy, copy the service URL (e.g. https://price-api.onrender.com)

## 5. Streamlit Community Cloud (Frontend)
- Connect your GitHub repo and add secret:
  - `API_URL = "https://price-api.onrender.com"`
- Deploy; Streamlit will provide a shareable link.

## 6. Notes on limits & production readiness
- Hugging Face Inference has rate limits on free tier — consider caching popular queries.
- Serper.dev free tier ~100 searches/day.
- Supabase free tier has query/row limits; create pruning jobs for old data.
- Add caching (Redis or simple DB cache) to avoid repeated HF/search calls.
- Add API key / rate-limiting for public use.

