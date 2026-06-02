import streamlit as st
import requests
import json
import time

# --- Configuration ---
st.set_page_config(
    page_title="O-RAN Digital Twin AI",
    page_icon="🗼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# API Endpoint configuration
API_URL = "http://rag-core-api:8000/api/v1/query"

# --- Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00D2FF;
        margin-bottom: 0px;
        text-align: center;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #888888;
        margin-bottom: 30px;
        text-align: center;
    }
    .source-box {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 8px;
        border-left: 4px solid #00D2FF;
        margin-top: 10px;
        font-size: 0.85rem;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="main-title">🗼 O-RAN Digital Twin Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intelligent Context-Aware RAG Engine</div>', unsafe_allow_html=True)

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Chat Interface ---
# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("View Context Sources"):
                st.markdown(f'<div class="source-box">{message["sources"]}</div>', unsafe_allow_html=True)

# Accept user input
if prompt := st.chat_input("Ask about Near-RT RIC, E2 nodes, or O-RAN specs..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🧠 *Analyzing query and retrieving context...*")
        
        try:
            # Send request to RAG Core API
            start_time = time.time()
            response = requests.post(
                API_URL,
                json={"query": prompt},
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            answer = data.get("response", "No response generated.")
            sources = data.get("sources", "No explicit sources provided.")
            
            # Display final answer
            message_placeholder.markdown(answer)
            
            # Show sources in an expander
            if sources:
                with st.expander("View Context Sources"):
                    st.markdown(f'<div class="source-box">{sources}</div>', unsafe_allow_html=True)
            
            # Add to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer,
                "sources": sources
            })
            
        except requests.exceptions.ConnectionError:
            error_msg = "❌ **Connection Error**: Cannot reach the RAG API. Ensure Docker containers are running (`docker compose up -d`)."
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        except requests.exceptions.Timeout:
            error_msg = "❌ **Timeout Error**: The RAG API took too long to respond. The models might still be loading."
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        except Exception as e:
            error_msg = f"❌ **Execution Error**: `{str(e)}`"
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
