import os

from pypdf import PdfReader

from app.embeddings import embed_text
from app.vector_store import VectorStore

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OPENSEARCH_BASE_URL = os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")


def extract_text(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(file_path, "r") as f:
        return f.read()


def ingest_documents(folder_path: str) -> int:
    store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")
    store.ensure_index()

    total_documents = 0
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith((".md", ".txt", ".pdf")):
            continue
        content = extract_text(os.path.join(folder_path, filename))
        embedding = embed_text(content, base_url=OLLAMA_BASE_URL)
        store.index_document(
            doc_id=filename,
            text=content,
            embedding=embedding,
            metadata={"source": filename},
        )
        total_documents += 1

    return total_documents
