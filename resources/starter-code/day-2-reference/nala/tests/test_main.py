import json
import os
import tempfile

import httpx
import pytest
from fastapi.testclient import TestClient

from app.embeddings import embed_text
from app.ingest import chunk_markdown, chunk_text, ingest_documents
from app.ollama_client import OllamaClient
from app.vector_store import VectorStore


def test_embed_text_calls_correct_endpoint(monkeypatch):
    captured = {}

    def fake_post(self, url, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"embeddings": [[0.1, 0.2, 0.3]]}

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = embed_text("halo dunia", base_url="http://ollama:11434")

    assert result == [0.1, 0.2, 0.3]
    assert captured["url"] == "http://ollama:11434/api/embed"
    assert captured["json"]["model"] == "nomic-embed-text"
    assert captured["json"]["input"] == "halo dunia"


def test_vector_store_index_document_calls_correct_endpoint(monkeypatch):
    captured = {}

    def fake_put(self, url, json, params, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["params"] = params

        class FakeResponse:
            def raise_for_status(self):
                pass

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "put", fake_put)

    store = VectorStore(base_url="http://opensearch:9200", index_name="nala-docs")
    store.index_document(
        doc_id="doc-1",
        text="contoh isi chunk",
        embedding=[0.1, 0.2, 0.3],
        metadata={"source": "sop-test.md"},
    )

    assert captured["url"] == "http://opensearch:9200/nala-docs/_doc/doc-1"
    assert captured["json"]["text"] == "contoh isi chunk"
    assert captured["json"]["embedding"] == [0.1, 0.2, 0.3]
    assert captured["json"]["metadata"]["source"] == "sop-test.md"
    assert captured["params"] == {"refresh": "true"}


def test_vector_store_search_parses_hits(monkeypatch):
    def fake_post(self, url, json, timeout):
        assert url == "http://opensearch:9200/nala-docs/_search"

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "hits": {
                        "hits": [
                            {
                                "_score": 0.9,
                                "_source": {
                                    "text": "chunk relevan",
                                    "metadata": {"source": "sop-test.md"},
                                },
                            }
                        ]
                    }
                }

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    store = VectorStore(base_url="http://opensearch:9200", index_name="nala-docs")
    results = store.search(query_embedding=[0.1, 0.2, 0.3], top_k=3)

    assert results == [
        {"text": "chunk relevan", "score": 0.9, "metadata": {"source": "sop-test.md"}}
    ]


def test_chunk_text_splits_with_overlap():
    text = "a" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) == 3
    assert chunks[0] == "a" * 500
    assert chunks[1][:50] == "a" * 50  # overlap dari akhir chunk sebelumnya


def test_chunk_markdown_splits_by_heading():
    text = (
        "# SOP Cuti\n\n"
        "## 1. Ketentuan\n"
        "Karyawan berhak 12 hari cuti.\n\n"
        "## 2. Pengajuan\n"
        "Ajukan H-3 lewat HRIS."
    )
    chunks = chunk_markdown(text)

    assert len(chunks) == 3
    assert chunks[0].startswith("# SOP Cuti")
    assert chunks[1].startswith("## 1. Ketentuan")
    assert chunks[2].startswith("## 2. Pengajuan")


def test_chunk_markdown_falls_back_to_fixed_size_for_long_section():
    text = "## Section Panjang\n" + "a" * 1200
    chunks = chunk_markdown(text, chunk_size=500, overlap=50)

    assert len(chunks) == 3
    assert chunks[0].startswith("## Section Panjang")


def test_chunk_markdown_without_headings_returns_single_chunk():
    text = "Dokumen tanpa heading Markdown sama sekali."
    chunks = chunk_markdown(text)

    assert chunks == [text]


def test_ingest_documents_uses_chunk_markdown_for_md_files(monkeypatch):
    seen_chunks = []

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        seen_chunks.append(text)
        return [0.1, 0.2, 0.3]

    def fake_index_document(self, doc_id, text, embedding, metadata):
        pass

    def fake_ensure_index(self, dims=768):
        pass

    monkeypatch.setattr("app.ingest.embed_text", fake_embed_text)
    monkeypatch.setattr("app.vector_store.VectorStore.index_document", fake_index_document)
    monkeypatch.setattr("app.vector_store.VectorStore.ensure_index", fake_ensure_index)

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "sop.md"), "w") as f:
            f.write("# Judul\n\n## Bagian Satu\nIsi bagian satu.\n\n## Bagian Dua\nIsi bagian dua.")

        ingest_documents(tmpdir)

    assert len(seen_chunks) == 3
    assert seen_chunks[1].startswith("## Bagian Satu")


def test_ingest_documents_indexes_all_chunks(monkeypatch):
    indexed = []

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    def fake_index_document(self, doc_id, text, embedding, metadata):
        indexed.append((doc_id, text, metadata))

    def fake_ensure_index(self, dims=768):
        pass

    monkeypatch.setattr("app.ingest.embed_text", fake_embed_text)
    monkeypatch.setattr("app.vector_store.VectorStore.index_document", fake_index_document)
    monkeypatch.setattr("app.vector_store.VectorStore.ensure_index", fake_ensure_index)

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "contoh.md"), "w") as f:
            f.write("Ini contoh dokumen SOP singkat untuk pengujian ingest.")

        count = ingest_documents(tmpdir)

    assert count == 1
    assert len(indexed) == 1
    assert indexed[0][1] == "Ini contoh dokumen SOP singkat untuk pengujian ingest."
    assert indexed[0][2]["source"] == "contoh.md"


