import streamlit as st
import requests
import os

from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000/generate_recipe")

st.title(" Recipe Agent RAG")
st.write("Enter your ingredients and get a recipe with sources!")

ingredients = st.text_input("Ingredients (comma separated):")

if st.button("Generate Recipe"):
    if not ingredients.strip():
        st.warning("Please enter some ingredients!")
    else:
        response = requests.post(API_URL, json={"ingredients": ingredients})
        if response.status_code == 200:
            st.markdown(response.json()["recipe"])
        else:
            st.error(f"Error: {response.status_code}")
