from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st, os

def get_llm(temperature: float = 0):
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key not found in secrets or ENV.")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=temperature,
    )
