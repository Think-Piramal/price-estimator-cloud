import streamlit as st
import requests
import os

# Load environment variables
HUGGINGFACE_TOKEN = "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"
SERPER_API_KEY = "3028b70cd2013ff71ec70dd689fe94c6dade03a0"
HF_API_URL = "https://api-inference.huggingface.co/models/mixtral-8x7b"
SERPER_API_URL = "https://serper.dev/search"

# Function to query Hugging Face for query parsing
def parse_query_with_hf(query):
    if not HUGGINGFACE_TOKEN:
        st.warning("Hugging Face API key missing")
        return query
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    payload = {
        "inputs": f"Extract the product or service from this query: {query}",
        "parameters": {"max_new_tokens": 50}
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()[0]["generated_text"].strip()
    except Exception as e:
        st.warning(f"Hugging Face API error: {e}")
        return query
    return query

# Function to get price from Serper
def get_price_from_serper(query):
    if not SERPER_API_KEY:
        return "Serper API key missing"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"q": f"{query} price"}
    try:
        response = requests.post(SERPER_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            for result in data.get("organic", []):
                snippet = result.get("snippet", "")
                if "price" in snippet.lower():
                    return snippet
        return "Price not found"
    except Exception as e:
        return f"Serper API error: {e}"

# Streamlit app
st.title("Anything Anywhere Cost Estimator")

# User input
query = st.text_input("Enter product or service (e.g., 'iPhone 14 price in India', 'flight from Mumbai to Delhi')")

if st.button("Get Price Estimate"):
    if query:
        # Parse query using Hugging Face
        parsed_query = parse_query_with_hf(query)
        st.write(f"Parsed Query: {parsed_query}")

        # Fetch price from Serper
        price_info = get_price_from_serper(parsed_query)
        st.write(f"Price Info: {price_info}")
    else:
        st.error("Please enter a query.")