def test_health_endpoint():
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_uses_retrieved_context(monkeypatch):
    import app.main as main_module

    def fake_search(self, query_embedding, top_k=3):
        return [{"text": "Proses kredit 3-5 hari kerja.", "score": 0.9, "metadata": {"source": "sop-kredit.md"}}]

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    captured = {}

    def fake_generate(self, system_prompt, user_message):
        captured["user_message"] = user_message
        return "Prosesnya 3-5 hari kerja."

    monkeypatch.setattr(main_module.VectorStore, "search", fake_search)
    monkeypatch.setattr(main_module, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_module.OllamaClient, "generate", fake_generate)

    client = TestClient(main_module.app)
    response = client.post("/chat", json={"message": "Berapa lama proses kredit?"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Prosesnya 3-5 hari kerja."}
    assert "Proses kredit 3-5 hari kerja." in captured["user_message"]
    assert "Berapa lama proses kredit?" in captured["user_message"]


def test_chunk_text_overlap_boundaries_are_exact():
    # Distinguishable content (not all "a") so overlap slicing can't be faked
    # by an implementation that ignores `overlap`.
    text = "".join(str(i % 10) for i in range(1200))
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) == 3
    assert chunks[0] == text[0:500]
    assert chunks[1] == text[450:950]
    assert chunks[2] == text[900:1200]
    assert len(chunks[2]) == 300
    assert chunks[1][:50] == chunks[0][-50:]


def test_chat_endpoint_builds_exact_prompt_and_uses_grounded_system_prompt(monkeypatch):
    import app.main as main_module
    from app.system_prompt import NALA_SYSTEM_PROMPT

    hits = [
        {"text": "Proses kredit 3-5 hari kerja.", "score": 0.9, "metadata": {"source": "sop-kredit.md"}},
        {"text": "Dokumen wajib: KTP dan NPWP.", "score": 0.8, "metadata": {"source": "sop-kredit.md"}},
    ]

    def fake_search(self, query_embedding, top_k=3):
        return hits

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    captured = {}

    def fake_generate(self, system_prompt, user_message):
        captured["system_prompt"] = system_prompt
        captured["user_message"] = user_message
        return "Prosesnya 3-5 hari kerja, dokumennya KTP dan NPWP."

    monkeypatch.setattr(main_module.VectorStore, "search", fake_search)
    monkeypatch.setattr(main_module, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_module.OllamaClient, "generate", fake_generate)

    client = TestClient(main_module.app)
    message = "Berapa lama proses kredit dan dokumen apa saja?"
    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200

    expected_context = "\n\n".join(h["text"] for h in hits)
    expected_prompt = f"Konteks:\n{expected_context}\n\nPertanyaan: {message}"
    assert captured["user_message"] == expected_prompt

    assert captured["system_prompt"] == NALA_SYSTEM_PROMPT
    assert "Jawab HANYA berdasarkan konteks tersebut" in captured["system_prompt"]


def test_chat_endpoint_falls_back_to_no_context_prompt_when_no_documents_indexed(monkeypatch):
    import app.main as main_module
    from app.system_prompt import NALA_SYSTEM_PROMPT_NO_CONTEXT

    def fake_search(self, query_embedding, top_k=3):
        return []

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    captured = {}

    def fake_generate(self, system_prompt, user_message):
        captured["system_prompt"] = system_prompt
        captured["user_message"] = user_message
        return "Halo, saya NALA. Dokumen SOP belum tersedia."

    monkeypatch.setattr(main_module.VectorStore, "search", fake_search)
    monkeypatch.setattr(main_module, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_module.OllamaClient, "generate", fake_generate)

    client = TestClient(main_module.app)
    message = "Halo, kamu siapa?"
    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    assert captured["system_prompt"] == NALA_SYSTEM_PROMPT_NO_CONTEXT
    assert captured["user_message"] == message
    assert "Konteks:" not in captured["user_message"]


def test_upload_endpoint_calls_ingest_documents(monkeypatch, tmp_path):
    import app.main as main_module

    captured = {}

    def fake_ingest_documents(folder_path):
        captured["folder_path"] = folder_path
        return 1

    monkeypatch.setattr(main_module, "ingest_documents", fake_ingest_documents)
    monkeypatch.setattr(main_module, "KNOWLEDGE_BASE_PATH", str(tmp_path))

    client = TestClient(main_module.app)
    response = client.post(
        "/upload", files={"file": ("test.md", b"test content", "text/markdown")}
    )

    assert response.status_code == 200
    assert captured["folder_path"] == str(tmp_path)


def test_upload_endpoint_saves_file_even_when_ingest_fails(monkeypatch, tmp_path):
    import app.main as main_module

    def fake_ingest_documents_raises(folder_path):
        raise httpx.HTTPError("OpenSearch belum siap")

    monkeypatch.setattr(main_module, "ingest_documents", fake_ingest_documents_raises)
    monkeypatch.setattr(main_module, "KNOWLEDGE_BASE_PATH", str(tmp_path))

    client = TestClient(main_module.app)
    response = client.post(
        "/upload", files={"file": ("test.md", b"test content", "text/markdown")}
    )

    assert response.status_code == 200
    assert (tmp_path / "test.md").read_bytes() == b"test content"
    assert "berhasil disimpan" in response.text
    assert "belum sempat di-index" in response.text


def test_ensure_index_creates_index_with_768_dimensions_when_missing(monkeypatch):
    captured = {}

    def fake_head(self, url, timeout):
        class FakeResponse:
            status_code = 404

        return FakeResponse()

    def fake_put(self, url, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class FakeResponse:
            def raise_for_status(self):
                pass

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "head", fake_head)
    monkeypatch.setattr(httpx.Client, "put", fake_put)

    store = VectorStore(base_url="http://opensearch:9200", index_name="nala-docs")
    store.ensure_index()

    assert captured["json"]["settings"]["index"]["knn"] is True
    assert (
        captured["json"]["mappings"]["properties"]["embedding"]["dimension"] == 768
    )


def test_ollama_client_chat_stream_yields_content_chunks(monkeypatch):
    lines = [
        json.dumps({"message": {"content": "Ha"}, "done": False}),
        json.dumps({"message": {"content": "lo"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]

    class FakeStreamResponse:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(lines)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    captured = {}

    def fake_stream(self, method, url, json, timeout):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = json
        return FakeStreamResponse()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    client = OllamaClient(base_url="http://ollama:11434", model="llama3.2:3b")
    chunks = list(client.chat_stream([{"role": "user", "content": "Halo"}]))

    assert chunks == ["Ha", "lo"]
    assert captured["method"] == "POST"
    assert captured["url"] == "http://ollama:11434/api/chat"
    assert captured["json"]["model"] == "llama3.2:3b"
    assert captured["json"]["stream"] is True
    assert captured["json"]["messages"] == [{"role": "user", "content": "Halo"}]


def test_chat_stream_endpoint_rejects_empty_messages():
    from app.main import app

    client = TestClient(app)
    response = client.post("/chat/stream", json={"messages": []})

    assert response.status_code == 400


def test_chat_stream_endpoint_rejects_last_message_not_user():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/chat/stream", json={"messages": [{"role": "assistant", "content": "hai"}]}
    )

    assert response.status_code == 400


def test_chat_stream_endpoint_streams_grounded_reply(monkeypatch):
    import app.main as main_module

    def fake_search(self, query_embedding, top_k=3):
        return [
            {"text": "Proses kredit 3-5 hari kerja.", "score": 0.9, "metadata": {"source": "sop-kredit.md"}}
        ]

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    captured = {}

    def fake_chat_stream(self, messages):
        captured["messages"] = messages
        yield "Prosesnya "
        yield "3-5 hari kerja."

    monkeypatch.setattr(main_module.VectorStore, "search", fake_search)
    monkeypatch.setattr(main_module, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_module.OllamaClient, "chat_stream", fake_chat_stream)

    client = TestClient(main_module.app)
    response = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "Berapa lama proses kredit?"}]},
    )

    assert response.status_code == 200
    assert response.text == "Prosesnya 3-5 hari kerja."
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][0]["content"] == main_module.NALA_SYSTEM_PROMPT
    assert "Konteks:" in captured["messages"][-1]["content"]
    assert "Berapa lama proses kredit?" in captured["messages"][-1]["content"]


