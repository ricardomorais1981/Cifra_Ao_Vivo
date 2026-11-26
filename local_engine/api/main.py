"""
Cifra ao Vivo v2.0 — API FastAPI
Serve em http://localhost:8000
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from typing import Optional

# Adiciona o diretório raiz ao path para imports relativos
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import aiofiles

from shared.schemas.music_data import MusicData, TaskStatus, PipelineStatus
from local_engine.audio.prepare import load_audio, estimate_tempo, SUPPORTED
from local_engine.audio.music_start import detect_music_bounds
from local_engine.recognition.engine import recognize
from local_engine.recognition.merge import merge_chord_family
from local_engine.validation.pipeline import run_pipeline
from local_engine.export.txt_export import export_txt
from local_engine.lyrics.lrclib import fetch_lrclib

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Cifra ao Vivo",
    version="2.0.0",
    description="Transcrição de acordes e letra para música gospel",
)

# Arquivos estáticos e templates
_WEBAPP = os.path.join(_ROOT, "webapp")
app.mount("/static", StaticFiles(directory=os.path.join(_WEBAPP, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_WEBAPP, "templates"))

# Diretório de uploads temporários
_UPLOADS = os.path.join(_ROOT, "_uploads")
os.makedirs(_UPLOADS, exist_ok=True)

# ---------------------------------------------------------------------------
# Estado em memória (tarefas)
# ---------------------------------------------------------------------------
_tasks: dict[str, dict] = {}  # task_id -> {status, music, progress, error}


def _new_task(task_id: str):
    _tasks[task_id] = {
        "id":       task_id,
        "status":   TaskStatus.QUEUED,
        "progress": 0,
        "message":  "Aguardando arquivo...",
        "music":    None,
        "error":    None,
        "created":  time.time(),
    }


def _get_task(task_id: str) -> dict:
    t = _tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return t


# ---------------------------------------------------------------------------
# Processamento em background
# ---------------------------------------------------------------------------
async def _process(task_id: str, audio_path: str,
                   title: str, artist: str):
    task = _tasks[task_id]
    task["status"] = TaskStatus.PROCESSING

    def progress(pct: int, msg: str):
        task["progress"] = pct
        task["message"]  = msg

    try:
        progress(5, "Carregando áudio...")
        prepared = await asyncio.get_event_loop().run_in_executor(
            None, load_audio, audio_path
        )

        # Ignora o que vem antes/depois da música (silêncio, fala, abertura)
        progress(8, "Procurando o início da música...")
        m_start, m_end = await asyncio.get_event_loop().run_in_executor(
            None, detect_music_bounds, prepared.y, prepared.sr
        )
        y  = prepared.y[int(m_start * prepared.sr):int(m_end * prepared.sr)]
        sr = prepared.sr
        music_duration = len(y) / sr

        music = MusicData(
            title=title or "Desconhecido",
            artist=artist or "",
            duration=music_duration,
            audio_file=os.path.basename(audio_path),
        )

        # Tempo
        progress(10, "Estimando BPM...")
        music.tempo = await asyncio.get_event_loop().run_in_executor(
            None, estimate_tempo, y, sr
        )

        # Reconhecimento (v2.1: hop=2048 para estabilidade CQT, self_prob=0.95)
        def _recognize():
            return recognize(
                y, sr,
                hop=2048,
                self_prob=0.95,
                progress_cb=lambda p, m: progress(10 + int(p * 0.6), m)
            )

        progress(15, "Reconhecendo acordes...")
        raw_events = await asyncio.get_event_loop().run_in_executor(None, _recognize)

        from shared.schemas.music_data import ChordEvent
        music.chords = [
            ChordEvent(
                start=e["start"], end=e["end"],
                root=e["root"], quality=e["quality"],
                confidence=e["confidence"],
            )
            for e in raw_events
        ]

        # Validação + correção
        progress(75, "Validando e corrigindo harmonia...")
        music.chords = merge_chord_family(music.chords)   # D/D7, Bm/Bm7... antes
        music = await asyncio.get_event_loop().run_in_executor(
            None, run_pipeline, music
        )
        music.chords = merge_chord_family(music.chords)   # e depois das correções

        # Letra
        progress(85, "Buscando letra sincronizada...")
        if title:
            lyrics = await fetch_lrclib(title, artist, music_duration)
            if lyrics:
                music.lyrics = lyrics

        # Onde a música começa na gravação original (para o relatório)
        music.music_start = round(m_start, 1)

        progress(100, "Concluído!")
        task["music"]  = music
        task["status"] = TaskStatus.DONE

    except Exception as exc:
        task["status"] = TaskStatus.ERROR
        task["error"]  = str(exc)
        task["message"] = f"Erro: {exc}"
    finally:
        # Remove arquivo temporário
        try:
            os.remove(audio_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/tasks", status_code=201)
async def create_task(
    title:  str = "",
    artist: str = "",
):
    """Cria uma nova tarefa. Retorna task_id para upload do áudio."""
    task_id = str(uuid.uuid4())[:8]
    _new_task(task_id)
    _tasks[task_id]["title"]  = title
    _tasks[task_id]["artist"] = artist
    return {"task_id": task_id}


@app.post("/tasks/{task_id}/audio")
async def upload_audio(
    task_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Recebe o arquivo de áudio e inicia o processamento."""
    task = _get_task(task_id)
    if task["status"] != TaskStatus.QUEUED:
        raise HTTPException(status_code=400,
                            detail="Tarefa já em processamento ou concluída.")

    # Valida extensão
    fname = file.filename or "audio.tmp"
    ext   = os.path.splitext(fname)[1].lower()
    if ext not in SUPPORTED:
        raise HTTPException(status_code=422,
                            detail=f"Formato não suportado: {ext}")

    # Salva arquivo
    dest = os.path.join(_UPLOADS, f"{task_id}{ext}")
    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    title  = task.get("title", "")
    artist = task.get("artist", "")
    background_tasks.add_task(_process, task_id, dest, title, artist)

    return {"task_id": task_id, "status": "processing"}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Status e progresso de uma tarefa."""
    task = _get_task(task_id)
    resp = {
        "task_id":  task["id"],
        "status":   task["status"],
        "progress": task["progress"],
        "message":  task["message"],
    }
    if task.get("error"):
        resp["error"] = task["error"]
    if task.get("music"):
        m = task["music"]
        resp["summary"] = {
            "title":           m.title,
            "artist":          m.artist,
            "duration":        m.duration,
            "key":             m.key,
            "tempo":           m.tempo,
            "n_chords":        len(m.chords),
            "n_lyrics":        len(m.lyrics),
            "pipeline_status": m.pipeline_status,
        }
    return resp


@app.get("/tasks/{task_id}/result")
async def get_result(task_id: str):
    """Retorna os dados completos da música em JSON."""
    task = _get_task(task_id)
    if task["status"] != TaskStatus.DONE:
        raise HTTPException(status_code=400,
                            detail="Processamento ainda não concluído.")
    m = task["music"]
    return {
        "title":    m.title,
        "artist":   m.artist,
        "duration": m.duration,
        "key":      m.key,
        "tempo":    m.tempo,
        "music_start": getattr(m, "music_start", 0.0),
        "pipeline_status": m.pipeline_status,
        "chords": [
            {
                "start":      c.start,
                "end":        c.end,
                "chord":      c.chord_name(),
                "confidence": c.confidence,
                "uncertain":  c.uncertain,
            }
            for c in m.chords
        ],
        "lyrics": [
            {"t": l.t, "text": l.text}
            for l in m.lyrics
        ],
        "corrections": [
            {"t": c.t, "original": c.original,
             "corrected": c.corrected, "reason": c.reason}
            for c in m.corrections
        ],
    }


@app.post("/tasks/{task_id}/lyrics")
async def search_lyrics(task_id: str, title: str = "", artist: str = ""):
    """Busca a letra pelo nome digitado pelo usuário e a associa à música."""
    task = _get_task(task_id)
    if task["status"] != TaskStatus.DONE:
        raise HTTPException(status_code=400,
                            detail="Processamento ainda não concluído.")
    title, artist = title.strip(), artist.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Escreva o nome da música.")
    m = task["music"]
    errors: list[str] = []
    lyrics = await fetch_lrclib(title, artist, m.duration, errors)
    if not lyrics:
        if errors:
            raise HTTPException(
                status_code=502,
                detail="Não consegui acessar o site de letras (LRCLIB). "
                       "Verifique a internet e tente de novo. "
                       f"Detalhe: {errors[0]}")
        raise HTTPException(
            status_code=404,
            detail=f"Não encontrei a letra de \"{title}\""
                   + (f" de {artist}" if artist else "")
                   + ". Confira a grafia ou tente só o nome da música.")
    m.lyrics = lyrics
    m.title  = title
    if artist:
        m.artist = artist
    return {"found": True, "n_lines": len(lyrics),
            "title": m.title, "artist": m.artist}


@app.get("/tasks/{task_id}/export/txt",
         response_class=PlainTextResponse)
async def export_task_txt(
    task_id:   str,
    transpose: int = 0,
    flats:     bool = False,
    simplify:  bool = False,
    capo:      int = 0,
    lyrics_offset: float = 0.0,
):
    """Exporta a cifra em formato TXT. capo = casa do capotraste (0–11);
    lyrics_offset = ajuste da letra em segundos (−60 a 60)."""
    task = _get_task(task_id)
    if task["status"] != TaskStatus.DONE:
        raise HTTPException(status_code=400,
                            detail="Processamento ainda não concluído.")
    return export_txt(task["music"], transpose=transpose, flats=flats,
                      simplify=simplify, capo=max(0, min(11, capo)),
                      lyrics_offset=max(-60.0, min(60.0, lyrics_offset)))


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str):
    """Remove uma tarefa da memória."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    del _tasks[task_id]


@app.get("/tasks")
async def list_tasks():
    """Lista todas as tarefas ativas."""
    return [
        {
            "task_id": t["id"],
            "status":  t["status"],
            "title":   t.get("title", ""),
            "created": t["created"],
        }
        for t in _tasks.values()
    ]


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("local_engine.api.main:app",
                host="127.0.0.1", port=8000, reload=False)
