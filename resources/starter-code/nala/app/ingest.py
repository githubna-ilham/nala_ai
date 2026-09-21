import os

from pypdf import PdfReader
import re

from app.embeddings import embed_text
from app.vector_store import VectorStore

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OPENSEARCH_BASE_URL = os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")


# app/ingest.py, di bawah chunk_text()
def extract_text(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(file_path, "r") as f:
        return f.read()
    
# app/ingest.py
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks

def chunk_markdown(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    sections = re.split(r"\n(?=#{1,6} )", text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            chunks.extend(chunk_text(section, chunk_size=chunk_size, overlap=overlap))
    return chunks

# app/ingest.py, di bawah extract_text()
def ingest_documents(folder_path: str) -> int:
    store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")
    store.ensure_index()

    total_chunks = 0
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith((".md", ".txt", ".pdf")):
            continue
        content = extract_text(os.path.join(folder_path, filename))
        chunks = chunk_markdown(content) if filename.endswith(".md") else chunk_text(content)

        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk, base_url=OLLAMA_BASE_URL)
            store.index_document(
                doc_id=f"{filename}-{i}",
                text=chunk,
                embedding=embedding,
                metadata={"source": filename},
            )
            total_chunks += 1

    return total_chunks