def test_chat_stream_endpoint_windows_history_to_last_10_messages(monkeypatch):
    import app.main as main_module

    def fake_search(self, query_embedding, top_k=3):
        return []

    def fake_embed_text(text, base_url, model="nomic-embed-text"):
        return [0.1, 0.2, 0.3]

    captured = {}

    def fake_chat_stream(self, messages):
        captured["messages"] = messages
        yield "ok"

    monkeypatch.setattr(main_module.VectorStore, "search", fake_search)
    monkeypatch.setattr(main_module, "embed_text", fake_embed_text)
    monkeypatch.setattr(main_module.OllamaClient, "chat_stream", fake_chat_stream)

    long_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"pesan {i}"}
        for i in range(11)
    ]
    long_history[-1]["role"] = "user"

    client = TestClient(main_module.app)
    response = client.post("/chat/stream", json={"messages": long_history})

    assert response.status_code == 200
    # 1 system message + 9 riwayat (setelah windowing ke 10, minus pesan terakhir) + 1 pesan terakhir
    assert len(captured["messages"]) == 11
    assert captured["messages"][1]["content"] == "pesan 1"


def test_ensure_index_skips_put_when_index_already_exists(monkeypatch):
    put_called = {"called": False}

    def fake_head(self, url, timeout):
        class FakeResponse:
            status_code = 200

        return FakeResponse()

    def fake_put(self, url, json, timeout):
        put_called["called"] = True

        class FakeResponse:
            def raise_for_status(self):
                pass

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "head", fake_head)
    monkeypatch.setattr(httpx.Client, "put", fake_put)

    store = VectorStore(base_url="http://opensearch:9200", index_name="nala-docs")
    store.ensure_index()

    assert put_called["called"] is False
