"""
Validação e carregamento de arquivos de áudio.
Suporta: wav, flac, ogg, aiff, mp3, aac, m4a, opus, webm, wma
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

SUPPORTED = {".wav", ".flac", ".ogg", ".aiff", ".aif",
             ".mp3", ".aac", ".m4a", ".opus", ".webm", ".wma"}

MAX_SIZE_MB    = 500
MIN_DURATION   = 5.0
MAX_DURATION   = 3600.0
TARGET_SR      = 22050


@dataclass
class AudioInfo:
    path: str
    size_mb: float
    extension: str


@dataclass
class PreparedAudio:
    y: np.ndarray        # mono float32 normalizado
    sr: int
    duration: float
    info: AudioInfo


def validate_file(path: str) -> AudioInfo:
    """Valida extensão e tamanho do arquivo."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Formato não suportado: '{ext}'. "
                         f"Use: {', '.join(sorted(SUPPORTED))}")

    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise ValueError(f"Arquivo muito grande ({size_mb:.1f} MB). Limite: {MAX_SIZE_MB} MB")

    return AudioInfo(path=path, size_mb=size_mb, extension=ext)


def load_audio(path: str, target_sr: int = TARGET_SR) -> PreparedAudio:
    """
    Carrega o áudio, converte para mono float32 normalizado.
    Aceita qualquer formato suportado via soundfile + fallback ffmpeg/librosa.
    """
    info = validate_file(path)

    try:
        import soundfile as sf
        y, sr = sf.read(path, dtype="float32", always_2d=True)
        y = y.mean(axis=1)  # estéreo → mono
    except Exception:
        # fallback: librosa usa ffmpeg para mp3/aac/m4a etc.
        import librosa
        y, sr = librosa.load(path, sr=None, mono=True)

    # Resample
    if sr != target_sr:
        import librosa
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        sr = target_sr

    # Normalização peak
    peak = np.abs(y).max()
    if peak > 1e-6:
        y = y / peak

    duration = len(y) / sr
    if duration < MIN_DURATION:
        raise ValueError(f"Áudio muito curto ({duration:.1f}s). Mínimo: {MIN_DURATION}s")
    if duration > MAX_DURATION:
        raise ValueError(f"Áudio muito longo ({duration:.1f}s). Máximo: {MAX_DURATION/3600:.0f}h")

    return PreparedAudio(y=y, sr=sr, duration=duration, info=info)


def estimate_tempo(y: np.ndarray, sr: int) -> float:
    """Estima BPM via librosa beat tracker."""
    try:
        import librosa
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return float(np.atleast_1d(tempo)[0])
    except Exception:
        return 0.0
