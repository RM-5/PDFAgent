# PDFAgent
 
A fully local RAG-powered document assistant that ingests large documents —
up to 300-400 pages — across formats including PDF, PPTX, DOCX, XLSX,
HTML, and images, and lets you ask natural language questions against their
full content.
 
No data leaves your device and it involves No API keys.
 
## Stack
- **Docling** — parses PDF, PPTX, DOCX, tables, images
- **ChromaDB** — local vector database
- **Ollama + Qwen** — local LLM for answering questions
- **LangChain** — orchestration
- **FastAPI** — REST API backend
- **PostgreSQL + SQLAlchemy** — user accounts, chat history, document log
- **Streamlit** — web-based chat UI (no terminal needed after setup)
## Project Structure
```
PDFAgent/
├── .env                        ← your config (see Setup below)
├── requirements.txt
└── app/
    ├── main.py                 ← FastAPI entry point
    ├── streamlit_app.py        ← Streamlit UI (login + chat)
    ├── configs/settings.py
    ├── db/
    │   ├── database.py         ← SQLAlchemy engine/session
    │   ├── models.py           ← User, Session, Message, Document tables
    │   └── vectorstore.py      ← ChromaDB logic
    ├── models/
    │   ├── schemas.py
    │   └── auth_schemas.py
    ├── routers/
    │   ├── auth.py             ← /auth/register, /auth/login, /auth/me
    │   ├── history.py          ← /history/sessions, /history/documents
    │   └── rag.py              ← /ingest, /query (auth-protected)
    ├── services/
    │   ├── loader.py           ← Docling document loader
    │   ├── qa_chain.py         ← RAG query logic
    │   ├── auth_service.py     ← JWT + password hashing
    │   └── history_service.py  ← save/fetch chat history
    └── utils/file_utils.py
```
 
## Setup
 
### 1. Install dependencies
```bash
pip install -r requirements.txt
```
 
### 2. Install and pull Ollama models
```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```
 
### 3. Set up PostgreSQL
```bash
brew install postgresql@16       # Mac
brew services start postgresql@16
 
psql postgres
```
Inside the `psql` prompt:
```sql
CREATE DATABASE pdfagent;
CREATE USER pdfagent_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE pdfagent TO pdfagent_user;
\q
```
 
### 4. Create your `.env` file
Create `PDFAgent/.env` with:
```env
DATABASE_URL=postgresql+asyncpg://pdfagent_user:yourpassword@localhost:5432/pdfagent
SECRET_KEY=generate-with-command-below
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
LLM_MODEL=qwen2.5:7b
EMBED_MODEL=nomic-embed-text
CHROMA_DIR=chroma_db
COLLECTION=rag_docs
```
 
Generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
 
## Run
 
You need **two terminals** running at the same time — the API backend and the Streamlit UI.
 
**Terminal 1 — API backend** (creates DB tables automatically on first run):
```bash
cd PDFAgent
python -m app.main
```
Runs on `http://localhost:8001`. Visit `/docs` for the raw API reference.
 
**Terminal 2 — Streamlit UI:**
```bash
cd PDFAgent
streamlit run app/streamlit_app.py
```
Opens automatically in your browser, usually at `http://localhost:8501`.
 
## Using the app
 
1. Open the Streamlit UI in your browser
2. **Register** a new account (email + password) or **log in** if you already have one
3. Upload a PDF, PPTX, DOCX, or paste a URL in the upload panel
4. Ask questions in the chat box at the bottom
5. Your conversations are saved automatically — click any entry in the
   **Chat history** panel on the left to reload a past session
6. Click **+ New chat** to start a fresh conversation
7. Click **Sign out** to log out

## Notes
- All chat history, documents, and accounts are stored in your local PostgreSQL database — nothing leaves your machine.
- Uploaded documents and their embeddings persist in `chroma_db/` between restarts.
- To wipe all indexed documents (but keep your account/history), use the **Clear index** button in the UI.
