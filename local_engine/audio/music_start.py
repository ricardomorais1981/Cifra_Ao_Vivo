"""
Detecção do início (e do fim) da música dentro de uma gravação.

Serve para ignorar o que vem antes da música de verdade — o silêncio entre
clicar em "Gravar" e dar play, ou uma fala/abertura de vídeo — para que os
tempos dos acordes batam com os tempos da letra sincronizada (LRCLIB), que
começam no início da faixa.

Critérios, por bloco de 0,5 s:
  - silêncio: energia muito abaixo do volume típico da gravação;
  - continuidade: música quase não tem pausas; fala tem pausas entre palavras;
  - estabilidade tonal: música sustenta notas/acordes (o "chroma" muda pouco
    de um bloco para o outro); na fala a altura varia o tempo todo.
O início é o primeiro ponto a partir do qual os próximos ~6 s são, em sua
maioria, música. Usa só numpy/scipy.
"""

from __future__ import annotations
import numpy as np
from scipy.signal import stft

BLOCK_S        = 0.5     # tamanho do bloco de decisão
LOOKAHEAD_S    = 6.0     # janela que precisa ser "música" a partir do início
MUSIC_FRACTION = 0.8     # fração mínima de blocos de música nessa janela
MAX_START_S    = 90.0    # não procura início depois disto
SILENCE_DB     = -40.0   # relativo ao volume típico (percentil 90) da gravação


def _features(y: np.ndarray, sr: int):
    n_fft, hop = 2048, 512
    f, _, Z = stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop,
                   boundary=None, padded=False)
    P = np.abs(Z) ** 2                                   # (freq, frames)
    frame_db = 10 * np.log10(P.sum(axis=0) + 1e-12)

    # chroma simples: bins de 80 Hz a 2 kHz somados por classe de altura
    sel = (f >= 80) & (f <= 2000)
    pc = (np.round(12 * np.log2(f[sel] / 440.0)) % 12).astype(int)
    chroma = np.zeros((12, P.shape[1]))
    np.add.at(chroma, pc, np.sqrt(P[sel]))
    return frame_db, chroma, hop / sr


def _block_flags(y: np.ndarray, sr: int):
    """Para cada bloco de 0,5 s: (é_silêncio, é_música)."""
    frame_db, chroma, fdur = _features(y, sr)
    per_block = max(1, int(round(BLOCK_S / fdur)))
    n_blocks = len(frame_db) // per_block
    if n_blocks < 2:
        return np.zeros(0, bool), np.zeros(0, bool), np.zeros(0, bool)
    ref = np.percentile(frame_db, 90)

    silent = np.zeros(n_blocks, bool)
    cont   = np.zeros(n_blocks)
    chroma_b = np.zeros((n_blocks, 12))
    for b in range(n_blocks):
        sl = slice(b * per_block, (b + 1) * per_block)
        db = frame_db[sl]
        silent[b] = np.median(db) < ref + SILENCE_DB
        # continuidade: fração de frames a menos de 20 dB do máximo do bloco
        cont[b] = np.mean(db > db.max() - 20)
        c = chroma[:, sl].mean(axis=1)
        chroma_b[b] = c / (np.linalg.norm(c) + 1e-12)

    # estabilidade tonal: semelhança com o bloco anterior e o seguinte
    # (vizinho em silêncio não conta: senão o 1º bloco da música é penalizado)
    sim = np.einsum("ij,ij->i", chroma_b[1:], chroma_b[:-1])
    sim[silent[1:] | silent[:-1]] = 0.0
    stab = np.empty(n_blocks)
    stab[0], stab[-1] = sim[0], sim[-1]
    stab[1:-1] = np.maximum(sim[1:], sim[:-1])

    continuous = (~silent) & (cont >= 0.85)
    music = continuous & (stab >= 0.80)
    return silent, music, continuous


def detect_music_bounds(y: np.ndarray, sr: int) -> tuple[float, float]:
    """
    Retorna (início, fim) da música em segundos.
    Na dúvida, devolve (0, duração) — nunca corta música por engano de forma
    agressiva: o início só avança se o trecho seguinte for claramente música.
    """
    dur = len(y) / sr
    silent, music, continuous = _block_flags(y, sr)
    if len(music) == 0:
        return 0.0, dur

    look = int(LOOKAHEAD_S / BLOCK_S)
    max_b = min(len(music) - 1, int(MAX_START_S / BLOCK_S))
    start_b = 0
    found = False
    for b in range(0, max_b + 1):
        if silent[b]:
            continue
        window = music[b:b + look]
        if len(window) and window.mean() >= MUSIC_FRACTION and music[b]:
            start_b, found = b, True
            break
    if found:
        # recua enquanto o som continuar contínuo (sem as pausas da fala):
        # o início real costuma vir 1–2 blocos antes do primeiro bloco "estável"
        while start_b > 0 and continuous[start_b - 1]:
            start_b -= 1
    else:
        # não achou um início claro: corta só o silêncio inicial
        nz = np.flatnonzero(~silent)
        start_b = int(nz[0]) if len(nz) else 0

    nz = np.flatnonzero(~silent)
    end_b = int(nz[-1]) + 1 if len(nz) else len(silent)
    start = start_b * BLOCK_S
    end = min(dur, end_b * BLOCK_S)
    if end - start < 10:          # algo deu errado: não mexe
        return 0.0, dur
    return start, end
