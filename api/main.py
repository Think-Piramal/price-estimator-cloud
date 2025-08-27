import os, re, statistics, time
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import trafilatura
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "google/flan-t5-small")
SERPER_KEY = os.getenv("SERPER_API_KEY")
FX = {"INR":1.0, "USD":84.0, "EUR":92.0, "GBP":108.0}

if not DATABASE_URL:
    raise RuntimeError("Please set DATABASE_URL env var (Supabase/Railway)")

engine = create_engine(DATABASE_URL, poolclass=NullPool)

app = FastAPI(title="Price Estimator (cloud-ready)", version="0.2.0")

CATEGORY_KEYWORDS = {
    "grocery":["grocery","vegetable","vegetables","fruit","bigbasket","jiomart"],
    "product":["price","price of","buy","amazon","flipkart","product"],
    "electronics":["iphone","mobile","laptop","electronics"],
    "travel":["flight","hotel","itinerary","train","bus"],
    "real_estate_rent":["rent","2bhk","1bhk","rent in"],
    "real_estate_sale":["buy apartment","sell","for sale"],
    "healthcare":["hospital","surgery","knee","practo","doctor"],
    "services_general":["plumbing","carpenter","service charge","fee"],
    "education":["tuition","course","fee"],
    "transport":["taxi","cab","ola","uber","fare"],
    "fuel":["petrol","diesel","fuel price"]
}

def guess_category(q: str) -> str:
    ql = q.lower()
    for k, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in ql:
                return k
    return "other"

def extract_prices_from_text(text: str) -> List[Dict[str,Any]]:
    patterns = [
        r"(₹|Rs\.?\s*|INR\s*)?(\d{1,3}(?:[, ]\d{2,3})+(?:\.\d{1,2})?)",
        r"(USD|\$|EUR|€|GBP|£)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(INR|₹|Rs\.?|USD|€|EUR|GBP|£)"
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            g = m.groups()
            cur = None
            amt = None
            for token in g:
                if not token: continue
                t = token.strip().replace(",", "")
                if t in ["₹","Rs","INR","$","USD","€","EUR","£","GBP"]:
                    cur = t.replace(".", "")
                else:
                    try:
                        amt = float(t)
                    except:
                        pass
            if amt:
                found.append({"currency": cur or "INR", "amount": amt})
    return found

async def hf_classify(query: str) -> str:
    global HF_TOKEN, HF_MODEL
    if not HF_TOKEN:
        return guess_category(query)
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    prompt = f"Classify this short price query into one word category (grocery, product, electronics, travel, real_estate_rent, real_estate_sale, healthcare, services_general, education, transport, fuel, other):\n{query}\nCategory:"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Accept":"application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json={"inputs": prompt})
        if r.status_code != 200:
            return guess_category(query)
        out = r.json()
        txt = ""
        if isinstance(out, dict) and out.get("error"):
            return guess_category(query)
        if isinstance(out, list):
            try:
                txt = out[0].get("generated_text","")
            except:
                txt = str(out)
        elif isinstance(out, dict):
            txt = out.get("generated_text") or out.get("text") or str(out)
        else:
            txt = str(out)
        txt = txt.lower()
        for cat in ["grocery","product","electronics","travel","real_estate_rent","real_estate_sale","healthcare","services_general","education","transport","fuel","other"]:
            if cat in txt:
                return cat
    return guess_category(query)

async def serper_search(q: str, num:int=6) -> List[str]:
    if not SERPER_KEY:
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type":"application/json"}
    payload = {"q": q, "num": num}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            return []
        data = r.json()
        links = []
        for r in data.get("organic", [])[:num]:
            u = r.get("link")
            if u:
                links.append(u)
        return links

async def ddg_search(q: str, num:int=6) -> List[str]:
    url = "https://duckduckgo.com/html/"
    params = {"q": q}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, data=params)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        links = []
        for a in soup.select("a.result__a")[:num]:
            href = a.get("href")
            if href:
                links.append(href)
        if not links:
            for a in soup.select("a")[:num*3]:
                href = a.get("href")
                if href and href.startswith("http"):
                    links.append(href)
        return links[:num]

async def fetch_text(url:str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent":"PriceEstimatorBot"}) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
        text = trafilatura.extract(html) or BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        return text
    except Exception:
        return ""

def to_inr(amount:float, currency:str) -> float:
    if not currency:
        return amount
    cur = currency.upper().replace("₹","INR").replace("RS","INR")
    return amount * FX.get(cur, 1.0)

class EstimateRequest(BaseModel):
    query: str
    location: Optional[str] = None
    max_sources: int = 6

class EstimateResponse(BaseModel):
    query: str
    location: Optional[str]
    category: str
    baseline_inr: Optional[dict]
    observations: List[dict]
    notes: Optional[str]
    generated_at: datetime

@app.get("/health")
async def health():
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}

@app.post("/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest):
    if not req.query or len(req.query) < 3:
        raise HTTPException(status_code=400, detail="Query too short")
    cat = await hf_classify(req.query)
    with engine.begin() as conn:
        res = conn.execute(text("INSERT INTO queries (query_text, location, category) VALUES (:q,:loc,:cat) RETURNING id"),
                           {"q": req.query, "loc": req.location, "cat": cat})
        qid = res.scalar_one()
    q_mod = req.query + (" in " + req.location if req.location else "")
    q_mod += " price cost"
    links = await serper_search(q_mod, num=req.max_sources)
    if not links:
        links = await ddg_search(q_mod, num=req.max_sources)
    observations = []
    for url in links:
        t = await fetch_text(url)
        if not t:
            continue
        prices = extract_prices_from_text(t[:200000])
        for p in prices:
            amt = p.get("amount")
            cur = p.get("currency") or "INR"
            amt_inr = to_inr(amt, cur)
            observations.append({"source_url": url, "source_title": "", "currency": cur, "amount": amt, "amount_in_inr": amt_inr})
    with engine.begin() as conn:
        for obs in observations[:200]:
            conn.execute(text(
                "INSERT INTO price_observations (query_id, source_url, source_title, currency, amount, amount_in_inr) VALUES (:qid,:u,:t,:cur,:amt,:inr)"
            ), {"qid": qid, "u": obs["source_url"], "t": obs["source_title"], "cur": obs["currency"], "amt": obs["amount"], "inr": obs["amount_in_inr"]})
    amounts = [o["amount_in_inr"] for o in observations if o["amount_in_inr"] and o["amount_in_inr"]>0]
    baseline = None
    notes = None
    if amounts:
        amounts_sorted = sorted(amounts)
        n = len(amounts_sorted)
        median = float(statistics.median(amounts_sorted))
        k = max(1, int(0.2*n))
        trimmed = amounts_sorted[k:n-k] if n>2*k else amounts_sorted
        mean = float(sum(trimmed)/len(trimmed))
        low = float(amounts_sorted[max(0,int(0.25*n)-1)])
        high = float(amounts_sorted[min(n-1,int(0.75*n))])
        baseline = {"low": low, "median": median, "mean": mean, "high": high}
    else:
        notes = "No price observations found. Try adding a city or using a more specific query."
    return EstimateResponse(query=req.query, location=req.location, category=cat, baseline_inr=baseline, observations=observations[:50], notes=notes, generated_at=datetime.utcnow())
