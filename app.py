# Monkeypatch protobuf to bypass call-stack checks in Python 3.13+ / 3.14+
try:
    from google._upb import _message as _upb_message
    _upb_message.Message._CheckCalledFromGeneratedFile = lambda *args, **kwargs: None
except Exception:
    pass

try:
    from google.protobuf.pyext import _message as _cpp_message
    _cpp_message.Message._CheckCalledFromGeneratedFile = lambda *args, **kwargs: None
except Exception:
    pass

import streamlit as st
import tempfile
import agent
from langchain_core.callbacks import BaseCallbackHandler
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import threading
import base64

class RealTimeThinkingCallbackHandler(BaseCallbackHandler):
    def __init__(self, expander_container):
        self.container = expander_container
        self.logs = []
        self.ctx = get_script_run_ctx()

    def _wrap_with_ctx(self, fn):
        def wrapper(*args, **kwargs):
            if self.ctx:
                add_script_run_ctx(threading.current_thread(), self.ctx)
            try:
                return fn(*args, **kwargs)
            except Exception:
                pass
        return wrapper

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if name.startswith("on_") and callable(attr):
            return self._wrap_with_ctx(attr)
        return attr

    def on_llm_start(self, serialized, prompts, **kwargs):
        log = "LLM starting generation..."
        self.logs.append(log)
        self.container.markdown(log)
        
    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "Unknown Tool")
        log = f"Executing tool `{tool_name}` with input: `{input_str}`"
        self.logs.append(log)
        self.container.markdown(log)
        
    def on_tool_end(self, output, **kwargs):
        serialized_output = str(output)
        if isinstance(output, tuple) and len(output) > 0:
            serialized_output = str(output[0])
            
        if len(serialized_output) > 500:
            serialized_output = serialized_output[:500] + "... (truncated)"
            
        log = f"Tool finished! Result:\n```\n{serialized_output}\n```"
        self.logs.append(log)
        self.container.markdown(log)
        
    def on_llm_end(self, response, **kwargs):
        log = "LLM finished generating."
        self.logs.append(log)
        self.container.markdown(log)

# Modern minimalist SVG avatars in black and white
user_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="46" fill="#0d0d0d" stroke="#333333" stroke-width="4"/>
  <text x="50" y="59" font-family="'Inter', -apple-system, system-ui, sans-serif" font-size="28" font-weight="600" fill="#ffffff" text-anchor="middle">ME</text>
</svg>"""

assistant_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="46" fill="#ffffff" stroke="#ffffff" stroke-width="4"/>
  <text x="50" y="59" font-family="'Inter', -apple-system, system-ui, sans-serif" font-size="28" font-weight="700" fill="#000000" text-anchor="middle">AI</text>
</svg>"""

user_avatar = f"data:image/svg+xml;base64,{base64.b64encode(user_svg.encode()).decode()}"
assistant_avatar = f"data:image/svg+xml;base64,{base64.b64encode(assistant_svg.encode()).decode()}"

st.set_page_config(page_title="Search Agent", page_icon="🔍", layout="wide")

