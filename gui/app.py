import streamlit as st
import requests
import time

st.set_page_config(
    page_title="O-RAN Copilot",
    page_icon="🗼",
    layout="centered",
    initial_sidebar_state="expanded",
)

API_URL = "http://rag-core-api:8000/api/v1/query"

THEMES = {
    "Light": {
        "bg":           "#F4F7F5",
        "surface":      "#FFFFFF",
        "surface2":     "#E8EFEA",
        "primary":      "#0F7643",
        "primary_dim":  "#0B5932",
        "text":         "#1A2E22",      
        "text_muted":   "#5A7A68",
        "border":       "#CFDBD3",
        "input_bg":     "#FFFFFF",
        "user_bubble":  "#E8EFEA",
        "icon":         "☀️",
        "label":        "Light",
    },
    "Dark": {
        "bg":           "#050806",
        "surface":      "#0D1410",
        "surface2":     "#121B16",
        "primary":      "#4674F0",     
        "primary_dim":  "#16A54D",
        "text":         "#E8F0EB",      
        "text_muted":   "#7AAD8A",      
        "border":       "#1A2E24",
        "input_bg":     "#0D1410",
        "user_bubble":  "#121B16",
        "icon":         "🌑",
        "label":        "Dark",
    },
    "Comfort": {
        "bg":           "#ECE7DC",
        "surface":      "#F4EFE3",
        "surface2":     "#DFD9CA",
        "primary":      "#2D5A27",
        "primary_dim":  "#1E3F1A",
        "text":         "#1E2D1C",      # بني-أخضر داكن مقروء
        "text_muted":   "#6B7D65",
        "border":       "#D2C9B5",
        "input_bg":     "#F4EFE3",
        "user_bubble":  "#DFD9CA",
        "icon":         "🔅",
        "label":        "Comfort",
    },
}

THEME_KEYS = list(THEMES.keys())

if "theme" not in st.session_state:
    st.session_state.theme = "Light"
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

t = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stAppViewBlockContainer"] {{
        background-color: {t['bg']} !important;
        color: {t['text']} !important;
    }}
    [data-testid="stHeader"] {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stMainBlockContainer"] {{
        background-color: {t['bg']} !important;
        color: {t['text']} !important;
    }}
    [data-testid="stBottom"] {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stBottom"] > div {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stBottom"] div {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stBottomBlockContainer"] {{
        background-color: {t['bg']} !important;
    }}
    .stChatInputContainer {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stChatInputPropagator"] {{
        background-color: {t['bg']} !important;
    }}
    section[data-testid="stBottom"] > div {{
        background-color: {t['bg']} !important;
    }}
    .stChatInput {{
        background-color: {t['bg']} !important;
    }}
    [class*="bottom"] {{
        background-color: {t['bg']} !important;
    }}
    div[class*="InputContainer"] {{
        background-color: {t['bg']} !important;
    }}
    [data-testid="stChatInputTextArea"] {{
        background-color: {t['input_bg']} !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: {t['surface']} !important;
        border-right: 1px solid {t['border']} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    [data-testid="stChatInput"] {{
        background-color: transparent !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background-color: {t['input_bg']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['border']} !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{
        color: {t['text_muted']} !important;
    }}
    [data-testid="stChatMessageContent"] {{
        background-color: {t['surface']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['border']} !important;
    }}
    [data-testid="stExpander"] {{
        background-color: {t['surface2']} !important;
        border: 1px solid {t['border']} !important;
    }}
    div[data-testid="stMarkdownContainer"] p {{
        color: {t['text']} !important;
    }}
    div[data-testid="stMarkdownContainer"] li {{
        color: {t['text']} !important;
    }}
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3 {{
        color: {t['primary']} !important;
    }}
    div[data-testid="stMarkdownContainer"] code {{
        color: {t['primary']} !important;
        background-color: {t['surface2']} !important;
    }}
    .stCaption {{
        color: {t['text_muted']} !important;
    }}
    .main-title {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {t['primary']};
        text-align: left;
        margin-bottom: 2px;
    }}
    .sub-title {{
        font-size: 1rem;
        color: {t['text_muted']};
        text-align: left;
        margin-bottom: 25px;
    }}
    .source-box {{
        background-color: {t['surface2']};
        padding: 10px 14px;
        border-radius: 8px;
        border-left: 4px solid {t['primary']};
        margin-top: 8px;
        font-size: 0.82rem;
        font-family: monospace;
        color: {t['text']};
        line-height: 1.6;
    }}
    .chat-history-title {{
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {t['text_muted']};
        margin-top: 10px;
        margin-bottom: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    if st.button("New Chat...", use_container_width=True):
        st.session_state.current_chat_id = None
        st.rerun()

    st.markdown('<div class="chat-history-title">Active</div>', unsafe_allow_html=True)
    if st.session_state.chats:
        for chat_id, chat_data in list(st.session_state.chats.items()):
            is_current = (chat_id == st.session_state.current_chat_id)
            if st.button(
                f"💬 {chat_data['title']}",
                key=f"sidebar_chat_{chat_id}",
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                st.session_state.current_chat_id = chat_id
                st.rerun()
    else:
        st.caption("No active sessions yet.")

    st.divider()
    st.markdown(
        f'<p style="font-size:0.8rem; font-weight:600; color:{t["primary"]}; margin-bottom:2px;">O-RAN RAG Knowledge Core</p>'
        f'<p style="font-size:0.75rem; color:{t["text_muted"]}; margin-top:0px;">Powered by RAG System Team</p>',
        unsafe_allow_html=True,
    )

# --- Header: title + theme icons on same line ---
header_cols = st.columns([0.7, 0.1, 0.1, 0.1])

with header_cols[0]:
    st.markdown('<div class="main-title">🗼 O-RAN Copilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">High-Precision Context-Aware Spec Verification Core</div>', unsafe_allow_html=True)

for idx, key in enumerate(THEME_KEYS):
    with header_cols[idx + 1]:
        is_active = key == st.session_state.theme
        if st.button(
            THEMES[key]['icon'],
            key=f"top_theme_btn_{key}",
            help=f"Switch to {THEMES[key]['label']} mode",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            if key != st.session_state.theme:
                st.session_state.theme = key
                st.rerun()

st.markdown("---")

# --- Chat Area ---
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chats:
    active_messages = st.session_state.chats[st.session_state.current_chat_id]["messages"]
else:
    active_messages = []

for message in active_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("View Context Sources"):
                st.markdown(
                    f'<div class="source-box">{message["sources"]}</div>',
                    unsafe_allow_html=True,
                )

# --- Input ---
if prompt := st.chat_input("Here you are :)"):
    if st.session_state.current_chat_id is None:
        timestamp_id = str(time.time())
        words = prompt.split()
        generated_title = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
        st.session_state.chats[timestamp_id] = {"title": generated_title, "messages": []}
        st.session_state.current_chat_id = timestamp_id
        active_messages = st.session_state.chats[timestamp_id]["messages"]

    active_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🧠 Analyzing")

        try:
            response = requests.post(API_URL, json={"query": prompt}, timeout=120)
            response.raise_for_status()

            data = response.json()
            answer = data.get("response", "No response generated.")
            sources = data.get("sources", "")

            placeholder.markdown(answer)

            if sources:
                with st.expander("View Context Sources"):
                    st.markdown(
                        f'<div class="source-box">{sources}</div>',
                        unsafe_allow_html=True,
                    )

            active_messages.append({"role": "assistant", "content": answer, "sources": sources})
            st.rerun()

        except requests.exceptions.ConnectionError:
            msg = "❌ **Connection Error**: Cannot reach the RAG API. Ensure Docker containers are running (`docker compose up -d`)."
            active_messages.append({"role": "assistant", "content": msg})
            st.rerun()

        except requests.exceptions.Timeout:
            msg = "❌ **Timeout Error**: The RAG API took too long to respond. The models might still be loading."
            active_messages.append({"role": "assistant", "content": msg})
            st.rerun()

        except Exception as e:
            msg = f"❌ **Execution Error**: `{str(e)}`"
            active_messages.append({"role": "assistant", "content": msg})
            st.rerun()
