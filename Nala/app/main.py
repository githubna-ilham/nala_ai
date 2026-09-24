import os
from typing import Literal

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langfuse import Langfuse
from pydantic import BaseModel

from app.embeddings import embed_text
from app.ingest import ingest_document
from app.ollama_client import OllamaClient
from app.reranker import Reranker
from app.system_prompt import (
    NALA_SYSTEM_PROMPT,
    NALA_SYSTEM_PROMPT_NO_CONTEXT,
    NALA_SYSTEM_PROMPT_RAG_OFF,
)
from app.vector_store import VectorStore

app = FastAPI(title="NALA")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

ollama_client = OllamaClient(
    base_url=OLLAMA_BASE_URL,
    model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
)

KNOWLEDGE_BASE_PATH = os.environ.get("KNOWLEDGE_BASE_PATH", "/app/knowledge-base")

OPENSEARCH_BASE_URL = os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")
vector_store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")

RERANK_ENABLED = os.environ.get("RERANK_ENABLED", "true").lower() == "true"
reranker = Reranker() if RERANK_ENABLED else None

langfuse_client = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
)


def list_knowledge_base_documents() -> list[str]:
    if not os.path.isdir(KNOWLEDGE_BASE_PATH):
        return []
    return sorted(
        f for f in os.listdir(KNOWLEDGE_BASE_PATH)
        if f.endswith((".md", ".txt", ".pdf"))
    )


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    messages: list[ChatMessage]
    use_rag: bool = True
    search_method: Literal["vector", "bm25", "hybrid"] = "hybrid"
    use_reranking: bool = True


HISTORY_WINDOW = 10


@app.get("/health")
def health_check():
    return {"status": "ok"}


def traced_chat_stream(trace, ollama_messages: list[dict]):
    generation = trace.generation(
        name="llm_generate_stream",
        model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
        input=ollama_messages,
    )
    accumulated = ""
    try:
        for token in ollama_client.chat_stream(ollama_messages):
            accumulated += token
            yield token
    finally:
        generation.end(output=accumulated)
        trace.update(output={"reply": accumulated})
        langfuse_client.flush()


@app.post("/chat/stream")
def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    if not request.messages or request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="messages harus non-kosong dan elemen terakhir harus role 'user'",
        )

    recent = request.messages[-HISTORY_WINDOW:]
    last_user_message = recent[-1].content

    trace = langfuse_client.trace(name="chat_stream", input={"message": last_user_message})

    if request.use_rag:
        try:
            do_rerank = request.use_reranking and reranker is not None
            pool_size = 20 if do_rerank else (3 if request.search_method == "hybrid" else 6)

            retrieval_span = trace.span(
                name="retrieval",
                input={"query": last_user_message, "method": request.search_method},
            )
            if request.search_method == "bm25":
                candidates = vector_store.search_bm25(last_user_message, top_k=pool_size)
            elif request.search_method == "hybrid":
                query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
                candidates = vector_store.search_hybrid(
                    query_text=last_user_message,
                    query_embedding=query_embedding,
                    top_k=pool_size,
                )
            else:
                query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
                candidates = vector_store.search(query_embedding, top_k=pool_size)
            retrieval_span.end(output={"candidate_count": len(candidates)})

            if do_rerank:
                rerank_span = trace.span(name="rerank", input={"candidate_count": len(candidates)})
                results = reranker.rerank(last_user_message, candidates, top_k=3)
                rerank_span.end(output={"top_chunks": [r["text"][:100] for r in results]})
            else:
                results = candidates
        except httpx.HTTPError as exc:
            results = []
            trace.update(output={"error": f"retrieval_failed: {exc}"}, level="ERROR")
    else:
        results = []

    if request.use_rag and results:
        context = "\n\n".join(
            f"[{r['metadata']['source']}]\n{r['text']}" for r in results
        )
        system_prompt = NALA_SYSTEM_PROMPT
        grounded_content = f"Konteks:\n{context}\n\nPertanyaan: {last_user_message}"
    elif request.use_rag:
        system_prompt = NALA_SYSTEM_PROMPT_NO_CONTEXT
        grounded_content = last_user_message
    else:
        system_prompt = NALA_SYSTEM_PROMPT_RAG_OFF
        grounded_content = last_user_message

    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages += [{"role": m.role, "content": m.content} for m in recent[:-1]]
    ollama_messages.append({"role": "user", "content": grounded_content})

    return StreamingResponse(
        traced_chat_stream(trace, ollama_messages), media_type="text/plain"
    )


@app.get("/", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        request,
        "upload.html",
        {"message": None, "documents": list_knowledge_base_documents()},
    )


@app.post("/upload", response_class=HTMLResponse)
def upload_document(request: Request, file: UploadFile = File(...)):
    os.makedirs(KNOWLEDGE_BASE_PATH, exist_ok=True)
    dest_path = os.path.join(KNOWLEDGE_BASE_PATH, file.filename)
    with open(dest_path, "wb") as f:
        f.write(file.file.read())

    try:
        count = ingest_document(dest_path)
        message = f"Dokumen '{file.filename}' berhasil diunggah dan di-index ({count} chunk)."
    except httpx.HTTPError:
        message = (
            f"Dokumen '{file.filename}' berhasil disimpan, tapi belum sempat di-index "
            "(OpenSearch belum terjangkau) — akan otomatis diproses begitu pipeline-nya berjalan."
        )
    return templates.TemplateResponse(
        request,
        "upload.html",
        {"message": message, "documents": list_knowledge_base_documents()},
    )
