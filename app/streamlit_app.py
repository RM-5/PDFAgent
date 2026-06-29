"""
PDFAgent - Streamlit UI
Run from PDFAgent/ root:
    streamlit run app/streamlit_app.py
"""

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

/* Hide sidebar and its toggle entirely */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }

/* Force all text light */
p, span, label, li, h1, h2, h3, h4, h5, h6 {
    color: #E2E2E8 !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span { color: #E2E2E8 !important; }
[data-testid="stSlider"] label,
[data-testid="stSlider"] p,
[data-testid="stSlider"] span { color: #E2E2E8 !important; }
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p { color: #A0A0B0 !important; }
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: #E2E2E8 !important; }
::placeholder { color: #4A4A58 !important; opacity: 1 !important; }

/* Main container - full width */
.main .block-container {
    padding: 1.5rem 2rem;
    max-width: 100%;
}

/* Top bar */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 1rem 0;
    border-bottom: 1px solid #2A2A32;
    margin-bottom: 1.25rem;
}
.top-bar-left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.top-bar h1 {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: #F0F0F5 !important;
    margin: 0 !important;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #22C55E;
    box-shadow: 0 0 6px #22C55E88;
    flex-shrink: 0;
    display: inline-block;
}
.status-dot.offline {
    background: #EF4444;
    box-shadow: 0 0 6px #EF444488;
}
.status-text {
    font-size: 0.75rem !important;
    color: #6E6E80 !important;
}

/* Upload panel */
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

/* Stat badge */
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

/* Buttons */
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

/* Danger button */
.danger-btn .stButton > button {
    background: #1A1A1F !important;
    border: 1px solid #3A3A48 !important;
    color: #EF4444 !important;
}
.danger-btn .stButton > button p,
.danger-btn .stButton > button span { color: #EF4444 !important; }

/* Text input */
[data-testid="stTextInput"] input {
    background: #16161A !important;
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

/* File uploader */
[data-testid="stFileUploader"] {
    border: 1.5px dashed #2A2A32 !important;
    border-radius: 10px !important;
    background: #0E0E10 !important;
}
[data-testid="stFileUploader"]:hover { border-color: #6C63FF !important; }

/* Slider */
[data-testid="stSlider"] { padding: 0 !important; }

/* Doc chips */
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

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid #2A2A32;
    margin: 1rem 0;
}

/* Chat area */
.chat-area {
    min-height: 340px;
    margin-bottom: 1rem;
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

/* Source bar */
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

/* Empty state */
.empty-state {
    text-align: center;
    padding: 4rem 1rem;
}
.empty-state .icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
.empty-state p { font-size: 0.85rem; color: #3A3A48 !important; }

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border: 1px solid #2A2A32 !important;
    background: #16161A !important;
}
</style>
""", unsafe_allow_html=True)


def api_get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None

def api_post(path, json=None, files=None, data=None):
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, files=files, data=data, timeout=300)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_delete(path):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None

def format_relevance(score):
    return f"{score:.0%}"


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )


if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []
if "show_upload" not in st.session_state:
    st.session_state.show_upload = True
if "retrieval_k" not in st.session_state:
    st.session_state.retrieval_k = 10


health = api_get("/health")
online = health is not None
chunks = health.get("total_chunks", 0) if online else 0
model  = health.get("embed_model", "") if online else ""


col_title, col_badge, col_toggle = st.columns([4, 2, 1])
with col_title:
    dot_class = "status-dot" if online else "status-dot offline"
    status_text = "API connected" if online else "API offline"
    st.markdown(f"""
    <div class="top-bar-left" style="padding:0.5rem 0">
        <span class="{dot_class}"></span>
        <h1 style="font-size:1.1rem; font-weight:600; color:#F0F0F5; margin:0; display:inline">PDFAgent</h1>
        <span class="status-text" style="margin-left:8px">{status_text}</span>
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

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


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
        chunk_size = st.slider("Chunk size (tokens)", 500, 2500, 1200, 100, label_visibility="collapsed")
        st.session_state.retrieval_k = st.slider(
            "Chunks to retrieve", 5, 18, st.session_state.retrieval_k, 1,
            help="Higher = more thorough but slower. 8–12 is a good default.",
            label_visibility="collapsed",
        )

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
                content = escape_html(msg.get("content") or "No answer was generated.")
                st.markdown(f"""
                <div class="msg-ai">
                    <div class="bubble-ai">{content}{sources_html}</div>
                </div>
                """, unsafe_allow_html=True)


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
        result = api_post("/query", json={"question": question, "k": st.session_state.retrieval_k})
    if result and "error" not in result and "detail" not in result:
        answer = (result.get("answer") or "").strip() or "The model returned an empty answer. Restart the API and try again."
        st.session_state.messages.append({
            "role":    "assistant",
            "content": answer,
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
