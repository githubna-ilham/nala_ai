import os
import httpx

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.ollama_client import OllamaClient
from app.system_prompt import NALA_SYSTEM_PROMPT, NALA_SYSTEM_PROMPT_NO_CONTEXT
from app.embeddings import embed_text
from app.vector_store import VectorStore
from app.reranker import Reranker
from langfuse import Langfuse


from app.ingest import ingest_documents

app = FastAPI(title="NALA")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ollama_client = OllamaClient(
    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
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


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    messages: list[ChatMessage]


HISTORY_WINDOW = 10


def list_knowledge_base_documents() -> list[str]:
    if not os.path.isdir(KNOWLEDGE_BASE_PATH):
        return []
    return sorted(
        f for f in os.listdir(KNOWLEDGE_BASE_PATH)
        if f.endswith((".md", ".txt", ".pdf"))
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    trace = langfuse_client.trace(name="chat", input={"message": request.message})

    try:
        retrieval_span = trace.span(name="hybrid_search", input={"query": request.message})
        query_embedding = embed_text(request.message, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        candidates = vector_store.search_hybrid(
            query_text=request.message,
            query_embedding=query_embedding,
            top_k=20,
        )
        retrieval_span.end(output={"candidate_count": len(candidates)})

        rerank_span = trace.span(name="rerank", input={"candidate_count": len(candidates)})
        results = reranker.rerank(request.message, candidates, top_k=3) if reranker else candidates[:3]
        rerank_span.end(output={"top_chunks": [r["text"][:100] for r in results]})
    except httpx.HTTPError as e:
        trace.update(output={"error": str(e)}, level="ERROR")
        results = []

    if not results:
        generation = trace.generation(
            name="llm_generate_no_context",
            model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
            input=request.message,
        )
        reply = ollama_client.generate(
            system_prompt=NALA_SYSTEM_PROMPT_NO_CONTEXT,
            user_message=request.message,
        )
        generation.end(output=reply)
        trace.update(output={"reply": reply})
        langfuse_client.flush()
        return ChatResponse(reply=reply)

    context = "\n\n".join(r["text"] for r in results)
    prompt = f"Konteks:\n{context}\n\nPertanyaan: {request.message}"

    generation = trace.generation(
        name="llm_generate",
        model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
        input=prompt,
    )
    reply = ollama_client.generate(system_prompt=NALA_SYSTEM_PROMPT, user_message=prompt)
    generation.end(output=reply)

    trace.update(output={"reply": reply})
    langfuse_client.flush()
    return ChatResponse(reply=reply)



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

    try:
        retrieval_span = trace.span(name="hybrid_search", input={"query": last_user_message})
        query_embedding = embed_text(last_user_message, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        candidates = vector_store.search_hybrid(
            query_text=last_user_message,
            query_embedding=query_embedding,
            top_k=20,
        )
        retrieval_span.end(output={"candidate_count": len(candidates)})

        rerank_span = trace.span(name="rerank", input={"candidate_count": len(candidates)})
        results = reranker.rerank(last_user_message, candidates, top_k=3) if reranker else candidates[:3]
        rerank_span.end(output={"top_chunks": [r["text"][:100] for r in results]})
    except httpx.HTTPError:
        results = []

    if results:
        context = "\n\n".join(r["text"] for r in results)
        system_prompt = NALA_SYSTEM_PROMPT
        grounded_content = f"Konteks:\n{context}\n\nPertanyaan: {last_user_message}"
    else:
        system_prompt = NALA_SYSTEM_PROMPT_NO_CONTEXT
        grounded_content = last_user_message

    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages += [{"role": m.role, "content": m.content} for m in recent[:-1]]
    ollama_messages.append({"role": "user", "content": grounded_content})

    return StreamingResponse(
        traced_chat_stream(trace, ollama_messages), media_type="text/plain"
    )



@app.get("/", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "message": None, "documents": list_knowledge_base_documents()},
    )


@app.post("/upload", response_class=HTMLResponse)
def upload_document(request: Request, file: UploadFile = File(...)):
    os.makedirs(KNOWLEDGE_BASE_PATH, exist_ok=True)
    dest_path = os.path.join(KNOWLEDGE_BASE_PATH, file.filename)
    with open(dest_path, "wb") as f:
        f.write(file.file.read())

    try:
        count = ingest_documents(KNOWLEDGE_BASE_PATH)
        message = f"Dokumen '{file.filename}' berhasil diunggah dan di-index ({count} chunk total di knowledge base)."
    except httpx.HTTPError:
        message = (
            f"Dokumen '{file.filename}' berhasil disimpan, tapi belum sempat di-index "
            "(OpenSearch belum terjangkau) — akan otomatis diproses begitu pipeline-nya berjalan."
        )
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "message": message, "documents": list_knowledge_base_documents()},
    )