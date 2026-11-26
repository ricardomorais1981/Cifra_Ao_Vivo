"""
Testes de integração da API FastAPI.
Execute com: python -m pytest tests/integration/test_api.py -v
Requer: pip install httpx pytest pytest-asyncio
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import io
import wave
import struct
import math
import pytest
from fastapi.testclient import TestClient
from local_engine.api.main import app

client = TestClient(app)


def _make_wav(duration: float = 10.0, freq: float = 440.0,
              sr: int = 22050) -> bytes:
    """Gera um arquivo WAV sintético (tom puro)."""
    n = int(sr * duration)
    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(n):
            v = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sr))
            wf.writeframes(struct.pack("<h", v))
    return buf.getvalue()


# ---------------------------------------------------------------------------
class TestHealth:
    def test_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestTasks:
    def test_create_task(self):
        r = client.post("/tasks?title=Teste&artist=Artista")
        assert r.status_code == 201
        assert "task_id" in r.json()

    def test_task_not_found(self):
        r = client.get("/tasks/naoexiste")
        assert r.status_code == 404

    def test_upload_invalid_format(self):
        r = client.post("/tasks?title=X")
        task_id = r.json()["task_id"]

        fake = io.BytesIO(b"not an audio file")
        r2 = client.post(
            f"/tasks/{task_id}/audio",
            files={"file": ("song.xyz", fake, "application/octet-stream")},
        )
        assert r2.status_code == 422

    def test_full_flow(self):
        """Cria tarefa, envia WAV sintético, aguarda conclusão."""
        r1 = client.post("/tasks?title=Hallelujah&artist=Gospel")
        task_id = r1.json()["task_id"]

        wav_data = _make_wav(duration=10.0)
        r2 = client.post(
            f"/tasks/{task_id}/audio",
            files={"file": ("song.wav", io.BytesIO(wav_data), "audio/wav")},
        )
        assert r2.status_code == 200

        # Polling síncrono (TestClient executa background tasks de forma síncrona)
        import time
        for _ in range(30):
            r3 = client.get(f"/tasks/{task_id}")
            d  = r3.json()
            if d["status"] in ("done", "error"):
                break
            time.sleep(0.3)

        assert d["status"] == "done", f"Falhou: {d.get('error')}"
        assert "summary" in d

    def test_export_txt(self):
        """Verifica que o TXT é gerado após processamento."""
        r1 = client.post("/tasks?title=SongTxt")
        task_id = r1.json()["task_id"]
        wav_data = _make_wav(duration=10.0)
        client.post(f"/tasks/{task_id}/audio",
                    files={"file": ("s.wav", io.BytesIO(wav_data), "audio/wav")})

        import time
        for _ in range(30):
            st = client.get(f"/tasks/{task_id}").json()["status"]
            if st in ("done", "error"):
                break
            time.sleep(0.3)

        r_txt = client.get(f"/tasks/{task_id}/export/txt")
        assert r_txt.status_code == 200
        assert "MUSICA" in r_txt.text

    def test_delete_task(self):
        r = client.post("/tasks?title=Del")
        tid = r.json()["task_id"]
        r2  = client.delete(f"/tasks/{tid}")
        assert r2.status_code == 204
        r3  = client.get(f"/tasks/{tid}")
        assert r3.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
