import httpx
import pytest
from fastapi.testclient import TestClient

from app.ollama_client import OllamaClient


def test_ollama_client_generate_calls_correct_endpoint(monkeypatch):
    captured = {}

    def fake_post(self, url, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"response": "Halo, saya NALA."}

        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = OllamaClient(base_url="http://ollama:11434", model="llama3.2:3b")
    result = client.generate(system_prompt="Kamu adalah NALA.", user_message="Halo")

    assert result == "Halo, saya NALA."
    assert captured["url"] == "http://ollama:11434/api/generate"
    assert captured["json"]["model"] == "llama3.2:3b"
    assert "Kamu adalah NALA." in captured["json"]["system"]
    assert captured["json"]["prompt"] == "Halo"


def test_health_endpoint():
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_reply(monkeypatch):
    import app.main as main_module

    def fake_generate(self, system_prompt, user_message):
        return "Halo, saya NALA."

    monkeypatch.setattr(main_module.OllamaClient, "generate", fake_generate)

    client = TestClient(main_module.app)
    response = client.post("/chat", json={"message": "Halo"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Halo, saya NALA."}
