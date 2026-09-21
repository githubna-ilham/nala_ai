import os
import httpx

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from psycopg.rows import dict_row

from app.ollama_client import OllamaClient
from app.system_prompt import NALA_SYSTEM_PROMPT, NALA_SYSTEM_PROMPT_NO_CONTEXT, NALA_SYSTEM_PROMPT_AGENT
from app.embeddings import embed_text
from app.vector_store import VectorStore
from app.reranker import Reranker
from app.db import get_connection, get_write_connection
from app.agent import build_agent
from app.audit import log_audit
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

OLLAMA_BASE_URL_DEFAULT = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_DEFAULT = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    user_id: str = "anonim"
    role: str = "staff_umum"


class ChatResponse(BaseModel):
    reply: str


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


def fetch_pengajuan_kredit() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan "
                "FROM pengajuan_kredit ORDER BY id DESC"
            )
            return cur.fetchall()


def fetch_klaim_asuransi() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim "
                "FROM klaim_asuransi ORDER BY id DESC"
            )
            return cur.fetchall()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    trace = langfuse_client.trace(name="chat_agent", input={"message": request.message})

    agent = build_agent(
        ollama_client=ollama_client,
        vector_store=vector_store,
        ollama_base_url=OLLAMA_BASE_URL_DEFAULT,
        reranker=reranker,
        trace=trace,
        model_name=OLLAMA_MODEL_DEFAULT,
    )

    history_messages = [{"role": m.role, "content": m.content} for m in request.history]
    recent_history = (history_messages + [{"role": "user", "content": request.message}])[-HISTORY_WINDOW:]

    initial_state = {
        "messages": [
            {"role": "system", "content": NALA_SYSTEM_PROMPT_AGENT},
            *recent_history,
        ],
        "role": request.role,
        "called_tools": [],
    }
    final_state = agent.invoke(initial_state)
    reply = final_state["messages"][-1]["content"]

    called_tools = final_state.get("called_tools", [])
    if called_tools:
        for entry in called_tools:
            log_audit(
                user_id=request.user_id,
                role=request.role,
                pertanyaan=request.message,
                tool_dipanggil=entry["tool"],
                akses_diizinkan=entry["diizinkan"],
            )
    else:
        log_audit(
            user_id=request.user_id,
            role=request.role,
            pertanyaan=request.message,
            tool_dipanggil=None,
            akses_diizinkan=True,
        )

    trace.update(output={"reply": reply, "message_count": len(final_state["messages"])})
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


@app.get("/data-operasional", response_class=HTMLResponse)
def data_operasional_page(request: Request):
    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": None,
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )


@app.post("/data-operasional/pengajuan-kredit", response_class=HTMLResponse)
def add_pengajuan_kredit(
    request: Request,
    nasabah_id: str = Form(...),
    nama_nasabah: str = Form(...),
    jumlah_pengajuan: float = Form(...),
    status: str = Form(...),
    tanggal_pengajuan: str = Form(...),
    alasan_penolakan: str = Form(""),
):
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pengajuan_kredit "
                "(nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan, alasan_penolakan) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    nasabah_id,
                    nama_nasabah,
                    jumlah_pengajuan,
                    status,
                    tanggal_pengajuan,
                    alasan_penolakan or None,
                ),
            )
        conn.commit()

    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": f"Pengajuan kredit untuk nasabah '{nasabah_id}' berhasil ditambahkan.",
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )


@app.post("/data-operasional/klaim-asuransi", response_class=HTMLResponse)
def add_klaim_asuransi(
    request: Request,
    nasabah_id: str = Form(...),
    nama_nasabah: str = Form(...),
    jenis_klaim: str = Form(...),
    jumlah_klaim: float = Form(...),
    status: str = Form(...),
    tanggal_klaim: str = Form(...),
):
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO klaim_asuransi "
                "(nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim),
            )
        conn.commit()

    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": f"Klaim asuransi untuk nasabah '{nasabah_id}' berhasil ditambahkan.",
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )