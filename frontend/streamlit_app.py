import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL_DEFAULT = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000/generate_recipe")

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Recipe Agent RAG",
    layout="centered",
    initial_sidebar_state="expanded"  # keeps sidebar open on load
)

# ----------------------------
# Dark theme styling + hide Streamlit toolbar/settings
# ----------------------------
st.markdown(
    """
    <style>
        /* App background */
        .stApp {
            background: #0f1115;
            color: #e8eaed;
        }

        /* Main container */
        .main .block-container {
            max-width: 850px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* Title / subtitle */
        .app-title {
            font-size: 2rem;
            font-weight: 700;
            color: #f5f5f5;
            margin-bottom: 0.15rem;
        }

        .app-subtitle {
            color: #b0b6be;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        /* Chat bubble feel */
        [data-testid="stChatMessage"] {
            background: #161a22;
            border: 1px solid #232936;
            border-radius: 14px;
            padding: 0.25rem 0.5rem;
            margin-bottom: 0.75rem;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #12151c;
            border-right: 1px solid #202532;
        }

        section[data-testid="stSidebar"] * {
            color: #e8eaed !important;
        }

        /* Buttons */
        .stButton > button {
            background: #252b38;
            color: #f1f3f5;
            border: 1px solid #3a4252;
            border-radius: 10px;
        }

        .stButton > button:hover {
            border-color: #6b7280;
            background: #2d3442;
        }

        /* Selectbox / inputs */
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #171b23 !important;
            color: #f3f4f6 !important;
            border: 1px solid #2a3140 !important;
            border-radius: 10px !important;
        }

        /* Chat input */
        [data-testid="stChatInput"] {
            background: #0f1115;
        }

        [data-testid="stChatInput"] textarea {
            background: #171b23 !important;
            color: #f3f4f6 !important;
            border: 1px solid #2a3140 !important;
            border-radius: 12px !important;
        }

        /* Expander */
        .streamlit-expanderHeader {
            color: #e8eaed !important;
        }

        /* Code blocks */
        pre, code {
            border-radius: 10px !important;
        }

    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_url" not in st.session_state:
    st.session_state.api_url = API_URL_DEFAULT

# ----------------------------
# Sidebar (Clear chat + Quick prompts only)
# ----------------------------
with st.sidebar:
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Quick prompts")

    quick = st.selectbox(
        "Choose one",
        [
            "",
            "rice, chicken, garlic, onion",
            "eggs, tomato, spinach, cheese",
            "pasta, mushrooms, cream, garlic",
            "beans, corn, avocado, lime",
        ],
        index=0,
    )

    if st.button("Send quick prompt", use_container_width=True) and quick:
        st.session_state.messages.append(
            {"role": "user", "content": f"Ingredients: {quick}"}
        )
        st.rerun()

# ----------------------------
# Header
# ----------------------------
st.markdown('<div class="app-title">Recipe Assistant Chatbot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Tell me what ingredients you have, and I’ll suggest a recipe with steps and sources.</div>',
    unsafe_allow_html=True,
)


# ----------------------------
# Render chat history
# ----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ----------------------------
# Chat input
# ----------------------------
user_input = st.chat_input("Type ingredients (e.g., chicken, rice, garlic)...")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": f"Ingredients: {user_input}"}
    )
    st.rerun()

# ----------------------------
# Generate recipe response for latest user message
# ----------------------------
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    latest_text = st.session_state.messages[-1]["content"]
    ingredients = latest_text.replace("Ingredients:", "").strip()

    with st.chat_message("assistant"):
        with st.spinner("Cooking up a recipe..."):
            try:
                response = requests.post(
                    st.session_state.api_url,
                    json={"ingredients": ingredients},
                    timeout=45
                )

                if response.status_code == 200:
                    data = response.json()

                    recipe_text = (
                        data.get("recipe")
                        or data.get("answer")
                        or data.get("result")
                        or "No recipe returned."
                    )

                    st.markdown(recipe_text)

                    # Optional details if backend returns them
                    if any(k in data for k in ["sources", "context", "retrieval_query"]):
                        with st.expander("Details"):
                            if "sources" in data:
                                st.markdown("**Sources**")
                                if isinstance(data["sources"], list):
                                    for s in data["sources"]:
                                        st.markdown(f"- {s}")
                                else:
                                    st.write(data["sources"])

                            if "retrieval_query" in data:
                                st.markdown("**Retrieval query**")
                                st.code(str(data["retrieval_query"]))

                            if "context" in data:
                                st.markdown("**Context (trimmed)**")
                                st.code(str(data["context"])[:3000])

                    assistant_msg = recipe_text

                else:
                    assistant_msg = f"❌ Error {response.status_code}\n\n{response.text}"
                    st.error(assistant_msg)

            except requests.exceptions.ConnectionError:
                assistant_msg = (
                    "❌ Could not connect to the FastAPI backend.\n\n"
                    "Make sure your backend is running at:\n"
                    f"`{st.session_state.api_url}`"
                )
                st.error(assistant_msg)

            except requests.exceptions.Timeout:
                assistant_msg = "⏳ The request timed out. The backend took too long to respond."
                st.error(assistant_msg)

            except requests.exceptions.RequestException as e:
                assistant_msg = f"❌ Request failed: {e}"
                st.error(assistant_msg)

            except Exception as e:
                assistant_msg = f"❌ Unexpected error: {e}"
                st.error(assistant_msg)

    st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
    st.rerun()