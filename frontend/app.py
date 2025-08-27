import streamlit as st
import requests
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd

# Load environment variables
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/mixtral-8x7b"
SERPER_API_URL = "https://serper.dev/search"

# Initialize SQLite database
db_path = os.environ.get("DB_PATH", "data/db.sqlite")
os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure data/ exists
engine = create_engine(f'sqlite:///{db_path}')
Base = declarative_base()

class PriceEstimate(Base):
    __tablename__ = 'price_estimates'
    id = Column(Integer, primary_key=True)
    query = Column(String)
    product_service = Column(String)
    estimated_price = Column(Float)
    source = Column(String)
    timestamp = Column(DateTime)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Function to query Hugging Face
def parse_query_with_hf(query):
    if not HUGGINGFACE_TOKEN:
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
    except:
        pass
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
    except:
        pass
    return "Price not found"

# Streamlit app
st.title("Anything Anywhere Cost Estimator")

# User input
query = st.text_input("Enter product or service (e.g., 'iPhone 14 price in India', 'flight from Mumbai to Delhi')")

if st.button("Get Price Estimate"):
    if query:
        parsed_query = parse_query_with_hf(query)
        st.write(f"Parsed Query: {parsed_query}")

        session = Session()
        cached_result = session.query(PriceEstimate).filter_by(query=query).first()
        if cached_result:
            st.success(f"Cached Result: {cached_result.product_service} - ₹{cached_result.estimated_price} (Source: {cached_result.source})")
        else:
            price_info = get_price_from_serper(parsed_query)
            st.write(f"Price Info: {price_info}")

            estimated_price = 0.0  # Replace with actual price parsing
            new_estimate = PriceEstimate(
                query=query,
                product_service=parsed_query,
                estimated_price=estimated_price,
                source="Serper API",
                timestamp=datetime.now()
            )
            session.add(new_estimate)
            session.commit()
            st.success("Result cached in database!")
        session.close()
    else:
        st.error("Please enter a query.")

if st.button("Show Cached Estimates"):
    session = Session()
    estimates = session.query(PriceEstimate).all()
    if estimates:
        df = pd.DataFrame([(e.query, e.product_service, e.estimated_price, e.source, e.timestamp) for e in estimates],
                          columns=["Query", "Product/Service", "Price (₹)", "Source", "Timestamp"])
        st.dataframe(df)
    else:
        st.write("No cached estimates found.")
    session.close()
