
## PDFAgent

A fully local RAG-powered document assistant that ingests large documents 
— up to 300-400 pages — across formats including PDF, PPTX, DOCX, XLSX, HTML, 
lets you ask questions against their full content,
and answers them with relative precision to the content in the provided document. 

## Stack
- **Docling** — parses PDF, PPTX, DOCX, tables
- **ChromaDB** — local vector database
- **Ollama + Qwen** — local LLM for answering questions
- **LangChain** — orchestration
- **FastAPI** — REST API

## Project Structure

PDFAgent/

  └── app/

  ├── main.py

  ├── configs/settings.py

  ├── db/vectorstore.py

  ├── models/schemas.py

  ├── routers/rag.py

  ├── services/loader.py

  ├── services/qa_chain.py
  
  └── utils/file_utils.py

## Setup
In your Mac/Linux terminal, run:
```
pip install -r requirements.txt
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

## Run
In your Mac/Linux terminal, run:
```
python -m app.main
```
Then open `http://localhost:8001/docs` to use the API.
