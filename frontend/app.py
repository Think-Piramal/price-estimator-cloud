import os, requests, pandas as pd, streamlit as st
from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Anything Anywhere - Price Estimator", page_icon="🪙")
st.title("🪙 Anything Anywhere - Price Estimator (cloud-ready)")

with st.form("form"):
    q = st.text_input("What do you want the price for?", placeholder="e.g., iPhone 15 128GB in Hyderabad")
    loc = st.text_input("Location (optional)", placeholder="e.g., Hyderabad")
    max_s = st.slider("Max sources to search", 3, 12, 6)
    submitted = st.form_submit_button("Estimate")

if submitted:
    if not q or len(q) < 3:
        st.error("Please enter a valid query")
    else:
        try:
            r = requests.post(f"{API_URL}/estimate", json={"query": q, "location": loc or None, "max_sources": max_s}, timeout=120)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()
        st.subheader("Baseline (INR)")
        if data.get("baseline_inr"):
            b = data["baseline_inr"]
            st.metric("Median", f"₹ {b['median']:,.0f}")
            st.write(f"Range: ₹ {b['low']:,.0f} – ₹ {b['high']:,.0f} (trimmed mean: ₹ {b['mean']:,.0f})")
        else:
            st.warning(data.get("notes", "No baseline found"))
        st.subheader("Observations")
        obs = pd.DataFrame(data.get("observations", []))
        if not obs.empty:
            st.dataframe(obs)
        else:
            st.info("No observations to display.")
st.markdown("---")
st.caption("Deploy notes: set API_URL in Streamlit secrets or env to your deployed API.")
