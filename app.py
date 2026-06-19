import streamlit as st
from google import genai
from PIL import Image
import time

# 1. Page Configuration
st.set_page_config(page_title="KAI CHATBOT", layout="wide")

# 2. Refined, Minimalist Custom CSS
st.markdown("""
    <style>
    /* Main container wrapper alignment */
    .chat-body-wrapper {
        max-width: 800px !important;
        margin: 0 auto !important;
        display: flex;
        flex-direction: column;
    }

    .chatgpt-brand-header {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1e40af !important;
        display: inline-block;
        margin-bottom: 12vh;
        align-self: flex-start;
    }

    .hero-center-box {
        width: 100% !important;
        text-align: center !important;
        margin-top: 4vh;
        margin-bottom: 4vh;
    }
    
    .hero-title {
        font-size: 2.5rem; 
        font-weight: 700; 
        color: #1e3a8a !important;
        text-align: center !important;
        margin-bottom: 4vh;
    }

    /* Style global button roundings */
    div.stButton > button {
        border-radius: 0.5rem !important;
    }

    /* Target chip pill selections */
    div.stButton > button[key^="chip_"] {
        border-radius: 100px !important;
        padding: 0.6rem 1.6rem !important;
    }

    /* ========================================================== */
    /* CLEAN WIDGET FORMATTING: MAKING FILE UPLOADER SYMMETRICAL   */
    /* ========================================================== */
    /* Strip default drag-and-drop borders and text layout padding */
    div[data-testid="stFileUploader"] {
        padding: 0px !important;
    }
    div[data-testid="stFileUploader"] section {
        padding: 0px !important;
        border: none !important;
        background-color: transparent !important;
    }
    /* Hide the default small "200MB per file" caption helper */
    div[data-testid="stFileUploader"] label,
    div[data-testid="stFileUploader"] data-testid,
    div[data-testid="stFileUploader"] section + div {
        display: none !important;
    }

    /* Force the built-in Browse Files button to expand full-width like other buttons */
    div[data-testid="stFileUploader"] section button {
        width: 100% !important;
        min-height: 40px !important;
        border-radius: 0.5rem !important;
        margin: 0px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }

    .sidebar-header {
        color: #1e40af !important; 
        font-size: 0.85rem !important; 
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        display: block;
    }
    
    .staged-preview {
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px;
        margin-bottom: 12px;
        display: inline-block;
    }

    /* Blue Highlight User Input Bar Accent Glow */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 2px solid #2563eb !important; 
        border-radius: 28px !important;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.15) !important; 
    }
    
    div[data-testid="stChatInput"] textarea {
        color: #0f172a !important;
        background-color: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Initialize Gemini Client
client = genai.Client()

# 4. State Containers
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0
if "prefill_prompt" not in st.session_state:
    st.session_state.prefill_prompt = None

def get_current_messages():
    cid = st.session_state.current_chat_id
    if cid and cid in st.session_state.all_chats:
        return st.session_state.all_chats[cid]["messages"]
    return []

# --- SIDEBAR COMPONENT PANEL ---
with st.sidebar:
    # Render the native file uploader directly with clean labels
    uploader_key = f"img_uploader_v_{st.session_state.uploader_version}"
    uploaded_image = st.file_uploader("📷 Upload an image", type=["jpg", "jpeg", "png"], key=uploader_key, label_visibility="collapsed")

    if st.button("New chat", use_container_width=True):
        st.session_state.current_chat_id = None
        st.session_state.uploader_version += 1
        st.session_state.prefill_prompt = None
        st.rerun()
        
    if st.button("Clear chat", use_container_width=True, key="clear_chat_action"):
        st.session_state.current_chat_id = None
        st.session_state.uploader_version += 1
        st.session_state.prefill_prompt = None
        st.rerun()

    st.markdown('<span class="sidebar-header">Pinned</span>', unsafe_allow_html=True)
    pinned_exist = False
    for cid, chat_info in list(st.session_state.all_chats.items()):
        if chat_info["pinned"]:
            pinned_exist = True
            col_btn, col_act = st.columns([0.8, 0.2])
            with col_btn:
                if st.button(f"📌 {chat_info['title']}", key=f"side_pin_{cid}", use_container_width=True):
                    st.session_state.current_chat_id = cid
                    st.rerun()
            with col_act:
                if st.button("✕", key=f"unpin_{cid}"):
                    st.session_state.all_chats[cid]["pinned"] = False
                    st.rerun()
    if not pinned_exist:
        st.caption("No pinned chats.")

    st.markdown('<span class="sidebar-header">History</span>', unsafe_allow_html=True)
    history_exist = False
    for cid, chat_info in st.session_state.all_chats.items():
        if not chat_info["pinned"]:
            history_exist = True
            col_btn, col_act = st.columns([0.8, 0.2])
            with col_btn:
                if st.button(f"💬 {chat_info['title']}", key=f"side_hist_{cid}", use_container_width=True):
                    st.session_state.current_chat_id = cid
                    st.rerun()
            with col_act:
                if st.button("📌", key=f"pin_{cid}"):
                    st.session_state.all_chats[cid]["pinned"] = True
                    st.rerun()
    if not history_exist:
        st.caption("No history streams.")

    st.markdown("---")
    selected_model = st.selectbox("Model Engine", options=["gemini-2.5-flash", "gemini-2.5-pro"], index=0)

# --- APPLICATION CONTENT VIEWPORT ---
st.markdown('<div class="chat-body-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="chatgpt-brand-header">KAI CHATBOT</div>', unsafe_allow_html=True)

current_messages = get_current_messages()

if not current_messages:
    st.markdown('<div class="hero-center-box">', unsafe_allow_html=True)
    st.markdown('<h2 class="hero-title">What\'s on your mind today?</h2>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_left_space, col_chip1, col_chip2, col_right_space = st.columns([1.2, 2, 2, 1.2])
    with col_chip1:
        if st.button("🎨 Create an image", key="chip_create", use_container_width=True):
            st.session_state.prefill_prompt = "Create an image of "
            st.rerun()
    with col_chip2:
        if st.button("📝 Write or edit", key="chip_write", use_container_width=True):
            st.session_state.prefill_prompt = "Help me write or edit a "
            st.rerun()

# Conversation logs
chat_container = st.container()
with chat_container:
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"]:
                st.image(message["image"], width=300)

if uploaded_image:
    st.markdown('<div class="staged-preview">', unsafe_allow_html=True)
    st.image(uploaded_image, width=60)
    st.caption("📷 Image Attached")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 5. Bottom Input Control Bar
current_placeholder = st.session_state.prefill_prompt if st.session_state.prefill_prompt else "Ask KAI..."
prompt = st.chat_input(current_placeholder)

if prompt:
    user_text = prompt
    img_obj = Image.open(uploaded_image) if uploaded_image else None
    st.session_state.prefill_prompt = None
    
    if st.session_state.current_chat_id is None:
        new_id = f"chat_{int(time.time())}"
        st.session_state.all_chats[new_id] = {
            "title": user_text[:22] + "..." if len(user_text) > 22 else user_text,
            "messages": [],
            "pinned": False
        }
        st.session_state.current_chat_id = new_id
        
    cid = st.session_state.current_chat_id
    st.session_state.all_chats[cid]["messages"].append({"role": "user", "content": user_text, "image": img_obj})
    
    try:
        payload = [user_text]
        if img_obj:
            payload.append(img_obj)
        response = client.models.generate_content(model=selected_model, contents=payload)
        ans_text = response.text
    except Exception as e:
        ans_text = f"⚠️ Error parsing request: {str(e)}"
        
    st.session_state.all_chats[cid]["messages"].append({"role": "assistant", "content": ans_text})
    st.session_state.uploader_version += 1
    st.rerun()