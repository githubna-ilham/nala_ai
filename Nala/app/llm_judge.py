import re

from app.ollama_client import OllamaClient

JUDGE_SYSTEM_PROMPT = """Kamu adalah evaluator jawaban AI. Kamu akan diberikan KONTEKS,
PERTANYAAN, dan JAWABAN. Tugasmu menilai dua hal dengan skor 1-5:
1. FAITHFULNESS: apakah JAWABAN didukung penuh oleh KONTEKS (bukan mengarang)?
   1 = mengarang total, 5 = seluruh klaim didukung konteks.
2. RELEVANCE: apakah JAWABAN benar-benar menjawab PERTANYAAN?
   1 = tidak nyambung, 5 = menjawab tepat sasaran.
Jawab HANYA dalam format persis:
FAITHFULNESS: <angka>
RELEVANCE: <angka>
Jangan tambahkan penjelasan lain."""


def judge_answer(judge_client: OllamaClient, context: str, question: str, answer: str) -> dict:
    prompt = f"KONTEKS:\n{context}\n\nPERTANYAAN:\n{question}\n\nJAWABAN:\n{answer}"
    raw = judge_client.generate(system_prompt=JUDGE_SYSTEM_PROMPT, user_message=prompt)

    faithfulness = re.search(r"FAITHFULNESS:\s*(\d)", raw)
    relevance = re.search(r"RELEVANCE:\s*(\d)", raw)
    return {
        "faithfulness": int(faithfulness.group(1)) if faithfulness else None,
        "relevance": int(relevance.group(1)) if relevance else None,
        "raw": raw,
    }