# Inject Minimalistic Black and White CSS stylesheet
st.markdown(
    """
    <style>
    /* Clean Minimalistic Font and Color Palette */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Solid Dark Background */
    .stApp {
        background-color: #0d0d0d !important;
        color: #ffffff !important;
    }
    
    /* Sidebar styling: black background with minimal border */
    section[data-testid="stSidebar"] {
        background-color: #080808 !important;
        border-right: 1px solid #222222 !important;
    }
    
    /* Minimalist Title */
    .app-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: -1rem;
        margin-bottom: 0.2rem;
        letter-spacing: -0.03em;
    }
    
    .app-subtitle {
        font-size: 1rem;
        color: #737373;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* File Uploader styling */
    div[data-testid="stFileUploader"] {
        background-color: #121212 !important;
        border: 1px dashed #222222 !important;
        border-radius: 8px !important;
        padding: 8px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: #ffffff !important;
    }
    
    /* Premium Solid Black & White Buttons */
    .stButton>button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ffffff !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    
    .stButton>button:hover {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #ffffff !important;
    }
    
    .stButton>button:active {
        transform: translateY(0px) !important;
    }
    
    /* Secondary Clear / Reset buttons overrides */
    button[data-testid="baseButton-secondary"] {
        background-color: #0d0d0d !important;
        border: 1px solid #222222 !important;
        color: #888888 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #181818 !important;
        color: #ffffff !important;
        border-color: #555555 !important;
    }
    
    /* Chat message container styling */
    div[data-testid="stChatMessage"] {
        background-color: #121212 !important;
        border: 1px solid #222222 !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
        padding: 12px !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
    }
    
    div[data-testid="stChatMessage"][data-test-user="user"] {
        background-color: #181818 !important;
        border: 1px solid #333333 !important;
    }
    
    /* Expander card custom design */
    div[data-testid="stExpander"] {
        background-color: #121212 !important;
        border: 1px solid #222222 !important;
        border-radius: 6px !important;
        margin-top: 8px !important;
    }
    
    /* Hide details chevron / plus in expanders */
    div[data-testid="stExpander"] details summary svg {
        display: none !important;
    }
    div[data-testid="stExpander"] details summary {
        list-style: none !important;
        padding-left: 10px !important;
    }
    div[data-testid="stExpander"] details summary::-webkit-details-marker {
        display: none !important;
    }
    
    /* Code block styling */
    code {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-family: monospace !important;
    }
    
    /* Thinking expander animation keyframes (White/Gray pulsing) */
    @keyframes pulse-glow {
        0% { opacity: 0.6; border-color: #222222; }
        50% { opacity: 1.0; border-color: #555555; }
        100% { opacity: 0.6; border-color: #222222; }
    }
    
    div:has(.thinking-marker) ~ div div[data-testid="stExpander"] {
        animation: pulse-glow 2s infinite ease-in-out !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    div:has(.thinking-marker) ~ div div[data-testid="stExpander"] summary {
        background-color: #121212 !important;
    }
    div:has(.thinking-marker) ~ div div[data-testid="stExpander"] summary p {
        color: #ffffff !important;
        font-weight: 500 !important;
        text-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="app-title">Document Search Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Upload documents (PDF, DOCX, TXT, MD) and ask questions. Uses local RAG and web search fallback.</div>', unsafe_allow_html=True)

# Sidebar for file upload and database status
with st.sidebar:
    st.header("Document Ingestion")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt", "md"])
    
    if uploaded_file is not None:
        if st.button("Process Document"):
            with st.status("Indexing document...", expanded=True) as status:
                status.write("Saving temporary file...")
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    num_chunks = agent.process_document(tmp_path, original_filename=uploaded_file.name, status_container=status)
                    status.update(label=f"Successfully indexed! ({num_chunks} chunks)", state="complete", expanded=False)
                    st.rerun()
                except Exception as e:
                    status.update(label=f"Error processing document: {e}", state="error", expanded=True)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
    
    st.markdown("---")
    st.header("Indexed Documents")
    indexed_docs = agent.get_indexed_documents()
    if indexed_docs:
        for doc in indexed_docs:
            st.write(f"• {doc}")
        
        st.markdown("")
        if st.button("Clear Database", type="secondary"):
            agent.clear_vector_store()
            st.success("Database cleared!")
            st.rerun()
    else:
        st.info("No documents indexed yet.")
        
    st.markdown("---")
    st.header("Chat Control")
    if st.session_state.get("generating", False):
        if st.button("Stop Generation", type="primary", use_container_width=True):
            st.session_state.generating = False
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()
            st.rerun()
    else:
        if st.button("Stop & Reset Chat", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.generating = False
            st.rerun()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generating" not in st.session_state:
    st.session_state.generating = False

# Display chat history
for message in st.session_state.messages:
    role = message["role"]
    avatar = user_avatar if role == "user" else assistant_avatar
    with st.chat_message(role, avatar=avatar):
        # Render thinking logs if present
        if role == "assistant" and message.get("thinking"):
            with st.expander("Thinking...", expanded=False):
                for log in message["thinking"]:
                    st.markdown(log)
                    
        st.markdown(message["content"])
        if role == "assistant" and message.get("sources"):
            with st.expander("View Sources & Citations", expanded=False):
                for idx, src in enumerate(message["sources"]):
                    st.markdown(
                        f"""
                        <div style="
                            padding: 12px; 
                            margin-bottom: 10px; 
                            border-radius: 6px; 
                            border: 1px solid #333333; 
                            background-color: #161616;
                        ">
                            <strong style="color: #ffffff; font-size: 13.5px;">Source {idx+1}: {src['source']} (Page {src['page']})</strong>
                            <p style="margin-top: 6px; margin-bottom: 0px; font-size: 13px; line-height: 1.5; color: #a3a3a3; font-style: italic;">
                                "{src['content']}"
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# Handle new user input
if not st.session_state.generating:
    if prompt := st.chat_input("Ask a question about your document..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.generating = True
        st.rerun()

# If in generating state, run the agent
if st.session_state.generating:
    user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_messages:
        prompt = user_messages[-1]["content"]
        
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.markdown('<div class="thinking-marker"></div>', unsafe_allow_html=True)
            thinking_placeholder = st.empty()
            with thinking_placeholder.container():
                st_callback_container = st.expander("Thinking...", expanded=False)
                
            st_callback = RealTimeThinkingCallbackHandler(st_callback_container)
            
            try:
                # History is all messages except the last user query
                history = st.session_state.messages[:-1]
                response = agent.ask_agent(prompt, chat_history=history, callbacks=[st_callback])
                
                # Replace pulsing expander with static populated expander
                with thinking_placeholder.container():
                    with st.expander("Thinking...", expanded=False):
                        for log in st_callback.logs:
                            st.markdown(log)
                            
                st.markdown(response["content"])
                
                if response.get("sources"):
                    with st.expander("View Sources & Citations", expanded=False):
                        for idx, src in enumerate(response["sources"]):
                            st.markdown(
                                f"""
                                <div style="
                                    padding: 12px; 
                                    margin-bottom: 10px; 
                                    border-radius: 6px; 
                                    border: 1px solid #333333; 
                                    background-color: #161616;
                                ">
                                    <strong style="color: #ffffff; font-size: 13.5px;">Source {idx+1}: {src['source']} (Page {src['page']})</strong>
                                    <p style="margin-top: 6px; margin-bottom: 0px; font-size: 13px; line-height: 1.5; color: #a3a3a3; font-style: italic;">
                                        "{src['content']}"
                                    </p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                
                # Append assistant response with thinking logs to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["content"],
                    "sources": response.get("sources", []),
                    "thinking": st_callback.logs
                })
                st.session_state.generating = False
                st.rerun()
                
            except Exception as e:
                st.session_state.generating = False
                st.error(f"Error: {e}")
