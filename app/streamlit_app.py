from __future__ import annotations
import tempfile
from pathlib import Path
import requests
import streamlit as st
 
st.set_page_config(
    page_title="PDFAgent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)
 
API_BASE = "http://localhost:8001"
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
 
html, body, [data-testid="stApp"] {
    background-color: #0E0E10;
    color: #E2E2E8;
    font-family: 'Inter', sans-serif;
}
 
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
 
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
 
p, span, label, li, h1, h2, h3, h4, h5, h6 {
    color: #E2E2E8 !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span { color: #E2E2E8 !important; }
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p { color: #A0A0B0 !important; }
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: #E2E2E8 !important; }
::placeholder { color: #4A4A58 !important; opacity: 1 !important; }
 
.main .block-container {
    padding: 1.5rem 2rem;
    max-width: 100%;
}
 
/* Login page container */
.login-wrap {
    max-width: 400px;
    margin: 4rem auto;
}
.login-logo {
    text-align: center;
    margin-bottom: 2rem;
}
.login-logo h1 {
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    color: #F0F0F5 !important;
    margin: 0 !important;
}
.login-logo p {
    font-size: 0.85rem !important;
    color: #6E6E80 !important;
    margin-top: 4px !important;
}
.login-card {
    background: #16161A;
    border: 1px solid #2A2A32;
    border-radius: 14px;
    padding: 2rem;
}
.login-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 1.5rem;
    background: #0E0E10;
    border-radius: 8px;
    padding: 4px;
}
 
/* Top bar */
.top-bar-left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #22C55E;
    box-shadow: 0 0 6px #22C55E88;
    flex-shrink: 0;
    display: inline-block;
}
.status-dot.offline { background: #EF4444; box-shadow: 0 0 6px #EF444488; }
.status-text { font-size: 0.75rem !important; color: #6E6E80 !important; }
 
.upload-panel {
    background: #16161A;
    border: 1px solid #2A2A32;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}
.upload-panel-title {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #6E6E80 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.75rem !important;
}
.stat-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #16161A;
    border: 1px solid #2A2A32;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
}
.stat-badge .val { color: #6C63FF !important; font-weight: 600; }
.stat-badge .lbl { color: #6E6E80 !important; }
 
.stButton > button {
    background: #6C63FF !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.45rem 1rem !important;
    transition: opacity 0.15s ease !important;
    width: 100%;
}
.stButton > button p,
.stButton > button span { color: #ffffff !important; }
.stButton > button:hover { opacity: 0.85 !important; }
.stButton > button:disabled { opacity: 0.4 !important; }
 
.danger-btn .stButton > button {
    background: #1A1A1F !important;
    border: 1px solid #3A3A48 !important;
    color: #EF4444 !important;
}
.danger-btn .stButton > button p,
.danger-btn .stButton > button span { color: #EF4444 !important; }
 
.ghost-btn .stButton > button {
    background: transparent !important;
    border: 1px solid #2A2A32 !important;
    color: #A0A0B0 !important;
}
.ghost-btn .stButton > button p,
.ghost-btn .stButton > button span { color: #A0A0B0 !important; }
 
[data-testid="stTextInput"] input {
    background: #0E0E10 !important;
    border: 1px solid #2A2A32 !important;
    border-radius: 8px !important;
    color: #E2E2E8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 2px #6C63FF22 !important;
    outline: none !important;
}
 
[data-testid="stFileUploader"] {
    border: 1.5px dashed #2A2A32 !important;
    border-radius: 10px !important;
    background: #0E0E10 !important;
}
[data-testid="stFileUploader"]:hover { border-color: #6C63FF !important; }
 
.doc-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}
.doc-chip {
    font-size: 0.72rem;
    background: #0E0E10;
    border: 1px solid #2A2A32;
    border-radius: 20px;
    padding: 3px 10px;
    color: #A0A0B0 !important;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
 
.session-item {
    background: #16161A;
    border: 1px solid #2A2A32;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 6px;
    font-size: 0.8rem;
    color: #A0A0B0 !important;
    cursor: pointer;
}
.session-item.active {
    border-color: #6C63FF;
    background: #1A1830;
}
 
.section-divider {
    border: none;
    border-top: 1px solid #2A2A32;
    margin: 1rem 0;
}
 
.msg-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
}
.msg-ai {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.75rem;
}
.bubble-user {
    background: #6C63FF;
    color: #fff !important;
    padding: 10px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    font-size: 0.9rem;
    line-height: 1.55;
}
.bubble-user * { color: #fff !important; }
.bubble-ai {
    background: #16161A;
    border: 1px solid #2A2A32;
    color: #E2E2E8 !important;
    padding: 12px 16px;
    border-radius: 4px 18px 18px 18px;
    max-width: 75%;
    font-size: 0.9rem;
    line-height: 1.6;
}
.bubble-ai * { color: #E2E2E8 !important; }
 
.source-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #2A2A32;
}
.source-pill {
    font-size: 0.68rem;
    font-family: 'JetBrains Mono', monospace;
    background: #0E0E10;
    border: 1px solid #2A2A32;
    color: #A0A0B0 !important;
    padding: 2px 8px;
    border-radius: 20px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.source-pill .score { color: #6C63FF !important; font-weight: 500; }
 
.empty-state {
    text-align: center;
    padding: 4rem 1rem;
}
.empty-state .icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
.empty-state p { font-size: 0.85rem; color: #3A3A48 !important; }
 
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border: 1px solid #2A2A32 !important;
    background: #16161A !important;
}
</style>
""", unsafe_allow_html=True)
 
 
# Helpers 
 
def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}
 
def api_get(path, auth=True):
    try:
        headers = auth_headers() if auth else {}
        r = requests.get(f"{API_BASE}{path}", headers=headers, timeout=10)
        if r.status_code == 401:
            st.session_state.token = None
            st.rerun()
        return r.json() if r.ok else None
    except Exception:
        return None
 
def api_post(path, json=None, files=None, data=None, auth=True, form=False):
    try:
        headers = auth_headers() if auth else {}
        if form:
            r = requests.post(f"{API_BASE}{path}", data=json, headers=headers, timeout=300)
        else:
            r = requests.post(f"{API_BASE}{path}", json=json, files=files, data=data, headers=headers, timeout=300)
        if r.status_code == 401:
            st.session_state.token = None
            st.rerun()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
 
def api_delete(path, auth=True):
    try:
        headers = auth_headers() if auth else {}
        r = requests.delete(f"{API_BASE}{path}", headers=headers, timeout=10)
        return r.json() if r.ok else None
    except Exception:
        return None
 
def format_relevance(score):
    return f"{score:.0%}"
 
 
# Session state 
if "token" not in st.session_state:
    st.session_state.token = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []
if "show_upload" not in st.session_state:
    st.session_state.show_upload = True
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
 
 
 
if not st.session_state.token:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="login-logo">
        <h1>PDFAgent</h1>
        <p>Sign in to access your documents and chat history</p>
    </div>
    """, unsafe_allow_html=True)
 
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
 
    tab_col1, tab_col2 = st.columns(2)
    with tab_col1:
        if st.button("Login", key="tab_login"):
            st.session_state.auth_mode = "login"
            st.rerun()
    with tab_col2:
        if st.button("Register", key="tab_register"):
            st.session_state.auth_mode = "register"
            st.rerun()
 
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
 
    email    = st.text_input("Email", placeholder="you@example.com", key="auth_email")
    password = st.text_input("Password", placeholder="••••••••", type="password", key="auth_password")
 
    if st.session_state.auth_mode == "login":
        if st.button("Sign in", key="do_login"):
            if not email or not password:
                st.error("Enter both email and password")
            else:
                result = api_post("/auth/login", json={"username": email, "password": password}, auth=False, form=True)
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.success("Signed in")
                    st.rerun()
                else:
                    st.error(result.get("detail", "Login failed") if result else "Could not reach server")
    else:
        if st.button("Create account", key="do_register"):
            if not email or not password:
                st.error("Enter both email and password")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                result = api_post("/auth/register", json={"email": email, "password": password}, auth=False)
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.success("Account created")
                    st.rerun()
                else:
                    st.error(result.get("detail", "Registration failed") if result else "Could not reach server")
 
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
 
# MAIN APP (only reached if logged in)

 
health = api_get("/health")
online = health is not None
chunks = health.get("total_chunks", 0) if online else 0
 
user_info = api_get("/auth/me")
user_email = user_info.get("email", "") if user_info else ""
 
 
# Top bar
col_title, col_badge, col_toggle, col_logout = st.columns([3, 2, 1, 1])
with col_title:
    dot_class = "status-dot" if online else "status-dot offline"
    status_text = "API connected" if online else "API offline"
    st.markdown(f"""
    <div class="top-bar-left" style="padding:0.5rem 0">
        <span class="{dot_class}"></span>
        <h1 style="font-size:1.1rem; font-weight:600; color:#F0F0F5; margin:0; display:inline">PDFAgent</h1>
        <span class="status-text" style="margin-left:8px">{status_text} · {user_email}</span>
    </div>
    """, unsafe_allow_html=True)
 
with col_badge:
    if online:
        st.markdown(f"""
        <div style="padding:0.5rem 0">
            <span class="stat-badge">
                <span class="val">{chunks:,}</span>
                <span class="lbl">chunks indexed</span>
            </span>
        </div>
        """, unsafe_allow_html=True)
 
with col_toggle:
    toggle_label = "Hide upload" if st.session_state.show_upload else "Upload docs"
    if st.button(toggle_label):
        st.session_state.show_upload = not st.session_state.show_upload
        st.rerun()
 
with col_logout:
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button("Sign out"):
        st.session_state.token = None
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
 
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
 
 
# Layout: sessions list on left, main content on right
col_sessions, col_main = st.columns([1, 3])
 
with col_sessions:
    st.markdown('<p class="upload-panel-title">Chat history</p>', unsafe_allow_html=True)
    if st.button("+ New chat"):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.rerun()
 
    sessions = api_get("/history/sessions") or []
    for s in sessions:
        is_active = s["id"] == st.session_state.current_session_id
        label = s["title"][:30] + ("..." if len(s["title"]) > 30 else "")
        if st.button(label, key=f"session_{s['id']}"):
            detail = api_get(f"/history/sessions/{s['id']}")
            if detail:
                st.session_state.current_session_id = s["id"]
                st.session_state.messages = [
                    {"role": m["role"], "content": m["content"], "sources": m.get("sources", [])}
                    for m in detail["messages"]
                ]
                st.rerun()
 
with col_main:
    if st.session_state.show_upload:
        st.markdown('<div class="upload-panel">', unsafe_allow_html=True)
        st.markdown('<p class="upload-panel-title">Document ingestion</p>', unsafe_allow_html=True)
 
        up_col1, up_col2, up_col3 = st.columns([3, 2, 2])
 
        with up_col1:
            uploaded = st.file_uploader(
                "Upload file",
                type=["pdf", "docx", "pptx", "xlsx", "html", "md", "txt", "png", "jpg", "jpeg"],
                label_visibility="collapsed",
            )
 
        with up_col2:
            url_input = st.text_input("URL", placeholder="Paste a URL...", label_visibility="collapsed")
            chunk_size = st.slider("Chunk size", 200, 2000, 500, 50, label_visibility="collapsed")
 
        with up_col3:
            st.write("")
            if st.button("Ingest file", disabled=not (uploaded and online)):
                suffix = Path(uploaded.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name
                with st.spinner(f"Ingesting {uploaded.name}..."):
                    with open(tmp_path, "rb") as f:
                        result = api_post(
                            "/ingest/file",
                            files={"file": (uploaded.name, f, uploaded.type)},
                            data={"chunk_size": chunk_size},
                        )
                    Path(tmp_path).unlink(missing_ok=True)
                if result and "error" not in result:
                    st.success(f"Stored {result.get('chunks_stored','?')} chunks")
                    st.session_state.indexed_docs.append(uploaded.name)
                    st.rerun()
                else:
                    st.error(result.get("error", result.get("detail", "Error")))
 
            if st.button("Ingest URL", disabled=not (url_input and online)):
                with st.spinner("Ingesting URL..."):
                    result = api_post("/ingest/url", json={"url": url_input, "chunk_size": chunk_size})
                if result and "error" not in result:
                    st.success(f"Stored {result.get('chunks_stored','?')} chunks")
                    st.session_state.indexed_docs.append(url_input)
                    st.rerun()
                else:
                    st.error(result.get("error", result.get("detail", "Error")))
 
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("Clear index", disabled=not online):
                api_delete("/reset")
                st.session_state.indexed_docs = []
                st.session_state.messages = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
 
        if st.session_state.indexed_docs:
            chips = ""
            for doc in st.session_state.indexed_docs:
                icon = "🌐" if doc.startswith("http") else "📄"
                chips += f'<span class="doc-chip">{icon} {doc}</span>'
            st.markdown(f'<div class="doc-chips">{chips}</div>', unsafe_allow_html=True)
 
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
 
    # Chat history
    with st.container():
        if not st.session_state.messages:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">📂</div>
                <p>Upload a document above, then ask a question below.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="msg-user">
                        <div class="bubble-user">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    sources_html = ""
                    if msg.get("sources"):
                        pills = ""
                        for s in msg["sources"]:
                            src   = s.get("source", "?")
                            page  = s.get("page", "?")
                            score = s.get("relevance_score", 0)
                            pills += f'<span class="source-pill">📄 {src} p.{page} <span class="score">{format_relevance(score)}</span></span>'
                        sources_html = f'<div class="source-bar">{pills}</div>'
                    st.markdown(f"""
                    <div class="msg-ai">
                        <div class="bubble-ai">{msg["content"]}{sources_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
 
    # Input row
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    q_col, btn_col = st.columns([8, 1])
    with q_col:
        question = st.text_input(
            "Ask",
            placeholder="What is this document about?",
            label_visibility="collapsed",
            key="question_input",
        )
    with btn_col:
        ask_btn = st.button("Ask", disabled=not (online and question.strip()))
 
    if ask_btn and question.strip():
        st.session_state.messages.append({"role": "user", "content": question})
        with st.spinner("Thinking..."):
            query_path = "/query"
            if st.session_state.current_session_id:
                query_path += f"?session_id={st.session_state.current_session_id}"
            result = api_post(query_path, json={"question": question, "k": 15})
        if result and "error" not in result and "detail" not in result:
            st.session_state.current_session_id = result.get("session_id", st.session_state.current_session_id)
            st.session_state.messages.append({
                "role":    "assistant",
                "content": result.get("answer", "No answer returned."),
                "sources": result.get("sources", []),
                "model":   result.get("model", ""),
                "chunks":  result.get("chunks_used", 0),
            })
        else:
            err = result.get("detail", result.get("error", "Something went wrong.")) if result else "Could not reach the API."
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Could not get a response: {err}".replace("<","&lt;").replace(">","&gt;"),
                "sources": [],
            })
        st.rerun()